from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_instruction_extraction import build_client_instruction_extraction_dry_run
from relaylm.client_instruction_identity import (
    ClientInstructionIdentityResult,
    assert_client_instruction_identity_diagnostics_content_free,
    build_client_instruction_identity,
    build_client_instruction_identity_diagnostics,
)

_DEFAULT_ARTIFACT = object()

RAW_SENTINELS = (
    "system identity secret",
    "developer identity secret",
    "user identity secret",
    "assistant identity secret",
    "tool identity secret",
    "https://example.invalid/identity-image.png",
    "call_identity_secret_123",
    "Cafe\u0301 identity secret",
    "Café identity secret",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _payload(messages: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": "relaylm-default",
        "messages": messages,
        "metadata": {"unrelated": "metadata"},
        "temperature": 0.7,
    }
    payload.update(extra)
    return payload


def _artifact(payload: dict[str, Any]) -> dict[str, Any]:
    artifact = build_client_instruction_extraction_dry_run(payload, enabled=True)
    require(isinstance(artifact, dict), artifact)
    return artifact


def _identity(
    payload: dict[str, Any],
    artifact: dict[str, Any] | None | object = _DEFAULT_ARTIFACT,
    **kwargs: Any,
) -> ClientInstructionIdentityResult:
    source_artifact = _artifact(payload) if artifact is _DEFAULT_ARTIFACT else artifact
    result = build_client_instruction_identity(
        payload,
        source_artifact,
        enabled=True,
        route_model=kwargs.pop("route_model", "relaylm-default"),
        character_id=kwargs.pop("character_id", None),
        **kwargs,
    )
    require(isinstance(result, ClientInstructionIdentityResult), result)
    return result


def _ready(result: ClientInstructionIdentityResult) -> tuple[str, str]:
    require(result.ready is True, result)
    require(result.blocked_reasons == (), result)
    require(result.identity is not None, result)
    require(result.identity.runtime_private is True, result.identity)
    require(result.identity.content_bearing is True, result.identity)
    fingerprint = result.identity.instruction_fingerprint_sha256
    cache_key = result.identity.cache_key_sha256
    require(len(fingerprint) == 64 and fingerprint == fingerprint.lower(), fingerprint)
    require(len(cache_key) == 64 and cache_key == cache_key.lower(), cache_key)
    return fingerprint, cache_key


def _blocked(result: ClientInstructionIdentityResult, *reasons: str) -> None:
    require(result.ready is False, result)
    require(result.identity is None, result)
    blocked = result.blocked_reasons
    for reason in reasons:
        require(reason in blocked, result)


def _assert_no_raw_content(value: Any, *, extra_forbidden: tuple[str, ...] = ()) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for raw in RAW_SENTINELS + extra_forbidden:
        require(raw not in encoded, f"content leaked into diagnostics: {raw!r}")


def _assert_default_off() -> None:
    payload = _payload([{"role": "system", "content": "system identity secret"}])
    result = build_client_instruction_identity(
        payload,
        _artifact(payload),
        enabled=False,
        route_model="relaylm-default",
        character_id=None,
    )
    require(result is None, result)
    require(build_client_instruction_identity_diagnostics(result) is None, result)
    print("ok default-off returns None")


def _assert_deterministic_identity() -> None:
    payload = _payload(
        [
            {"role": "system", "content": "system identity secret"},
            {"role": "developer", "content": "developer identity secret"},
            {"role": "user", "content": "user identity secret"},
        ]
    )
    original_payload = copy.deepcopy(payload)
    artifact = _artifact(payload)
    original_artifact = copy.deepcopy(artifact)
    first = _identity(payload, artifact)
    second = _identity(payload, artifact)
    require(_ready(first) == _ready(second), (first, second))
    require(payload == original_payload, payload)
    require(artifact == original_artifact, artifact)
    print("ok deterministic identity and immutable inputs")


def _assert_normalization_equivalence() -> None:
    base = _payload(
        [
            {"role": "system", "content": "  Café identity secret\nline two  \t\n"},
            {"role": "developer", "content": "developer identity secret"},
        ]
    )
    equivalent_payloads = [
        _payload(
            [
                {"role": "system", "content": "Café identity secret\r\nline two"},
                {"role": "developer", "content": "developer identity secret"},
            ]
        ),
        _payload(
            [
                {"role": "system", "content": "Cafe\u0301 identity secret\nline two"},
                {"role": "developer", "content": "developer identity secret"},
            ]
        ),
        _payload(
            [
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": "Café identity secret"},
                        {"type": "input_text", "text": "line two"},
                    ],
                },
                {"role": "developer", "content": "developer identity secret"},
            ]
        ),
    ]
    expected_fp, _ = _ready(_identity(base))
    for payload in equivalent_payloads:
        fingerprint, _ = _ready(_identity(payload))
        require(fingerprint == expected_fp, (payload, fingerprint, expected_fp))
    print("ok safe normalization equivalence")


