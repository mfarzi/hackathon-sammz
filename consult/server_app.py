"""The hub: fan out a consult, ask a follow-up, then let the panel argue.

The hub holds no patient data and never sees any. It turns the clinician's
description into a structured query, asks every hospital, ranks what comes back,
asks one targeted follow-up it could not have known to ask at the start, and
then hands the whole assembled picture to the adversarial panel.

Ranking here is deliberately mechanical - it decides what gets discussed, not
what is true. The panel decides what it means.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

from flwr.app import Context
from flwr.serverapp import Grid, ServerApp

from review_panel.model import build_client, json_call, runtime_is_available

from .panel import format_evidence, format_query, run_panel
from .protocol import CONSULT, FOLLOWUP, pack, unpack
from .schemas import FOLLOWUP_QUESTION_SCHEMA, QUERY_SCHEMA
from .scoring import DiseaseEvidence, rank_network
from .vocabulary import constrain, load_vocabulary

app = ServerApp()

# Round-trip budget for one fan-out. Sites that miss it are reported as
# non-responding rather than quietly treated as having found nothing.
SITE_TIMEOUT_S = 90.0

DEFAULT_CASE = (
    "Young adult with several weeks of progressive confusion and personality "
    "change, then seizures and abnormal involuntary facial movements. Persistently "
    "afebrile. Extensive infection screen negative."
)


def _apply_api_key(context: Context) -> None:
    """Take a model key from the run config, if one was supplied.

    `flwr run` has no environment passthrough, so a deployment where the Flower
    runtime does not supply model credentials has only the run config to carry
    them. The key then travels with the run and is visible in its metadata on
    whoever hosts the SuperLink - treat any key sent this way as disclosed, and
    rotate it afterwards. Locally, prefer OPENAI_API_KEY or a .env file and
    leave this unset.
    """
    key = context.run_config.get("panel.api-key")
    if isinstance(key, str) and key.strip():
        os.environ["OPENAI_API_KEY"] = key.strip()


def _cfg_str(context: Context, key: str, default: str) -> str:
    value = context.run_config.get(key, default)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _cfg_bool(context: Context, key: str, default: bool) -> bool:
    value = context.run_config.get(key, default)
    return bool(value) if isinstance(value, bool) else default


def _cfg_int(context: Context, key: str, default: int) -> int:
    value = context.run_config.get(key, default)
    return int(value) if isinstance(value, (int, float)) else default


def _parse_case(client, model: str, description: str) -> dict[str, Any]:
    """Turn the clinician's description into a structured query.

    The parse is constrained to the shared symptom vocabulary. Left free, a model
    writes reasonable synonyms that match no record at all, and the consult comes
    back empty in a way indistinguishable from genuinely finding nothing.

    Falls back to a bare token split if the model call fails: a broken parse
    should degrade the search, not end the consult.
    """
    vocabulary = load_vocabulary()
    instructions = (
        "You are triaging a consult request written by a clinician. Map the "
        "presenting features onto a controlled symptom vocabulary.\n\n"
        "You MUST choose symptoms only from this list, copied exactly:\n"
        f"{', '.join(vocabulary)}\n\n"
        "Pick the closest available token for each feature the clinician describes. "
        "If nothing in the list fits a feature, leave it out rather than inventing a "
        "token - an invented one matches no record. Record only what was stated; do "
        "not infer, and do not add what you would expect to see. Leave sex or age "
        "bracket empty if they were not given."
    )
    try:
        parsed = json_call(
            client,
            model=model,
            instructions=instructions,
            prompt=description,
            schema_name="consult_query",
            schema=QUERY_SCHEMA,
        )
        raw = [str(s) for s in parsed.get("symptoms") or [] if str(s).strip()]
        symptoms, dropped = constrain(raw, vocabulary)
        if dropped:
            # Say it out loud. Silent drift is how a consult returns nothing and
            # looks like it simply found nothing.
            print(f"[hub] parse produced {len(dropped)} unknown token(s), ignored: {', '.join(dropped)}")
        if symptoms:
            return {
                "symptoms": symptoms,
                "gender": str(parsed.get("gender", "")).strip(),
                "age_bracket": str(parsed.get("age_bracket", "")).strip(),
                "summary": str(parsed.get("summary", "")).strip(),
            }
    except Exception as err:  # noqa: BLE001
        print(f"[hub] structured parse failed, falling back to tokens: {err}")

    return {
        "symptoms": _fallback_tokens(description),
        "gender": "",
        "age_bracket": "",
        "summary": description,
    }


def _fallback_tokens(description: str) -> list[str]:
    """Guess symptoms from raw words, for when there is no model to ask.

    Matches against the shared vocabulary rather than emitting bare words: a
    dry run whose symptoms are "woman", "twenties", "months" exercises nothing
    and looks broken. A vocabulary token counts as present when all the words
    making it up appear in the description, which catches `slurred_speech` and
    `mood_change` from ordinary prose without needing a model.
    """
    words = set(re.findall(r"[a-z]+", description.lower()))
    if not words:
        return []
    matched = [
        token
        for token in load_vocabulary()
        if all(part in words for part in token.split("_"))
    ]
    # Prefer the most specific matches when there are more than the cap allows.
    matched.sort(key=lambda t: (-len(t.split("_")), t))
    return matched[:12]


def _fan_out(grid: Grid, payload: dict, message_type: str, node_ids: list[int], group: str):
    """Send one message to each node and collect whatever comes back in time."""
    messages = [
        grid.create_message(
            content=pack(payload),
            message_type=message_type,
            dst_node_id=node_id,
            group_id=group,
        )
        for node_id in node_ids
    ]
    replies = list(grid.send_and_receive(messages, timeout=SITE_TIMEOUT_S))

    collected, failed = [], []
    for reply in replies:
        if reply.has_error():
            failed.append(str(reply.metadata.src_node_id))
            continue
        try:
            collected.append(unpack(reply))
        except Exception as err:  # noqa: BLE001
            print(f"[hub] unreadable reply from {reply.metadata.src_node_id}: {err}")
            failed.append(str(reply.metadata.src_node_id))

    # A node that never replied is not a node that found nothing.
    missing = len(node_ids) - len(replies)
    return collected, failed, missing


def _decide_followup(client, model: str, query: dict, evidence: list[DiseaseEvidence]):
    """Work out the one question worth asking the network next."""
    if len(evidence) < 2:
        return None
    instructions = (
        "You are coordinating a consult between hospitals. The first round is in: "
        "several sites have reported comparable cases and the candidates are ranked "
        "below.\n\n"
        "Ask ONE question that would most change the ranking - something answerable "
        "from case records that discriminates between the leading candidates. A good "
        "question separates the top candidate from its nearest rival. A useless one "
        "asks about something already reported, or something no record would contain."
    )
    prompt = (
        f"The patient\n{format_query(query)}\n\n"
        f"What the network reported\n{format_evidence(evidence)}"
    )
    try:
        return json_call(
            client,
            model=model,
            instructions=instructions,
            prompt=prompt,
            schema_name="followup_question",
            schema=FOLLOWUP_QUESTION_SCHEMA,
        )
    except Exception as err:  # noqa: BLE001
        print(f"[hub] follow-up planning failed, continuing without it: {err}")
        return None


def _describe(candidates) -> str:
    if not candidates:
        return "  (none)"
    lines = []
    for c in candidates:
        lines.append(
            f"  - {c.disease}\n"
            f"    raised by: {', '.join(sorted(set(c.raised_by)))}\n"
            f"    claim: {c.claim}\n"
            f"    reasoning: {c.reasoning}\n"
            f"    votes: {c.refuted_count} of {c.votes_cast} refuted"
        )
        for v in c.verdicts:
            stance = "refuted" if v["refuted"] else "upheld"
            lines.append(f"      {v['lens']} ({stance}): {v['reasoning']}")
    return "\n".join(lines)


def _write_report(client, model: str, *, query, evidence, result, coverage) -> str:
    """Have the master write the clinician-facing report."""
    caveats = list(coverage)
    cal = result.calibration
    if cal is not None and not cal["passed"]:
        caveats.insert(
            0,
            f"CALIBRATION FAILURE: a planted false candidate ({cal['disease']}) was NOT "
            f"rejected by the panel ({cal['refuted']} of {cal['votes']} refuted). The "
            "verifiers are not reliably refuting, so everything below carries much "
            "weaker evidence than survival normally implies.",
        )
    elif cal is not None:
        caveats.insert(
            0,
            f"Calibration passed: a planted false candidate ({cal['disease']}) was "
            f"correctly rejected ({cal['refuted']} of {cal['votes']} refuted).",
        )
    if result.failed_lenses:
        caveats.append(f"These specialists failed and cast no assessment: {', '.join(result.failed_lenses)}.")
    if result.dropped:
        caveats.append(f"{result.dropped} lower-ranked candidate(s) were never verified, due to the candidate cap.")
    if result.unverified:
        caveats.append(
            f"{len(result.unverified)} candidate(s) drew too few verdicts to judge and "
            "are listed as unverified rather than counted either way."
        )

    prompt = (
        f"The patient\n{format_query(query)}\n\n"
        f"What the network reported\n{format_evidence(evidence)}\n\n"
        f"SURVIVED refutation:\n{_describe(result.survivors)}\n\n"
        f"KILLED by refutation:\n{_describe(result.killed)}\n\n"
        f"UNVERIFIED (too few verdicts):\n{_describe(result.unverified)}\n\n"
        f"Process caveats: {' '.join(caveats) if caveats else 'none'}"
    )

    instructions = (
        "You are the master of a diagnostic review panel, writing for the clinician "
        "who asked. Structure it as markdown:\n\n"
        "1. A one-line verdict: how many candidates survived adversarial refutation.\n"
        "2. `## Worth considering` - each survivor, what the network's evidence "
        "actually is (how many cases, across how many sites, at what similarity), and "
        "why it withstood attack. Where a verifier upheld it with a caveat, keep the "
        "caveat. If a survivor drew a dissenting vote, say so; never present a split "
        "verdict as unanimous.\n"
        "3. `## Rejected by the panel` - what was raised and why the verifiers killed "
        "it. Keep this section: showing what did not survive is what makes the "
        "survivors worth trusting.\n"
        "4. `## Coverage and limits` - state the process caveats. If a caveat reports "
        "a calibration failure, lead with it and say plainly that this run's verdicts "
        "should not be trusted.\n\n"
        "Report only what the panel data supports. Do not add candidates of your own, "
        "do not promote a killed candidate, do not soften a survivor. If nothing "
        "survived, say so plainly - an empty result is a real result.\n\n"
        "This supports a clinician's reasoning and does not replace it. Never state a "
        "diagnosis as established, never recommend treatment, and describe case "
        "counts as leads to investigate rather than as proof."
    )

    stream = client.responses.create(
        model=model, instructions=instructions, input=prompt, stream=True
    )
    chunks: list[str] = []
    for event in stream:
        if event.type in {"error", "response.failed"}:
            raise RuntimeError(f"Master report failed: {event}")
        if event.type == "response.output_text.delta":
            chunks.append(event.delta)
    return "".join(chunks)


@app.main()
def main(grid: Grid, context: Context) -> None:
    """Run one federated consult."""
    started = time.time()
    description = _cfg_str(context, "consult.case", DEFAULT_CASE)
    model = _cfg_str(context, "panel.model", "openai/gpt-5.6-sol")

    # Dry run exercises the federation - fan-out, per-site search, ranking -
    # with no model calls at all. It is how you check the network works, and how
    # you demo it without spending a token.
    dry_run = _cfg_bool(context, "consult.dry-run", False)
    _apply_api_key(context)
    print(f"[hub] model runtime from Flower: {runtime_is_available()}")
    if dry_run:
        print("[hub] DRY RUN: retrieval and ranking only, no agents, no panel")

    client = None if dry_run else build_client()

    node_ids = list(grid.get_node_ids())
    print(f"[hub] {len(node_ids)} hospital site(s) online")
    if not node_ids:
        print("[hub] no sites available; nothing to consult")
        return

    # --- the clinician's case, structured --------------------------------
    preset = _cfg_str(context, "consult.symptoms", "")
    if preset:
        # An explicit symptom list skips the parse. Useful for a reproducible
        # demo, and required for a dry run, which has no model to parse with.
        query = {
            "symptoms": [s.strip().lower() for s in preset.split(",") if s.strip()],
            "gender": _cfg_str(context, "consult.gender", ""),
            "age_bracket": _cfg_str(context, "consult.age-bracket", ""),
            "summary": description if description != DEFAULT_CASE else "",
        }
    elif dry_run:
        query = {"symptoms": _fallback_tokens(description), "gender": "", "age_bracket": "",
                 "summary": description}
    else:
        query = _parse_case(client, model, description)
    print(f"[hub] symptoms: {', '.join(query['symptoms'])}")

    # --- round 1: ask every hospital -------------------------------------
    reports, failed, missing = _fan_out(grid, query, CONSULT, node_ids, "consult")
    responded = [r for r in reports if r.get("diseases")]
    silent = [r["site"] for r in reports if not r.get("diseases")]
    print(f"[hub] {len(responded)} site(s) had comparable cases; {len(silent)} had none")
    for site in silent:
        print(f"[hub]   {site}: no data")

    evidence = rank_network(reports)
    if not evidence:
        print("[hub] no site in the network reported a comparable case.")
        return

    print("[hub] ranked candidates (score | cases | sites):")
    for ev in evidence[:8]:
        print(f"[hub]   {ev.disease:<44} {ev.score:.3f} | {ev.case_count:>4} | {','.join(ev.sites)}")

    if dry_run:
        print(f"[hub] dry run finished in {time.time() - started:.1f}s")
        return

    # --- the second hop: one targeted follow-up ---------------------------
    followups: list[dict[str, Any]] = []
    if context.run_config.get("consult.followup", True) is not False:
        question = _decide_followup(client, model, query, evidence[:5])
        if question:
            target = str(question.get("target_disease", ""))
            asked = [
                node_ids[i]
                for i, r in enumerate(reports)
                if any(d["disease"] == target for d in r.get("diseases") or [])
            ] or node_ids
            print(f'[hub] follow-up on {target}: "{question.get("question", "")}"')
            answers, _, _ = _fan_out(
                grid,
                {"question": question.get("question", ""), "target_disease": target, "query": query},
                FOLLOWUP,
                asked,
                "followup",
            )
            followups.append({**question, "answers": answers})
            for a in answers:
                mark = "" if a.get("has_evidence") else " [no evidence]"
                print(f"[hub]   {a.get('site')}{mark}: {a.get('answer', '')[:160]}")

    # --- the panel --------------------------------------------------------
    result = run_panel(
        client,
        model,
        query=query,
        evidence=evidence,
        followups=followups,
        max_per_lens=_cfg_int(context, "panel.max-findings-per-lens", 3),
        max_candidates=_cfg_int(context, "panel.max-candidates", 5),
        refuters_per_candidate=_cfg_int(context, "panel.refuters-per-finding", 3),
        min_votes=_cfg_int(context, "panel.min-votes", 2),
        canary=context.run_config.get("panel.canary", True) is not False,
        emit=None,
    )

    coverage = []
    if silent:
        coverage.append(f"{len(silent)} site(s) reported no comparable case: {', '.join(silent)}.")
    if failed or missing:
        coverage.append(
            f"{len(failed) + missing} site(s) did not answer and are not counted as "
            "having found nothing."
        )
    capped = sum(int(r.get("dropped", 0)) for r in reports)
    if capped:
        coverage.append(f"{capped} weaker disease match(es) were trimmed by the per-site cap.")

    report = _write_report(
        client, model, query=query, evidence=evidence, result=result, coverage=coverage
    )
    print("\n" + "=" * 72 + "\n")
    print(report)
    print("\n" + "=" * 72)
    print(f"[hub] consult finished in {time.time() - started:.1f}s")
