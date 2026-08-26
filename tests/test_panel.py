"""Offline checks for the panel logic.

No model calls, no network: this exercises the parts of the panel that decide
what counts as evidence. Run from the repo root:

    PYTHONPATH=. python tests/test_panel.py
"""
import sys

from review_panel.agent_app import (
    Finding,
    _assign_refuters,
    _dedupe,
    _load_source,
    _same_defect,
)
from review_panel.lenses import LENSES, refute_instructions, review_instructions

ok = True


def check(label, cond):
    global ok
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        ok = False


# --- source loading -----------------------------------------------------
src, files, trunc = _load_source("fixtures/buggy_cart")
check("loads both fixture files", sorted(files) == [
    "fixtures/buggy_cart/__init__.py",
    "fixtures/buggy_cart/cart.py",
    "fixtures/buggy_cart/store.py",
])
check("source not truncated", trunc is False)
check("lines are numbered", "   1 | " in src)
check("single file target works", _load_source("fixtures/buggy_cart/cart.py")[1] == [
    "fixtures/buggy_cart/cart.py"])
try:
    _load_source("../../../etc")
    check("path escape rejected", False)
except ValueError:
    check("path escape rejected", True)
try:
    _load_source("fixtures/nope")
    check("missing target rejected", False)
except ValueError:
    check("missing target rejected", True)


def mk(title, file="a.py", line=10, claim="sql injection via f-string in query",
       sev="high", conf=0.8, by=("security",)):
    return Finding(title=title, file=file, line=line, severity=sev, claim=claim,
                   failure_scenario="x", confidence=conf, raised_by=list(by))


# --- dedupe -------------------------------------------------------------
a = mk("A", claim="untrusted category interpolated into sql string")
b = mk("B", line=11, claim="category interpolated directly into the sql string",
       by=("correctness",))
check("same defect merges across lenses", _same_defect(a, b))
merged = _dedupe([a, b])
check("merge yields one finding", len(merged) == 1)
check("merge keeps both raisers", sorted(set(merged[0].raised_by)) == ["correctness", "security"])

# Regression: the real duplicate pair from the first SuperGrid run. Two lenses,
# same defect at cart.py:81, differently worded claims.
d1 = mk("Validation errors leak across calls", file="cart.py", line=81,
        claim="validate_quantities mutates a shared mutable default argument",
        by=("contracts",))
d2 = mk("Validation errors persist across calls", file="cart.py", line=81,
        claim="the default errors list is created once and retains entries",
        by=("robustness",))
check("real-world duplicate pair merges", _same_defect(d1, d2))
check("duplicate pair collapses to one", len(_dedupe([d1, d2])) == 1)

# Distinct defects that happen to sit on adjacent lines must stay apart.
n1 = mk("SQL injection in search", file="s.py", line=43,
        claim="category is interpolated into the sql string", by=("security",))
n2 = mk("Stock check ignores reservations", file="s.py", line=44,
        claim="available stock omits quantities already reserved by open carts",
        by=("correctness",))
check("adjacent distinct defects not merged", not _same_defect(n1, n2))

c = mk("C", line=80, claim="quadratic loop over cart items", by=("performance",))
check("distinct defects stay separate", len(_dedupe([mk("A"), c])) == 2)
check("far apart lines not merged", not _same_defect(mk("A", line=10), mk("A", line=40)))

# --- verdict accounting -------------------------------------------------
f = mk("V")
check("no votes means unverified", f.status == "unverified")
f.verdicts = [{"lens": "x", "refuted": False, "reasoning": "", "confidence": 1.0}]
check("1 of 1 upheld is unverified under the min-votes gate", f.status == "unverified")
f.verdicts.append({"lens": "y", "refuted": True, "reasoning": "", "confidence": 1.0})
check("1 of 2 refuted survives (no majority)", f.status == "survivor")
f.verdicts.append({"lens": "z", "refuted": True, "reasoning": "", "confidence": 1.0})
check("2 of 3 refuted is killed", f.status == "killed")

