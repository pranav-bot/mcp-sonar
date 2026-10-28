from __future__ import annotations

import json
from typing import Any


def last_json_object(text: str) -> dict[str, Any]:
    """Return the last valid JSON object in text.

    Log lines and model replies often contain an earlier brace. The object
    that finishes the payload is the one callers want.
    """
    decoder = json.JSONDecoder()
    found: dict[str, Any] | None = None
    found_end = -1
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        # Prefer the object that finishes latest. That is the last top-level
        # object, not a nested one inside it.
        if isinstance(value, dict) and end > found_end:
            found = value
            found_end = end
    if found is None:
        raise ValueError("text did not contain a JSON object")
    return found
