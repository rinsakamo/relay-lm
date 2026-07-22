from __future__ import annotations

from relaylm.config import RelayLMConfig
from relaylm.evidence_runtime import resolve_evidence_gate
from relaylm.routing import resolve_route


def _config(route: dict) -> RelayLMConfig:
    return RelayLMConfig(
        backends={
            "local": {
                "type": "openai_compatible",
                "base_url": "http://127.0.0.1:8000/v1",
            }
        },
        model_routes={"relaylm-default": {"backend": "local", **route}},
        evidence_capture_enabled=True,
        evidence_capture_dry_run_only=False,
        evidence_capture_apply_enabled=True,
        evidence_data_root="/tmp/relaylm-evidence-test",
    )


def test_ev1_apply_requires_explicit_private_route_identity() -> None:
    config = _config(
        {
            "mode": "memory_light",
            "character_id": "char1",
            "memory_namespace": "ns1",
            "session_id": "sess1",
        }
    )
    route = resolve_route(config, "relaylm-default")
    gate = resolve_evidence_gate(config, route, {"session_id": "sess1"})
    assert "evidence_private_route_user_required" in gate.blocked_reasons


def test_ev1_rejects_shared_scene_route() -> None:
    config = _config(
        {
            "mode": "memory_light",
            "character_id": "char1",
            "memory_namespace": "ns1",
            "user_id": "user1",
            "session_id": "sess1",
            "room_id": "room1",
        }
    )
    route = resolve_route(config, "relaylm-default")
    gate = resolve_evidence_gate(
        config,
        route,
        {"user_id": "user1", "session_id": "sess1", "room_id": "room1", "scene_id": None},
    )
    assert "evidence_shared_scope_unsupported_in_ev1" in gate.blocked_reasons


def test_ev1_stream_apply_is_fail_closed_until_recovery_exists() -> None:
    config = _config(
        {
            "mode": "memory_light",
            "character_id": "char1",
            "memory_namespace": "ns1",
            "user_id": "user1",
            "session_id": "sess1",
        }
    )
    route = resolve_route(config, "relaylm-default")
    gate = resolve_evidence_gate(
        config,
        route,
        {"user_id": "user1", "session_id": "sess1", "room_id": None, "scene_id": None},
        stream_enabled=True,
    )
    assert "evidence_stream_apply_requires_recovery_support" in gate.blocked_reasons