# --- refuter assignment -------------------------------------------------
f2 = mk("R", by=("security",))
refs = _assign_refuters(f2, 0, 3)
check("3 refuters assigned", len(refs) == 3)
check("raiser excluded from refuters", "security" not in [l.key for l in refs])
check("refuters are distinct", len({l.key for l in refs}) == 3)
allfive = mk("R2", by=tuple(l.key for l in LENSES))
check("all-raised falls back rather than empty", len(_assign_refuters(allfive, 0, 3)) == 3)
rot0 = [l.key for l in _assign_refuters(mk("x", by=("security",)), 0, 2)]
rot1 = [l.key for l in _assign_refuters(mk("x", by=("security",)), 1, 2)]
check("rotation spreads load", rot0 != rot1)
check("cap above eligible count is clamped", len(_assign_refuters(f2, 0, 99)) == 4)

# --- prompts ------------------------------------------------------------
check("5 lenses defined", len(LENSES) == 5)
check("lens keys unique", len({l.key for l in LENSES}) == 5)
ri = review_instructions(LENSES[0], 4)
check("review prompt states blindness", "blind" in ri.lower())
check("review prompt carries the cap", "at most 4" in ri)
fi = refute_instructions(LENSES[0])
check("refute prompt demands refutation", "refute" in fi.lower())
check("refute prompt defaults to refuted", "refuted=true" in fi)

# --- exact-line merge (regression from run 3) ---------------------------
e1 = mk("Stale validation errors persist", file="c.py", line=75,
        claim="errors accumulate in the shared default list", by=("robustness",))
e2 = mk("Validation state grows without bound", file="c.py", line=75,
        claim="the list retains entries indefinitely across invocations",
        by=("contracts",))
check("low lexical overlap still merges on exact line", _same_defect(e1, e2))
check("exact-line pair collapses to one", len(_dedupe([e1, e2])) == 1)
check("exact-line merge keeps both raisers",
      sorted(set(_dedupe([e1, e2])[0].raised_by)) == ["contracts", "robustness"])
check("different files never merge",
      not _same_defect(mk("A", file="x.py", line=75), mk("A", file="y.py", line=75)))

# --- calibration canary -------------------------------------------------
from review_panel.agent_app import _make_canary

canary = _make_canary()
check("canary claim is false about real code",
      "multiplies price_pence by quantity twice" in canary.claim)
check("canary targets a real fixture file",
      canary.file == "fixtures/buggy_cart/cart.py")
src_cart, _, _ = _load_source("fixtures/buggy_cart/cart.py")
check("canary's file really is loadable", "subtotal_pence" in src_cart)
check("canary is not attributed to a real lens", canary.raised_by == ["canary"])
check("all five lenses may refute the canary",
      len(_assign_refuters(canary, 0, 5)) == 5)
check("canary starts unverified", canary.status == "unverified")
canary.verdicts = [
    {"lens": "correctness", "refuted": True, "reasoning": "", "confidence": 1.0},
    {"lens": "security", "refuted": True, "reasoning": "", "confidence": 1.0},
    {"lens": "performance", "refuted": False, "reasoning": "", "confidence": 1.0},
]
check("canary killed by 2 of 3 = calibration passes", canary.status == "killed")

# --- min-votes gate (regression from run 4) -----------------------------
thin = mk("One vote only")
thin.verdicts = [{"lens": "a", "refuted": False, "reasoning": "", "confidence": 1.0}]
check("single upheld vote is unverified, not survivor", thin.status == "unverified")
thin.verdicts.append({"lens": "b", "refuted": False, "reasoning": "", "confidence": 1.0})
check("two upheld votes survive", thin.status == "survivor")

solo = mk("Solo kill")
solo.verdicts = [{"lens": "a", "refuted": True, "reasoning": "", "confidence": 1.0}]
check("single refuting vote is also unverified", solo.status == "unverified")

relaxed = mk("Relaxed gate")
relaxed.min_votes = 1
relaxed.verdicts = [{"lens": "a", "refuted": False, "reasoning": "", "confidence": 1.0}]
check("min_votes=1 permits a one-vote survivor", relaxed.status == "survivor")

print()
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
