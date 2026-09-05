from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from relaylm.v2_cognitive_ir_actual_model import (
    build_s2_target_messages,
    form_s2_representations,
)
from relaylm.v2_cognitive_ir_experiment import REPRESENTATION_KINDS
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import generate_transfer_family
from tools.v2_cognitive_ir_s2_host import S2HostError, run_s2_host_smoke


_EXECUTION_ORDER = [
    "form-p2",
    "form-p3",
    "form-p4",
    "probe-p0",
    "probe-p1",
    "probe-p2",
    "probe-p3",
    "probe-p4",
    "probe-p5",
    "probe-p6",
]


class QueueClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[dict[str, str], ...]] = []

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("unexpected provider call")
        return ExperimentCompletion(
            content=self.responses.pop(0),
            input_tokens=17,
            output_tokens=6,
            response_id=f"review-{len(self.calls)}",
        )


def _rule_json(family) -> str:
    return json.dumps(
        {
            "permutation": list(family.source_rule.permutation),
            "offsets": list(family.source_rule.offsets),
            "modulus": family.modulus,
        },
        separators=(",", ":"),
    )


def _responses(*, invalid_target: bool = False, mixed_target: bool = False) -> tuple[object, list[str]]:
    family = generate_transfer_family(seed=2211, regime="shared")
    expected = json.dumps(list(family.expected_output(0)), separators=(",", ":"))
    targets = [expected for _ in REPRESENTATION_KINDS]
    if invalid_target:
        targets[0] = "not-json"
    if mixed_target:
        wrong = [0, 0, 0, 0]
        if wrong == list(family.expected_output(0)):
            wrong[0] = 1
        targets[0] = json.dumps(wrong, separators=(",", ":"))
    return family, [
        "faithful plain-text recap of the observed episodes",
        "compact plain-text reusable gist of the observed episodes",
        _rule_json(family),
        *targets,
    ]


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository(root: Path) -> dict[str, object]:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True, text=True)
    _git(root, "config", "user.email", "s2-review@example.invalid")
    _git(root, "config", "user.name", "S2 Review")
    (root / "tracked.txt").write_text("s2-review\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "fixture")
    return {
        "commit": _git(root, "rev-parse", "HEAD"),
        "tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "clean_required": True,
    }


def _minimal_identity(repository: dict[str, object]) -> dict[str, object]:
    return {
        "repository": repository,
        "model": {"id": "loaded-test-model", "revision": "local-stable-id"},
        "backend": "lm_studio",
        "runtime": "lm-studio-openai-compatible",
        "decoding": {"temperature": 0, "top_p": 1},
        "reasoning": {"mode": "provider_default"},
        "execution_order": list(_EXECUTION_ORDER),
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
    }


def test_s2_text_controls_accept_plain_text_and_all_target_arms_receive_public_modulus():
    family, responses = _responses()
    client = QueueClient(responses[:3])
    representations = form_s2_representations(client, family)

    assert json.loads(representations["P2_ORDINARY_SUMMARY"].serialized) == {
        "summary": "faithful plain-text recap of the observed episodes"
    }
    assert json.loads(representations["P3_SEMANTIC_CACHE"].serialized) == {
        "gist": "compact plain-text reusable gist of the observed episodes"
    }

    tasks = []
    for kind in REPRESENTATION_KINDS:
        prompt = build_s2_target_messages(
            representations[kind],
            family,
            step_index=0,
            examples_visible=0,
        )
        packet = json.loads(prompt.messages[1]["content"])
        tasks.append(packet["task"])
    assert all(task == tasks[0] for task in tasks)
    assert tasks[0]["modulus"] == family.modulus


def test_s2_host_accepts_minimal_stable_identity_without_citable_launch_admission(tmp_path: Path):
    family, responses = _responses()
    repository_root = tmp_path / "repo"
    repository = _repository(repository_root)
    identity = _minimal_identity(repository)
    client = QueueClient(responses)
    root = tmp_path / "artifacts"

    result = run_s2_host_smoke(
        artifact_root=root,
        identity=identity,
        repository_root=repository_root,
        live_binding_probe=lambda: {"model": identity["model"]},
        client=client,
        family=family,
        step_index=0,
        examples_visible=0,
    )

    assert len(client.calls) == 10
    assert result.status == "COMPLETED"
    assert result.mechanical_classification == "CEILING"
    assert result.typed_generic_semantic_equal is True
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    assert manifest["live_binding_fields"] == ["model"]
    assert "launch_admission" not in manifest["identity"]
    summary = json.loads((root / "s2-smoke-result.json").read_text(encoding="utf-8"))
    assert summary["protocol_assessment"]["classification"] == "CEILING"
    assert summary["protocol_assessment"]["s3_preregistration_allowed"] is False


def test_s2_initial_live_binding_failure_is_durable_incomplete_with_zero_model_calls(tmp_path: Path):
    family, responses = _responses()
    repository_root = tmp_path / "repo"
    repository = _repository(repository_root)
    identity = _minimal_identity(repository)
    client = QueueClient(responses)
    root = tmp_path / "artifacts"

    def broken_probe() -> dict[str, object]:
        raise RuntimeError("provider metadata endpoint unavailable")

    with pytest.raises(S2HostError, match="preflight"):
        run_s2_host_smoke(
            artifact_root=root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=broken_probe,
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    assert client.calls == []
    state = json.loads((root / "run-state.json").read_text(encoding="utf-8"))
    assert state["status"] == "INCOMPLETE"
    assert state["provider_calls"] == 0
    evidence = (root / "request-evidence.jsonl").read_text(encoding="utf-8")
    assert "physical_binding_probe_failure" in evidence


def test_s2_output_protocol_defect_is_completed_but_blocks_s3(tmp_path: Path):
    family, responses = _responses(invalid_target=True)
    repository_root = tmp_path / "repo"
    repository = _repository(repository_root)
    identity = _minimal_identity(repository)
    root = tmp_path / "artifacts"

    result = run_s2_host_smoke(
        artifact_root=root,
        identity=identity,
        repository_root=repository_root,
        live_binding_probe=lambda: {"model": identity["model"]},
        client=QueueClient(responses),
        family=family,
        step_index=0,
        examples_visible=0,
    )

    assert result.status == "COMPLETED"
    assert result.mechanical_classification == "OUTPUT_PROTOCOL_DEFECT"
    summary = json.loads((root / "s2-smoke-result.json").read_text(encoding="utf-8"))
    assessment = summary["protocol_assessment"]
    assert assessment["all_outputs_protocol_valid"] is False
    assert assessment["s3_preregistration_allowed"] is False


def test_s2_mixed_protocol_valid_answers_are_mechanically_discriminating(tmp_path: Path):
    family, responses = _responses(mixed_target=True)
    repository_root = tmp_path / "repo"
    repository = _repository(repository_root)
    identity = _minimal_identity(repository)
    root = tmp_path / "artifacts"

    result = run_s2_host_smoke(
        artifact_root=root,
        identity=identity,
        repository_root=repository_root,
        live_binding_probe=lambda: {"model": identity["model"]},
        client=QueueClient(responses),
        family=family,
        step_index=0,
        examples_visible=0,
    )

    assert result.mechanical_classification == "MECHANICALLY_DISCRIMINATING"
    summary = json.loads((root / "s2-smoke-result.json").read_text(encoding="utf-8"))
    assert summary["protocol_assessment"]["s3_preregistration_allowed"] is True
    assert summary["protocol_assessment"]["typed_generic_semantic_equal"] is True
    assert summary["protocol_assessment"]["p4_p5_p6_shared_formation"] is True
