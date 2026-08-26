"""Deterministic similarity and network-wide ranking.

This module is the one part of the system that must produce identical numbers
everywhere. Sites are separate processes in separate institutions; if each one
scored similarity with its own model call, a 0.85 from site A and a 0.85 from
site B would not be the same claim, and ranking across them would measure
scoring noise rather than similarity. So the number is computed by identical
deterministic code at every site, and the agents are left to do the judgement.

The ranking rule matters as much as the metric. The corpus is wildly uneven -
hundreds of cases for some diseases, one or two for many - so any score that
scales with the number of matching patients hands the top of the list to
whatever is best published. That is the exact opposite of the point. Rank on
normalised top-N similarity; carry the count as provenance only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# How many of a disease's best-matching patients contribute to its score.
# Fewer than this is not penalised: a disease with one 0.80 match scores 0.80,
# which is how a genuinely rare presentation stays competitive with a common one.
TOP_N = 3


def similarity(query_symptoms: list[str], record_symptoms: list[str]) -> float:
    """Jaccard overlap of two symptom sets.

    Deliberately dumb. It decides what gets discussed, not what is true - the
    lenses do that, and they see the symptom names rather than this number.
    """
    a = {s.strip().lower() for s in query_symptoms if s.strip()}
    b = {s.strip().lower() for s in record_symptoms if s.strip()}
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def symptom_breakdown(
    query_symptoms: list[str], record_symptoms: list[str]
) -> dict[str, list[str]]:
    """Which symptoms are shared, which the query has alone, which the record has alone.

    The lenses reason about these names; the float above only orders the list.
    """
    a = {s.strip().lower() for s in query_symptoms if s.strip()}
    b = {s.strip().lower() for s in record_symptoms if s.strip()}
    return {
        "shared": sorted(a & b),
        "absent_in_record": sorted(a - b),
        "extra_in_record": sorted(b - a),
    }


def top_n_mean(scores: list[float], n: int = TOP_N) -> float:
    """Mean of the best `n` scores, taking fewer if fewer exist.

    Fewer-than-n is not penalised. Averaging over a fixed n and padding with
    zeros would reintroduce exactly the count bias this is here to avoid.
    """
    if not scores:
        return 0.0
    best = sorted(scores, reverse=True)[:n]
    return sum(best) / len(best)


@dataclass
class DiseaseEvidence:
    """One disease's evidence, pooled across every site that reported it."""

    disease: str
    # Best per-patient scores contributed by each site, pooled. Not averaged per
    # site: that would let a site with many cases outvote a site with one.
    scores: list[float] = field(default_factory=list)
    # Provenance. Never an input to the score.
    case_count: int = 0
    sites: list[str] = field(default_factory=list)
    shared_symptoms: list[str] = field(default_factory=list)
    absent_symptoms: list[str] = field(default_factory=list)
    abstractions: list[dict] = field(default_factory=list)

    @property
    def score(self) -> float:
        return top_n_mean(self.scores)


def rank_network(site_reports: list[dict]) -> list[DiseaseEvidence]:
    """Pool per-site disease evidence and rank it for the whole network.

    `site_reports` is one entry per responding site:
        {"site": "st-mary", "diseases": [
            {"disease": ..., "top_scores": [...], "case_count": int,
             "shared_symptoms": [...], "absent_symptoms": [...],
             "abstraction": {...}}, ...]}

    Scores from every site land in one pool and the best TOP_N of that pool are
    averaged, so the network's three best-matching patients decide the ranking
    no matter which hospitals they came from.
    """
    pooled: dict[str, DiseaseEvidence] = {}

    for report in site_reports:
        site = str(report.get("site", "unknown"))
        for entry in report.get("diseases") or []:
            name = str(entry.get("disease", "")).strip()
            if not name:
                continue
            ev = pooled.setdefault(name, DiseaseEvidence(disease=name))
            ev.scores.extend(float(s) for s in entry.get("top_scores") or [])
            ev.case_count += int(entry.get("case_count", 0))
            if site not in ev.sites:
                ev.sites.append(site)
            for sym in entry.get("shared_symptoms") or []:
                if sym not in ev.shared_symptoms:
                    ev.shared_symptoms.append(sym)
            for sym in entry.get("absent_symptoms") or []:
                if sym not in ev.absent_symptoms:
                    ev.absent_symptoms.append(sym)
            abstraction = entry.get("abstraction")
            if abstraction:
                ev.abstractions.append({"site": site, **abstraction})

    # Score first, then case count purely to break exact ties deterministically.
    # A tie-break cannot promote a lower-scoring disease above a higher one.
    return sorted(pooled.values(), key=lambda e: (e.score, e.case_count), reverse=True)
