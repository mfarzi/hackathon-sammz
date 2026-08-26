"""Offline checks over the parts that decide what counts as evidence.

No model calls and no Flower runtime. These cover the rules the system's claims
rest on: that case count never drives ranking, that nothing identifying reaches
the wire, and that a candidate is never silently promoted to a survivor.

    PYTHONPATH=. python tests/test_consult.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from consult.client_app import _strip_for_wire
from consult.lenses import LENSES
from consult.panel import Candidate, _dedupe, assign_refuters, format_evidence, make_canary
from consult.records import load_records, search
from consult.scoring import (
    DiseaseEvidence,
    rank_network,
    similarity,
    symptom_breakdown,
    top_n_mean,
)

ok = True


def check(label, cond):
    global ok
    ok = ok and bool(cond)
    print(("PASS  " if cond else "FAIL  ") + label)


# --- similarity -------------------------------------------------------------

check("identical symptom sets score 1.0", similarity(["a", "b"], ["b", "a"]) == 1.0)
check("disjoint sets score 0.0", similarity(["a"], ["b"]) == 0.0)
check("3 shared of 5 union is 0.6", abs(similarity(["a", "b", "c"], ["a", "b", "c", "d", "e"]) - 0.6) < 1e-9)
check("empty query scores 0.0", similarity([], ["a"]) == 0.0)
check("case and whitespace are ignored", similarity([" A "], ["a"]) == 1.0)

bd = symptom_breakdown(["fever", "cough"], ["cough", "rash"])
check("breakdown finds the shared symptom", bd["shared"] == ["cough"])
check("breakdown finds what the record lacks", bd["absent_in_record"] == ["fever"])
check("breakdown finds what the record adds", bd["extra_in_record"] == ["rash"])

# --- the ranking rule -------------------------------------------------------

check("top_n_mean of one score is that score", top_n_mean([0.8]) == 0.8)
check("top_n_mean takes only the best three", abs(top_n_mean([0.9, 0.8, 0.7, 0.1]) - 0.8) < 1e-9)
check("fewer than three is not padded with zeros", top_n_mean([0.9, 0.9]) == 0.9)
check("no scores means no score", top_n_mean([]) == 0.0)

# The rule the whole pitch rests on: one case must be able to beat a hundred.
ranked = rank_network([
    {"site": "a", "diseases": [{"disease": "rare", "top_scores": [0.80], "case_count": 1}]},
    {"site": "b", "diseases": [{"disease": "common", "top_scores": [0.80, 0.79, 0.78], "case_count": 100}]},
])
check("a single strong match outranks a hundred weaker ones", ranked[0].disease == "rare")
check("case count is carried as provenance", ranked[1].case_count == 100)

# Volume must not accumulate into score, however many sites report it.
ranked = rank_network(
    [{"site": f"s{i}", "diseases": [{"disease": "common", "top_scores": [0.5, 0.5, 0.5], "case_count": 50}]} for i in range(5)]
    + [{"site": "x", "diseases": [{"disease": "rare", "top_scores": [0.6], "case_count": 1}]}]
)
check("five sites reporting a weaker match still lose", ranked[0].disease == "rare")
check("scores pool across sites", ranked[1].case_count == 250)

# Pooling must take the network's best, not a per-site average.
ranked = rank_network([
    {"site": "a", "diseases": [{"disease": "d", "top_scores": [0.9], "case_count": 1}]},
    {"site": "b", "diseases": [{"disease": "d", "top_scores": [0.1, 0.1, 0.1, 0.1], "case_count": 40}]},
])
check("one site's strong match is not diluted by another's weak ones", ranked[0].score > 0.3)
check("both sites are credited", sorted(ranked[0].sites) == ["a", "b"])

# --- nothing identifying reaches the wire -----------------------------------

entry = {
    "disease": "wilson_disease", "top_scores": [0.5], "case_count": 1,
    "shared_symptoms": ["tremor"], "absent_symptoms": [], "extra_symptoms": [],
    "demographic_notes": [], "_notes": ["a full clinical note"],
    "record_id": "DEADBEEF", "text": "free text that must not travel",
}
wire = _strip_for_wire(entry)
check("record_id never reaches the wire", "record_id" not in wire)
check("free text never reaches the wire", "text" not in wire)
check("local notes never reach the wire", "_notes" not in wire)
check("the disease does reach the wire", wire["disease"] == "wilson_disease")
check("scores do reach the wire", wire["top_scores"] == [0.5])
# An allowlist, so a field added to records later cannot leak by being forgotten.
check("a newly added record field cannot leak", "surprise" not in _strip_for_wire({**entry, "surprise": "x"}))

# --- vote accounting --------------------------------------------------------

def mk(disease="d", **kw):
    return Candidate(disease=disease, claim="c", reasoning="r", confidence=0.5, **kw)


thin = mk()
thin.verdicts = [{"lens": "a", "refuted": False, "reasoning": "", "confidence": 1.0}]
check("a single upheld vote is unverified, not a survivor", thin.status == "unverified")
thin.verdicts.append({"lens": "b", "refuted": False, "reasoning": "", "confidence": 1.0})
check("two upheld votes survive", thin.status == "survivor")

solo = mk()
solo.verdicts = [{"lens": "a", "refuted": True, "reasoning": "", "confidence": 1.0}]
check("a single refuting vote is also unverified", solo.status == "unverified")

split = mk()
split.verdicts = [
    {"lens": "a", "refuted": True, "reasoning": "", "confidence": 1.0},
    {"lens": "b", "refuted": True, "reasoning": "", "confidence": 1.0},
    {"lens": "c", "refuted": False, "reasoning": "", "confidence": 1.0},
]
check("a majority of refutations kills a candidate", split.status == "killed")
check("the dissenting vote is retained", sum(1 for v in split.verdicts if not v["refuted"]) == 1)

survived = mk()
survived.verdicts = [
    {"lens": "a", "refuted": False, "reasoning": "", "confidence": 1.0},
    {"lens": "b", "refuted": False, "reasoning": "", "confidence": 1.0},
    {"lens": "c", "refuted": True, "reasoning": "", "confidence": 1.0},
]
check("a minority refutation does not kill", survived.status == "survivor")

relaxed = mk()
relaxed.min_votes = 1
relaxed.verdicts = [{"lens": "a", "refuted": False, "reasoning": "", "confidence": 1.0}]
check("min_votes=1 permits a one-vote survivor", relaxed.status == "survivor")

# --- refuter assignment -----------------------------------------------------

raised = mk(raised_by=["symptom_fit"])
picked = assign_refuters(raised, 0, 3)
check("a refuter never attacks what it raised", "symptom_fit" not in [l.key for l in picked])
check("three refuters are assigned", len(picked) == 3)
check("refuters are distinct", len({l.key for l in picked}) == 3)

all_raised = mk(raised_by=[l.key for l in LENSES])
check("a unanimous candidate still gets refuters", len(assign_refuters(all_raised, 0, 3)) == 3)

# Regression: agreement used to shrink the refuter pool, so a candidate raised by
# four lenses drew one verdict, fell below min_votes and was reported unverified.
# The best-corroborated candidate got the least scrutiny. It must always get the
# full count, however many lenses raised it.
for n in range(len(LENSES) + 1):
    raisers = [l.key for l in LENSES][:n]
    got = assign_refuters(mk(raised_by=raisers), 0, 3)
    check(f"a candidate raised by {n} lens(es) still draws 3 refuters", len(got) == 3)
    check(f"its {n}-lens refuters are distinct", len({l.key for l in got}) == 3)

# Disinterested refuters are still preferred while any remain.
two_raised = assign_refuters(mk(raised_by=["symptom_fit", "demographics"]), 0, 3)
check("disinterested refuters are preferred", not {l.key for l in two_raised} & {"symptom_fit", "demographics"})

rotated = {tuple(l.key for l in assign_refuters(mk(raised_by=["symptom_fit"]), i, 3)) for i in range(4)}
check("assignment rotates across candidates", len(rotated) > 1)

# --- dedupe -----------------------------------------------------------------

merged = _dedupe([
    mk("wilson_disease", raised_by=["symptom_fit"]),
    mk("wilson_disease", raised_by=["contradictions"]),
    mk("influenza", raised_by=["common_first"]),
])
check("the same disease merges into one candidate", len(merged) == 2)
wilson = next(c for c in merged if c.disease == "wilson_disease")
check("every lens that raised it is recorded", sorted(wilson.raised_by) == ["contradictions", "symptom_fit"])
check("case-different names still merge", len(_dedupe([mk("Wilson_Disease"), mk("wilson_disease")])) == 1)

# --- the calibration probe --------------------------------------------------

evidence = [DiseaseEvidence(disease="wilson_disease", scores=[0.5], case_count=1)]
canary = make_canary(evidence, 2)
check("a canary is produced", canary is not None)
check("the canary names a disease no site reported", canary.disease != "wilson_disease")
check("the canary is flagged as such", canary.is_canary)
check("the canary claims support it does not have", "corroborat" in canary.claim)

# --- prompt rendering -------------------------------------------------------

rendered = format_evidence([
    DiseaseEvidence(disease="d", scores=[0.5], case_count=99, sites=["a"], absent_symptoms=["fever"])
])
check("case count is labelled as provenance, not strength", "NOT strength" in rendered)
check("absent symptoms are shown to the lenses", "fever" in rendered)
check("no evidence renders as an explicit statement", "no site reported" in format_evidence([]))

# --- record loading ---------------------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    rec = {"record_id": "1", "disease": "d", "symptoms": ["a"], "text": "t"}

    jsonl = Path(tmp) / "s.jsonl"
    jsonl.write_text(json.dumps(rec) + "\n" + json.dumps(rec) + "\n")
    check("JSON Lines loads", len(load_records(jsonl)) == 2)

    arr = Path(tmp) / "s.json"
    arr.write_text(json.dumps([rec, rec, rec]))
    check("a JSON array loads", len(load_records(arr)) == 3)

    broken = Path(tmp) / "b.jsonl"
    broken.write_text(json.dumps(rec) + "\n{ not json\n" + json.dumps(rec) + "\n")
    check("a malformed line is skipped, not fatal", len(load_records(broken)) == 2)

    check("a missing file yields no records", load_records(Path(tmp) / "nope.jsonl") == [])

# --- search -----------------------------------------------------------------

records = [
    {"record_id": "1", "disease": "target", "symptoms": ["a", "b", "c"], "text": "n1"},
    {"record_id": "2", "disease": "target", "symptoms": ["a", "b"], "text": "n2"},
    {"record_id": "3", "disease": "other", "symptoms": ["z"], "text": "n3"},
]
entries, dropped = search(records, {"symptoms": ["a", "b", "c"]})
check("search groups matches by disease", [e["disease"] for e in entries] == ["target"])
check("search counts every matching case", entries[0]["case_count"] == 2)
check("search keeps notes for the local agent", len(entries[0]["_notes"]) == 2)
check("an unrelated disease falls below the floor", all(e["disease"] != "other" for e in entries))
check("a query with no symptoms matches nothing", search(records, {"symptoms": []}) == ([], 0))

capped, dropped = search(
    [{"record_id": str(i), "disease": f"d{i}", "symptoms": ["a", "b"], "text": ""} for i in range(10)],
    {"symptoms": ["a", "b"]},
    max_diseases=3,
)
check("the per-site cap is applied", len(capped) == 3)
check("what the cap dropped is reported, not hidden", dropped == 7)

print()
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