def _assert_meaningful_differences() -> None:
    base = _payload(
        [
            {"role": "system", "content": "system identity secret"},
            {"role": "developer", "content": "developer identity secret"},
        ]
    )
    base_fp, _ = _ready(_identity(base))
    different_payloads = [
        _payload(
            [
                {"role": "developer", "content": "developer identity secret"},
                {"role": "system", "content": "system identity secret"},
            ]
        ),
        _payload([{"role": "developer", "content": "system identity secret"}]),
        _payload([{"role": "system", "content": "system  identity secret"}]),
        _payload([{"role": "system", "content": "system\nidentity secret"}]),
        _payload([{"role": "system", "content": "system identity secret!"}]),
        _payload([{"role": "system", "content": "changed instruction text"}]),
    ]
    for payload in different_payloads:
        fingerprint, _ = _ready(_identity(payload))
        require(fingerprint != base_fp, (payload, fingerprint, base_fp))
    print("ok meaningful instruction differences change fingerprint")


def _assert_cache_key_context() -> None:
    payload = _payload([{"role": "system", "content": "system identity secret"}])
    base_fp, base_key = _ready(_identity(payload))
    variants = [
        {"route_model": "other-model"},
        {"character_id": "char-1"},
        {"instruction_parse_schema_version": "client_instruction_parse.v2"},
        {"authority_policy_version": "client_instruction_authority.v2"},
        {"parser_version": "parser-v1"},
    ]
    for kwargs in variants:
        fingerprint, cache_key = _ready(_identity(payload, **kwargs))
        require(fingerprint == base_fp, (kwargs, fingerprint, base_fp))
        require(cache_key != base_key, (kwargs, cache_key, base_key))
    print("ok cache key context changes cache key only")


def _assert_history_independence() -> None:
    base = _payload(
        [
            {"role": "system", "content": "system identity secret"},
            {"role": "developer", "content": "developer identity secret"},
            {"role": "user", "content": "user identity secret"},
        ],
        top_p=1.0,
    )
    variant = _payload(
        [
            {"role": "assistant", "content": "assistant identity secret"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_identity_secret_123",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_identity_secret_123", "content": "tool identity secret"},
            {"role": "system", "content": "system identity secret"},
            {"role": "developer", "content": "developer identity secret"},
            {"role": "user", "content": "changed user content"},
            {"role": "assistant", "content": "changed assistant history"},
        ],
        metadata={"unrelated": "changed"},
        temperature=0.1,
        max_tokens=99,
    )
    require(_ready(_identity(base)) == _ready(_identity(variant)), variant)
    print("ok user/history/metadata/sampling independent")


def _assert_empty_instruction() -> None:
    payload = _payload(
        [
            {"role": "user", "content": "user identity secret"},
            {"role": "assistant", "content": "assistant identity secret"},
        ]
    )
    first = _identity(payload)
    second = _identity(payload)
    fingerprint, cache_key = _ready(first)
    require(_ready(second) == (fingerprint, cache_key), second)
    require(first.identity is not None and first.identity.empty_instruction is True, first)
    require(first.identity.candidates == (), first.identity)
    summary = build_client_instruction_identity_diagnostics(first)
    require(summary is not None, summary)
    require(summary.get("empty_instruction") is True, summary)
    require(summary.get("instruction_candidate_count") == 0, summary)
    print("ok empty instruction has stable identity")


