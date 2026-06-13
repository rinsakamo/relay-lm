from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_message_canonicalization import (
    build_client_message_canonicalization_dry_run,
    build_client_message_canonicalization_node_result,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def require_content_free(value: object, forbidden: list[str]) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for text in forbidden:
        require(text not in encoded, f"content leaked into diagnostics: {text!r}")


def main() -> int:
    disabled = build_client_message_canonicalization_dry_run(
        {"messages": [{"role": "user", "content": "hello"}]},
        enabled=False,
        managed_route=True,
    )
    require(disabled is None, disabled)
    print("ok default-off dry-run")

    system_text = "private system evidence"
    developer_text = "private developer evidence"
    old_user_text = "old user history"
    old_assistant_text = "old assistant history"
    current_text = "current multimodal request"
    image_url = "https://example.invalid/private-image.png"
    payload = {
        "model": "relaylm-default",
        "messages": [
            {"role": "system", "content": system_text},
            {
                "role": "developer",
                "content": [{"type": "text", "text": developer_text}],
            },
            {"role": "user", "content": old_user_text},
            {"role": "assistant", "content": old_assistant_text},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": current_text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    }
    artifact = build_client_message_canonicalization_dry_run(
        payload,
        enabled=True,
        managed_route=True,
    )
    require(isinstance(artifact, dict), artifact)
    require(artifact["schema_version"] == "client_message_canonicalization_dry_run.v0", artifact)
    require(artifact["content_free"] is True, artifact)
    require(artifact["diagnostics_only"] is True, artifact)
    require(artifact["canonicalization_candidate_ready"] is True, artifact)
    require(artifact["message_count"] == 5, artifact)
    require(artifact["system_message_count"] == 1, artifact)
    require(artifact["developer_message_count"] == 1, artifact)
    require(artifact["instruction_message_count"] == 2, artifact)
    require(artifact["instruction_text_message_count"] == 2, artifact)
    require(artifact["current_user_turn_present"] is True, artifact)
    require(artifact["current_user_content_valid"] is True, artifact)
    require(artifact["current_user_content_kind"] == "multimodal_parts", artifact)
    require(artifact["current_user_text_part_count"] == 1, artifact)
    require(artifact["current_user_non_text_part_count"] == 1, artifact)
    require(artifact["current_user_multimodal"] is True, artifact)
    require(artifact["prior_user_message_count"] == 1, artifact)
    require(artifact["prior_assistant_message_count"] == 1, artifact)
    require(artifact["blocked_reasons"] == [], artifact)
    require_content_free(
        artifact,
        [
            system_text,
            developer_text,
            old_user_text,
            old_assistant_text,
            current_text,
            image_url,
        ],
    )
    print("ok identify current request evidence without content leakage")

    node_result = build_client_message_canonicalization_node_result(artifact)
    require(node_result is not None, node_result)
    require(node_result.node_name == "client_message_canonicalization", node_result)
    require(node_result.status == "diagnostic_only", node_result)
    require(node_result.decision == "current_request_evidence_identified", node_result)
    require_content_free(
        node_result.to_log_dict(),
        [system_text, developer_text, current_text, image_url],
    )
    print("ok build content-free pipeline node result")

    tool_payload = {
        "messages": [
            {"role": "user", "content": "check the weather"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "call-1", "type": "function"}],
            },
            {"role": "tool", "tool_call_id": "call-1", "content": "secret result"},
        ]
    }
    tool_artifact = build_client_message_canonicalization_dry_run(
        tool_payload,
        enabled=True,
        managed_route=True,
    )
    require(isinstance(tool_artifact, dict), tool_artifact)
    require(tool_artifact["active_tool_transaction_candidate"] is True, tool_artifact)
    require(tool_artifact["canonicalization_candidate_ready"] is False, tool_artifact)
    require(
        "active_tool_transaction_requires_preservation"
        in tool_artifact["blocked_reasons"],
        tool_artifact,
    )
    require(tool_artifact["assistant_tool_call_message_count"] == 1, tool_artifact)
    require(tool_artifact["post_user_tool_message_count"] == 1, tool_artifact)
    require(tool_artifact["messages_after_current_user_count"] == 2, tool_artifact)
    require_content_free(tool_artifact, ["check the weather", "secret result", "call-1"])
    print("ok detect blocked active tool transaction candidate")

    pass_through = build_client_message_canonicalization_dry_run(
        payload,
        enabled=True,
        managed_route=False,
    )
    require(isinstance(pass_through, dict), pass_through)
    require(pass_through["canonicalization_candidate_ready"] is False, pass_through)
    require("pass_through_route_exempt" in pass_through["blocked_reasons"], pass_through)
    pass_node = build_client_message_canonicalization_node_result(pass_through)
    require(pass_node is not None and pass_node.status == "skipped", pass_node)
    print("ok preserve pass-through exemption")

    invalid = build_client_message_canonicalization_dry_run(
        {
            "messages": [
                {"role": "user", "content": "old request"},
                "not-an-object",
                {"role": "user", "content": []},
            ]
        },
        enabled=True,
        managed_route=True,
    )
    require(isinstance(invalid, dict), invalid)
    require(invalid["canonicalization_candidate_ready"] is False, invalid)
    require("messages_contain_non_object_items" in invalid["blocked_reasons"], invalid)
    require("current_user_content_invalid" in invalid["blocked_reasons"], invalid)
    require(invalid["current_user_content_kind"] == "invalid_parts", invalid)
    print("ok fail closed on malformed active request evidence")

    missing_text_part = build_client_message_canonicalization_dry_run(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text"},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ]
        },
        enabled=True,
        managed_route=True,
    )
    require(isinstance(missing_text_part, dict), missing_text_part)
    require(
        missing_text_part["canonicalization_candidate_ready"] is False,
        missing_text_part,
    )
    require(missing_text_part["current_user_content_valid"] is False, missing_text_part)
    require(missing_text_part["current_user_text_part_count"] == 0, missing_text_part)
    require(missing_text_part["current_user_non_text_part_count"] == 1, missing_text_part)
    require(missing_text_part["current_user_invalid_part_count"] == 1, missing_text_part)
    require(
        "current_user_content_invalid" in missing_text_part["blocked_reasons"],
        missing_text_part,
    )
    require_content_free(missing_text_part, [image_url])
    print("ok fail closed on missing text part text")

    null_text_part = build_client_message_canonicalization_dry_run(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": None},
                    ],
                }
            ]
        },
        enabled=True,
        managed_route=True,
    )
    require(isinstance(null_text_part, dict), null_text_part)
    require(
        null_text_part["canonicalization_candidate_ready"] is False,
        null_text_part,
    )
    require(null_text_part["current_user_content_valid"] is False, null_text_part)
    require(null_text_part["current_user_text_part_count"] == 0, null_text_part)
    require(null_text_part["current_user_non_text_part_count"] == 0, null_text_part)
    require(null_text_part["current_user_invalid_part_count"] == 1, null_text_part)
    require(
        "current_user_content_invalid" in null_text_part["blocked_reasons"],
        null_text_part,
    )
    print("ok fail closed on null input_text part text")

    non_string_text_part = build_client_message_canonicalization_dry_run(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": 123},
                    ],
                }
            ]
        },
        enabled=True,
        managed_route=True,
    )
    require(isinstance(non_string_text_part, dict), non_string_text_part)
    require(
        non_string_text_part["canonicalization_candidate_ready"] is False,
        non_string_text_part,
    )
    require(
        non_string_text_part["current_user_content_valid"] is False,
        non_string_text_part,
    )
    require(
        non_string_text_part["current_user_invalid_part_count"] == 1,
        non_string_text_part,
    )
    require(
        "current_user_content_invalid" in non_string_text_part["blocked_reasons"],
        non_string_text_part,
    )
    print("ok fail closed on non-string text part text")

    empty_text_part = build_client_message_canonicalization_dry_run(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": ""},
                    ],
                }
            ]
        },
        enabled=True,
        managed_route=True,
    )
    require(isinstance(empty_text_part, dict), empty_text_part)
    require(
        empty_text_part["canonicalization_candidate_ready"] is False,
        empty_text_part,
    )
    require(empty_text_part["current_user_content_valid"] is False, empty_text_part)
    require(empty_text_part["current_user_invalid_part_count"] == 1, empty_text_part)
    require(
        "current_user_content_invalid" in empty_text_part["blocked_reasons"],
        empty_text_part,
    )
    print("ok fail closed on empty input_text part text")

    missing_user = build_client_message_canonicalization_dry_run(
        {"messages": [{"role": "system", "content": "only instructions"}]},
        enabled=True,
        managed_route=True,
    )
    require(isinstance(missing_user, dict), missing_user)
    require("current_user_turn_missing" in missing_user["blocked_reasons"], missing_user)
    require(missing_user["canonicalization_candidate_ready"] is False, missing_user)
    print("ok fail closed when current user turn is missing")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
