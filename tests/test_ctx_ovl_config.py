from __future__ import annotations

import pytest
from pydantic import ValidationError

from relaylm.config import RelayLMConfig


def _base() -> dict[str, object]:
    return {
        "backends": {
            "local": {
                "type": "openai_compatible",
                "base_url": "http://127.0.0.1:8000/v1",
            }
        },
        "model_routes": {
            "relaylm-default": {
                "backend": "local",
                "backend_model": "local-model",
                "mode": "memory_light",
                "user_id": "user1",
                "session_id": "session1",
            }
        },
    }


def test_ctx_ovl_is_default_off() -> None:
    config = RelayLMConfig.model_validate(_base())
    assert config.ctx_ovl_enabled is False
    assert config.ctx_ovl_dry_run_only is True
    assert config.ctx_ovl_apply_enabled is False


def test_ctx_ovl_apply_requires_ev1_apply(tmp_path) -> None:
    payload = _base()
    payload.update(
        {
            "evidence_capture_enabled": True,
            "evidence_capture_dry_run_only": True,
            "evidence_capture_apply_enabled": False,
            "ctx_ovl_enabled": True,
            "ctx_ovl_dry_run_only": False,
            "ctx_ovl_apply_enabled": True,
            "evidence_data_root": str(tmp_path),
        }
    )
    with pytest.raises(
        ValidationError,
        match="ctx_ovl_apply_requires_evidence_capture_apply",
    ):
        RelayLMConfig.model_validate(payload)


def test_ctx_ovl_dry_run_requires_ev1_enabled() -> None:
    payload = _base()
    payload.update(
        {
            "ctx_ovl_enabled": True,
            "ctx_ovl_dry_run_only": True,
            "ctx_ovl_apply_enabled": False,
        }
    )
    with pytest.raises(
        ValidationError,
        match="ctx_ovl_requires_evidence_capture_enabled",
    ):
        RelayLMConfig.model_validate(payload)


def test_ctx_ovl_and_shared_assessment_dry_run_gates_coexist(tmp_path) -> None:
    payload = _base()
    payload.update(
        {
            "evidence_capture_enabled": True,
            "evidence_capture_dry_run_only": True,
            "evidence_capture_apply_enabled": False,
            "evidence_data_root": str(tmp_path),
            "shared_assessment_enabled": True,
            "shared_assessment_dry_run_only": True,
            "shared_assessment_apply_enabled": False,
            "ctx_ovl_enabled": True,
            "ctx_ovl_dry_run_only": True,
            "ctx_ovl_apply_enabled": False,
        }
    )
    config = RelayLMConfig.model_validate(payload)
    assert config.shared_assessment_enabled is True
    assert config.ctx_ovl_enabled is True


def test_ctx_ovl_and_shared_assessment_apply_gates_coexist(tmp_path) -> None:
    payload = _base()
    payload.update(
        {
            "evidence_capture_enabled": True,
            "evidence_capture_dry_run_only": False,
            "evidence_capture_apply_enabled": True,
            "evidence_data_root": str(tmp_path),
            "shared_assessment_enabled": True,
            "shared_assessment_dry_run_only": False,
            "shared_assessment_apply_enabled": True,
            "ctx_ovl_enabled": True,
            "ctx_ovl_dry_run_only": False,
            "ctx_ovl_apply_enabled": True,
        }
    )
    config = RelayLMConfig.model_validate(payload)
    assert config.shared_assessment_apply_enabled is True
    assert config.ctx_ovl_apply_enabled is True
