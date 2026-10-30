"""Centralized audit logging.

Every event is appended to an in-memory list and printed to stdout — the
terminal running `adk web` — so the harness's decisions are visible during
a demo. Never log API keys, secrets, chain-of-thought, or full account
numbers; only structured banking events.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger("banking_agent.audit")
if not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[AUDIT] %(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

_events: list[dict[str, Any]] = []

# Optional persistent trail: set AUDIT_LOG_FILE to append one JSON object per
# event, so the record survives an `adk web` restart (in-memory state doesn't).


def _write_file(path: str, entry: dict[str, Any]) -> None:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **entry}, default=str) + "\n")
    except OSError as exc:  # logging must never break a banking request
        _logger.warning("Could not write AUDIT_LOG_FILE=%r: %s", path, exc)


def log(event_type: str, **details: Any) -> None:
    entry = {"event": event_type, **details}
    _events.append(entry)
    path = os.environ.get("AUDIT_LOG_FILE", "").strip()  # read late: .env loads after import
    if path:
        _write_file(path, entry)
    detail_str = " ".join(f"{k}={v!r}" for k, v in details.items())
    _logger.info("%s %s", event_type, detail_str)


def events() -> list[dict[str, Any]]:
    """All audit events recorded so far, oldest first."""
    return list(_events)
