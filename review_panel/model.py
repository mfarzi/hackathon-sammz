"""Model access for the panel.

Every panel member reaches the model through the Flower runtime, using the OpenAI
SDK pointed at the runtime base URL. One client is shared across threads; the SDK
is thread-safe and each call opens its own child model task in the runtime.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

# Round-1 and round-2 calls are non-streaming: we need a whole JSON document
# before we can act on it. Only the master's closing report streams.
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _load_dotenv() -> None:
    """Pull credentials from a .env file near the working directory.

    Flower runs the ServerApp and each ClientApp as separate processes, launched
    by a SuperLink that may have started before the shell exported anything. An
    app that only reads its own environment therefore works or fails depending on
    launch order, which is not a thing to debug during a demo. Searching upward
    from the working directory makes it work either way.

    Only fills variables that are not already set: a real environment always wins.
    """
    here = Path.cwd()
    for directory in [here, *here.parents]:
        candidate = directory / ".env"
        if not candidate.is_file():
            continue
        try:
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            pass
        return


def build_client() -> OpenAI:
    """Create a model client, from a ServerApp, a ClientApp, or a plain script.

    Prefers the Flower runtime, which is what every panel member and site agent
    uses in a real run. Falls back to a directly configured OpenAI-compatible
    endpoint so the pipeline can be developed and demoed without the runtime -
    the alternative is that nothing downstream of a model call can be tested
    until deployment, which is the wrong risk to carry into a deadline.
    """
    base_url = os.environ.get("FLWR_RUNTIME_BASE_URL")
    api_key = os.environ.get("FLWR_RUNTIME_API_KEY")

    if not (base_url and api_key):
        _load_dotenv()
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")  # None is fine: SDK default
        if not api_key:
            raise RuntimeError(
                "No model access. Inside `flwr run` the Flower runtime supplies "
                "FLWR_RUNTIME_BASE_URL and FLWR_RUNTIME_API_KEY; outside it, set "
                "OPENAI_API_KEY (and optionally OPENAI_BASE_URL)."
            )

    # One retry, because a panel of ten concurrent calls will occasionally see a
    # transient failure and losing a whole reviewer to it skews the vote.
    return OpenAI(base_url=base_url, api_key=api_key, max_retries=1)


def runtime_is_available() -> bool:
    """Whether the Flower runtime supplied model credentials to this process."""
    return bool(
        os.environ.get("FLWR_RUNTIME_BASE_URL") and os.environ.get("FLWR_RUNTIME_API_KEY")
    )


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
