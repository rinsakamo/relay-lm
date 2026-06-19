"""Minimal non-streaming RelayCTX Unpack contract.

The Phase 5-A parser accepts ordinary response text and an optional explicit,
trailing JSON update block. It never guesses JSON/YAML from normal prose and it
never persists CTX, MEM, SOUL, or SLP state.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result


RELAYCTX_UPDATE_OPEN = "<relayctx_working_update>"
RELAYCTX_UPDATE_CLOSE = "</relayctx_working_update>"
RELAYCTX_UPDATE_SCHEMA_VERSION = "relayctx_working_update.v0"

RelayCTXUnpackStatus = Literal[
    "plain_text",
    "structured_update",
    "update_blocked",
    "empty_response",
]

_ALLOWED_UPDATE_FIELDS = frozenset(
    {
        "current_topic",
        "active_task",
        "active_question",
        "last_decision",
        "last_options",
        "referable_items",
        "unresolved_slots",
        "response_mode_hint",
        "next_expected_action",
    }
)
_DECISION_STATUSES = frozenset(
    {"candidate", "agreed", "rejected", "question", "pending"}
)
_REFERABLE_KINDS = frozenset(
    {
        "topic",
        "decision",
        "option",
        "task",
        "component",
        "object",
        "plan",
        "configuration",
    }
)


@dataclass(frozen=True)
class RelayCTXUnpackResult:
    """One content-separated non-streaming backend response."""

    user_visible_text: str
    ctx_working_update: dict[str, Any] | None
    status: RelayCTXUnpackStatus
    marker_present: bool
    update_candidate_present: bool
    update_accepted: bool
    blocked_reasons: tuple[str, ...]
    input_chars: int
    update_chars: int
    accepted_field_names: tuple[str, ...]

    def to_log_dict(self) -> dict[str, Any]:
        """Return content-free diagnostics for trace and node-result recording."""

        return {
            "schema_version": "relayctx_unpack_result.v0",
            "status": self.status,
            "marker_present": self.marker_present,
            "update_candidate_present": self.update_candidate_present,
            "update_accepted": self.update_accepted,
            "blocked_reasons": list(self.blocked_reasons),
            "input_chars": self.input_chars,
            "visible_chars": len(self.user_visible_text),
            "update_chars": self.update_chars,
            "accepted_field_names": list(self.accepted_field_names),
            "contains_user_visible_text": bool(self.user_visible_text),
            "contains_ctx_working_update": self.ctx_working_update is not None,
            "content_free": True,
            "persistence_allowed": False,
        }


def unpack_relayctx_response_text(
    response_text: str | None,
    *,
    max_update_chars: int = 4096,
) -> RelayCTXUnpackResult:
    """Separate visible text from one strict trailing CTX update block.

    Accepted structured form::

        user-visible response
        <relayctx_working_update>
        {"schema_version":"relayctx_working_update.v0",
         "ctx_working_update":{...}}
        </relayctx_working_update>

    On malformed or unexpected input, visible text is preserved when possible
    while the internal update candidate is blocked.
    """

    if not isinstance(response_text, str) or not response_text.strip():
        return RelayCTXUnpackResult(
            user_visible_text="",
            ctx_working_update=None,
            status="empty_response",
            marker_present=False,
            update_candidate_present=False,
            update_accepted=False,
            blocked_reasons=("response_text_empty",),
            input_chars=len(response_text) if isinstance(response_text, str) else 0,
            update_chars=0,
            accepted_field_names=(),
        )

    input_chars = len(response_text)
    open_index = response_text.find(RELAYCTX_UPDATE_OPEN)
    first_close_index = response_text.find(RELAYCTX_UPDATE_CLOSE)

    if open_index < 0 and first_close_index < 0:
        return RelayCTXUnpackResult(
            user_visible_text=response_text,
            ctx_working_update=None,
            status="plain_text",
            marker_present=False,
            update_candidate_present=False,
            update_accepted=False,
            blocked_reasons=(),
            input_chars=input_chars,
            update_chars=0,
            accepted_field_names=(),
        )

    if open_index < 0:
        return _blocked_result(
            visible=response_text[:first_close_index].rstrip(),
            input_chars=input_chars,
            update_chars=max(0, input_chars - first_close_index),
            reasons=("opening_marker_missing",),
        )

    if 0 <= first_close_index < open_index:
        return _blocked_result(
            visible=response_text[:first_close_index].rstrip(),
            input_chars=input_chars,
            update_chars=max(0, input_chars - first_close_index),
            reasons=("closing_marker_before_opening",),
        )

    visible_prefix = response_text[:open_index].rstrip()
    payload_start = open_index + len(RELAYCTX_UPDATE_OPEN)
    closing_after_open = response_text.rfind(RELAYCTX_UPDATE_CLOSE, payload_start)
    if closing_after_open < 0:
        return _blocked_result(
            visible=visible_prefix,
            input_chars=input_chars,
            update_chars=max(0, input_chars - open_index),
            reasons=("closing_marker_missing",),
        )

    raw_payload_text = response_text[payload_start:closing_after_open]
    payload_text = raw_payload_text.strip()
    raw_update_chars = len(raw_payload_text)
    suffix = response_text[closing_after_open + len(RELAYCTX_UPDATE_CLOSE) :]
    reasons: list[str] = []

    if RELAYCTX_UPDATE_OPEN in payload_text:
        reasons.append("multiple_opening_markers")
    if RELAYCTX_UPDATE_CLOSE in payload_text:
        reasons.append("embedded_closing_marker")

    max_chars_valid = (
        isinstance(max_update_chars, int)
        and not isinstance(max_update_chars, bool)
        and max_update_chars > 0
    )
    if not payload_text:
        reasons.append("update_payload_empty")
    if not max_chars_valid or raw_update_chars > max_update_chars:
        reasons.append("update_payload_too_large")

    envelope: Any = None
    payload_json_valid = False
    if payload_text and max_chars_valid and raw_update_chars <= max_update_chars:
        try:
            envelope = json.loads(payload_text)
            payload_json_valid = True
            if _contains_internal_marker(envelope):
                reasons.append("decoded_internal_marker")
        except json.JSONDecodeError:
            reasons.append("update_json_invalid")

    # Suffix text is exposed only after the complete payload parses as JSON.
    # This prevents JSON tails after an embedded close-marker from leaking.
    visible_suffix = ""
    if payload_json_valid:
        visible_suffix, suffix_marker_reasons = _safe_visible_suffix(suffix)
        reasons.extend(suffix_marker_reasons)
        if visible_suffix:
            reasons.append("update_block_not_trailing")

    visible = _join_visible_parts(visible_prefix, visible_suffix)
    if not visible:
        reasons.append("user_visible_text_empty")

    if reasons:
        return _blocked_result(
            visible=visible,
            input_chars=input_chars,
            update_chars=raw_update_chars,
            reasons=tuple(_dedupe(reasons)),
        )

    update, validation_reasons = _validate_envelope(envelope)
    if validation_reasons:
        return _blocked_result(
            visible=visible,
            input_chars=input_chars,
            update_chars=raw_update_chars,
            reasons=tuple(validation_reasons),
        )

    assert update is not None
    return RelayCTXUnpackResult(
        user_visible_text=visible,
        ctx_working_update=deepcopy(update),
        status="structured_update",
        marker_present=True,
        update_candidate_present=True,
        update_accepted=True,
        blocked_reasons=(),
        input_chars=input_chars,
        update_chars=raw_update_chars,
        accepted_field_names=tuple(sorted(update)),
    )


def build_relayctx_unpack_node_result(
    result: RelayCTXUnpackResult,
) -> PipelineNodeResult:
    """Build the Phase 4.5-compatible node result without copying content."""

    status = (
        "applied"
        if result.status == "structured_update"
        else "blocked"
        if result.status == "update_blocked"
        else "failed"
        if result.status == "empty_response"
        else "diagnostic_only"
    )
    return build_pipeline_node_result(
        node_name="relayctx_unpack",
        status=status,
        decision=result.status,
        blocked_reasons=result.blocked_reasons,
        diagnostics=result.to_log_dict(),
        artifacts=[
            {
                "artifact_name": "relayctx_unpack_result",
                "schema_version": "relayctx_unpack_result.v0",
                "present": True,
                "content_free": True,
                "update_accepted": result.update_accepted,
            }
        ],
    )


def _validate_envelope(
    envelope: Any,
) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(envelope, Mapping):
        return None, ["update_envelope_not_object"]

    reasons: list[str] = []
    if any(key not in {"schema_version", "ctx_working_update"} for key in envelope):
        reasons.append("update_envelope_unknown_fields")
    if envelope.get("schema_version") != RELAYCTX_UPDATE_SCHEMA_VERSION:
        reasons.append("update_schema_version_invalid")

    raw_update = envelope.get("ctx_working_update")
    if not isinstance(raw_update, Mapping):
        reasons.append("ctx_working_update_not_object")
        return None, reasons

    normalized, update_reasons = _validate_working_update(raw_update)
    reasons.extend(update_reasons)
    return (normalized if not reasons else None), _dedupe(reasons)


def _validate_working_update(
    raw_update: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    reasons: list[str] = []
    if any(key not in _ALLOWED_UPDATE_FIELDS for key in raw_update):
        reasons.append("ctx_working_update_unknown_fields")

    normalized: dict[str, Any] = {}
    for field_name in (
        "current_topic",
        "active_task",
        "active_question",
        "response_mode_hint",
        "next_expected_action",
    ):
        if field_name not in raw_update:
            continue
        value = raw_update[field_name]
        if value is None:
            normalized[field_name] = None
        elif _bounded_string(value, max_chars=512):
            normalized[field_name] = value
        else:
            reasons.append(f"{field_name}_invalid")

    if "last_decision" in raw_update:
        value, item_reasons = _validate_last_decision(raw_update["last_decision"])
        reasons.extend(item_reasons)
        if not item_reasons:
            normalized["last_decision"] = value

    if "last_options" in raw_update:
        value, item_reasons = _validate_last_options(raw_update["last_options"])
        reasons.extend(item_reasons)
        if not item_reasons:
            normalized["last_options"] = value

    if "referable_items" in raw_update:
        value, item_reasons = _validate_referable_items(raw_update["referable_items"])
        reasons.extend(item_reasons)
        if not item_reasons:
            normalized["referable_items"] = value

    if "unresolved_slots" in raw_update:
        value, item_reasons = _validate_unresolved_slots(raw_update["unresolved_slots"])
        reasons.extend(item_reasons)
        if not item_reasons:
            normalized["unresolved_slots"] = value

    if not raw_update:
        reasons.append("ctx_working_update_empty")

    return normalized, _dedupe(reasons)


def _validate_last_decision(value: Any) -> tuple[dict[str, Any] | None, list[str]]:
    if value is None:
        return None, []
    if not isinstance(value, Mapping):
        return None, ["last_decision_invalid"]
    if any(key not in {"text", "status", "confidence"} for key in value):
        return None, ["last_decision_unknown_fields"]
    if not _bounded_string(value.get("text"), max_chars=512):
        return None, ["last_decision_text_invalid"]
    if value.get("status") not in _DECISION_STATUSES:
        return None, ["last_decision_status_invalid"]
    if not _probability(value.get("confidence")):
        return None, ["last_decision_confidence_invalid"]
    return {
        "text": value["text"],
        "status": value["status"],
        "confidence": float(value["confidence"]),
    }, []


def _validate_last_options(value: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not _bounded_sequence(value, max_items=8):
        return [], ["last_options_invalid"]
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return [], ["last_options_item_invalid"]
        if any(key not in {"label", "status"} for key in item):
            return [], ["last_options_item_unknown_fields"]
        if not _bounded_string(item.get("label"), max_chars=256):
            return [], ["last_options_label_invalid"]
        if item.get("status") not in _DECISION_STATUSES:
            return [], ["last_options_status_invalid"]
        normalized.append({"label": item["label"], "status": item["status"]})
    return normalized, []


def _validate_referable_items(value: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not _bounded_sequence(value, max_items=12):
        return [], ["referable_items_invalid"]
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return [], ["referable_items_item_invalid"]
        if any(key not in {"label", "kind", "salience"} for key in item):
            return [], ["referable_items_item_unknown_fields"]
        if not _bounded_string(item.get("label"), max_chars=256):
            return [], ["referable_items_label_invalid"]
        if item.get("kind") not in _REFERABLE_KINDS:
            return [], ["referable_items_kind_invalid"]
        if not _probability(item.get("salience")):
            return [], ["referable_items_salience_invalid"]
        normalized.append(
            {
                "label": item["label"],
                "kind": item["kind"],
                "salience": float(item["salience"]),
            }
        )
    return normalized, []


def _validate_unresolved_slots(value: Any) -> tuple[list[str], list[str]]:
    if not _bounded_sequence(value, max_items=12):
        return [], ["unresolved_slots_invalid"]
    normalized: list[str] = []
    for item in value:
        if not _bounded_string(item, max_chars=128):
            return [], ["unresolved_slots_item_invalid"]
        if item not in normalized:
            normalized.append(item)
    return normalized, []


def _blocked_result(
    *,
    visible: str,
    input_chars: int,
    update_chars: int,
    reasons: tuple[str, ...],
) -> RelayCTXUnpackResult:
    return RelayCTXUnpackResult(
        user_visible_text=visible,
        ctx_working_update=None,
        status="update_blocked",
        marker_present=True,
        update_candidate_present=True,
        update_accepted=False,
        blocked_reasons=tuple(_dedupe(reasons)),
        input_chars=input_chars,
        update_chars=update_chars,
        accepted_field_names=(),
    )


def _safe_visible_suffix(suffix: str) -> tuple[str, list[str]]:
    marker_positions = [
        position
        for position in (
            suffix.find(RELAYCTX_UPDATE_OPEN),
            suffix.find(RELAYCTX_UPDATE_CLOSE),
        )
        if position >= 0
    ]
    if not marker_positions:
        return suffix.strip(), []

    first_marker = min(marker_positions)
    reasons: list[str] = []
    if RELAYCTX_UPDATE_OPEN in suffix:
        reasons.append("multiple_opening_markers")
    if RELAYCTX_UPDATE_CLOSE in suffix:
        reasons.append("multiple_closing_markers")
    return suffix[:first_marker].strip(), reasons


def _contains_internal_marker(value: Any) -> bool:
    if isinstance(value, str):
        return RELAYCTX_UPDATE_OPEN in value or RELAYCTX_UPDATE_CLOSE in value
    if isinstance(value, Mapping):
        return any(
            _contains_internal_marker(key) or _contains_internal_marker(item)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_internal_marker(item) for item in value)
    return False


def _join_visible_parts(prefix: str, suffix: str) -> str:
    if prefix and suffix:
        return f"{prefix}\n{suffix}"
    return prefix or suffix


def _bounded_string(value: Any, *, max_chars: int) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= max_chars
        and bool(value.strip())
        and "\x00" not in value
    )


def _bounded_sequence(value: Any, *, max_items: int) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and len(value) <= max_items
    )


def _probability(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0.0 <= float(value) <= 1.0
    )


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))
