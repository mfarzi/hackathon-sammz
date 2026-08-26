"""The hospital site: retrieval, local note-reading, and the follow-up answer.

Everything in this module runs inside the hospital. Two things leave it, both
built here and nowhere else:

  - a per-disease summary of matching cases: similarity scores, a case count,
    symptom names, and an abstraction the site's own agent wrote
  - an answer to a follow-up question the hub asked afterwards

The record's `record_id` and its free-text note are read locally and dropped.
That is why the agent is here rather than at the hub: the note never moves, and
its clinical content still reaches the network as a judgement the site authored.
"""

from __future__ import annotations

from typing import Any

from flwr.app import Context, Message
from flwr.clientapp import ClientApp

from review_panel.model import build_client, json_call

from .protocol import reply, unpack
from .records import load_records, search
from .schemas import ABSTRACTION_SCHEMA, FOLLOWUP_ANSWER_SCHEMA

app = ClientApp()

# Diseases the site agent writes an abstraction for. The rest travel as scores
# and symptom names, which is enough for the panel to weigh them.
ABSTRACT_TOP = 3


def _site_name(context: Context) -> str:
    """Which hospital this node is.

    Prefers an explicit name in the node config; otherwise derives one from the
    partition index the runtime assigns, so a simulated federation maps cleanly
    onto the per-hospital files without any node needing to be told by hand.
    """
    explicit = context.node_config.get("site-name")
    if explicit:
        return str(explicit)
    index = context.node_config.get("partition-id", 0)
    return f"hospital_{int(index) + 1}"


def _records_path(context: Context) -> str:
    """Where this site's records live.

    A node config entry wins outright - that is how a real hospital points at
    its own store. Otherwise the file is found under the configured data
    directory by site name.
    """
    configured = context.node_config.get("records-path")
    if configured:
        return str(configured)
    data_dir = str(context.run_config.get("consult.data-dir", "data")).rstrip("/")
    return f"{data_dir}/{_site_name(context)}.jsonl"


def _strip_for_wire(entry: dict[str, Any]) -> dict[str, Any]:
    """Drop everything that must not leave the hospital.

    An allowlist, not a blocklist: a field added to a record later cannot leak
    by being forgotten here, because only these keys are ever copied out.
    """
    return {
        "disease": entry["disease"],
        "top_scores": entry["top_scores"],
        "case_count": entry["case_count"],
        "shared_symptoms": entry["shared_symptoms"],
        "absent_symptoms": entry["absent_symptoms"],
        "demographic_notes": entry["demographic_notes"],
    }


def _read_notes(client, model: str, site: str, query: dict, entries: list[dict]) -> dict[str, dict]:
    """Have the site agent read its matching notes and characterise them.

    One call covering this site's strongest few diseases. Returns abstractions
    keyed by disease; a failure here loses the prose, not the site - the scores
    and symptom names still travel.
    """
    readable = [e for e in entries[:ABSTRACT_TOP] if e.get("_notes")]
    if not readable:
        return {}

    blocks = []
    for entry in readable:
        notes = "\n\n".join(f"    case note: {n}" for n in entry["_notes"])
        blocks.append(
            f"  {entry['disease']} - {entry['case_count']} matching case(s) here\n{notes}"
        )

    prompt = (
        "The presentation we were asked about\n"
        f"  symptoms: {', '.join(query.get('symptoms') or [])}\n"
        f"  sex: {query.get('gender') or 'not stated'}\n"
        f"  age bracket: {query.get('age_bracket') or 'not stated'}\n\n"
        "Our own matching cases, grouped by diagnosis\n\n"
        + "\n\n".join(blocks)
    )

    instructions = (
        f"You are the clinical records agent at {site}, answering a consult request "
        "from another hospital about a patient with an unusual presentation.\n\n"
        "You have read your own patients' notes. Characterise each group of cases: "
        "how the illness began and progressed, what the cases had in common, and what "
        "was notably absent. Say what fits the queried presentation and - just as "
        "importantly - what does not.\n\n"
        "Two hard rules. Describe the group, never an individual: no ages, dates, "
        "places, occupations, or any detail that could single a patient out, and never "
        "quote a note verbatim. And report what argues against the match as readily as "
        "what supports it; a site that only volunteers agreement is worse than useless "
        "to the panel that reads this."
    )

    payload = json_call(
        client,
        model=model,
        instructions=instructions,
        prompt=prompt,
        schema_name="site_abstractions",
        schema=ABSTRACTION_SCHEMA,
    )

    out = {}
    for item in payload.get("abstractions") or []:
        disease = str(item.get("disease", "")).strip()
        if disease:
            out[disease] = {
                "pattern": str(item.get("pattern", "")),
                "supporting": [str(x) for x in item.get("supporting") or []],
                "arguing_against": [str(x) for x in item.get("arguing_against") or []],
            }
    return out


