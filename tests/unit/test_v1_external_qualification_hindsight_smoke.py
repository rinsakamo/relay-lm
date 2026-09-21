from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
)
from tools import v1_external_qualification_hindsight_smoke as smoke


@dataclass(frozen=True)
class _FakeLifecycleSpec:
    database_profile: str
    llm_base_url: str = "http://127.0.0.1:18097/v1"


class _FakeCaptureProxy:
    instances: list["_FakeCaptureProxy"] = []

    def __init__(self, *, upstream_base_url: str, artifact_root: Path) -> None:
        assert upstream_base_url == "http://127.0.0.1:18097/v1"
        assert artifact_root.is_absolute()
        self.base_url = "http://127.0.0.1:49000/v1"
        self.port = 49000
        self.started = False
        self.cleaned = False
        self.__class__.instances.append(self)

    def start(self) -> None:
        self.started = True

    def cleanup(self):
        self.cleaned = True
        return {
            "format_version": 1,
            "proxy_base_url": self.base_url,
            "proxy_port": self.port,
            "upstream": "http://127.0.0.1:18097",
            "request_count": 0,
            "chat_completion_capture_count": 0,
            "captures": [],
            "all_owned_processes_terminated": True,
            "external_processes_touched": 0,
            "errors": [],
        }


@pytest.fixture(autouse=True)
def _synthetic_capture_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeCaptureProxy.instances.clear()
    monkeypatch.setattr(smoke, "SyntheticLlamaCaptureProxy", _FakeCaptureProxy)


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
        self.retain_calls: list[tuple[object, ...]] = []
        self.pending_allow_missing: list[bool] = []
        self.wait_calls = 0
        self.__class__.instances.append(self)

    def start(self) -> None:
        self.started = True

    def consolidation_pending_ids(
        self, *, bank_id: str, allow_missing_bank: bool = False
    ) -> set[str]:
        assert bank_id
        self.pending_allow_missing.append(allow_missing_bank)
        self.semantic_operation_count += 1
        return set()

    def retain(self, *, bank_id: str, items):
        assert bank_id
        self.semantic_operation_count += 1
        self.retain_items = tuple(items)
        self.retain_calls.append(self.retain_items)
        assert len(self.retain_items) == 1
        return {
            "success": True,
            "bank_id": bank_id,
            "items_count": 1,
            "async": False,
        }

    def wait_for_consolidation(
        self,
        *,
        bank_id: str,
        pre_existing_pending_ids: set[str],
    ):
        assert bank_id
        assert pre_existing_pending_ids == set()
        self.wait_calls += 1
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
    lifecycle_spec = _FakeLifecycleSpec(database_profile="diagnostic-owner")
    llama_spec = SimpleNamespace(port=18097)

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
    assert result["retain_response"]["success"] is True
    assert result["recall_response_shape"] == {"keys": ["results"], "result_count": 1}
    assert result["hindsight_semantic_operation_count"] == 4
    assert result["llama_cpp_launch_count"] == 1
    assert result["llama_capture"]["chat_completion_capture_count"] == 0
    assert result["cleanup"]["capture_proxy"]["all_owned_processes_terminated"] is True
    assert _FakeCaptureProxy.instances[0].started is True
    assert _FakeCaptureProxy.instances[0].cleaned is True
    assert _FakeLifecycle.instances[0].spec.llm_base_url == "http://127.0.0.1:49000/v1"
    assert live.cleaned is True
    assert _FakeLifecycle.instances[0].cleaned is True
    assert len(_FakeLifecycle.instances[0].retain_calls) == 1
    assert _FakeLifecycle.instances[0].pending_allow_missing == [True]
    assert _FakeLifecycle.instances[0].wait_calls == 1

    receipt = json.loads(
        (artifact_root / "synthetic-hindsight-smoke.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["status"] == "NON_CITABLE_DIAGNOSTIC_PASS"
    assert receipt["scientific_spend"] == "NOT_OPENED"


def test_current_host_source_runs_without_historical_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeLifecycle.instances.clear()
    health = SimpleNamespace(fingerprint="sha256:" + "a" * 64)
    lifecycle_spec = _FakeLifecycleSpec(database_profile="diagnostic-owner")
    llama_spec = SimpleNamespace(port=18097)
    material = smoke.CurrentHostMaterial(
        llama_cpp_root=(tmp_path / "llama.cpp").resolve(),
        model_path=(tmp_path / "model.gguf").resolve(),
        onnx_model_path=(tmp_path / "model.onnx").resolve(),
        onnx_tokenizer_path=(tmp_path / "tokenizer").resolve(),
        llama_port=18097,
        hindsight_port=44367,
    )
    observed: dict[str, object] = {}

    def derive(current, *, diagnostic_owner_id):
        observed["material"] = current
        observed["owner"] = diagnostic_owner_id
        return llama_spec, lifecycle_spec, health

    monkeypatch.setattr(smoke, "_derive_current_host_bindings", derive)
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

    artifact_root = (tmp_path / "current-host-diagnostic").resolve()
    result = smoke.run_synthetic_hindsight_smoke(
        source_descriptor=None,
        current_host_material=material,
        diagnostic_owner_id="diagnostic-owner",
        repo_root=tmp_path.resolve(),
        artifact_root=artifact_root,
    )

    assert observed == {
        "material": material,
        "owner": "diagnostic-owner",
    }
    assert result["status"] == "NON_CITABLE_DIAGNOSTIC_PASS"
    assert result["scientific_spend"] == "NOT_OPENED"
    assert result["operational_source"]["mode"] == "current_host_material"
    assert result["operational_source"]["model_path"] == str(
        material.model_path
    )
    assert result["operational_source"]["model_sha256"] == (
        smoke._DIAGNOSTIC_LLAMA_CPP_MODEL_SHA256
    )
    assert result["operational_source"]["llm_max_concurrent"] == 1


def test_synthetic_smoke_requires_exactly_one_operational_source(
    tmp_path: Path,
) -> None:
    material = smoke.CurrentHostMaterial(
        llama_cpp_root=(tmp_path / "llama.cpp").resolve(),
        model_path=(tmp_path / "model.gguf").resolve(),
        onnx_model_path=(tmp_path / "model.onnx").resolve(),
        onnx_tokenizer_path=(tmp_path / "tokenizer").resolve(),
        llama_port=18097,
        hindsight_port=44367,
    )
    neither_root = (tmp_path / "neither").resolve()
    with pytest.raises(
        CampaignCarriageError,
        match="requires exactly one operational source",
    ):
        smoke.run_synthetic_hindsight_smoke(
            source_descriptor=None,
            current_host_material=None,
            diagnostic_owner_id="diagnostic-owner",
            repo_root=tmp_path.resolve(),
            artifact_root=neither_root,
        )
    assert not neither_root.exists()

    both_root = (tmp_path / "both").resolve()
    with pytest.raises(
        CampaignCarriageError,
        match="requires exactly one operational source",
    ):
        smoke.run_synthetic_hindsight_smoke(
            source_descriptor={},
            current_host_material=material,
            diagnostic_owner_id="diagnostic-owner",
            repo_root=tmp_path.resolve(),
            artifact_root=both_root,
        )
    assert not both_root.exists()


def test_current_host_binding_is_derived_from_repository_pins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    material = smoke.CurrentHostMaterial(
        llama_cpp_root=(tmp_path / "llama.cpp").resolve(),
        model_path=(tmp_path / "model.gguf").resolve(),
        onnx_model_path=(tmp_path / "model.onnx").resolve(),
        onnx_tokenizer_path=(tmp_path / "tokenizer").resolve(),
        llama_port=18097,
        hindsight_port=44367,
    )
    captured: dict[str, dict[str, object]] = {}
    monkeypatch.setattr(
        smoke,
        "_require_current_host_material",
        lambda value: None,
    )

    def llama_from_mapping(raw):
        captured["llama"] = dict(raw)
        return SimpleNamespace(**raw)

    def lifecycle_from_mapping(raw):
        captured["lifecycle"] = dict(raw)
        return SimpleNamespace(**raw)

    def health_from_mapping(raw):
        captured["health"] = dict(raw)
        return SimpleNamespace(value=dict(raw))

    monkeypatch.setattr(
        smoke.LlamaCppLaunchSpec,
        "from_mapping",
        llama_from_mapping,
    )
    monkeypatch.setattr(
        smoke.HindsightLifecycleSpec,
        "from_mapping",
        lifecycle_from_mapping,
    )
    monkeypatch.setattr(
        smoke.HindsightHealthAttestation,
        "from_mapping",
        health_from_mapping,
    )

    _llama, lifecycle, _health = smoke._derive_current_host_bindings(
        material,
        diagnostic_owner_id="diag-owner",
    )

    assert captured["llama"]["upstream_revision"] == (
        smoke._DIAGNOSTIC_LLAMA_CPP_REVISION
    )
    assert captured["llama"]["artifact_sha256"] == (
        smoke._DIAGNOSTIC_LLAMA_CPP_MODEL_SHA256
    )
    assert captured["llama"]["context"] == 8192
    assert captured["llama"]["slots"] == 1
    assert captured["llama"]["gpu_layers"] == 999
    assert captured["llama"]["expected_model_alias"] == str(
        material.model_path
    )

    assert captured["lifecycle"]["runtime_python"] == str(
        Path(smoke.sys.executable).resolve()
    )
    assert captured["lifecycle"]["runtime_version"] == "v0.10.0"
    assert captured["lifecycle"]["source_revision"] == (
        smoke._DIAGNOSTIC_HINDSIGHT_SOURCE_REVISION
    )
    assert captured["lifecycle"]["source_tree"] == (
        smoke._DIAGNOSTIC_HINDSIGHT_SOURCE_TREE
    )
    assert captured["lifecycle"]["database_profile"] == "diag-owner"
    assert captured["lifecycle"]["llm_max_concurrent"] == 1
    assert captured["lifecycle"]["retain_max_completion_tokens"] == 4096
    assert captured["lifecycle"]["embeddings_onnx_model_sha256"] == (
        smoke._DIAGNOSTIC_HINDSIGHT_ONNX_SHA256
    )
    assert captured["lifecycle"]["embeddings_onnx_tokenizer_tree_sha256"] == (
        smoke._DIAGNOSTIC_HINDSIGHT_TOKENIZER_TREE_SHA256
    )
    assert captured["lifecycle"]["package_wheel_sha256"] == (
        smoke._DIAGNOSTIC_HINDSIGHT_WHEEL_SHA256
    )
    assert lifecycle.deployment_id.startswith(
        "hindsight-v0.10.0-pg0-owner-"
    )


def test_current_host_cli_is_mutually_exclusive_with_source_descriptor(
    tmp_path: Path,
) -> None:
    base = [
        "--diagnostic-owner-id",
        "diag-owner",
        "--repo-root",
        str(tmp_path.resolve()),
        "--artifact-root",
        str((tmp_path / "artifact").resolve()),
    ]
    parsed = smoke._parser().parse_args(
        ["--current-host-material", *base]
    )
    assert parsed.current_host_material is True
    assert parsed.source_descriptor is None

    with pytest.raises(SystemExit):
        smoke._parser().parse_args(
            [
                "--current-host-material",
                "--source-descriptor",
                str((tmp_path / "source.json").resolve()),
                *base,
            ]
        )


def test_post2986_stress_profile_reproduces_bounded_pressure_without_scientific_spend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeLifecycle.instances.clear()
    health = SimpleNamespace(fingerprint="sha256:" + "a" * 64)
    lifecycle_spec = _FakeLifecycleSpec(database_profile="diagnostic-owner")
    llama_spec = SimpleNamespace(port=18097)
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

    artifact_root = (tmp_path / "post2986-stress").resolve()
    result = smoke.run_synthetic_hindsight_smoke(
        source_descriptor={},
        diagnostic_owner_id="diagnostic-owner",
        repo_root=tmp_path.resolve(),
        artifact_root=artifact_root,
        stress_profile="post2986",
    )

    lifecycle = _FakeLifecycle.instances[0]
    assert result["status"] == "NON_CITABLE_DIAGNOSTIC_PASS"
    assert result["scientific_spend"] == "NOT_OPENED"
    assert result["benchmark_text_used"] is False
    assert result["retain_count"] == 85
    assert result["synthetic_contract"]["stress_profile"] == "post2986"
    assert result["synthetic_contract"]["post2986_shape"] == {
        "warmup_completed_shape": 40,
        "stress_burst_shape": 45,
    }
    assert [item["retain_count"] for item in result["consolidation_receipts"]] == [
        40,
        45,
    ]
    assert len(lifecycle.retain_calls) == 85
    assert lifecycle.pending_allow_missing == [True, False]
    assert lifecycle.wait_calls == 2
    assert result["hindsight_semantic_operation_count"] == 90


def test_synthetic_smoke_preserves_failure_receipt_without_scientific_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailingLifecycle(_FakeLifecycle):
        def retain(self, *, bank_id: str, items):
            super().retain(bank_id=bank_id, items=items)
            raise CampaignCarriageError("synthetic retain failed")

    health = SimpleNamespace(fingerprint="sha256:" + "a" * 64)
    lifecycle_spec = _FakeLifecycleSpec(database_profile="diagnostic-owner")
    llama_spec = SimpleNamespace(port=18097)
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
    assert receipt["llama_capture"]["chat_completion_capture_count"] == 0
    assert receipt["cleanup"]["capture_proxy"]["all_owned_processes_terminated"] is True


def test_synthetic_smoke_preserves_retain_and_recall_shape_on_empty_recall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _EmptyRecallLifecycle(_FakeLifecycle):
        def recall(
            self,
            prompt: str,
            *,
            bank_id: str,
            query_timestamp: str | None = None,
        ):
            super().recall(
                prompt,
                bank_id=bank_id,
                query_timestamp=query_timestamp,
            )
            return {"results": [], "trace": {"synthetic": True}}

    health = SimpleNamespace(fingerprint="sha256:" + "a" * 64)
    lifecycle_spec = _FakeLifecycleSpec(database_profile="diagnostic-owner")
    llama_spec = SimpleNamespace(port=18097)
    monkeypatch.setattr(
        smoke,
        "_derive_diagnostic_bindings",
        lambda source, diagnostic_owner_id: (
            llama_spec,
            lifecycle_spec,
            health,
        ),
    )
    monkeypatch.setattr(smoke, "HindsightDeploymentSession", _EmptyRecallLifecycle)
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

    artifact_root = (tmp_path / "diagnostic-empty-recall").resolve()
    with pytest.raises(CampaignCarriageError, match="no mapped memories"):
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
    assert receipt["retain_response"]["success"] is True
    assert receipt["recall_response_shape"] == {
        "keys": ["results", "trace"],
        "result_count": 0,
    }
    assert receipt["llama_capture"]["chat_completion_capture_count"] == 0


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
    tree = ast.parse(source)
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "ScientificSpendLedger" not in imported_names
