from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.request_scope import (
    build_scope_resolution_diagnostics,
    extract_request_scope_identity,
)
from relaylm.routing import resolve_route


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _route_with_overrides(overrides: dict[str, str | None]) -> object:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    route_cfg = cfg["model_routes"]["relaylm-default"]
    for key, value in overrides.items():
        route_cfg[key] = value
    config = RelayLMConfig.model_validate(cfg)
    return resolve_route(config, "relaylm-default")


def main() -> int:
    payload = {"model": "relaylm-default", "metadata": {"session_id": "meta-session"}}
    payload_before = copy.deepcopy(payload)

    route_only = _route_with_overrides(
        {
            "user_id": "route-user",
            "user_type": "route-type",
            "room_id": "route-room",
            "scene_id": "route-scene",
            "session_id": "route-session",
        }
    )
    req_missing = extract_request_scope_identity(None, {"model": "relaylm-default"})
    d_route_only = build_scope_resolution_diagnostics(route_only, req_missing)
    require(d_route_only.resolution_status == "ok", d_route_only)
    require(d_route_only.merged_scope["user_id"] == "route-user", d_route_only)
    print("ok scope resolution route only")

    route_fill = _route_with_overrides(
        {
            "user_id": None,
            "user_type": None,
            "room_id": None,
            "scene_id": None,
            "session_id": None,
        }
    )
    req_fill = extract_request_scope_identity(
        {"x-relaylm-user-id": "hdr-user", "x-relaylm-room-id": "hdr-room"},
        {"model": "relaylm-default", "metadata": {"scene_id": "meta-scene", "session_id": "meta-session"}},
    )
    d_fill = build_scope_resolution_diagnostics(route_fill, req_fill)
    require(d_fill.merged_scope["user_id"] == "hdr-user", d_fill)
    require("user_id" in d_fill.request_fill_fields, d_fill)
    require(d_fill.resolution_status == "partial", d_fill)
    print("ok scope resolution request fill")

    route_same = _route_with_overrides({"user_id": "same-user"})
    req_same = extract_request_scope_identity({"x-relaylm-user-id": "same-user"}, {"model": "relaylm-default"})
    d_same = build_scope_resolution_diagnostics(route_same, req_same)
    require(d_same.conflict_fields == [], d_same)
    require(d_same.merged_scope["user_id"] == "same-user", d_same)
    print("ok scope resolution same value")

    route_conflict = _route_with_overrides({"user_id": "route-user"})
    req_conflict = extract_request_scope_identity({"x-relaylm-user-id": "req-user"}, {"model": "relaylm-default"})
    d_conflict = build_scope_resolution_diagnostics(route_conflict, req_conflict)
    require(d_conflict.resolution_status == "conflict", d_conflict)
    require("user_id" in d_conflict.conflict_fields, d_conflict)
    require("user_id" in d_conflict.request_override_fields, d_conflict)
    require(d_conflict.merged_scope["user_id"] == "route-user", d_conflict)
    print("ok scope resolution conflict")

    route_missing = _route_with_overrides({"user_id": None, "room_id": None, "scene_id": None, "session_id": None, "user_type": None})
    req_missing_all = extract_request_scope_identity(None, {"model": "relaylm-default"})
    d_missing = build_scope_resolution_diagnostics(route_missing, req_missing_all)
    require(d_missing.resolution_status == "partial", d_missing)
    for field in ("user_id", "room_id", "scene_id", "session_id"):
        require(field in d_missing.missing_fields, d_missing)
    print("ok scope resolution missing")

    require(payload == payload_before, (payload, payload_before))
    print("ok scope resolution payload non-mutation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