@app.query("consult")
def consult(message: Message, context: Context) -> Message:
    """Search this hospital's records and report what it found."""
    query = unpack(message)
    site = _site_name(context)
    model = str(context.run_config.get("panel.model", "openai/gpt-5.6-sol"))

    records = load_records(_records_path(context))
    if not records:
        print(f"[{site}] no records available at {_records_path(context)}")
        return reply(message, {"site": site, "diseases": [], "error": "no records"})

    entries, dropped = search(records, query)
    print(f"[{site}] {len(records)} records searched, {len(entries)} disease(s) matched")

    if not entries:
        # A real and useful answer. Saying nothing would be worse.
        return reply(message, {"site": site, "diseases": [], "dropped": dropped})

    if bool(context.run_config.get("consult.dry-run", False)):
        print(f"[{site}] dry run: skipping note reading")
        return reply(
            message,
            {"site": site, "diseases": [_strip_for_wire(e) for e in entries], "dropped": dropped},
        )

    abstractions: dict[str, dict] = {}
    try:
        abstractions = _read_notes(build_client(), model, site, query, entries)
        print(f"[{site}] agent read notes for {len(abstractions)} disease(s)")
    except Exception as err:  # noqa: BLE001 - lose the prose, not the site
        print(f"[{site}] note reading failed, sending scores only: {err}")

    diseases = []
    for entry in entries:
        out = _strip_for_wire(entry)
        if entry["disease"] in abstractions:
            out["abstraction"] = abstractions[entry["disease"]]
        diseases.append(out)

    return reply(message, {"site": site, "diseases": diseases, "dropped": dropped})


@app.query("followup")
def followup(message: Message, context: Context) -> Message:
    """Answer one targeted question from the hub, from this site's records."""
    payload = unpack(message)
    site = _site_name(context)
    model = str(context.run_config.get("panel.model", "openai/gpt-5.6-sol"))
    question = str(payload.get("question", ""))
    disease = str(payload.get("target_disease", ""))
    query = payload.get("query") or {}

    records = load_records(_records_path(context))
    matching = [r for r in records if str(r.get("disease", "")) == disease]
    if not matching:
        return reply(
            message,
            {"site": site, "answer": "No cases of this condition in our records.",
             "has_evidence": False},
        )

    notes = "\n\n".join(
        f"  case note: {str(r.get('text', ''))[:1200]}" for r in matching[:4]
    )
    prompt = (
        f"Question from the consulting hospital: {question}\n\n"
        f"It concerns {disease}, of which we hold {len(matching)} case(s).\n"
        f"The patient under discussion presents with: "
        f"{', '.join(query.get('symptoms') or [])}\n\n"
        f"Our own case notes\n\n{notes}"
    )
    instructions = (
        f"You are the clinical records agent at {site}. Another hospital has asked a "
        "specific question about your cases. Answer it from the notes, aggregated "
        "across the cases - never about one patient, with no identifying detail and "
        "nothing quoted verbatim.\n\n"
        "If the notes do not answer the question, say so and set has_evidence to "
        "false. An honest 'our records do not show this' is worth more to the panel "
        "than a confident guess."
    )

    try:
        answer = json_call(
            build_client(),
            model=model,
            instructions=instructions,
            prompt=prompt,
            schema_name="followup_answer",
            schema=FOLLOWUP_ANSWER_SCHEMA,
        )
        print(f"[{site}] answered follow-up on {disease}")
        return reply(
            message,
            {
                "site": site,
                "answer": str(answer.get("answer", "")),
                "has_evidence": bool(answer.get("has_evidence", False)),
            },
        )
    except Exception as err:  # noqa: BLE001
        print(f"[{site}] follow-up failed: {err}")
        return reply(
            message,
            {"site": site, "answer": f"Could not answer: {err}", "has_evidence": False},
        )
