from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relayctx_unpack import RELAYCTX_UPDATE_CLOSE, RELAYCTX_UPDATE_OPEN
from relaylm.relayctx_unpack_runtime import apply_relayctx_unpack_runtime


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _body(content: object) -> dict[str, object]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def _structured_content(secret: str = "internal candidate secret") -> str:
    envelope = {
        "schema_version": "relayctx_working_update.v0",
        "ctx_working_update": {
            "current_topic": secret,
            "unresolved_slots": ["runtime persistence forbidden"],
        },
    }
    return (
        f"Visible answer.\n{RELAYCTX_UPDATE_OPEN}\n"
        f"{json.dumps(envelope, ensure_ascii=False)}\n"
        f"{RELAYCTX_UPDATE_CLOSE}"
    )


def _assert_dry_run_preserves_backend_body() -> None:
    original = _body(_structured_content())
    result = apply_relayctx_unpack_runtime(
        original,
        status_code=200,
        apply_enabled=False,
        dry_run_only=True,
        max_update_chars=4096,
    )
    require(result.response_body is original, result)
    require(result.applied_to_response is False, result)
    require(result.node_result.status == "diagnostic_only", result.node_result)
    require(result.node_result.decision == "structured_update_dry_run", result.node_result)
    require(result.ctx_working_update_candidate is not None, result)
    require(
        result.ctx_working_update_candidate["current_topic"]
        == "internal candidate secret",
        result,
    )
    encoded_node = json.dumps(result.node_result.to_log_dict(), ensure_ascii=False)
    require("internal candidate secret" not in encoded_node, encoded_node)
    require("runtime persistence forbidden" not in encoded_node, encoded_node)
    require(
        result.node_result.diagnostics["candidate_persistence_allowed"] is False,
        result.node_result,
    )
    print("ok RelayCTX Unpack runtime dry-run preserves backend body")


def _assert_apply_replaces_only_assistant_content() -> None:
    original = _body(_structured_content())
    result = apply_relayctx_unpack_runtime(
        original,
        status_code=200,
        apply_enabled=True,
        dry_run_only=False,
        max_update_chars=4096,
    )
    require(result.response_body is not original, result)
    require(original["choices"][0]["message"]["content"] != "Visible answer.", original)
    require(
        result.response_body["choices"][0]["message"]["content"]
        == "Visible answer.",
        result.response_body,
    )
    require(result.response_body["id"] == original["id"], result.response_body)
    require(
        result.response_body["choices"][0]["finish_reason"] == "stop",
        result.response_body,
    )
    require(result.applied_to_response is True, result)
    require(result.node_result.status == "applied", result.node_result)
    require(result.node_result.decision == "visible_text_applied", result.node_result)
    print("ok RelayCTX Unpack runtime replaces only assistant content")


def _assert_blocked_update_sanitizes_visible_text() -> None:
    content = (
        f"Safe visible answer.\n{RELAYCTX_UPDATE_OPEN}\n"
        '{"schema_version":"relayctx_working_update.v0",bad}\n'
        f"{RELAYCTX_UPDATE_CLOSE}"
    )
    result = apply_relayctx_unpack_runtime(
        _body(content),
        status_code=200,
        apply_enabled=True,
        dry_run_only=False,
        max_update_chars=4096,
    )
    require(
        result.response_body["choices"][0]["message"]["content"]
        == "Safe visible answer.",
        result.response_body,
    )
    require(result.ctx_working_update_candidate is None, result)
    require(result.node_result.status == "blocked", result.node_result)
    require(
        result.node_result.decision == "blocked_update_visible_text_applied",
        result.node_result,
    )
    require("update_json_invalid" in result.node_result.blocked_reasons, result.node_result)
    print("ok RelayCTX Unpack runtime sanitizes visible text when update is blocked")


def _assert_unsupported_and_error_responses_are_preserved() -> None:
    unsupported = _body([{"type": "text", "text": "not string content"}])
    result = apply_relayctx_unpack_runtime(
        unsupported,
        status_code=200,
        apply_enabled=True,
        dry_run_only=False,
        max_update_chars=4096,
    )
    require(result.response_body is unsupported, result)
    require(result.node_result.status == "skipped", result.node_result)
    require(result.node_result.decision == "response_shape_unsupported", result.node_result)

    backend_error = {"error": {"message": "backend failure"}}
    result = apply_relayctx_unpack_runtime(
        backend_error,
        status_code=500,
        apply_enabled=True,
        dry_run_only=False,
        max_update_chars=4096,
    )
    require(result.response_body is backend_error, result)
    require(result.node_result.status == "skipped", result.node_result)
    require(result.node_result.decision == "backend_status_not_success", result.node_result)
    print("ok RelayCTX Unpack runtime preserves unsupported and error responses")


def main() -> None:
    _assert_dry_run_preserves_backend_body()
    _assert_apply_replaces_only_assistant_content()
    _assert_blocked_update_sanitizes_visible_text()
    _assert_unsupported_and_error_responses_are_preserved()


if __name__ == "__main__":
    main()
