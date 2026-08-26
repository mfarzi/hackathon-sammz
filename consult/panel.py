"""The adversarial diagnostic panel: five blind lenses, two rounds.

Round 1  Five lens agents assess the network's candidates independently and in
         parallel. No agent sees another's assessment, so their errors stay
         uncorrelated.
Round 2  Every candidate raised is attacked by lenses that did not raise it,
         each asked to refute rather than to discuss, each still blind to the
         other verdicts.

The panel never converges by discussion. Showing round-1 assessments back to all
five and asking them to agree would correlate their judgements and turn
consensus into a measure of contagion rather than of correctness - which matters
more here than in code review, because anchoring on the first plausible
diagnosis is the classic way a differential goes wrong.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from review_panel.model import VERDICT_SCHEMA, json_call

from .lenses import LENSES, Lens, assess_instructions, refute_instructions
from .schemas import ASSESSMENT_SCHEMA
from .scoring import DiseaseEvidence


@dataclass
class Candidate:
    """One candidate diagnosis raised in round 1."""

    disease: str
    claim: str
    reasoning: str
    confidence: float
    raised_by: list[str] = field(default_factory=list)
    verdicts: list[dict[str, Any]] = field(default_factory=list)
    min_votes: int = 2
    is_canary: bool = False

    @property
    def votes_cast(self) -> int:
        return len(self.verdicts)

    @property
    def refuted_count(self) -> int:
        return sum(1 for v in self.verdicts if v["refuted"])

    @property
    def status(self) -> str:
        """Survivor, killed, or unverified - never silently a survivor.

        A candidate needs `min_votes` verdicts before survival means anything.
        One upheld vote, after two refuters failed, is thin evidence and must not
        be presented as having withstood the panel.
        """
        if self.votes_cast < self.min_votes:
            return "unverified"
        majority = self.votes_cast // 2 + 1
        return "killed" if self.refuted_count >= majority else "survivor"


def format_query(query: dict[str, Any]) -> str:
    """Render the patient's presentation for a prompt."""
    parts = [f"  symptoms: {', '.join(query.get('symptoms') or []) or 'none given'}"]
    if query.get("gender"):
        parts.append(f"  sex: {query['gender']}")
    if query.get("age_bracket"):
        parts.append(f"  age bracket: {query['age_bracket']}")
    if query.get("summary"):
        parts.append(f"  presentation: {query['summary']}")
    return "\n".join(parts)


def format_evidence(
    evidence: list[DiseaseEvidence], followups: list[dict[str, Any]] | None = None
) -> str:
    """Render what the network reported, for a prompt.

    Scores and case counts are labelled so a lens cannot mistake one for the
    other: the count is provenance and must not be read as strength.
    """
    if not evidence:
        return "  (no site reported a comparable case)"

    blocks = []
    for ev in evidence:
        lines = [
            f"  - {ev.disease}",
            f"      similarity: {ev.score:.3f} (mean of the network's best matches)",
            f"      provenance: {ev.case_count} case(s) across {len(ev.sites)} site(s)"
            f" - {', '.join(ev.sites)}. Case count is provenance, NOT strength.",
        ]
        if ev.shared_symptoms:
            lines.append(f"      shared symptoms: {', '.join(ev.shared_symptoms)}")
        if ev.absent_symptoms:
            lines.append(
                f"      patient symptoms NOT seen in these cases: {', '.join(ev.absent_symptoms)}"
            )
        for abstraction in ev.abstractions:
            site = abstraction.get("site", "a site")
            lines.append(f"      {site} reports: {abstraction.get('pattern', '')}")
            for item in abstraction.get("supporting") or []:
                lines.append(f"        supports: {item}")
            for item in abstraction.get("arguing_against") or []:
                lines.append(f"        argues against: {item}")
        blocks.append("\n".join(lines))

    rendered = "\n".join(blocks)

    if followups:
        answers = ["\n  Follow-up asked of specific sites after the first round:"]
        for f in followups:
            answers.append(f"    Q ({f.get('target_disease', '?')}): {f.get('question', '')}")
            for a in f.get("answers") or []:
                mark = "" if a.get("has_evidence") else " [no evidence at this site]"
                answers.append(f"      {a.get('site', '?')}{mark}: {a.get('answer', '')}")
        rendered += "\n" + "\n".join(answers)

    return rendered


# Plausible-sounding conditions used to build the calibration probe. The one
# chosen is asserted to have network support it demonstrably does not have, so a
# refuter that checks the evidence can see it is unsupported.
_CANARY_POOL = (
    "fabry_disease",
    "erdheim_chester_disease",
    "pompe_disease",
    "castleman_disease",
    "susac_syndrome",
)


