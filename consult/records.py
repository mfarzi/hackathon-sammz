"""Loading and searching a single hospital's records.

Everything here runs inside the hospital. `search` returns per-disease evidence
with the free-text notes still attached, because the site agent that reads them
runs in this process too. Stripping the notes is the job of the code that builds
the reply message, not of the search.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .scoring import TOP_N, similarity, symptom_breakdown

APP_ROOT = Path(__file__).resolve().parent.parent

# How many of a disease's best-matching notes the site agent reads. Reading
# every match would blow the context on a common disease for no benefit - the
# agent is characterising a presentation, not doing a census.
NOTES_PER_DISEASE = 3

# Notes run to a few hundred words. Truncating keeps a site's whole reading task
# inside one comfortable call; the clinically decisive detail is near the top.
MAX_NOTE_CHARS = 1200

# A record this dissimilar is noise, not a match. Without a floor, every disease
# in the hospital comes back with a score above zero and the panel drowns.
MIN_SIMILARITY = 0.15

# A site with 26k records across 58 diseases will overlap weakly with almost
# everything. Cap what travels, and report the cap rather than hiding it.
MAX_DISEASES_PER_SITE = 6

# Only the strongest few diseases are worth spending a read on.
DISEASES_READ_PER_SITE = 4


def load_records(path: str | Path) -> list[dict[str, Any]]:
    """Read one site's records.

    Accepts either JSON Lines (one record per line) or a JSON array, because a
    hospital's export format is not something this system gets to dictate. A
    malformed line is skipped rather than failing the whole site: losing one
    record is better than a site dropping out of the consult entirely.
    """
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = APP_ROOT / resolved
    if not resolved.exists():
        return []

    text = resolved.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        data = json.loads(text)
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []

    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _demographics_note(query: dict[str, Any], record: dict[str, Any]) -> list[str]:
    """Where the record's demographics differ from the query's.

    Reported, never scored. A rare disease presenting outside its usual bracket
    is interesting rather than disqualifying, so this is evidence for the lenses
    to weigh, not a filter.
    """
    notes = []
    for field in ("gender", "age_bracket"):
        want, got = query.get(field), record.get(field)
        if want and got and str(want) != str(got):
            notes.append(f"{field}: query {want}, case {got}")
    return notes


def search(
    records: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    max_diseases: int = MAX_DISEASES_PER_SITE,
    read_top: int = DISEASES_READ_PER_SITE,
) -> tuple[list[dict[str, Any]], int]:
    """Group this site's matching records by disease, best first.

    Returns `(entries, n_dropped)`. Each entry carries the disease's best
    `TOP_N` scores, its symptom breakdown, and - for the strongest `read_top`
    only - the notes the site agent should read. Case count is recorded but
    plays no part in the ordering.

    `n_dropped` is how many weaker diseases the cap removed. The caller reports
    it: a site that quietly trims its answer is lying by omission.
    """
    query_symptoms = [str(s) for s in query.get("symptoms") or []]
    if not query_symptoms:
        # Same shape as every other return: a caller unpacking this must not
        # crash just because the query came through empty.
        return [], 0

    by_disease: dict[str, list[tuple[float, dict[str, Any]]]] = {}
    for record in records:
        score = similarity(query_symptoms, [str(s) for s in record.get("symptoms") or []])
        if score < MIN_SIMILARITY:
            continue
        disease = str(record.get("disease", "")).strip()
        if not disease:
            continue
        by_disease.setdefault(disease, []).append((score, record))

    entries = []
    for disease, matches in by_disease.items():
        matches.sort(key=lambda m: m[0], reverse=True)
        best_score, best_record = matches[0]
        breakdown = symptom_breakdown(
            query_symptoms, [str(s) for s in best_record.get("symptoms") or []]
        )
        entries.append(
            {
                "disease": disease,
                "top_scores": [round(s, 4) for s, _ in matches[:TOP_N]],
                "case_count": len(matches),
                "shared_symptoms": breakdown["shared"],
                "absent_symptoms": breakdown["absent_in_record"],
                "extra_symptoms": breakdown["extra_in_record"],
                "demographic_notes": _demographics_note(query, best_record),
                # Read locally by the site agent, then dropped. Never serialised
                # into a reply - see client_app._strip_for_wire.
                "_notes": [
                    str(r.get("text", ""))[:MAX_NOTE_CHARS]
                    for _, r in matches[:NOTES_PER_DISEASE]
                ],
            }
        )

    entries.sort(key=lambda e: max(e["top_scores"], default=0.0), reverse=True)
    dropped = max(0, len(entries) - max_diseases)
    entries = entries[:max_diseases]

    # Only the strongest few get read. The rest travel as numbers and symptom
    # names, which is enough for the panel to weigh them.
    for rank, entry in enumerate(entries):
        entry["_notes"] = entry["_notes"][:NOTES_PER_DISEASE] if rank < read_top else []

    return entries, dropped
