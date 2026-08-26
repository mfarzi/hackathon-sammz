"""JSON schemas for every model call in the consult pipeline.

Kept in one place because the schemas are the contract between the agents: what
a site is allowed to say back, what a lens is allowed to assert, what the hub
may ask. Several of them exist as much to constrain output as to shape it - the
site abstraction schema has no field for a patient identifier, so there is
nowhere for one to go even if a model tried.
"""

from __future__ import annotations

from typing import Any

# --- hub: clinician's free text -> a structured query -----------------------

QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["symptoms", "gender", "age_bracket", "summary"],
    "properties": {
        "symptoms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "snake_case symptom tokens, e.g. orofacial_dyskinesia.",
        },
        "gender": {"type": "string", "description": "M, F, or empty if not stated."},
        "age_bracket": {
            "type": "string",
            "description": "e.g. 18-30, 31-40, or empty if not stated.",
        },
        "summary": {
            "type": "string",
            "description": "One sentence restating the presentation.",
        },
    },
}

# --- site: what an agent may say about its own patients ---------------------

ABSTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["abstractions"],
    "properties": {
        "abstractions": {
            "type": "array",
            "description": "One entry per disease you were asked about.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["disease", "pattern", "supporting", "arguing_against"],
                "properties": {
                    "disease": {"type": "string"},
                    "pattern": {
                        "type": "string",
                        "description": (
                            "Two or three sentences on what this site's matching cases "
                            "had in common: onset, course, what was notably absent. "
                            "Describe the group, never an individual, and quote no "
                            "identifying detail."
                        ),
                    },
                    "supporting": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Features of our cases fitting the queried presentation.",
                    },
                    "arguing_against": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Features that do not fit. Report these even when they "
                            "weaken the match - a site that only volunteers agreement "
                            "is useless."
                        ),
                    },
                },
            },
        }
    },
}

# --- hub -> site: the second hop --------------------------------------------

FOLLOWUP_QUESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["question", "target_disease", "why"],
    "properties": {
        "question": {
            "type": "string",
            "description": (
                "One specific clinical question answerable from case records that "
                "would discriminate between the leading candidates."
            ),
        },
        "target_disease": {
            "type": "string",
            "description": "Which candidate the answer would most change.",
        },
        "why": {"type": "string", "description": "One sentence: what it would settle."},
    },
}

FOLLOWUP_ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "has_evidence"],
    "properties": {
        "answer": {
            "type": "string",
            "description": (
                "What this site's records show, aggregated. Say so plainly if the "
                "records do not answer the question."
            ),
        },
        "has_evidence": {
            "type": "boolean",
            "description": "False if our records cannot answer it.",
        },
    },
}

# --- panel: a lens assessing the network's candidates ------------------------

ASSESSMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["disease", "claim", "reasoning", "confidence"],
                "properties": {
                    "disease": {
                        "type": "string",
                        "description": "Must be one of the candidate diseases given.",
                    },
                    "claim": {
                        "type": "string",
                        "description": (
                            "One sentence on why this candidate could explain the "
                            "patient's presentation as a whole, within your mandate. "
                            "Never a claim that the candidate does NOT fit - omit it "
                            "instead."
                        ),
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "The specific evidence, cited from what you were shown.",
                    },
                    "confidence": {"type": "number", "description": "0.0 to 1.0."},
                },
            },
        }
    },
}