def make_canary(evidence: list[DiseaseEvidence], min_votes: int) -> Candidate | None:
    """Build a known-false candidate to calibrate the refuters.

    A panel that never rejects anything is indistinguishable from a rubber stamp,
    and "it survived the panel" then carries no information. So one candidate
    rides through round 2 whose claim is checkable against the evidence and
    wrong: it asserts multi-site support for a disease no site reported at all.

    If the canary survives, the refuters are not actually refuting, and the
    report says so instead of presenting the other verdicts as trustworthy.
    """
    present = {ev.disease for ev in evidence}
    for disease in _CANARY_POOL:
        if disease not in present:
            return Candidate(
                disease=disease,
                claim=(
                    f"{disease} is the strongest candidate, independently corroborated "
                    "by several sites with high symptom overlap."
                ),
                reasoning=(
                    "Multiple hospitals returned closely matching cases of this "
                    "condition, and their descriptions agree with the presentation."
                ),
                confidence=0.9,
                raised_by=["canary"],
                min_votes=min_votes,
                is_canary=True,
            )
    return None


def assign_refuters(candidate: Candidate, index: int, count: int) -> list[Lens]:
    """Pick refuters that did not raise the candidate, rotating to spread load.

    Prefers lenses with no stake in the candidate, but always returns `count` of
    them, topping up from the lenses that raised it when too few are left over.

    That top-up is not a nicety. Without it, the more lenses independently agree
    on a candidate, the fewer refuters remain eligible, the fewer verdicts it
    draws - and a candidate raised by four of five lenses lands below `min_votes`
    and is reported as unverified. The best-corroborated finding would be the one
    the panel scrutinises least and then declines to stand behind, which inverts
    the whole point of running the first round blind. A lens attacking its own
    claim is a weaker check than a disinterested one; it is a far better one than
    no check at all.
    """
    disinterested = [lens for lens in LENSES if lens.key not in candidate.raised_by]
    raisers = [lens for lens in LENSES if lens.key in candidate.raised_by]

    if disinterested:
        offset = index % len(disinterested)
        ordered = disinterested[offset:] + disinterested[:offset]
    else:
        ordered = []

    if len(ordered) < count and raisers:
        offset = index % len(raisers)
        ordered = ordered + raisers[offset:] + raisers[:offset]

    return ordered[:count]


def _assess(client, model, lens, query_block, evidence_block, cap):
    """One blind round-1 assessment. Returns candidates, or an error string."""
    prompt = (
        f"The patient\n{query_block}\n\n"
        f"What the hospital network reported\n{evidence_block}\n\n"
        "Assess these candidates within your mandate."
    )
    try:
        payload = json_call(
            client,
            model=model,
            instructions=assess_instructions(lens, cap),
            prompt=prompt,
            schema_name="panel_assessment",
            schema=ASSESSMENT_SCHEMA,
        )
    except Exception as err:  # noqa: BLE001 - one lens failing must not end the run
        return lens, None, f"{type(err).__name__}: {err}"

    out = []
    for raw in (payload.get("findings") or [])[:cap]:
        try:
            out.append(
                Candidate(
                    disease=str(raw["disease"]).strip(),
                    claim=str(raw["claim"]),
                    reasoning=str(raw["reasoning"]),
                    confidence=float(raw["confidence"]),
                    raised_by=[lens.key],
                )
            )
        except (KeyError, TypeError, ValueError):
            continue  # Malformed finding, not a malformed reviewer.
    return lens, out, None


