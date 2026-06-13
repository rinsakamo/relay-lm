from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_instruction_extraction import (
    assert_client_instruction_extraction_content_free,
    build_client_instruction_extraction_dry_run,
    build_client_instruction_extraction_node_result,
)


RAW_VALUES = (
    "system secret instruction",
    "developer secret instruction",
    "user private current request",
    "assistant private answer",
    "tool private result",
    "https://example.invalid/private-instruction-image.png",
    "call-secret",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _base_payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {"model": "relaylm-default", "messages": messages, "stream": False}


def _assert_no_raw_content(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    for raw in RAW_VALUES:
        require(raw not in encoded, f"content leaked into dry-run artifact: {raw!r}")
    assert_client_instruction_extraction_content_free(value)


def _assert_default_off() -> None:
    payload = _base_payload(
        [
            {"role": "system", "content": "system secret instruction"},
            {"role": "user", "content": "user private current request"},
        ]
    )
    artifact = build_client_instruction_extraction_dry_run(payload, enabled=False)
    require(artifact is None, artifact)
    print("ok default-off returns None")


def _assert_instruction_candidates_ready() -> None:
    payload = _base_payload(
        [
            {"role": "system", "content": "system secret instruction"},
            {
                "role": "developer",
                "content": [{"type": "text", "text": "developer secret instruction"}],
            },
            {"role": "user", "content": "user private current request"},
        ]
    )
    artifact = build_client_instruction_extraction_dry_run(payload, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("content_free") is True, artifact)
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("message_count") == 3, artifact)
    require(artifact.get("valid_message_count") == 3, artifact)
    require(artifact.get("instruction_candidate_count") == 2, artifact)
    require(artifact.get("candidate_roles") == ["system", "developer"], artifact)
    require(artifact.get("candidate_indices") == [0, 1], artifact)
    require(artifact.get("content_shape_counts") == {"string": 1, "text_parts": 1}, artifact)
    require(artifact.get("fingerprint_candidate_ready") is True, artifact)
    require(artifact.get("blocked_reasons") == [], artifact)
    _assert_no_raw_content(artifact)

    result = build_client_instruction_extraction_node_result(artifact)
    require(result is not None, result)
    _assert_no_raw_content(result)
    logged = result.to_log_dict()
    require(logged.get("node_name") == "client_instruction_extraction", logged)
    require(logged.get("status") == "diagnostic_only", logged)
    require(logged.get("decision") == "instruction_fingerprint_candidate_ready", logged)
    require(logged.get("blocked_reasons") == [], logged)
    require(logged.get("diagnostics", {}).get("fingerprint_candidate_ready") is True, logged)
    _assert_no_raw_content(logged)
    print("ok instruction candidates ready and content-free")


def _assert_user_assistant_tool_bodies_not_targets() -> None:
    payload = _base_payload(
        [
            {"role": "assistant", "content": "assistant private answer"},
            {"role": "tool", "content": "tool private result", "tool_call_id": "tool-1"},
            {"role": "user", "content": "user private current request"},
        ]
    )
    artifact = build_client_instruction_extraction_dry_run(payload, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("instruction_candidate_count") == 0, artifact)
    require(artifact.get("candidate_roles") == [], artifact)
    require(artifact.get("candidate_indices") == [], artifact)
    require(artifact.get("fingerprint_candidate_ready") is True, artifact)
    _assert_no_raw_content(artifact)
    print("ok user/assistant/tool bodies are not instruction targets")


def _assert_malformed_instruction_candidates_blocked() -> None:
    cases: list[tuple[str, Any]] = [
        ("missing", None),
        ("empty", ""),
        ("text part missing text", [{"type": "text"}]),
        ("text part null text", [{"type": "text", "text": None}]),
        ("text part non-string text", [{"type": "input_text", "text": 123}]),
        ("text part empty text", [{"type": "input_text", "text": ""}]),
        ("unknown object", {"unexpected": True}),
    ]
    for name, content in cases:
        payload = _base_payload(
            [
                {"role": "system", "content": content},
                {"role": "user", "content": "user private current request"},
            ]
        )
        artifact = build_client_instruction_extraction_dry_run(payload, enabled=True)
        require(isinstance(artifact, dict), (name, artifact))
        require(artifact.get("fingerprint_candidate_ready") is False, (name, artifact))
        require(
            "instruction_candidate_content_invalid" in artifact.get("blocked_reasons", []),
            (name, artifact),
        )
        _assert_no_raw_content(artifact)
    print("ok malformed instruction candidates fail closed")


def _assert_multimodal_instruction_candidate_blocks() -> None:
    payload = _base_payload(
        [
            {
                "role": "developer",
                "content": [
                    {"type": "text", "text": "developer secret instruction"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://example.invalid/private-instruction-image.png"
                        },
                    },
                ],
            },
            {"role": "user", "content": "user private current request"},
        ]
    )
    artifact = build_client_instruction_extraction_dry_run(payload, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("instruction_candidate_count") == 1, artifact)
    require(artifact.get("has_multimodal_instruction_candidate") is True, artifact)
    require(artifact.get("multimodal_instruction_candidate_count") == 1, artifact)
    require(artifact.get("fingerprint_candidate_ready") is False, artifact)
    require(
        "multimodal_instruction_candidate_requires_preservation"
        in artifact.get("blocked_reasons", []),
        artifact,
    )
    _assert_no_raw_content(artifact)
    print("ok multimodal instruction candidate blocks fingerprint readiness")


def _assert_active_tool_transaction_blocks() -> None:
    payload = _base_payload(
        [
            {"role": "system", "content": "system secret instruction"},
            {"role": "user", "content": "user private current request"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-secret",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call-secret", "content": "tool private result"},
        ]
    )
    artifact = build_client_instruction_extraction_dry_run(payload, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("fingerprint_candidate_ready") is False, artifact)
    require(artifact.get("active_tool_transaction_candidate") is True, artifact)
    require(artifact.get("assistant_tool_call_message_count_after_latest_user") == 1, artifact)
    require(artifact.get("tool_message_count_after_latest_user") == 1, artifact)
    require(
        "active_tool_transaction_requires_preservation" in artifact.get("blocked_reasons", []),
        artifact,
    )
    _assert_no_raw_content(artifact)
    print("ok active tool transaction blocks fingerprint readiness")


def _assert_invalid_messages_block() -> None:
    payload = {"model": "relaylm-default", "messages": ["not-object"], "stream": False}
    artifact = build_client_instruction_extraction_dry_run(payload, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("fingerprint_candidate_ready") is False, artifact)
    require("messages_contain_non_object_items" in artifact.get("blocked_reasons", []), artifact)
    _assert_no_raw_content(artifact)
    print("ok non-object message items block")


def main() -> None:
    _assert_default_off()
    _assert_instruction_candidates_ready()
    _assert_user_assistant_tool_bodies_not_targets()
    _assert_malformed_instruction_candidates_blocked()
    _assert_multimodal_instruction_candidate_blocks()
    _assert_active_tool_transaction_blocks()
    _assert_invalid_messages_block()
    print("client_instruction_extraction_dry_run_smoke passed")


if __name__ == "__main__":
    main()
