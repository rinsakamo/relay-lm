#!/usr/bin/env python3
"""Smoke checks for typed parse and gated cache-write behavior."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.client_instruction_cache import build_client_instruction_cache_dry_run
from relaylm.client_instruction_cache_lookup import resolve_client_instruction_cache_lookup
from relaylm.client_instruction_cache_write import (
    assert_client_instruction_cache_write_diagnostics_content_free,
    build_client_instruction_cache_write_diagnostics,
    build_client_instruction_cache_write_node_result,
    build_client_instruction_cache_write_preflight,
)
from relaylm.client_instruction_extraction import build_client_instruction_extraction_dry_run
from relaylm.client_instruction_fingerprint import build_client_instruction_fingerprint_dry_run
from relaylm.client_instruction_identity import build_client_instruction_identity
from relaylm.client_instruction_identity_runtime import (
    client_instruction_identity_dependency_enabled,
)
from relaylm.client_instruction_typed_parse import (
    assert_client_instruction_typed_parse_diagnostics_content_free,
    build_client_instruction_typed_parse_diagnostics,
    validate_client_instruction_typed_parse_candidate,
)

ROUTE = "relaylm-c5a-route"
CHARACTER = "relaylm-c5a-character"
RAW_VALUES = (
    "c5a role private",
    "c5a setting private",
    "c5a task private",
    "c5a participant private",
    "c5a constraint private",
    "c5a durable private",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def identity_result() -> Any:
    payload = {
        "messages": [
            {"role": "system", "content": "c5a system instruction"},
            {"role": "developer", "content": "c5a developer instruction"},
            {"role": "user", "content": "c5a user"},
        ]
    }
    extraction = build_client_instruction_extraction_dry_run(
        payload, enabled=True, managed_route=True
    )
    result = build_client_instruction_identity(
        payload,
        extraction,
        enabled=True,
        route_model=ROUTE,
        character_id=CHARACTER,
    )
    require(result is not None and result.ready and result.identity is not None, result)
    return result


def valid_candidate() -> dict[str, Any]:
    return {
        "scene_type": "implementation_work",
        "scene_role": {
            "role_name": RAW_VALUES[0],
            "role_scope": "scene",
            "confidence": 0.95,
        },
        "scene_context": {
            "setting": RAW_VALUES[1],
            "task": RAW_VALUES[2],
            "participants": [RAW_VALUES[3]],
        },
        "scene_constraints": [
            {"constraint_type": "response_length", "value": RAW_VALUES[4]}
        ],
        "durable_persona_candidates": [
            {
                "candidate_kind": "value",
                "normalized_value": RAW_VALUES[5],
                "confidence": 0.8,
            }
        ],
        "blocked_instruction_kinds": ["runtime_policy_override"],
    }


def assert_not_leaked(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for raw in RAW_VALUES + ("a" * 64,):
        require(raw not in encoded, raw)


def test_typed_parse_contract() -> Any:
    require(
        validate_client_instruction_typed_parse_candidate(
            valid_candidate(), enabled=False
        )
        is None,
        "default-off",
    )
    missing = validate_client_instruction_typed_parse_candidate(None, enabled=True)
    require(missing is not None and missing.status == "skipped", missing)
    candidate = valid_candidate()
    original = copy.deepcopy(candidate)
    result = validate_client_instruction_typed_parse_candidate(candidate, enabled=True)
    require(result is not None and result.status == "valid" and result.artifact, result)
    require(candidate == original, candidate)
    require(result.artifact.scene_type == "implementation_work", result.artifact)
    require(len(result.artifact.durable_persona_candidates) == 1, result.artifact)
    diagnostics = build_client_instruction_typed_parse_diagnostics(result)
    require(diagnostics is not None and diagnostics["parse_ready"] is True, diagnostics)
    assert_not_leaked(diagnostics)
    assert_client_instruction_typed_parse_diagnostics_content_free(diagnostics)
    unsafe = dict(diagnostics, role_name=RAW_VALUES[0])
    try:
        assert_client_instruction_typed_parse_diagnostics_content_free(unsafe)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe typed parse diagnostics accepted")
    print("ok typed parse default-off valid content-free diagnostics")
    return result


def test_typed_parse_malformed() -> None:
    cases = [
        (dict(valid_candidate(), extra=True), "parse_candidate_unknown_or_missing_field"),
        (dict(valid_candidate(), raw_instruction="secret"), "parse_candidate_unknown_or_missing_field"),
        (
            {**valid_candidate(), "scene_type": "not_a_scene"},
            "scene_type_invalid",
        ),
        (
            {
                **valid_candidate(),
                "scene_role": {"role_name": RAW_VALUES[0], "role_scope": "bad", "confidence": 0.5},
            },
            "scene_role_scope_invalid",
        ),
        (
            {
                **valid_candidate(),
                "scene_context": {"setting": "/tmp/private", "task": None, "participants": []},
            },
            "scene_context_setting_invalid",
        ),
        (
            {**valid_candidate(), "durable_persona_candidates": ["bad"]},
            "durable_persona_candidate_invalid",
        ),
        (
            {**valid_candidate(), "blocked_instruction_kinds": ["x", "x"]},
            "blocked_instruction_kinds_duplicate",
        ),
    ]
    for candidate, reason in cases:
        result = validate_client_instruction_typed_parse_candidate(candidate, enabled=True)
        require(result is not None and result.status == "blocked", (reason, result))
        require(reason in result.blocked_reasons, (reason, result.blocked_reasons))
    print("ok typed parse malformed candidates fail closed")


def test_cache_write_preflight(parse_result: Any) -> None:
    identity = identity_result()
    require(
        build_client_instruction_cache_write_preflight(
            parse_result=parse_result,
            identity_result=identity,
            enabled=False,
            dry_run_only=True,
            managed_route=True,
            route_model=ROUTE,
            character_id=CHARACTER,
        )
        is None,
        "cache write default-off",
    )
    result = build_client_instruction_cache_write_preflight(
        parse_result=parse_result,
        identity_result=identity,
        enabled=True,
        dry_run_only=True,
        managed_route=True,
        route_model=ROUTE,
        character_id=CHARACTER,
    )
    require(result is not None and result.status == "dry_run", result)
    require(result.write_preflight_ready is True, result)
    require(result.cache_write_attempted is False, result)
    require(result.cache_entry_written is False, result)
    require(result.cache_entry_candidate is not None, result)
    require(result.cache_entry_candidate["raw_instruction_persisted"] is False, result)
    require(result.cache_entry_candidate["raw_response_persisted"] is False, result)
    diagnostics = build_client_instruction_cache_write_diagnostics(result)
    require(diagnostics is not None and diagnostics["cache_entry_written"] is False, diagnostics)
    assert_not_leaked(diagnostics)
    assert_client_instruction_cache_write_diagnostics_content_free(diagnostics)

    missing_root = build_client_instruction_cache_write_preflight(
        parse_result=parse_result,
        identity_result=identity,
        enabled=True,
        dry_run_only=False,
        managed_route=True,
        route_model=ROUTE,
        character_id=CHARACTER,
    )
    require(missing_root is not None and missing_root.status == "blocked", missing_root)
    require("cache_root_missing" in missing_root.blocked_reasons, missing_root)
    require(missing_root.cache_write_attempted is False, missing_root)

    blocked = build_client_instruction_cache_write_preflight(
        parse_result=None,
        identity_result=identity,
        enabled=True,
        dry_run_only=True,
        managed_route=True,
        route_model=ROUTE,
        character_id=CHARACTER,
    )
    require(blocked is not None and blocked.status == "blocked", blocked)
    require("source_typed_parse_not_ready" in blocked.blocked_reasons, blocked)
    print("ok cache write preflight is gated and content-free")


def test_cache_write_apply(parse_result: Any) -> None:
    identity = identity_result()
    assert identity.identity is not None
    with tempfile.TemporaryDirectory(prefix="relaylm-c5b-cache-") as cache_root:
        too_large = build_client_instruction_cache_write_preflight(
            parse_result=parse_result,
            identity_result=identity,
            enabled=True,
            dry_run_only=False,
            managed_route=True,
            route_model=ROUTE,
            character_id=CHARACTER,
            cache_root=cache_root,
            max_entry_bytes=1,
        )
        require(too_large is not None and too_large.status == "blocked", too_large)
        require("cache_entry_too_large" in too_large.blocked_reasons, too_large)
        require(too_large.cache_write_attempted is False, too_large)
        require(not list(Path(cache_root).glob("*.json")), list(Path(cache_root).glob("*.json")))

        applied = build_client_instruction_cache_write_preflight(
            parse_result=parse_result,
            identity_result=identity,
            enabled=True,
            dry_run_only=False,
            managed_route=True,
            route_model=ROUTE,
            character_id=CHARACTER,
            cache_root=cache_root,
            max_entry_bytes=65536,
        )
        require(applied is not None and applied.status == "written", applied)
        require(applied.cache_write_attempted is True, applied)
        require(applied.cache_entry_written is True, applied)
        require(applied.atomic_write_used is True, applied)
        require(applied.applied is True and applied.diagnostics_only is False, applied)
        require(applied.cache_entry_bytes is not None and applied.cache_entry_bytes > 0, applied)

        diagnostics = build_client_instruction_cache_write_diagnostics(applied)
        require(diagnostics is not None and diagnostics["cache_entry_written"] is True, diagnostics)
        require(diagnostics["atomic_write_used"] is True, diagnostics)
        assert_not_leaked(diagnostics)
        assert_client_instruction_cache_write_diagnostics_content_free(diagnostics)

        node = build_client_instruction_cache_write_node_result(applied)
        require(node is not None and node.status == "applied", node)
        require(node.decision == "client_instruction_cache_write_written", node)
        require(node.artifacts and node.artifacts[0]["applied"] is True, node)

        target = Path(cache_root) / f"{identity.identity.cache_key_sha256}.json"
        require(target.exists() and target.is_file(), target)
        persisted = json.loads(target.read_text(encoding="utf-8"))
        require(persisted["raw_instruction_persisted"] is False, persisted)
        require(persisted["raw_response_persisted"] is False, persisted)
        lookup = resolve_client_instruction_cache_lookup(
            identity,
            persisted,
            enabled=True,
            route_model=ROUTE,
            character_id=CHARACTER,
            parser_version=parse_result.parser_version,
        )
        require(lookup is not None and lookup.status == "hit" and lookup.hit is True, lookup)
    print("ok cache write applies atomically and reader validates persisted entry")


def test_cache_plan_save_requested() -> None:
    payload = {
        "messages": [
            {"role": "system", "content": "c5a system instruction"},
            {"role": "user", "content": "c5a user"},
        ]
    }
    extraction = build_client_instruction_extraction_dry_run(
        payload, enabled=True, managed_route=True
    )
    fingerprint = build_client_instruction_fingerprint_dry_run(extraction, enabled=True)
    disabled = build_client_instruction_cache_dry_run(
        fingerprint,
        enabled=True,
        lookup_requested=True,
        save_requested=False,
    )
    enabled = build_client_instruction_cache_dry_run(
        fingerprint,
        enabled=True,
        lookup_requested=True,
        save_requested=True,
    )
    require(disabled is not None and disabled["save_requested"] is False, disabled)
    require(enabled is not None and enabled["save_requested"] is True, enabled)
    require(enabled["cache_save_attempted"] is False, enabled)
    require(enabled["persistence_applied"] is False, enabled)
    print("ok cache dry-run save request remains no-op")


def test_cache_write_dependency_gate() -> None:
    route = SimpleNamespace(
        client_instruction_extraction_dry_run_enabled=False,
        client_instruction_cache_lookup_enabled=False,
        client_instruction_cache_write_enabled=True,
        client_history_exclusion_apply_enabled=False,
    )
    require(client_instruction_identity_dependency_enabled(route) is True, route)
    route.client_instruction_cache_write_enabled = False
    require(client_instruction_identity_dependency_enabled(route) is False, route)
    print("ok cache write flag enables instruction dependency gate")


def main() -> int:
    parse_result = test_typed_parse_contract()
    test_typed_parse_malformed()
    test_cache_write_preflight(parse_result)
    test_cache_write_apply(parse_result)
    test_cache_plan_save_requested()
    test_cache_write_dependency_gate()
    print("client_instruction_typed_parse_cache_write_smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
