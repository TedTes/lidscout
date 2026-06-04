"""Stable keys for planned agent action idempotency."""
from __future__ import annotations

import json
from typing import Any

from domain.agent import AgentAction


def agent_action_dedupe_key(action: AgentAction) -> tuple[str, str]:
    """Return a stable key for suppressing duplicate planned actions."""
    metadata = action.metadata
    target = _target_metadata(action.action_type, metadata)
    return (
        action.action_type,
        json.dumps(target, sort_keys=True, separators=(",", ":")),
    )


def _target_metadata(action_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
    if action_type == "answer_follow_up":
        return {"follow_up_id": metadata.get("follow_up_id")}
    if action_type == "pause_source":
        return {"source_id": metadata.get("source_id")}
    if action_type == "source_needs_attention":
        return {"source_id": metadata.get("source_id")}
    if action_type == "send_alert":
        return {"alert_id": metadata.get("alert_id")}
    if action_type == "suggest_source":
        return {
            "locator": metadata.get("locator"),
            "niche_id": metadata.get("niche_id"),
            "source_count": metadata.get("source_count"),
        }
    if action_type == "scan_sources":
        return {"niche_id": metadata.get("niche_id")}
    return metadata
