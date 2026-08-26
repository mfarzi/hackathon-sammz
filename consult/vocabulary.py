"""The controlled symptom vocabulary shared by every site.

Retrieval matches symptom tokens exactly, so the hub's parse of a clinician's
free text has to land on the same tokens the records use. Left unconstrained a
model writes plausible synonyms - `seizures` for `seizure`, `subacute_confusion`
for `confusion` - and every one of them silently matches nothing. A consult that
returns an empty network because of vocabulary drift looks exactly like a
consult that found no comparable case, which is the worst possible failure.

So the vocabulary is closed and the parse is constrained to it. In a real
deployment this is a shared clinical ontology agreed between sites; here it is
derived from the corpus. Either way it is a symptom list, not patient data, and
carries nothing identifying.
"""

from __future__ import annotations

import json
from pathlib import Path

_VOCAB_PATH = Path(__file__).resolve().parent / "symptom_vocabulary.json"


def load_vocabulary() -> list[str]:
    """The full list of symptom tokens the records use."""
    try:
        tokens = json.loads(_VOCAB_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return sorted({str(t).strip().lower() for t in tokens if str(t).strip()})


def constrain(symptoms: list[str], vocabulary: list[str]) -> tuple[list[str], list[str]]:
    """Keep only tokens the vocabulary contains; report the rest.

    Returns `(kept, dropped)`. Dropped tokens are surfaced rather than silently
    discarded - if the parse is drifting, the run should say so out loud.

    A light singular/plural fallback is applied first, because that one
    difference accounts for most near-misses and costs nothing to absorb.
    """
    known = set(vocabulary)
    kept, dropped = [], []
    for raw in symptoms:
        token = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
        if token in known:
            kept.append(token)
        elif token.endswith("s") and token[:-1] in known:
            kept.append(token[:-1])
        elif f"{token}s" in known:
            kept.append(f"{token}s")
        else:
            dropped.append(token)
    # Preserve order but drop repeats: a symptom named twice is not stronger.
    seen, unique = set(), []
    for token in kept:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique, dropped
