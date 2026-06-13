from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.client_instruction_cache_lookup import (
    resolve_client_instruction_cache_lookup,
)
from relaylm.client_instruction_extraction import (
    build_client_instruction_extraction_dry_run,
)
from relaylm.client_instruction_identity import build_client_instruction_identity


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    route_model = "relaylm-cache-empty-contract"
    character_id = "cache-empty-character"
    payload = {
        "messages": [
            {"role": "user", "content": "current user turn"},
            {"role": "assistant", "content": "prior assistant turn"},
        ]
    }
    extraction = build_client_instruction_extraction_dry_run(
        payload,
        enabled=True,
        managed_route=True,
    )
    identity_result = build_client_instruction_identity(
        payload,
        extraction,
        enabled=True,
        route_model=route_model,
        character_id=character_id,
    )
    require(identity_result is not None and identity_result.ready, identity_result)
    require(identity_result.identity is not None, identity_result)
    require(identity_result.identity.empty_instruction is True, identity_result)
    require(identity_result.identity.candidates == (), identity_result)

    identity = identity_result.identity
    candidate_entry = {
        "schema_version": "relaylm.client_instruction_cache.v0",
        "cache_key_sha256": identity.cache_key_sha256,
        "instruction_fingerprint_sha256": identity.instruction_fingerprint_sha256,
        "route_model": route_model,
        "character_id": character_id,
        "instruction_parse_schema_version": "client_instruction_parse.v1",
        "authority_policy_version": "client_instruction_authority.v1",
        "parser_version": None,
        "parse_status": "valid",
        "scene_state": {
            "scene_type": "implementation_work",
            "scene_role": None,
            "scene_context": {
                "setting": None,
                "task": None,
                "participants": [],
            },
            "scene_constraints": [],
        },
        "durable_candidate_count": 0,
        "blocked_instruction_kinds": [],
        "raw_instruction_persisted": False,
        "raw_response_persisted": False,
    }
    lookup = resolve_client_instruction_cache_lookup(
        identity_result,
        candidate_entry,
        enabled=True,
        route_model=route_model,
        character_id=character_id,
    )
    require(lookup is not None and lookup.status == "blocked", lookup)
    require(lookup.hit is False and lookup.entry is None, lookup)
    require(
        lookup.blocked_reasons == ("source_instruction_candidates_missing",),
        lookup,
    )
    print("ok empty instruction identity cannot produce a cache hit")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
