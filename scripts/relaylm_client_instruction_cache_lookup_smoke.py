from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.client_instruction_cache_lookup import (
    assert_client_instruction_cache_lookup_diagnostics_content_free,
    build_client_instruction_cache_lookup_diagnostics,
    resolve_client_instruction_cache_lookup,
)
from relaylm.client_instruction_extraction import build_client_instruction_extraction_dry_run
from relaylm.client_instruction_identity import build_client_instruction_identity

ROUTE = "relaylm-cache-contract-route"
CHARACTER = "cache-contract-character"
PRIVATE_VALUES = (
    ROUTE,
    CHARACTER,
    "cache-contract-role",
    "cache-contract-setting",
    "cache-contract-task",
    "cache-contract-participant",
    "cache-contract-constraint",
)


def require(value: bool, detail: object) -> None:
    if not value:
        raise AssertionError(detail)


def identity_result():
    payload = {
        "messages": [
            {"role": "system", "content": "cache lookup instruction"},
            {"role": "user", "content": "cache lookup user"},
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


def valid_entry(result: Any) -> dict[str, Any]:
    identity = result.identity
    return {
        "schema_version": "relaylm.client_instruction_cache.v0",
        "cache_key_sha256": identity.cache_key_sha256,
        "instruction_fingerprint_sha256": identity.instruction_fingerprint_sha256,
        "route_model": ROUTE,
        "character_id": CHARACTER,
        "instruction_parse_schema_version": "client_instruction_parse.v1",
        "authority_policy_version": "client_instruction_authority.v1",
        "parser_version": None,
        "parse_status": "valid",
        "scene_state": {
            "scene_type": "implementation_work",
            "scene_role": {
                "role_name": PRIVATE_VALUES[2],
                "role_scope": "scene",
                "role_source": "client_system",
                "confidence": 0.9,
            },
            "scene_context": {
                "setting": PRIVATE_VALUES[3],
                "task": PRIVATE_VALUES[4],
                "participants": [PRIVATE_VALUES[5]],
            },
            "scene_constraints": [
                {"constraint_type": "response_length", "value": PRIVATE_VALUES[6]}
            ],
        },
        "durable_candidate_count": 0,
        "blocked_instruction_kinds": ["runtime_policy_override"],
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
    }


def resolve(result: Any, entry: Any, *, enabled: bool = True):
    return resolve_client_instruction_cache_lookup(
        result,
        entry,
        enabled=enabled,
        route_model=ROUTE,
        character_id=CHARACTER,
    )


def changed(result: Any, mutate: Callable[[dict[str, Any]], None]):
    entry = valid_entry(result)
    mutate(entry)
    return entry


def assert_basics(result: Any) -> None:
    require(resolve(result, valid_entry(result), enabled=False) is None, "default-off")
    miss = resolve(result, None)
    require(miss.status == "miss" and miss.miss_reason == "cache_entry_not_found", miss)
    candidate = valid_entry(result)
    original = deepcopy(candidate)
    hit = resolve(result, candidate)
    require(hit.status == "hit" and hit.hit and hit.entry is not None, hit)
    require(candidate == original, candidate)
    require(hit.entry.scene_context.participants == (PRIVATE_VALUES[5],), hit.entry)
    try:
        hit.entry.scene_type = "casual_chat"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("entry must be frozen")
    require(resolve(None, candidate).blocked_reasons == ("source_identity_missing",), "missing")
    blocked_source = type(result)(result.schema_version, False, None, ("blocked",))
    require(
        resolve(blocked_source, candidate).blocked_reasons == ("source_identity_not_ready",),
        "not ready",
    )
    print("ok default-off/miss/hit/source/immutability")


def assert_mismatch_and_malformed(result: Any) -> None:
    mismatch_cases = [
        ("cache_key_mismatch", lambda e: e.__setitem__("cache_key_sha256", "0" * 64)),
        (
            "instruction_fingerprint_mismatch",
            lambda e: e.__setitem__("instruction_fingerprint_sha256", "1" * 64),
        ),
        ("route_model_mismatch", lambda e: e.__setitem__("route_model", "other")),
        ("character_id_mismatch", lambda e: e.__setitem__("character_id", "other")),
        (
            "instruction_parse_schema_version_mismatch",
            lambda e: e.__setitem__("instruction_parse_schema_version", "other"),
        ),
        (
            "authority_policy_version_mismatch",
            lambda e: e.__setitem__("authority_policy_version", "other"),
        ),
        ("parser_version_mismatch", lambda e: e.__setitem__("parser_version", "v2")),
    ]
    for reason, mutate in mismatch_cases:
        lookup = resolve(result, changed(result, mutate))
        require(reason in lookup.blocked_reasons, (reason, lookup))
    malformed_cases = [
        ([], "cache_entry_invalid"),
        (changed(result, lambda e: e.__setitem__("extra", True)), "cache_entry_unknown_field"),
        (changed(result, lambda e: e.pop("parse_status")), "cache_entry_missing_field"),
        (changed(result, lambda e: e.__setitem__("raw_instruction_persisted", True)), "raw_instruction_persisted_not_false"),
        (changed(result, lambda e: e["scene_state"].__setitem__("scene_type", [])), "scene_type_invalid"),
        (changed(result, lambda e: e["scene_state"]["scene_role"].__setitem__("role_scope", [])), "scene_role_scope_invalid"),
        (changed(result, lambda e: e["scene_state"]["scene_role"].__setitem__("confidence", math.nan)), "scene_role_confidence_invalid"),
        (changed(result, lambda e: e["scene_state"]["scene_context"].__setitem__("participants", ["x"] * 17)), "scene_context_participants_invalid"),
        (changed(result, lambda e: e["scene_state"]["scene_constraints"][0].__setitem__("value", math.inf)), "scene_constraint_value_invalid"),
        (changed(result, lambda e: e.__setitem__("durable_candidate_count", True)), "durable_candidate_count_invalid"),
        (changed(result, lambda e: e.__setitem__("blocked_instruction_kinds", ["x", "x"])), "blocked_instruction_kinds_duplicate"),
        (changed(result, lambda e: e["scene_state"]["scene_context"].__setitem__("content", "private")), "cache_entry_content_forbidden"),
    ]
    for entry, reason in malformed_cases:
        lookup = resolve(result, entry)
        require(lookup.status == "blocked" and reason in lookup.blocked_reasons, (reason, lookup))
    print("ok mismatch/malformed fail-closed")


def assert_diagnostics(result: Any) -> None:
    lookup = resolve(result, valid_entry(result))
    diagnostics = build_client_instruction_cache_lookup_diagnostics(lookup)
    require(diagnostics is not None and diagnostics["cache_hit"] is True, diagnostics)
    encoded = json.dumps(diagnostics, sort_keys=True)
    for value in PRIVATE_VALUES + (
        result.identity.cache_key_sha256,
        result.identity.instruction_fingerprint_sha256,
    ):
        require(value not in encoded, value)
    assert_client_instruction_cache_lookup_diagnostics_content_free(diagnostics)
    unsafe = dict(diagnostics, cache_key_sha256=result.identity.cache_key_sha256)
    try:
        assert_client_instruction_cache_lookup_diagnostics_content_free(unsafe)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe diagnostics accepted")
    print("ok diagnostics content-free")


def main() -> int:
    result = identity_result()
    assert_basics(result)
    assert_mismatch_and_malformed(result)
    assert_diagnostics(result)
    print("client_instruction_cache_lookup_smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
