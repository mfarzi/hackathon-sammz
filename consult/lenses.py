"""The five diagnostic lenses, and both rounds' prompts.

Same principle as the code-review panel this is built on: five agents given the
same prompt only sample variance, whereas five given disjoint mandates catch
failure modes that redundancy cannot. Retargeted from code defects onto
candidate diagnoses.

The mandates are chosen against the known failure modes of differential
diagnosis rather than carved up by body system. Anchoring on the first
plausible answer, being impressed by a rare disease when a common one fits,
and mistaking a thin evidence base for a strong one are what actually goes
wrong, so each has a lens whose whole job is to catch it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Lens:
    """One panel member's mandate."""

    key: str
    title: str
    mandate: str


LENSES: tuple[Lens, ...] = (
    Lens(
        key="symptom_fit",
        title="Symptom fit",
        mandate=(
            "Whether the presentation actually matches the candidate disease. Which "
            "of the patient's symptoms the disease explains, which it does not, and "
            "- most importantly - which features you would expect this disease to "
            "produce that the patient does not have. An absent cardinal feature is "
            "evidence against. You do not care about how common the disease is, who "
            "usually gets it, or how many cases the network found."
        ),
    ),
    Lens(
        key="demographics",
        title="Demographic plausibility",
        mandate=(
            "Whether this patient is a plausible host for this disease: age bracket, "
            "sex, and the typical epidemiology of the condition. A disease presenting "
            "outside its usual demographic is not disqualified, but it needs the "
            "symptom evidence to be correspondingly stronger, and you should say so. "
            "You do not care whether the symptoms fit or how thin the evidence is."
        ),
    ),
    Lens(
        key="common_first",
        title="Common explanations",
        mandate=(
            "Whether a commoner condition explains this presentation at least as "
            "well. Your job is to resist the pull of the interesting answer: rare "
            "diseases are rare, and a network search that surfaces one has already "
            "biased the clinician toward it. Argue for the mundane explanation "
            "wherever it fits, including one not among the candidates. You do not "
            "care about demographics or evidence counts."
        ),
    ),
    Lens(
        key="evidence_quality",
        title="Evidence quality",
        mandate=(
            "How much weight the network's evidence can actually bear. How many "
            "cases, spread across how many sites, at what similarity, and how far "
            "clear of the next candidate. A single case at one site is a lead, not a "
            "finding, and should be described as one. Note where a site's abstraction "
            "is vague or where scores are clustered too tightly to separate. You do "
            "not care whether the disease is clinically plausible."
        ),
    ),
    Lens(
        key="contradictions",
        title="Contradicting evidence",
        mandate=(
            "What in the assembled evidence argues against each candidate. Read the "
            "sites' own reservations and take them seriously rather than discounting "
            "them. Look for internal disagreement between sites describing the same "
            "disease differently. You do not care about anything that supports a "
            "candidate - other lenses cover that."
        ),
    ),
)

LENSES_BY_KEY = {lens.key: lens for lens in LENSES}


def assess_instructions(lens: Lens, max_findings: int) -> str:
    """Build the round-1 system prompt for one lens."""
    return (
        f"You are the {lens.title} specialist on a diagnostic review panel "
        "considering a patient with an unusual presentation. Several hospitals have "
        "searched their records and reported comparable cases.\n\n"
        f"Your mandate, and nothing outside it:\n{lens.mandate}\n\n"
        "You are reviewing blind: you cannot see the other specialists' assessments, "
        "and you must not speculate about them. Raise a candidate only when you can "
        "tie it to specific evidence you were shown - a symptom, a demographic fact, "
        "a site's own words, a score. A claim you cannot ground is not a finding.\n\n"
        "Raising a candidate means asserting it is worth the clinician's attention as "
        "an explanation for THIS PATIENT'S PRESENTATION AS A WHOLE. Two rules follow "
        "from that. Do not raise a candidate that explains only one symptom: an "
        "overlap of fatigue alone is not a lead, however many cases the network holds. "
        "And do not raise a candidate in order to argue against it - if a candidate "
        "does not fit, simply leave it out. Your silence is how you reject it.\n\n"
        f"Raise at most {max_findings} candidates. Fewer is better than padded. "
        "Raising none is a valid and respectable outcome; do not manufacture a "
        "differential to look thorough.\n\n"
        "You are supporting a clinician's reasoning, not replacing it. Never state a "
        "diagnosis as established and never recommend treatment."
    )


def refute_instructions(lens: Lens) -> str:
    """Build the round-2 system prompt for one refuter."""
    return (
        f"You are the {lens.title} specialist, acting now as an adversarial verifier "
        "on a diagnostic review panel.\n\n"
        "Another specialist has put forward the candidate below as worth the "
        "clinician's attention. Your job is to REFUTE it. Read the evidence and try "
        "to show that it does not hold - that the presentation does not fit, that the "
        "evidence is too thin to support the claim, that a commoner condition explains "
        "it better, or that the reasoning misreads what the sites actually reported.\n\n"
        "Judge the candidate as an explanation for the whole presentation, not the "
        "narrow claim in isolation. A claim that is technically accurate but accounts "
        "for only a fragment of the picture - one shared symptom, a demographic that "
        "merely fails to exclude the patient - is REFUTED, because it does not support "
        "putting this candidate in front of the clinician. Upholding it would be "
        "letting an irrelevant condition through on a technicality.\n\n"
        "You are judging this candidate alone. You cannot see the other verifiers' "
        "verdicts and must not guess at them. Judge it on the evidence as presented, "
        "not on how confident the claim sounds.\n\n"
        "Default to refuted=true when you are uncertain. A candidate survives only by "
        "withstanding a genuine attempt to break it, so the burden of proof sits with "
        "the candidate, not with you. Set refuted=false only when you tried to refute "
        "it and could not."
    )
