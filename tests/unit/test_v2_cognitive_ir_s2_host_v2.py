from __future__ import annotations

import json
from pathlib import Path
import subprocess

import httpx
import pytest

from relaylm.v2_lmstudio_native_experiment import LMStudioNativeExperimentClient
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from relaylm.v2_transfer_experiment import generate_transfer_family
from tools.v2_cognitive_ir_s2_host import S2HostError, S2RepositoryState
from tools.v2_cognitive_ir_s2_host_v2 import run_s2_host_smoke_v2


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_repo(root: Path) -> tuple[Path, S2RepositoryState]:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True, text=True)
    _git(root, "config", "user.email", "s2-v2@example.invalid")
    _git(root, "config", "user.name", "S2 V2 Host Test")
    (root / "tracked.txt").write_text("relaylm2-cognitive-ir-s2-host-v2\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "fixture")
    return root, S2RepositoryState(
        commit=_git(root, "rev-parse", "HEAD"),
        tree=_git(root, "rev-parse", "HEAD^{tree}"),
        clean=True,
    )


def _transport() -> dict[str, object]:
    return {
        "api": "test-transport-v1",
        "model": "test-model",
        "model_instance_id": "test-model",
        "timeout_seconds": 300.0,
        "reasoning": "off",
        "max_output_tokens": 512,
        "context_length": 8192,
        "temperature": None,
        "top_p": None,
        "store": False,
    }


def _identity(repository: S2RepositoryState) -> dict[str, object]:
    return {
        "repository": {
            "commit": repository.commit,
            "tree": repository.tree,
            "clean_required": True,
        },
        "model": {"id": "test-model", "revision": "fixture"},
        "backend": "test-backend",
        "runtime": "test-runtime",
        "transport": _transport(),
        "execution_order": [
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
        ],
        "retry_policy": {"automatic_retry": False, "semantic_retry": False},
    }


def _responses(seed: int = 2211) -> tuple[object, list[str]]:
    family = generate_transfer_family(seed=seed, regime="shared")
    learned = json.dumps(
        {
            "permutation": list(family.source_rule.permutation),
            "offsets": list(family.source_rule.offsets),
            "modulus": family.modulus,
        },
        separators=(",", ":"),
    )
    target = json.dumps(list(family.expected_output(0)), separators=(",", ":"))
    return family, [
        "faithful concise recap",
        "compact reusable semantic gist",
        learned,
        target,
        target,
        target,
        target,
        target,
        target,
        target,
    ]


class AttemptAwareFakeClient:
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = list(responses)
        self.provider_attempts = 0
        self.provider_completions = 0
        self.calls: list[tuple[dict[str, str], ...]] = []

    @property
    def transport_identity(self) -> dict[str, object]:
        return _transport()

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        self.provider_attempts += 1
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("unexpected provider call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        self.provider_completions += 1
        return ExperimentCompletion(
            content=response,
            input_tokens=17,
            output_tokens=6,
            response_id=f"fake-{self.provider_completions}",
        )


def test_s2_host_v2_records_failed_provider_attempt_without_completion(tmp_path: Path):
    family, _ = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    client = AttemptAwareFakeClient([StructureProposalError("timeout")])
    artifact = tmp_path / "artifact"

    with pytest.raises(S2HostError, match="provider failure"):
        run_s2_host_smoke_v2(
            artifact_root=artifact,
            identity=_identity(state),
            repository_root=repository_root,
            live_binding_probe=lambda: {"model": _identity(state)["model"]},
            client=client,
            family=family,
            step_index=0,
            examples_visible=0,
        )

    run_state = json.loads((artifact / "run-state.json").read_text(encoding="utf-8"))
    assert run_state["status"] == "INCOMPLETE"
    assert run_state["provider_calls"] == 0
    assert run_state["provider_attempts"] == 1
    assert run_state["provider_completions"] == 0


def test_s2_host_v2_success_preserves_ten_completed_calls_and_attempts(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    client = AttemptAwareFakeClient(responses)
    artifact = tmp_path / "artifact"

    result = run_s2_host_smoke_v2(
        artifact_root=artifact,
        identity=_identity(state),
        repository_root=repository_root,
        live_binding_probe=lambda: {"model": _identity(state)["model"]},
        client=client,
        family=family,
        step_index=0,
        examples_visible=0,
    )

    assert result.status == "COMPLETED"
    assert result.provider_calls == 10
    assert result.provider_attempts == 10
    assert result.provider_completions == 10
    run_state = json.loads((artifact / "run-state.json").read_text(encoding="utf-8"))
    durable = json.loads((artifact / "s2-smoke-result.json").read_text(encoding="utf-8"))
    assert run_state["provider_attempts"] == 10
    assert run_state["provider_completions"] == 10
    assert durable["provider_attempts"] == 10
    assert durable["provider_completions"] == 10
    assert durable["cost_accounting"]["physical_provider_attempts"] == 10
    assert durable["cost_accounting"]["physical_provider_completions"] == 10


def test_s2_host_v2_requires_transport_identity_match_before_artifacts(tmp_path: Path):
    family, responses = _responses()
    repository_root, state = _git_repo(tmp_path / "repo")
    identity = _identity(state)
    identity["transport"] = {**_transport(), "timeout_seconds": 120.0}
    artifact = tmp_path / "artifact"

    with pytest.raises(S2HostError, match="transport identity"):
        run_s2_host_smoke_v2(
            artifact_root=artifact,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=lambda: {"model": identity["model"]},
            client=AttemptAwareFakeClient(responses),
            family=family,
            step_index=0,
            examples_visible=0,
        )
    assert not artifact.exists()


def test_lmstudio_native_client_freezes_visible_answer_contract():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/api/v1/chat"
        assert body == {
            "model": "google/gemma-4-12b",
            "input": "user packet",
            "system_prompt": "system instruction",
            "stream": False,
            "reasoning": "off",
            "max_output_tokens": 512,
            "context_length": 8192,
            "store": False,
        }
        return httpx.Response(
            200,
            json={
                "model_instance_id": "google/gemma-4-12b",
                "output": [{"type": "message", "content": "visible answer"}],
                "stats": {
                    "input_tokens": 42,
                    "total_output_tokens": 9,
                    "reasoning_output_tokens": 0,
                },
            },
        )

    client = LMStudioNativeExperimentClient(
        base_url="http://provider.invalid",
        model="google/gemma-4-12b",
        model_instance_id="google/gemma-4-12b",
        context_length=8192,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    completion = client.complete(
        (
            {"role": "system", "content": "system instruction"},
            {"role": "user", "content": "user packet"},
        )
    )

    assert completion.content == "visible answer"
    assert completion.input_tokens == 42
    assert completion.output_tokens == 9
    assert client.provider_attempts == 1
    assert client.provider_completions == 1
    assert client.transport_identity["timeout_seconds"] == 300.0
    assert client.transport_identity["reasoning"] == "off"
    assert client.transport_identity["max_output_tokens"] == 512


def test_lmstudio_native_client_charges_timeout_attempt_without_completion():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow provider", request=request)

    client = LMStudioNativeExperimentClient(
        base_url="http://provider.invalid",
        model="google/gemma-4-12b",
        model_instance_id="google/gemma-4-12b",
        context_length=8192,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(StructureProposalError, match="provider request failed"):
        client.complete(
            (
                {"role": "system", "content": "system instruction"},
                {"role": "user", "content": "user packet"},
            )
        )
    assert client.provider_attempts == 1
    assert client.provider_completions == 0


def test_lmstudio_native_client_does_not_promote_hidden_reasoning_to_answer():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model_instance_id": "google/gemma-4-12b",
                "output": [
                    {"type": "reasoning", "content": "hidden work"},
                    {"type": "message", "content": ""},
                ],
                "stats": {
                    "input_tokens": 42,
                    "total_output_tokens": 4048,
                    "reasoning_output_tokens": 4048,
                },
            },
        )

    client = LMStudioNativeExperimentClient(
        base_url="http://provider.invalid",
        model="google/gemma-4-12b",
        model_instance_id="google/gemma-4-12b",
        context_length=8192,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(StructureProposalError, match="reasoning"):
        client.complete(
            (
                {"role": "system", "content": "system instruction"},
                {"role": "user", "content": "user packet"},
            )
        )
    assert client.provider_attempts == 1
    assert client.provider_completions == 0
