"""Model access for the panel.

Every panel member reaches the model through the Flower runtime, using the OpenAI
SDK pointed at the runtime base URL. One client is shared across threads; the SDK
is thread-safe and each call opens its own child model task in the runtime.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI

# Round-1 and round-2 calls are non-streaming: we need a whole JSON document
# before we can act on it. Only the master's closing report streams.
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def build_client() -> OpenAI:
    """Create a client bound to the Flower runtime."""
    try:
        base_url = os.environ["FLWR_RUNTIME_BASE_URL"]
        api_key = os.environ["FLWR_RUNTIME_API_KEY"]
    except KeyError as err:
        raise RuntimeError(
            "Missing Flower runtime environment. Run this app through "
            "`flwr run`, not as a plain Python script."
        ) from err

    # One retry, because a panel of ten concurrent calls will occasionally see a
    # transient failure and losing a whole reviewer to it skews the vote.
    return OpenAI(base_url=base_url, api_key=api_key, max_retries=1)


def json_call(
    client: OpenAI,
    *,
    model: str,
    instructions: str,
    prompt: str,
    schema_name: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Ask the model for one JSON document matching `schema`.

    Raises on anything that is not parseable JSON, so a mangled reply drops the
    calling agent out of the vote rather than silently counting as agreement.
    """
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
    )

    text = (response.output_text or "").strip()
    if not text:
        raise ValueError("Model returned an empty response.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Served models behind the runtime do not all honour strict json_schema.
        # Recover the outermost JSON object rather than losing the reviewer.
        match = _JSON_BLOCK.search(text)
        if not match:
            raise ValueError(f"Model returned no JSON object: {text[:200]!r}") from None
        return json.loads(match.group(0))


FINDINGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings"],
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "title",
                    "file",
                    "line",
                    "severity",
                    "claim",
                    "failure_scenario",
                    "confidence",
                ],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Six words or fewer.",
                    },
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "claim": {
                        "type": "string",
                        "description": "One sentence stating the defect.",
                    },
                    "failure_scenario": {
                        "type": "string",
                        "description": "Concrete inputs or conditions, then the wrong result.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "0.0 to 1.0.",
                    },
                },
            },
        }
    },
}

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["refuted", "reasoning", "confidence"],
    "properties": {
        "refuted": {
            "type": "boolean",
            "description": "True if the finding does not hold.",
        },
        "reasoning": {
            "type": "string",
            "description": "One or two sentences citing the code.",
        },
        "confidence": {"type": "number", "description": "0.0 to 1.0."},
    },
}
