from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import relaylm.actual_model_stage_r_llama_cpp_semantic_continuity_projection as host
import relaylm.actual_model_stage_r_llama_cpp_semantic_continuity_projection_transaction as selector
import relaylm.actual_model_stage_r_llama_cpp_transaction as transaction
import tools.v1_llama_cpp_controller_preflight as controller_preflight
import tools.v1_stage_r_llama_cpp_semantic_continuity_projection_wsl as projection_wrapper
import tools.v1_stage_r_llama_cpp_wsl as base_wrapper
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionCompletionMetadata,
    CognitionExtractionOutput,
)
from relaylm.events import Event
from relaylm.identity import Identity


def _synthetic_input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("Synthetic evaluation identity."),
        state_classes={},
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "The parcel label is visible, but its contents are not known."},
            event_id="evt-current",
            timestamp="2026-01-01T00:00:00+00:00",
        ),
    )


def _retained_payload() -> dict[str, object]:
    return {
        "format_version": 1,
        "diagnostic": "epistemic-formation-t2",
        "mechanical_validation": "pass",
        "items": [
            {
                "subject_span": "its contents",
                "unknown_evidence_span": "contents are not known",
                "source_event_id": "evt-current",
            }
        ],
        "semantic_review": {"status": "not_run"},
    }


def _write_payload(path: Path, payload: object) -> bytes:
    raw = (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return raw


def test_retained_formation_binding_preserves_hash_and_only_formed_fields(
    tmp_path: Path,
) -> None:
    path = tmp_path / "retained.json"
    raw = _write_payload(path, _retained_payload())

    binding = host.load_retained_formation_binding(
        path=path,
        cognitive_input=_synthetic_input(),
    )

    assert binding["sha256"] == f"sha256:{hashlib.sha256(raw).hexdigest()}"
    assert binding["item_count"] == 1
    assert binding["continuity_expectation_supplied"] is False
    assert set(binding["items"][0]) == {
        "subject_span",
        "unknown_evidence_span",
        "source_event_id",
    }


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"diagnostic": "wrong", "mechanical_validation": "pass", "items": []},
        {
            "diagnostic": "epistemic-formation-t2",
            "mechanical_validation": "fail",
            "items": [],
        },
        {
            "diagnostic": "epistemic-formation-t2",
            "mechanical_validation": "pass",
            "items": [],
        },
    ],
)
def test_retained_formation_binding_rejects_malformed_inputs(
    tmp_path: Path,
    payload: object,
) -> None:
    path = tmp_path / "retained.json"
    _write_payload(path, payload)

    with pytest.raises(Exception):
        host.load_retained_formation_binding(
            path=path,
            cognitive_input=_synthetic_input(),
        )


def test_retained_formation_binding_rejects_wrong_source_event(tmp_path: Path) -> None:
    payload = _retained_payload()
    payload["items"][0]["source_event_id"] = "evt-other"
    path = tmp_path / "retained.json"
    _write_payload(path, payload)

    with pytest.raises(Exception, match="source_event_id"):
        host.load_retained_formation_binding(
            path=path,
            cognitive_input=_synthetic_input(),
        )


def test_retained_formation_binding_rejects_non_source_span(tmp_path: Path) -> None:
    payload = _retained_payload()
    payload["items"][0]["subject_span"] = "a phrase absent from the event"
    path = tmp_path / "retained.json"
    _write_payload(path, payload)

    with pytest.raises(Exception, match="substring"):
        host.load_retained_formation_binding(
            path=path,
            cognitive_input=_synthetic_input(),
        )


def test_retained_formation_binding_rejects_expected_ir_fields(tmp_path: Path) -> None:
    payload = _retained_payload()
    payload["items"][0]["expected_kind"] = "forbidden"
    path = tmp_path / "retained.json"
    _write_payload(path, payload)

    with pytest.raises(Exception, match="invalid fields"):
        host.load_retained_formation_binding(
            path=path,
            cognitive_input=_synthetic_input(),
        )


