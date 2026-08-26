"""The five review lenses.

Each lens is a deliberately narrow reviewer. Narrowness is the point: five agents
given the same prompt only sample variance, whereas five agents given disjoint
mandates catch failure modes that redundancy cannot.
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
        key="correctness",
        title="Correctness",
        mandate=(
            "Logic that produces a wrong result: off-by-one errors, inverted or "
            "short-circuiting conditionals, wrong operator, mishandled empty or "
            "single-element inputs, state mutated while being iterated, integer or "
            "float precision mistakes. You do not care about style, security, or "
            "speed - only about inputs that yield an incorrect output."
        ),
    ),
    Lens(
        key="security",
        title="Security",
        mandate=(
            "Untrusted input reaching a dangerous sink: SQL/command/template "
            "injection, path traversal, unsafe deserialisation, missing "
            "authorisation checks, secrets in source, tokens compared "
            "non-constant-time. You do not care about performance or readability - "
            "only about what an attacker can actually cause."
        ),
    ),
    Lens(
        key="performance",
        title="Performance",
        mandate=(
            "Work that scales worse than it needs to: accidental quadratic loops, "
            "N+1 queries, IO or allocation inside a hot loop, repeated recomputation "
            "of an invariant, unbounded memory growth. Quantify the complexity you "
            "claim. You do not care about correctness or security."
        ),
    ),
    Lens(
        key="robustness",
        title="Error handling and robustness",
        mandate=(
            "How the code behaves when something goes wrong: exceptions swallowed "
            "into silence, bare excepts, resources leaked on the error path, retries "
            "without backoff, partial writes left uncommitted, error values ignored "
            "by the caller. You do not care whether the happy path is correct."
        ),
    ),
    Lens(
        key="contracts",
        title="Contracts and testability",
        mandate=(
            "Interfaces that invite misuse: undocumented invariants, functions that "
            "return different shapes on different paths, mutable default arguments, "
            "behaviour that cannot be tested without network or clock, missing "
            "coverage of a branch that carries real risk. You do not care about "
            "speed or attackers."
        ),
    ),
)

LENSES_BY_KEY = {lens.key: lens for lens in LENSES}


def review_instructions(lens: Lens, max_findings: int) -> str:
    """Build the round-1 system prompt for one lens."""
    return (
        f"You are the {lens.title} reviewer on a code review panel.\n\n"
        f"Your mandate, and nothing outside it:\n{lens.mandate}\n\n"
        "You are reviewing blind: you cannot see the other reviewers' findings, and "
        "you must not speculate about them. Report only defects you can tie to "
        "specific code, with a concrete failure scenario - inputs or conditions, and "
        "the wrong behaviour that results. A finding you cannot make concrete is not "
        "a finding.\n\n"
        f"Report at most {max_findings} findings. Fewer is better than padded. "
        "Reporting zero findings is a valid and respectable outcome; do not invent "
        "work to look thorough. Style opinions, naming preferences, and hypothetical "
        "refactors are not defects."
    )


def refute_instructions(lens: Lens) -> str:
    """Build the round-2 system prompt for one refuter."""
    return (
        f"You are the {lens.title} reviewer, acting now as an adversarial verifier.\n\n"
        "Another reviewer has raised the finding below. Your job is to REFUTE it. "
        "Read the code and try to show the finding is wrong, already prevented "
        "elsewhere, unreachable in practice, or a misreading of what the code does.\n\n"
        "You are judging this finding alone. You cannot see other verifiers' verdicts "
        "and must not guess at them. Judge the claim on the code as written, not on "
        "how confident the claim sounds.\n\n"
        "Default to refuted=true when you are uncertain. A finding survives only by "
        "withstanding a genuine attempt to break it, so the burden of proof sits with "
        "the finding, not with you. Set refuted=false only when you tried to refute it "
        "and could not."
    )