def _refute(client, model, lens, candidate, query_block, evidence_block):
    """One blind adversarial verdict on one candidate."""
    prompt = (
        f"Candidate to refute\n"
        f"  disease: {candidate.disease}\n"
        f"  raised by: {', '.join(candidate.raised_by)}\n"
        f"  claim: {candidate.claim}\n"
        f"  reasoning given: {candidate.reasoning}\n\n"
        f"The patient\n{query_block}\n\n"
        f"What the hospital network reported\n{evidence_block}"
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
        return candidate, {
            "lens": lens.key,
            "refuted": bool(payload["refuted"]),
            "reasoning": str(payload.get("reasoning", "")),
            "confidence": float(payload.get("confidence", 0.0)),
        }
    except Exception as err:  # noqa: BLE001
        # No vote is recorded. A verifier that crashed did not agree.
        print(f"[panel] refuter {lens.key} failed on {candidate.disease}: {err}")
        return candidate, None


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    """Merge candidates naming the same disease, keeping every lens that raised it.

    Independent agreement is evidence, and it is genuine here because round 1 was
    blind. Unlike code findings, two lenses naming one disease are unambiguously
    talking about the same thing, so the disease name is the whole key.
    """
    merged: dict[str, Candidate] = {}
    for candidate in candidates:
        key = candidate.disease.lower()
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
            continue
        existing.raised_by.extend(candidate.raised_by)
        if candidate.confidence > existing.confidence:
            existing.confidence = candidate.confidence
        # Keep the fullest reasoning rather than whichever arrived first.
        if len(candidate.reasoning) > len(existing.reasoning):
            existing.claim, existing.reasoning = candidate.claim, candidate.reasoning
    return list(merged.values())


@dataclass
class PanelResult:
    survivors: list[Candidate]
    killed: list[Candidate]
    unverified: list[Candidate]
    calibration: dict[str, Any] | None
    failed_lenses: list[str]
    dropped: int
    raised_raw: int


def run_panel(
    client,
    model: str,
    *,
    query: dict[str, Any],
    evidence: list[DiseaseEvidence],
    followups: list[dict[str, Any]] | None = None,
    max_per_lens: int = 3,
    max_candidates: int = 5,
    refuters_per_candidate: int = 3,
    min_votes: int = 2,
    canary: bool = True,
    emit: Callable[[dict[str, Any]], None] | None = None,
) -> PanelResult:
    """Run both blind rounds over the network's candidates."""

    def report(event: dict[str, Any]) -> None:
        if emit is not None:
            emit(event)

    min_votes = min(min_votes, refuters_per_candidate)
    query_block = format_query(query)
    evidence_block = format_evidence(evidence, followups)

    # --- Round 1: five blind assessments, in parallel -----------------------
    raised: list[Candidate] = []
    failed_lenses: list[str] = []
    with ThreadPoolExecutor(max_workers=len(LENSES)) as pool:
        futures = [
            pool.submit(_assess, client, model, lens, query_block, evidence_block, max_per_lens)
            for lens in LENSES
        ]
        for future in as_completed(futures):
            lens, found, error = future.result()
            if error is not None:
                failed_lenses.append(lens.key)
                print(f"[panel] lens {lens.key} failed: {error}")
                report({"type": "panel.lens.failed", "lens": lens.key, "error": error})
                continue
            raised.extend(found or [])
            print(f"[panel] lens {lens.key} raised {len(found or [])} candidate(s)")
            report(
                {
                    "type": "panel.lens.completed",
                    "lens": lens.key,
                    "count": len(found or []),
                    "diseases": [c.disease for c in (found or [])],
                }
            )

    raw_count = len(raised)
    candidates = _dedupe(raised)
    candidates.sort(key=lambda c: (len(set(c.raised_by)), c.confidence), reverse=True)
    dropped = max(0, len(candidates) - max_candidates)
    if dropped:
        # Never truncate silently: a capped panel reporting "all clear" is lying.
        print(f"[panel] {dropped} lower-ranked candidate(s) dropped by the cap")
    candidates = candidates[:max_candidates]
    for candidate in candidates:
        candidate.min_votes = min_votes

    report(
        {
            "type": "panel.round1.completed",
            "raised": raw_count,
            "verifying": len(candidates),
            "dropped_by_cap": dropped,
            "failed_lenses": failed_lenses,
        }
    )

    # --- Round 2: adversarial refutation, in parallel ----------------------
    probe = make_canary(evidence, min_votes) if canary else None
    to_verify = candidates + ([probe] if probe else [])

    jobs = [
        (candidate, lens)
        for index, candidate in enumerate(to_verify)
        for lens in assign_refuters(candidate, index, refuters_per_candidate)
    ]
    print(f"[panel] round 2: {len(jobs)} refutation attempt(s) over {len(candidates)} candidate(s)")

    if jobs:
        with ThreadPoolExecutor(max_workers=min(12, len(jobs))) as pool:
            futures = [
                pool.submit(_refute, client, model, lens, candidate, query_block, evidence_block)
                for candidate, lens in jobs
            ]
            for future in as_completed(futures):
                candidate, verdict = future.result()
                if verdict is None:
                    continue
                candidate.verdicts.append(verdict)
                report(
                    {
                        "type": "panel.verdict",
                        "disease": candidate.disease,
                        "lens": verdict["lens"],
                        "refuted": verdict["refuted"],
                        "reasoning": verdict["reasoning"],
                    }
                )

    calibration = None
    if probe is not None:
        calibration = {
            "disease": probe.disease,
            "status": probe.status,
            "refuted": probe.refuted_count,
            "votes": probe.votes_cast,
            "passed": probe.status == "killed",
        }
        print(
            f"[panel] calibration probe {'caught' if calibration['passed'] else 'MISSED'}: "
            f"planted {probe.disease} {probe.refuted_count}/{probe.votes_cast} refuted"
        )
        report({"type": "panel.calibration", **calibration})

    for candidate in candidates:
        print(
            f"[panel] {candidate.status:10s} {candidate.disease} "
            f"({candidate.refuted_count}/{candidate.votes_cast} refuted)"
        )

    return PanelResult(
        survivors=[c for c in candidates if c.status == "survivor"],
        killed=[c for c in candidates if c.status == "killed"],
        unverified=[c for c in candidates if c.status == "unverified"],
        calibration=calibration,
        failed_lenses=failed_lenses,
        dropped=dropped,
        raised_raw=raw_count,
    )