def _assert_fail_closed() -> None:
    ready_payload = _payload([{"role": "system", "content": "system identity secret"}])
    ready_artifact = _artifact(ready_payload)
    _blocked(
        _identity(ready_payload, None),
        "source_extraction_artifact_missing",
    )
    unsupported = dict(ready_artifact, schema_version="unsupported")
    _blocked(_identity(ready_payload, unsupported), "source_extraction_schema_unsupported")
    not_ready = dict(ready_artifact, fingerprint_candidate_ready=False)
    _blocked(_identity(ready_payload, not_ready), "source_extraction_not_ready")
    source_blocked = dict(ready_artifact, blocked_reasons=["source_block"])
    _blocked(_identity(ready_payload, source_blocked), "source_extraction_blocked")
    mismatch = dict(ready_artifact, candidate_indices=[])
    _blocked(_identity(ready_payload, mismatch), "candidate_indices_mismatch")
    duplicate = dict(ready_artifact, candidate_indices=[0, 0])
    _blocked(_identity(ready_payload, duplicate), "candidate_indices_invalid")
    out_of_range = dict(ready_artifact, candidate_indices=[99])
    _blocked(_identity(ready_payload, out_of_range), "candidate_indices_invalid")
    invalid_role_artifact = dict(ready_artifact, candidate_roles=["user"])
    _blocked(_identity(ready_payload, invalid_role_artifact), "instruction_candidate_role_invalid")
    role_payload = _payload([{"role": "user", "content": "user identity secret"}])
    role_artifact = dict(ready_artifact, candidate_indices=[0])
    _blocked(_identity(role_payload, role_artifact), "instruction_candidate_role_invalid")

    invalid_contents: list[Any] = [None, "", 123, [{"type": "text"}], [{"type": "text", "text": None}], [{"type": "input_text", "text": ""}]]
    for content in invalid_contents:
        payload = _payload([{"role": "system", "content": content}])
        artifact = dict(ready_artifact, candidate_indices=[0])
        _blocked(_identity(payload, artifact), "instruction_candidate_content_invalid")
    unknown_payload = _payload([{"role": "system", "content": [{"unexpected": True}]}])
    _blocked(_identity(unknown_payload, dict(ready_artifact, candidate_indices=[0])), "instruction_candidate_content_invalid")
    multimodal_payload = _payload(
        [
            {
                "role": "developer",
                "content": [
                    {"type": "text", "text": "developer identity secret"},
                    {"type": "image_url", "image_url": {"url": "https://example.invalid/identity-image.png"}},
                ],
            }
        ]
    )
    _blocked(
        _identity(multimodal_payload, _artifact(multimodal_payload)),
        "source_extraction_not_ready",
        "source_extraction_blocked",
        "multimodal_instruction_candidate_requires_preservation",
    )
    tool_payload = _payload(
        [
            {"role": "system", "content": "system identity secret"},
            {"role": "user", "content": "user identity secret"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_identity_secret_123",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_identity_secret_123", "content": "tool identity secret"},
        ]
    )
    _blocked(
        _identity(tool_payload, _artifact(tool_payload)),
        "source_extraction_not_ready",
        "source_extraction_blocked",
        "active_tool_transaction_requires_preservation",
    )
    _blocked(_identity(ready_payload, route_model=""), "route_model_invalid")
    _blocked(
        _identity(ready_payload, instruction_parse_schema_version=""),
        "identity_context_version_invalid",
    )
    print("ok fail-closed validation")


def _assert_content_free_summary() -> None:
    payload = _payload(
        [
            {"role": "system", "content": "system identity secret"},
            {"role": "developer", "content": "developer identity secret"},
            {"role": "user", "content": "user identity secret"},
        ]
    )
    result = _identity(payload, route_model="private-model", character_id="private-character")
    require(result.identity is not None, result)
    summary = build_client_instruction_identity_diagnostics(result)
    require(summary is not None, summary)
    assert_client_instruction_identity_diagnostics_content_free(summary)
    _assert_no_raw_content(
        summary,
        extra_forbidden=(
            result.identity.instruction_fingerprint_sha256,
            result.identity.cache_key_sha256,
            "private-model",
            "private-character",
        ),
    )
    require(summary.get("ready") is True, summary)
    require(summary.get("instruction_candidate_count") == 2, summary)
    require(summary.get("candidate_roles") == ["system", "developer"], summary)
    require(summary.get("candidate_indices") == [0, 1], summary)
    require(summary.get("instruction_fingerprint_computed") is True, summary)
    require(summary.get("cache_key_computed") is True, summary)
    require(summary.get("hash_algorithm") == "sha256", summary)
    print("ok content-free diagnostics summary")


def main() -> int:
    _assert_default_off()
    _assert_deterministic_identity()
    _assert_normalization_equivalence()
    _assert_meaningful_differences()
    _assert_cache_key_context()
    _assert_history_independence()
    _assert_empty_instruction()
    _assert_fail_closed()
    _assert_content_free_summary()
    print("client_instruction_identity_smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
