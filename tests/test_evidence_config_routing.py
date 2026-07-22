"""Config/routing gate wiring tests for EV-1 (default-off, triple-gate posture)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from relaylm.config import RelayLMConfig
from relaylm.evidence_runtime import resolve_evidence_gate
from relaylm.routing import resolve_route

BASE_CONFIG_KWARGS = dict(
    backends={
        "local_backend": {
            "type": "openai_compatible",
            "base_url": "http://127.0.0.1:8000/v1",
        }
    },
    model_routes={
        "relaylm-default": {
            "backend": "local_backend",
            "mode": "memory_light",
            "character_id": "char1",
            "memory_namespace": "ns1",
            "user_id": "user1",
            "session_id": "sess1",
        },
        "relaylm-pass-through": {
            "backend": "local_backend",
            "mode": "pass_through",
        },
    },
)


def test_evidence_capture_defaults_to_fully_off() -> None:
    config = RelayLMConfig(**BASE_CONFIG_KWARGS)
    assert config.evidence_capture_enabled is False
    assert config.evidence_capture_dry_run_only is True
    assert config.evidence_capture_apply_enabled is False
    route = resolve_route(config, "relaylm-default")
    gate = resolve_evidence_gate(config, route)
    assert gate.enabled is False


def test_apply_mode_requires_evidence_data_root() -> None:
    with pytest.raises(ValidationError):
        RelayLMConfig(
            **BASE_CONFIG_KWARGS,
            evidence_capture_enabled=True,
            evidence_capture_dry_run_only=False,
            evidence_capture_apply_enabled=True,
            evidence_data_root=None,
        )


def test_invalid_gate_combination_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RelayLMConfig(
            **BASE_CONFIG_KWARGS,
            evidence_capture_enabled=True,
            evidence_capture_dry_run_only=False,
            evidence_capture_apply_enabled=False,
        )


def test_valid_apply_gate_combination_is_accepted(tmp_path) -> None:
    config = RelayLMConfig(
        **BASE_CONFIG_KWARGS,
        evidence_capture_enabled=True,
        evidence_capture_dry_run_only=False,
        evidence_capture_apply_enabled=True,
        evidence_data_root=str(tmp_path / "evidence"),
    )
    route = resolve_route(config, "relaylm-default")
    gate = resolve_evidence_gate(config, route)
    assert gate.enabled is True
    assert gate.apply_enabled is True
    assert gate.dry_run_only is False


def test_pass_through_route_never_enables_capture_even_if_globally_on(tmp_path) -> None:
    config = RelayLMConfig(
        **BASE_CONFIG_KWARGS,
        evidence_capture_enabled=True,
        evidence_capture_dry_run_only=False,
        evidence_capture_apply_enabled=True,
        evidence_data_root=str(tmp_path / "evidence"),
    )
    route = resolve_route(config, "relaylm-pass-through")
    gate = resolve_evidence_gate(config, route)
    assert gate.enabled is False


def test_enabling_evidence_capture_turns_on_the_current_user_preflight() -> None:
    config = RelayLMConfig(
        **BASE_CONFIG_KWARGS,
        evidence_capture_enabled=True,
        evidence_capture_dry_run_only=True,
        evidence_capture_apply_enabled=False,
    )
    route = resolve_route(config, "relaylm-default")
    assert route.client_history_exclusion_preflight_enabled is True