def test_missing_retained_formation_fails_before_projection(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="not a file"):
        host.load_retained_formation_binding(
            path=tmp_path / "missing.json",
            cognitive_input=_synthetic_input(),
        )


def test_projection_run_invokes_exactly_one_semantic_generation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = {"generate": 0, "client_close": 0, "provider_close": 0}

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def aclose(self) -> None:
            calls["client_close"] += 1

    class FakeProvider:
        def __init__(self, **kwargs) -> None:
            self.raw_observation_artifacts = []
            self.request_body_artifacts = []
            self.completion_artifacts = []
            self.input_count_artifacts = []

        async def generate_projection(self, cognitive_input, *, observations, pass_request):
            calls["generate"] += 1
            return CognitionExtractionOutput(
                state_candidates=(),
                continuity_candidates=(),
                completion=CognitionCompletionMetadata(),
            )

        async def aclose(self) -> None:
            calls["provider_close"] += 1

    monkeypatch.setattr(host.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(host, "ProjectionLlamaProvider", FakeProvider)

    result = asyncio.run(
        host._run_projection(
            base_url="http://127.0.0.1:1234/v1",
            request_model="synthetic-model",
            workspace_root=tmp_path / "workspace",
            artifact_root=tmp_path / "artifacts",
            replicate_id="0",
            api_key=None,
            authority=type(
                "Authority",
                (),
                {"temperature": 0.0, "top_p": 1.0, "seed": None},
            )(),
            cognitive_input=_synthetic_input(),
            observations=(),
            counter=object(),
        )
    )

    assert calls == {"generate": 1, "client_close": 1, "provider_close": 1}
    assert result["projection_generation_count"] == 1
    assert result["formation_generation_count"] == 0
    assert result["pass1_generation_count"] == 0
    assert result["state_generation_count"] == 0
    assert result["t3_generation_count"] == 0


def test_selector_forwards_retained_path_only_as_opaque_host_arg(
    tmp_path: Path,
    monkeypatch,
) -> None:
    retained = tmp_path / "retained.json"
    retained.write_text("{}", encoding="utf-8")
    observed: dict[str, object] = {}

    def fake_run_transaction(
        argv,
        *,
        host_module,
        host_summary_filename,
        host_args,
    ) -> int:
        observed.update(
            argv=list(argv),
            host_module=host_module,
            host_summary_filename=host_summary_filename,
            host_args=tuple(host_args),
        )
        return 17

    monkeypatch.setattr(selector, "run_transaction", fake_run_transaction)

    rc = selector.main(
        [
            "--retained-formation-artifact",
            str(retained),
            "--origin",
            "http://127.0.0.1:1234",
        ]
    )

    assert rc == 17
    assert observed["host_module"] == selector.HOST_MODULE
    assert observed["host_summary_filename"] == selector.HOST_SUMMARY_FILENAME
    assert observed["host_args"] == (
        "--retained-formation-artifact",
        str(retained.resolve()),
    )
    assert observed["argv"] == ["--origin", "http://127.0.0.1:1234"]


def test_projection_wrapper_forwards_retained_path_without_reading_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    retained = tmp_path / "does-not-need-to-exist-yet.json"
    observed: dict[str, object] = {}

    def fake_run_wsl_transaction(argv, *, inner_transaction, inner_args) -> int:
        observed.update(
            argv=list(argv),
            inner_transaction=inner_transaction,
            inner_args=tuple(inner_args),
        )
        return 23

    monkeypatch.setattr(projection_wrapper, "run_wsl_transaction", fake_run_wsl_transaction)

    rc = projection_wrapper.main(
        ["--retained-formation-artifact", str(retained)]
    )

    assert rc == 23
    assert observed["argv"] == []
    assert observed["inner_transaction"] == projection_wrapper.INNER_TRANSACTION
    assert observed["inner_args"] == (
        "--retained-formation-artifact",
        str(retained.resolve()),
    )


def test_base_wrapper_preserves_ordinary_command_and_can_forward_inner_args(
    tmp_path: Path,
    monkeypatch,
) -> None:
    operator_home = tmp_path / "operator-home"
    operator_home.mkdir()
    monkeypatch.setenv("HOME", str(operator_home))
    commands: list[list[str]] = []
    runtime_roots: list[Path] = []

    def fake_run(command, *, cwd, env, check):
        commands.append(list(command))
        runtime_roots.append(Path(env["HOME"]).parent)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(base_wrapper.subprocess, "run", fake_run)

    try:
        assert base_wrapper.main([]) == 0
        assert (
            base_wrapper.main(
                [],
                inner_transaction="synthetic.transaction",
                inner_args=("--probe-input", "/tmp/evidence.json"),
            )
            == 0
        )
    finally:
        for root in runtime_roots:
            shutil.rmtree(root, ignore_errors=True)

    ordinary = commands[0]
    forwarded = commands[1]
    assert ordinary[1:3] == ["-m", base_wrapper.INNER_TRANSACTION]
    assert "--probe-input" not in ordinary
    assert forwarded[1:5] == [
        "-m",
        "synthetic.transaction",
        "--probe-input",
        "/tmp/evidence.json",
    ]
    assert forwarded.index("--probe-input") < forwarded.index("--repo-root")


def test_transaction_forwards_host_args_before_owned_host_arguments(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    selected_summary = artifact_root / "selected-summary.json"
    selected_summary.write_text(
        json.dumps({"classification": "PASS"}),
        encoding="utf-8",
    )
    observed: list[str] = []

    def fake_run(command, **kwargs):
        observed.extend(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(transaction.subprocess, "run", fake_run)

    result = transaction._invoke_host(
        repo_root=tmp_path,
        api_base="http://127.0.0.1:1234/v1",
        request_model="synthetic-model",
        artifact_path=tmp_path / "model.gguf",
        revision="r" * 40,
        version="synthetic",
        build=1,
        gpu_identity="synthetic-gpu",
        launch_command=["llama-server"],
        log_path=tmp_path / "server.log",
        workspace_root=tmp_path / "workspace",
        artifact_root=artifact_root,
        replicate_id="0",
        host_module="synthetic.host",
        host_summary_path=selected_summary,
        host_args=("--probe-input", "/tmp/evidence.json"),
    )

    assert result["summary"]["classification"] == "PASS"
    assert observed[1:5] == [
        "-m",
        "synthetic.host",
        "--probe-input",
        "/tmp/evidence.json",
    ]
    assert observed.index("--probe-input") < observed.index("--repo-root")


def test_controller_preflight_emits_exact_wrapper_arguments() -> None:
    ordinary = controller_preflight.one_shot_command(
        "tools.synthetic_wrapper",
        executable="/venv/bin/python",
    )
    projection = controller_preflight.one_shot_command(
        "tools.synthetic_wrapper",
        executable="/venv/bin/python",
        wrapper_args=(
            "--retained-formation-artifact",
            "/tmp/retained.json",
        ),
    )

    assert ordinary == ["/venv/bin/python", "-m", "tools.synthetic_wrapper"]
    assert projection == ordinary + [
        "--retained-formation-artifact",
        "/tmp/retained.json",
    ]


def test_zero_semantic_counts_cover_non_projection_paths() -> None:
    counts = host._zero_semantic_counts()
    assert counts["projection_generation_count"] == 0
    assert counts["formation_generation_count"] == 0
    assert counts["pass1_generation_count"] == 0
    assert counts["state_generation_count"] == 0
    assert counts["t3_generation_count"] == 0
    assert counts["semantic_retry_count"] == 0
    assert counts["replay_count"] == 0
    assert counts["reseed_count"] == 0
    assert counts["fallback_count"] == 0
    assert counts["fastcal_count"] == 0
    assert counts["lm_studio_contact_count"] == 0
    assert counts["repository_mutation_count"] == 0
