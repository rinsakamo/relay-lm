from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from relaylm.v2_transfer_actual_model import StructureProposalError
from tools import v2_cognitive_ir_s2_selected_lmstudio as entry
from tools.v2_cognitive_ir_s2_host import S2HostError, S2RepositoryState
from tools.v2_cognitive_ir_s2_host_v2 import S2HostV2Result


_MESSAGES = (
    {"role": "system", "content": "Do the declared task."},
    {"role": "user", "content": "{}"},
)


def _provider_response(
    content: str,
    *,
    reasoning_tokens: int = 0,
    reasoning_content: str | None = None,
    finish_reason: str = "stop",
) -> dict[str, object]:
    message: dict[str, object] = {"content": content}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    return {
        "id": "resp-1",
        "choices": [{"finish_reason": finish_reason, "message": message}],
        "usage": {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "completion_tokens_details": {"reasoning_tokens": reasoning_tokens},
        },
    }


def _binding() -> dict[str, object]:
    return {
        "model": "google/gemma-4-12b",
        "model_instance_id": "google/gemma-4-12b",
        "context_length": 8192,
        "runtime": {
            "architecture": "gemma4",
            "format": "gguf",
            "quantization": "Q4_K_M",
            "selected_variant": "google/gemma-4-12b@q4_k_m",
            "reasoning_capability": {
                "allowed_options": ["off", "on"],
                "default": "on",
            },
        },
    }


def test_selected_s2_client_uses_plain_text_then_strict_machine_readable_schemas() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        bodies.append(body)
        index = len(bodies) - 1
        if index == 0:
            content = "faithful recap"
        elif index == 1:
            content = "compact semantic gist"
        elif index == 2:
            content = '{"permutation":[0,1,2,3],"offsets":[3,2,1,1],"modulus":10}'
        else:
            content = "[9,7,7,9]"
        return httpx.Response(200, json=_provider_response(content))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = entry.SelectedS2OpenAIClient(
            base_url="http://lmstudio:1234/v1",
            model="google/gemma-4-12b",
            http_client=http_client,
        )
        completions = [client.complete(_MESSAGES) for _ in entry.S2_SELECTED_CALL_PLAN]

    assert len(completions) == 10
    assert client.provider_attempts == client.provider_completions == 10
    assert "response_format" not in bodies[0]
    assert "response_format" not in bodies[1]
    assert bodies[2]["response_format"]["type"] == "json_schema"
    assert bodies[2]["response_format"]["json_schema"]["strict"] is True
    assert bodies[2]["response_format"]["json_schema"]["schema"]["type"] == "object"
    assert bodies[2]["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    for body in bodies[3:]:
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["strict"] is True
        assert body["response_format"]["json_schema"]["schema"]["type"] == "array"
    assert all("reasoning" not in body and "reasoning_effort" not in body for body in bodies)
    assert all(body["max_tokens"] == 512 for body in bodies)
    assert client.transport_identity["reasoning"] == "off"
    assert client.transport_identity["reasoning_verification"] == (
        "usage.completion_tokens_details.reasoning_tokens==0"
    )


def test_selected_s2_client_rejects_nonzero_reasoning_tokens() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json=_provider_response("summary", reasoning_tokens=3),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = entry.SelectedS2OpenAIClient(
            base_url="http://lmstudio:1234/v1",
            model="google/gemma-4-12b",
            http_client=http_client,
        )
        with pytest.raises(StructureProposalError, match="reasoning_tokens=3"):
            client.complete(_MESSAGES)

    assert client.provider_attempts == 1
    assert client.provider_completions == 0


def test_selected_s2_client_rejects_nonempty_reasoning_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json=_provider_response("summary", reasoning_content="hidden work"),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        client = entry.SelectedS2OpenAIClient(
            base_url="http://lmstudio:1234/v1",
            model="google/gemma-4-12b",
            http_client=http_client,
        )
        with pytest.raises(StructureProposalError, match="non-empty reasoning content"):
            client.complete(_MESSAGES)


def test_selected_s2_entrypoint_builds_frozen_family_and_fresh_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        entry,
        "probe_s2_git_repository",
        lambda root: S2RepositoryState(commit="commit", tree="tree", clean=True),
    )
    monkeypatch.setattr(entry, "_probe_binding", lambda **kwargs: _binding())

    def fake_run(**kwargs):
        captured.update(kwargs)
        return S2HostV2Result(
            run_id="s2-test",
            identity_fingerprint="sha256:test",
            status="COMPLETED",
            claim_status="NON_CITABLE_S2_SMOKE",
            citable=False,
            provider_calls=10,
            provider_attempts=10,
            provider_completions=10,
            arm_correctness=(False,) * 7,
            mechanical_classification="FLOOR",
            typed_generic_semantic_equal=True,
        )

    monkeypatch.setattr(entry, "run_s2_host_smoke_v2", fake_run)

    result = entry.run_lmstudio_selected_s2_transaction(
        base_url="http://lmstudio:1234",
        model="google/gemma-4-12b",
        repository_root=tmp_path / "repo",
        artifact_root=tmp_path / "artifact",
    )

    identity = captured["identity"]
    assert identity["repository"] == {
        "commit": "commit",
        "tree": "tree",
        "clean_required": True,
    }
    assert identity["model"] == identity["transport"]["model"] == "google/gemma-4-12b"
    assert identity["context_length"] == 8192
    assert identity["runtime"]["architecture"] == "gemma4"
    assert identity["runtime"]["format"] == "gguf"
    assert identity["runtime"]["quantization"] == "Q4_K_M"
    assert identity["execution_order"] == list(entry.S2_SELECTED_CALL_PLAN)
    assert identity["selected_task_regime"] == "V2_IDENTITY_OFFSET_NO_WRAP"
    assert identity["retry_policy"] == {
        "automatic_retry": False,
        "semantic_retry": False,
    }
    family = captured["family"]
    assert family.seed == 1399709667
    assert family.target_steps[0].query == (6, 5, 6, 8)
    assert captured["step_index"] == 0
    assert captured["examples_visible"] == 0
    assert result.status == "COMPLETED"


def test_selected_s2_entrypoint_rejects_runtime_case_drift_before_provider_calls(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        entry,
        "probe_s2_git_repository",
        lambda root: S2RepositoryState(commit="commit", tree="tree", clean=True),
    )
    bad = _binding()
    bad["runtime"] = dict(bad["runtime"])
    bad["runtime"]["architecture"] = "Gemma4"
    monkeypatch.setattr(entry, "_probe_binding", lambda **kwargs: bad)

    with pytest.raises(S2HostError, match="runtime mismatch: architecture"):
        entry.run_lmstudio_selected_s2_transaction(
            base_url="http://lmstudio:1234",
            model="google/gemma-4-12b",
            repository_root=tmp_path / "repo",
            artifact_root=tmp_path / "artifact",
        )


def test_selected_s2_entrypoint_checks_each_call_plan_equality_independently(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        entry,
        "probe_s2_git_repository",
        lambda root: S2RepositoryState(commit="commit", tree="tree", clean=True),
    )
    monkeypatch.setattr(entry, "S2_SELECTED_PHYSICAL_CALLS", 9)

    with pytest.raises(AssertionError, match="call-plan constants diverged"):
        entry.run_lmstudio_selected_s2_transaction(
            base_url="http://lmstudio:1234",
            model="google/gemma-4-12b",
            repository_root=tmp_path / "repo",
            artifact_root=tmp_path / "artifact",
        )
