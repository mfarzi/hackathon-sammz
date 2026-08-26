"""Adversarial review panel: five blind reviewers, one master, two rounds.

Round 1  Five lens agents review the target independently and in parallel. No
         agent sees another's findings, so their errors stay uncorrelated.
Master   Deduplicates and ranks the candidates. Decides nothing about truth.
Round 2  Every candidate is attacked by reviewers who did not raise it, each
         asked to refute rather than to discuss, and each still blind to the
         other verdicts.
Report   Survivors are reported with the dissent attached, killed findings are
         shown rather than hidden, and anything that could not be verified is
         labelled as such instead of being counted as agreement.

The panel never converges by discussion. Showing round-1 results back to all
five and asking them to agree would correlate their judgements and turn
consensus into a measure of contagion rather than of correctness.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flwr.agentapp import AgentApp, AgentSession
from flwr.app import Context

from .lenses import LENSES, LENSES_BY_KEY, Lens, refute_instructions, review_instructions
from .model import FINDINGS_SCHEMA, VERDICT_SCHEMA, build_client, json_call

APP_ROOT = Path(__file__).resolve().parent.parent

# Keep the reviewed source well inside a single model context. Truncation is
# reported rather than applied silently.
MAX_SOURCE_CHARS = 40_000
SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}
_STOPWORDS = frozenset(
    "a an the is are was were be been of in on to for with and or not this that "
    "it its if then than when where which who whom can could may might will "
    "would should does do did has have had".split()
)

app = AgentApp()


@dataclass
class Finding:
    """A candidate defect raised in round 1."""

    title: str
    file: str
    line: int
    severity: str
    claim: str
    failure_scenario: str
    confidence: float
    raised_by: list[str] = field(default_factory=list)
    verdicts: list[dict[str, Any]] = field(default_factory=list)
    min_votes: int = 2

    @property
    def votes_cast(self) -> int:
        return len(self.verdicts)

    @property
    def refuted_count(self) -> int:
        return sum(1 for v in self.verdicts if v["refuted"])

    @property
    def status(self) -> str:
        """Survivor, killed, or unverified - never silently a survivor.

        A finding needs `min_votes` verdicts before survival means anything. One
        upheld vote, after two refuters failed, is thin evidence and must not be
        presented as having withstood the panel.
        """
        if self.votes_cast < self.min_votes:
            return "unverified"
        majority = self.votes_cast // 2 + 1
        return "killed" if self.refuted_count >= majority else "survivor"


def _config_str(context: Context, key: str, default: str) -> str:
    value = context.run_config.get(key, default)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _config_int(context: Context, key: str, default: int) -> int:
    value = context.run_config.get(key, default)
    return int(value) if isinstance(value, (int, float)) else default


def _load_source(target: str) -> tuple[str, list[str], bool]:
    """Return line-numbered source, the files included, and whether it was cut."""
    root = (APP_ROOT / target).resolve()
    if not str(root).startswith(str(APP_ROOT)):
        raise ValueError(f"panel.target must stay inside the app: {target!r}")
    if not root.exists():
        raise ValueError(f"panel.target does not exist: {target!r}")

    paths = sorted(root.rglob("*.py")) if root.is_dir() else [root]
    if not paths:
        raise ValueError(f"No Python files found under {target!r}")

    blocks: list[str] = []
    names: list[str] = []
    total = 0
    truncated = False
    for path in paths:
        rel = path.relative_to(APP_ROOT).as_posix()
        body = path.read_text(encoding="utf-8")
        numbered = "\n".join(
            f"{n:4d} | {line}" for n, line in enumerate(body.splitlines(), start=1)
        )
        block = f"--- {rel} ---\n{numbered}"
        if total + len(block) > MAX_SOURCE_CHARS:
            truncated = True
            break
        blocks.append(block)
        names.append(rel)
        total += len(block)

    return "\n\n".join(blocks), names, truncated


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]{3,}", text.lower()) if t not in _STOPWORDS}


def _overlap(a: str, b: str) -> float:
    """Jaccard overlap of the significant words in two strings."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _same_defect(a: Finding, b: Finding) -> bool:
    """Two findings describe one defect if they agree on location and substance.

    Two lenses describing the same defect rarely phrase the claim alike - one
    says "errors leak across calls", the other "errors persist across calls" -
    so a title match counts as well. Missing a duplicate is expensive: it spends
    a second refutation budget on one defect and reports it twice.
    """
    if a.file != b.file or abs(a.line - b.line) > 2:
        return False
    # A single line is usually a single statement, so two findings pinned to the
    # exact same line are the same defect however differently they are worded.
    # Wording similarity is too weak to catch these on its own: "stale errors
    # persist" and "validation state grows without bound" share one word.
    if a.line == b.line:
        return True
    return _overlap(a.claim, b.claim) >= 0.35 or _overlap(a.title, b.title) >= 0.5


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Merge duplicate reports, recording every lens that raised each defect.

    Independent agreement is evidence, so a defect raised by three lenses keeps
    all three names - but agreement here is genuine, because round 1 was blind.
    """
    merged: list[Finding] = []
    for finding in findings:
        for existing in merged:
            if _same_defect(existing, finding):
                existing.raised_by.extend(finding.raised_by)
                if SEVERITY_RANK.get(finding.severity, 0) > SEVERITY_RANK.get(
                    existing.severity, 0
                ):
                    existing.severity = finding.severity
                existing.confidence = max(existing.confidence, finding.confidence)
                break
        else:
            merged.append(finding)
    return merged


def _review(client: Any, model: str, lens: Lens, source: str, focus: str, cap: int):
    """One blind round-1 review. Returns findings, or an error string."""
    prompt = f"Review the following code.\n\n{source}"
    if focus:
        prompt += f"\n\nThe requester added this focus, honour it within your mandate:\n{focus}"
    try:
        payload = json_call(
            client,
            model=model,
            instructions=review_instructions(lens, cap),
            prompt=prompt,
            schema_name="panel_findings",
            schema=FINDINGS_SCHEMA,
        )
    except Exception as err:  # noqa: BLE001 - one lens failing must not end the run
        return lens, None, f"{type(err).__name__}: {err}"

    findings = []
    for raw in (payload.get("findings") or [])[:cap]:
        try:
            findings.append(
                Finding(
                    title=str(raw["title"]),
                    file=str(raw["file"]),
                    line=int(raw["line"]),
                    severity=str(raw["severity"]).lower(),
                    claim=str(raw["claim"]),
                    failure_scenario=str(raw["failure_scenario"]),
                    confidence=float(raw["confidence"]),
                    raised_by=[lens.key],
                )
            )
        except (KeyError, TypeError, ValueError):
            continue  # Malformed finding, not a malformed reviewer.
    return lens, findings, None


def _refute(client: Any, model: str, lens: Lens, source: str, finding: Finding):
    """One blind adversarial verdict on one finding."""
    prompt = (
        f"Finding to refute\n"
        f"  raised by: {', '.join(finding.raised_by)} reviewer\n"
        f"  location: {finding.file}:{finding.line}\n"
        f"  severity claimed: {finding.severity}\n"
        f"  claim: {finding.claim}\n"
        f"  failure scenario: {finding.failure_scenario}\n\n"
        f"The code under review\n\n{source}"
    )
    try:
        payload = json_call(
            client,
            model=model,
            instructions=refute_instructions(lens),
            prompt=prompt,
            schema_name="panel_verdict",
            schema=VERDICT_SCHEMA,
        )
        return finding, {
            "lens": lens.key,
            "refuted": bool(payload["refuted"]),
            "reasoning": str(payload.get("reasoning", "")),
            "confidence": float(payload.get("confidence", 0.0)),
        }
    except Exception as err:  # noqa: BLE001
        # No vote is recorded. A verifier that crashed did not agree.
        print(f"[panel] refuter {lens.key} failed on {finding.title}: {err}")
        return finding, None


def _make_canary() -> Finding:
    """A finding that is deliberately false, used to calibrate the refuters.

    A panel that never rejects anything is indistinguishable from a rubber
    stamp, and "it survived refutation" then carries no information. So one
    known-false finding rides through round 2 alongside the real candidates.
    Its claim is checkable against the code and wrong: `subtotal_pence`
    multiplies once, not twice.

    If the canary survives, the refuters are not actually refuting, and the
    report says so instead of presenting the other verdicts as trustworthy.
    """
    return Finding(
        title="Line items are double-charged",
        file="fixtures/buggy_cart/cart.py",
        line=20,
        severity="critical",
        claim=(
            "subtotal_pence multiplies price_pence by quantity twice, so every "
            "line item is charged at double its true amount."
        ),
        failure_scenario=(
            "A single item priced at 500 pence with quantity 2 contributes "
            "2000 pence to the subtotal instead of 1000."
        ),
        confidence=0.9,
        raised_by=["canary"],
    )


def _assign_refuters(finding: Finding, index: int, count: int) -> list[Lens]:
    """Pick refuters that did not raise the finding, rotating to spread load."""
    eligible = [lens for lens in LENSES if lens.key not in finding.raised_by]
    if not eligible:
        eligible = list(LENSES)
    offset = index % len(eligible)
    rotated = eligible[offset:] + eligible[:offset]
    return rotated[: min(count, len(rotated))]


@app.main()
def main(agent: AgentSession, context: Context) -> None:
    """Run the two-round adversarial panel over the configured target."""
    focus = _config_str(context, "agent.input", "")
    target = _config_str(context, "panel.target", "fixtures/buggy_cart")
    model = _config_str(context, "panel.model", "openai/gpt-5.6-sol")
    per_lens = _config_int(context, "panel.max-findings-per-lens", 4)
    max_candidates = _config_int(context, "panel.max-candidates", 8)
    refuters = _config_int(context, "panel.refuters-per-finding", 3)
    min_votes = min(_config_int(context, "panel.min-votes", 2), refuters)

    source, files, truncated = _load_source(target)
    client = build_client()

    agent.events.emit(
        {
            "type": "panel.started",
            "target": target,
            "files": files,
            "lenses": [lens.key for lens in LENSES],
            "model": model,
            "source_truncated": truncated,
        }
    )
    print(f"[panel] reviewing {len(files)} file(s) under {target} with {len(LENSES)} lenses")
    if truncated:
        print(f"[panel] source exceeded {MAX_SOURCE_CHARS} chars; later files were dropped")

    # --- Round 1: five blind reviews, in parallel ---------------------------
    candidates: list[Finding] = []
    failed_lenses: list[str] = []
    with ThreadPoolExecutor(max_workers=len(LENSES)) as pool:
        futures = [
            pool.submit(_review, client, model, lens, source, focus, per_lens)
            for lens in LENSES
        ]
        for future in as_completed(futures):
            lens, findings, error = future.result()
            if error is not None:
                failed_lenses.append(lens.key)
                print(f"[panel] lens {lens.key} failed: {error}")
                agent.events.emit(
                    {"type": "panel.lens.failed", "lens": lens.key, "error": error}
                )
                continue
            candidates.extend(findings or [])
            print(f"[panel] lens {lens.key} raised {len(findings or [])} finding(s)")
            agent.events.emit(
                {
                    "type": "panel.lens.completed",
                    "lens": lens.key,
                    "count": len(findings or []),
                    "titles": [f.title for f in (findings or [])],
                }
            )

    raw_count = len(candidates)
    candidates = _dedupe(candidates)
    candidates.sort(
        key=lambda f: (
            SEVERITY_RANK.get(f.severity, 0),
            len(f.raised_by),
            f.confidence,
        ),
        reverse=True,
    )
    dropped = max(0, len(candidates) - max_candidates)
    if dropped:
        # Never truncate silently: a capped panel that reports "all clear" is lying.
        print(f"[panel] {dropped} lower-ranked candidate(s) dropped by panel.max-candidates")
    candidates = candidates[:max_candidates]

    agent.events.emit(
        {
            "type": "panel.round1.completed",
            "raised": raw_count,
            "after_dedup": raw_count and len(candidates) + dropped,
            "verifying": len(candidates),
            "dropped_by_cap": dropped,
            "failed_lenses": failed_lenses,
        }
    )

    # --- Round 2: adversarial refutation, in parallel ----------------------
    # The canary rides along with the real candidates and is indistinguishable
    # from them to the refuters. It only makes sense when the code its claim
    # refers to is actually under review.
    for finding in candidates:
        finding.min_votes = min_votes

    canary = _make_canary()
    canary.min_votes = min_votes
    canary_enabled = (
        context.run_config.get("panel.canary", True) is not False
        and canary.file in files
    )
    to_verify = candidates + ([canary] if canary_enabled else [])
    if not canary_enabled:
        print("[panel] calibration probe skipped: not applicable to this target")

    jobs = [
        (finding, lens)
        for index, finding in enumerate(to_verify)
        for lens in _assign_refuters(finding, index, refuters)
    ]
    print(f"[panel] round 2: {len(jobs)} refutation attempt(s) across {len(candidates)} candidate(s)")

    if jobs:
        with ThreadPoolExecutor(max_workers=min(10, len(jobs))) as pool:
            futures = [
                pool.submit(_refute, client, model, lens, source, finding)
                for finding, lens in jobs
            ]
            for future in as_completed(futures):
                finding, verdict = future.result()
                if verdict is None:
                    continue
                finding.verdicts.append(verdict)
                agent.events.emit(
                    {
                        "type": "panel.verdict",
                        "finding": finding.title,
                        "lens": verdict["lens"],
                        "refuted": verdict["refuted"],
                        "reasoning": verdict["reasoning"],
                    }
                )

    survivors = [f for f in candidates if f.status == "survivor"]
    killed = [f for f in candidates if f.status == "killed"]
    unverified = [f for f in candidates if f.status == "unverified"]

    calibration = None
    if canary_enabled:
        calibration = {
            "status": canary.status,
            "refuted": canary.refuted_count,
            "votes": canary.votes_cast,
            "passed": canary.status == "killed",
        }
        verdict = "caught" if calibration["passed"] else "MISSED"
        print(
            f"[panel] calibration probe {verdict}: planted false finding "
            f"{canary.refuted_count}/{canary.votes_cast} refuted"
        )
        agent.events.emit({"type": "panel.calibration", **calibration})

    for finding in candidates:
        print(
            f"[panel] {finding.status:10s} {finding.file}:{finding.line} "
            f"{finding.title} ({finding.refuted_count}/{finding.votes_cast} refuted)"
        )

    agent.events.emit(
        {
            "type": "panel.round2.completed",
            "survivors": len(survivors),
            "killed": len(killed),
            "unverified": len(unverified),
        }
    )

    # --- Master's report: the only streamed, human-facing output ------------
    _stream_report(
        agent,
        client,
        model=model,
        target=target,
        files=files,
        survivors=survivors,
        killed=killed,
        unverified=unverified,
        dropped=dropped,
        failed_lenses=failed_lenses,
        truncated=truncated,
        calibration=calibration,
    )


def _describe(findings: list[Finding]) -> str:
    if not findings:
        return "  (none)"
    lines = []
    for f in findings:
        lines.append(
            f"  - {f.title} [{f.severity}] {f.file}:{f.line}\n"
            f"    raised by: {', '.join(sorted(set(f.raised_by)))}\n"
            f"    claim: {f.claim}\n"
            f"    scenario: {f.failure_scenario}\n"
            f"    votes: {f.refuted_count} of {f.votes_cast} refuted"
        )
        for v in f.verdicts:
            stance = "refuted" if v["refuted"] else "upheld"
            lines.append(f"      {v['lens']} ({stance}): {v['reasoning']}")
    return "\n".join(lines)


def _stream_report(
    agent: AgentSession,
    client: Any,
    *,
    model: str,
    target: str,
    files: list[str],
    survivors: list[Finding],
    killed: list[Finding],
    unverified: list[Finding],
    dropped: int,
    failed_lenses: list[str],
    truncated: bool,
    calibration: dict[str, Any] | None,
) -> None:
    """Have the master write the report, streaming it to the chat frontend."""
    caveats = []
    if calibration is not None and not calibration["passed"]:
        caveats.append(
            "CALIBRATION FAILURE: a planted false finding was NOT rejected by the "
            f"panel ({calibration['refuted']} of {calibration['votes']} refuted). "
            "The refuters are not reliably refuting, so surviving findings below "
            "carry much weaker evidence than survival normally implies."
        )
    elif calibration is not None:
        caveats.append(
            "Calibration passed: a planted false finding was correctly rejected "
            f"({calibration['refuted']} of {calibration['votes']} refuted)."
        )
    if failed_lenses:
        caveats.append(f"These reviewers failed and cast no findings: {', '.join(failed_lenses)}.")
    if dropped:
        caveats.append(f"{dropped} lower-ranked candidate(s) were never verified, due to the candidate cap.")
    if truncated:
        caveats.append("The source was truncated, so later files went unreviewed.")
    if unverified:
        caveats.append(
            f"{len(unverified)} finding(s) drew too few verdicts to judge and are "
            "listed as unverified rather than counted either way."
        )

    prompt = (
        f"Target reviewed: {target} ({len(files)} file(s): {', '.join(files)})\n\n"
        f"SURVIVED refutation:\n{_describe(survivors)}\n\n"
        f"KILLED by refutation:\n{_describe(killed)}\n\n"
        f"UNVERIFIED (no verdict returned):\n{_describe(unverified)}\n\n"
        f"Process caveats: {' '.join(caveats) if caveats else 'none'}"
    )

    instructions = (
        "You are the master of a code review panel, writing the final report for a "
        "human engineer.\n\n"
        "Structure it as markdown:\n"
        "1. A one-line verdict: how many findings survived adversarial refutation.\n"
        "2. `## Confirmed findings` - each survivor with its location, why it is "
        "real, and the concrete failure scenario. Where a verifier upheld it with "
        "a caveat, keep the caveat. If a survivor drew a dissenting vote, say so; "
        "do not present a split verdict as unanimous.\n"
        "3. `## Rejected by the panel` - what was raised and why the refuters "
        "killed it. Keep this section: showing what did not survive is what makes "
        "the surviving findings worth trusting.\n"
        "4. `## Coverage and limits` - state the process caveats verbatim if there "
        "are any, or say coverage was complete if there are none. If a caveat "
        "reports a calibration failure, lead this section with it and say plainly "
        "that the panel's verdicts should not be trusted on this run.\n\n"
        "Report only what the panel data supports. Do not add findings of your own, "
        "do not upgrade a killed finding, and do not soften a survivor. If nothing "
        "survived, say so plainly - an empty result is a real result."
    )

    stream = client.responses.create(
        model=model,
        instructions=instructions,
        input=prompt,
        stream=True,
    )

    chunks: list[str] = []
    for event in stream:
        agent.events.emit(event.to_dict())
        if event.type in {"error", "response.failed"}:
            raise RuntimeError(f"Master report failed: {event}")
        if event.type == "response.output_text.delta":
            chunks.append(event.delta)

    print("".join(chunks))
