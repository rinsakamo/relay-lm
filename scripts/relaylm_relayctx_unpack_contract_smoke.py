from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayctx_unpack import (
    RELAYCTX_UPDATE_CLOSE,
    RELAYCTX_UPDATE_OPEN,
    build_relayctx_unpack_node_result,
    unpack_relayctx_response_text,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _structured_text(update: dict[str, object], *, visible: str = "回答本文です。") -> str:
    envelope = {
        "schema_version": "relayctx_working_update.v0",
        "ctx_working_update": update,
    }
    return (
        f"{visible}\n{RELAYCTX_UPDATE_OPEN}\n"
        f"{json.dumps(envelope, ensure_ascii=False)}\n"
        f"{RELAYCTX_UPDATE_CLOSE}"
    )


def _assert_plain_text_passthrough() -> None:
    text = "通常の回答です。JSONという言葉があってもそのまま返します。"
    result = unpack_relayctx_response_text(text)
    require(result.status == "plain_text", result)
    require(result.user_visible_text == text, result)
    require(result.ctx_working_update is None, result)
    require(result.marker_present is False, result)
    require(result.update_accepted is False, result)
    print("ok RelayCTX Unpack preserves ordinary response text")


def _assert_valid_structured_update() -> None:
    text = _structured_text(
        {
            "current_topic": "RelayCTX Unpack",
            "active_task": "Phase 5-A contract",
            "active_question": None,
            "last_decision": {
                "text": "Use a strict trailing JSON block",
                "status": "agreed",
                "confidence": 0.95,
            },
            "last_options": [
                {"label": "strict JSON", "status": "agreed"},
                {"label": "guess YAML", "status": "rejected"},
            ],
            "referable_items": [
                {
                    "label": "RelayCTX Unpack",
                    "kind": "component",
                    "salience": 0.9,
                }
            ],
            "unresolved_slots": ["runtime wiring", "runtime wiring"],
            "response_mode_hint": "answer_now",
            "next_expected_action": "wire non-streaming response",
        }
    )
    result = unpack_relayctx_response_text(text)
    require(result.status == "structured_update", result)
    require(result.user_visible_text == "回答本文です。", result)
    require(result.update_accepted is True, result)
    require(isinstance(result.ctx_working_update, dict), result)
    require(
        result.ctx_working_update["unresolved_slots"] == ["runtime wiring"],
        result,
    )
    require(
        result.ctx_working_update["last_decision"]["confidence"] == 0.95,
        result,
    )
    require(
        result.accepted_field_names
        == tuple(sorted(result.ctx_working_update.keys())),
        result,
    )

    log_payload = result.to_log_dict()
    encoded = json.dumps(log_payload, ensure_ascii=False)
    require("回答本文です。" not in encoded, log_payload)
    require("Use a strict trailing JSON block" not in encoded, log_payload)
    require(log_payload["content_free"] is True, log_payload)
    require(log_payload["persistence_allowed"] is False, log_payload)

    node_result = build_relayctx_unpack_node_result(result)
    require(node_result.node_name == "relayctx_unpack", node_result)
    require(node_result.status == "applied", node_result)
    require(node_result.decision == "structured_update", node_result)
    node_encoded = json.dumps(node_result.to_log_dict(), ensure_ascii=False)
    require("回答本文です。" not in node_encoded, node_result)
    require("Use a strict trailing JSON block" not in node_encoded, node_result)
    print("ok RelayCTX Unpack accepts bounded structured update content-free")


def _assert_invalid_json_blocks_update_but_preserves_text() -> None:
    text = (
        f"見える回答。\n{RELAYCTX_UPDATE_OPEN}\n"
        '{"schema_version":"relayctx_working_update.v0",bad}\n'
        f"{RELAYCTX_UPDATE_CLOSE}"
    )
    result = unpack_relayctx_response_text(text)
    require(result.status == "update_blocked", result)
    require(result.user_visible_text == "見える回答。", result)
    require(result.ctx_working_update is None, result)
    require("update_json_invalid" in result.blocked_reasons, result)
    require(RELAYCTX_UPDATE_OPEN not in result.user_visible_text, result)
    require(RELAYCTX_UPDATE_CLOSE not in result.user_visible_text, result)
    node_result = build_relayctx_unpack_node_result(result)
    require(node_result.status == "blocked", node_result)
    print("ok RelayCTX Unpack blocks malformed JSON and preserves visible text")


def _assert_schema_and_field_validation_fail_closed() -> None:
    wrong_schema = _structured_text(
        {"current_topic": "topic"},
    ).replace("relayctx_working_update.v0", "relayctx_working_update.v9")
    result = unpack_relayctx_response_text(wrong_schema)
    require("update_schema_version_invalid" in result.blocked_reasons, result)
    require(result.ctx_working_update is None, result)

    unknown_field = _structured_text(
        {"current_topic": "topic", "raw_memory_write": "forbidden"}
    )
    result = unpack_relayctx_response_text(unknown_field)
    require("ctx_working_update_unknown_fields" in result.blocked_reasons, result)
    require(result.ctx_working_update is None, result)

    invalid_probability = _structured_text(
        {
            "referable_items": [
                {"label": "item", "kind": "object", "salience": 1.5}
            ]
        }
    )
    result = unpack_relayctx_response_text(invalid_probability)
    require("referable_items_salience_invalid" in result.blocked_reasons, result)
    require(result.ctx_working_update is None, result)
    print("ok RelayCTX Unpack rejects unexpected schema and unsafe fields")


def _assert_marker_failures_do_not_leak() -> None:
    missing_close = (
        f"安全な本文。\n{RELAYCTX_UPDATE_OPEN}\n"
        '{"schema_version":"relayctx_working_update.v0"}'
    )
    result = unpack_relayctx_response_text(missing_close)
    require(result.user_visible_text == "安全な本文。", result)
    require("closing_marker_missing" in result.blocked_reasons, result)

    close_only = f"本文。\n{RELAYCTX_UPDATE_CLOSE}"
    result = unpack_relayctx_response_text(close_only)
    require(result.user_visible_text == "本文。", result)
    require("opening_marker_missing" in result.blocked_reasons, result)

    non_trailing = _structured_text({"current_topic": "topic"}) + "\n追記本文。"
    result = unpack_relayctx_response_text(non_trailing)
    require(result.user_visible_text == "回答本文です。\n追記本文。", result)
    require("update_block_not_trailing" in result.blocked_reasons, result)
    require(result.ctx_working_update is None, result)
    require(RELAYCTX_UPDATE_OPEN not in result.user_visible_text, result)
    require(RELAYCTX_UPDATE_CLOSE not in result.user_visible_text, result)
    print("ok RelayCTX Unpack strips broken internal markers fail-closed")


def _assert_bounds_and_empty_response() -> None:
    oversized = _structured_text({"current_topic": "x" * 600})
    result = unpack_relayctx_response_text(oversized)
    require("current_topic_invalid" in result.blocked_reasons, result)

    result = unpack_relayctx_response_text(
        _structured_text({"current_topic": "topic"}),
        max_update_chars=10,
    )
    require("update_payload_too_large" in result.blocked_reasons, result)

    result = unpack_relayctx_response_text("   ")
    require(result.status == "empty_response", result)
    require(result.user_visible_text == "", result)
    node_result = build_relayctx_unpack_node_result(result)
    require(node_result.status == "failed", node_result)
    print("ok RelayCTX Unpack enforces bounds and reports empty response")


def main() -> None:
    _assert_plain_text_passthrough()
    _assert_valid_structured_update()
    _assert_invalid_json_blocks_update_but_preserves_text()
    _assert_schema_and_field_validation_fail_closed()
    _assert_marker_failures_do_not_leak()
    _assert_bounds_and_empty_response()


if __name__ == "__main__":
    main()
