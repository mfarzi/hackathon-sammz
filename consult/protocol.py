"""What travels between the hub and the hospital sites.

Payloads are JSON strings inside a ConfigRecord, because Flower's record values
are scalars and the structures here are nested. Keeping every payload behind
`pack`/`unpack` means there is exactly one place to look when asking what a
site is capable of sending.
"""

from __future__ import annotations

import json
from typing import Any

from flwr.app import ConfigRecord, Message, RecordDict

RECORD_KEY = "consult"
PAYLOAD_KEY = "payload"

# Message types. The suffix routes to the matching @app.query(...) handler.
CONSULT = "query.consult"
FOLLOWUP = "query.followup"


def pack(payload: dict[str, Any]) -> RecordDict:
    """Wrap a payload for sending."""
    return RecordDict({RECORD_KEY: ConfigRecord({PAYLOAD_KEY: json.dumps(payload)})})


def unpack(message: Message) -> dict[str, Any]:
    """Read a payload from a received message."""
    raw = message.content[RECORD_KEY][PAYLOAD_KEY]
    return json.loads(str(raw))


def reply(message: Message, payload: dict[str, Any]) -> Message:
    """Build a reply to `message` carrying `payload`."""
    return Message(pack(payload), reply_to=message)
