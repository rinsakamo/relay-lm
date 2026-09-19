from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
)
from tools import v1_external_qualification_hindsight_smoke as smoke


class _FakeLifecycle:
    instances: list["_FakeLifecycle"] = []

    def __init__(self, spec, expected, *, repo_root, evidence_root) -> None:
        self.spec = spec
        self.expected = expected
        self.repo_root = repo_root
        self.evidence_root = evidence_root
        self.semantic_operation_count = 0
        self.started = False
        self.cleaned = False
        self.retain_items = None
        self.__class__.instances.append(self)

    def start(self) -> None:
        self.started = True

    def consolidation_pending_ids(self, *, bank_id: str) -> set[str]:
        assert bank_id
        self.semantic_operation_count += 1
        return set()

    def retain(self, *, bank_id: str, items):
        assert bank_id
        self.semantic_operation_count += 1
        self.retain_items = tuple(items)
        assert len(self.retain_items) == 1
        assert "copper token" in str(self.retain_items[0]["content"])

    def wait_for_consolidation(
        self,
        *,
        bank_id: str,
        pre_existing_pending_ids: set[str],
    ):
        assert bank_id
        assert pre_existing_pending_ids == set()
        self.semantic_operation_count += 1
        return {
            "poll_count": 1,
            "elapsed_ms": 0.1,
            "pre_existing_pending_count": 0,
            "outstanding_count": 0,
        }

    def recall(
        self,
        prompt: str,
        *,
        bank_id: str,
        query_timestamp: str | None = None,
    ):
        assert prompt == "Where is the copper token stored?"
        assert bank_id
        assert query_timestamp == "2025-01-02T12:00:00+00:00"
        self.semantic_operation_count += 1
        return {
            "results": [
                {
                    "text": "The copper token is stored in drawer seven.",
                    "type": "observation",
                }
            ]
        }

    def cleanup(self):
        self.cleaned = True
        return {
            "started": self.started,
            "start_count": 1 if self.started else 0,
            "health_count": 1,
            "semantic_operation_count": self.semantic_operation_count,
            "cleanup_count": 1,
            "deployment_id": "synthetic-deployment",
            "all_owned_processes_terminated": True,
            "external_processes_touched": 0,
            "errors": [],
            "live_health_response": {},
            "runtime_identity_path": None,
        }


class _FakeLiveSession:
    launch_count = 1

    def __init__(self) -> None:
        self.cleaned = False

    def attest(self):
        return SimpleNamespace(fingerprint="sha256:" + "b" * 64)

    def cleanup(self):
        self.cleaned = True
        return {
            "all_owned_processes_terminated": True,
            "external_processes_touched": 0,
            "errors": [],
        }


def test_synthetic_smoke_is_repeatable_engineering_work_not_scientific_spend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeLifecycle.instances.clear()
    health = SimpleNamespace(fingerprint="sha256:" + "a" * 64)
    lifecycle_spec = SimpleNamespace(database_profile="diagnostic-owner")
    llama_spec = SimpleNamespace()

    monkeypatch.setattr(
        smoke,
        "_derive_diagnostic_bindings",
        lambda source, diagnostic_owner_id: (
            llama_spec,
            lifecycle_spec,
            health,
        ),
    )
    monkeypatch.setattr(smoke, "HindsightDeploymentSession", _FakeLifecycle)
    monkeypatch.setattr(
        smoke,
        "verify_hindsight_health",
        lambda expected, lifecycle: expected,
    )
    live = _FakeLiveSession()
    monkeypatch.setattr(
        smoke,
        "start_llama_cpp_session",
        lambda spec, evidence_root: live,
    )
    monkeypatch.setattr(
        smoke,
        "_llama_cpp_chat_smoke",
        lambda spec: {
            "endpoint": "/v1/chat/completions",
            "status_code": 200,
            "response_keys": ["choices"],
            "choice_count": 1,
        },
    )

    artifact_root = (tmp_path / "diagnostic").resolve()
    result = smoke.run_synthetic_hindsight_smoke(
        source_descriptor={},
        diagnostic_owner_id="diagnostic-owner",
        repo_root=tmp_path.resolve(),
        artifact_root=artifact_root,
    )

    assert result["status"] == "NON_CITABLE_DIAGNOSTIC_PASS"
    assert result["citable"] is False
    assert result["scientific_spend"] == "NOT_OPENED"
    assert result["benchmark_text_used"] is False
    assert result["benchmark_question_count"] == 0
    assert result["judge_call_count"] == 0
    assert result["retrieved_memory_count"] == 1
    assert result["hindsight_semantic_operation_count"] == 4
    assert result["llama_cpp_launch_count"] == 1
    assert live.cleaned is True
    assert _FakeLifecycle.instances[0].cleaned is True

    receipt = json.loads(
        (artifact_root / "synthetic-hindsight-smoke.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["status"] == "NON_CITABLE_DIAGNOSTIC_PASS"
    assert receipt["scientific_spend"] == "NOT_OPENED"


def test_synthetic_smoke_preserves_failure_receipt_without_scientific_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingLifecycle(_FakeLifecycle):
        def retain(self, *, bank_id: str, items):
            super().retain(bank_id=bank_id, items=items)
            raise CampaignCarriageError("synthetic retain failed")

    health = SimpleNamespace(fingerprint="sha256:" + "a" * 64)
    lifecycle_spec = SimpleNamespace(database_profile="diagnostic-owner")
    llama_spec = SimpleNamespace()
    monkeypatch.setattr(
        smoke,
        "_derive_diagnostic_bindings",
        lambda source, diagnostic_owner_id: (
            llama_spec,
            lifecycle_spec,
            health,
        ),
    )
    monkeypatch.setattr(smoke, "HindsightDeploymentSession", _FailingLifecycle)
    monkeypatch.setattr(
        smoke,
        "verify_hindsight_health",
        lambda expected, lifecycle: expected,
    )
    monkeypatch.setattr(
        smoke,
        "start_llama_cpp_session",
        lambda spec, evidence_root: _FakeLiveSession(),
    )

    artifact_root = (tmp_path / "diagnostic-failure").resolve()
    with pytest.raises(CampaignCarriageError, match="synthetic retain failed"):
        smoke.run_synthetic_hindsight_smoke(
            source_descriptor={},
            diagnostic_owner_id="diagnostic-owner",
            repo_root=tmp_path.resolve(),
            artifact_root=artifact_root,
        )

    receipt = json.loads(
        (artifact_root / "synthetic-hindsight-smoke.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["status"] == "NON_CITABLE_DIAGNOSTIC_FAIL"
    assert receipt["citable"] is False
    assert receipt["scientific_spend"] == "NOT_OPENED"
    assert receipt["benchmark_text_used"] is False
    assert receipt["failure"]["type"] == "CampaignCarriageError"


def test_shared_physical_registry_exposes_only_the_synthetic_smoke_module() -> None:
    registry = json.loads(
        (
            Path(__file__).parents[2]
            / ".ai"
            / "physical"
            / "llama_cpp_targets.json"
        ).read_text(encoding="utf-8")
    )
    target = registry["targets"][smoke.SMOKE_TARGET]
    assert target["branch"] == "v1"
    assert target["module"] == "tools.v1_external_qualification_hindsight_smoke"
    assert target["required_distributions"] == ["httpx"]


def test_synthetic_smoke_module_has_no_scientific_ledger_dependency() -> None:
    source = Path(smoke.__file__).read_text(encoding="utf-8")
    assert "ScientificSpendLedger" not in source
