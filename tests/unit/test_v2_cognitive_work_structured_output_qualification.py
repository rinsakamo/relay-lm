from __future__ import annotations

import json
from pathlib import Path
import subprocess

import httpx
import pytest

from tools.v2_cognitive_work_r0 import ExecutionBinding
from tools.v2_cognitive_work_structured_output_qualification import (
    ANSWER_RESPONSE_FORMAT_DIGEST,
    ANSWER_SCHEMA,
    ANSWER_SCHEMA_DIGEST,
    MANIFEST_NAME,
    OPERATION_RESPONSE_FORMAT_DIGEST,
    OPERATION_SCHEMA,
    OPERATION_SCHEMA_DIGEST,
    QUALIFICATION_CALL_COUNT,
    QUALIFICATION_PLAN_DIGEST,
    REQUEST_EVIDENCE_NAME,
    RESULT_NAME,
    STATE_NAME,
    OpenAICompatibleStructuredOutputClient,
    StructuredOutputCompletion,
    StructuredOutputExecutionAuthorization,
    StructuredOutputQualificationError,
    StructuredOutputQualificationIdentity,
    parse_answer,
    parse_operation,
    qualification_plan,
    response_format_for,
    run_structured_output_qualification,
)


class FakeStructuredClient:
    def __init__(self, *, wrapper_at: int | None = None, fail_at: int | None = None):
        self.wrapper_at = wrapper_at
        self.fail_at = fail_at
        self.calls: list[tuple[tuple[dict[str, str], ...], dict[str, object]]] = []

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        response_format: dict[str, object],
    ) -> StructuredOutputCompletion:
        index = len(self.calls)
        self.calls.append((messages, response_format))
        if self.fail_at is not None and index == self.fail_at:
            raise StructuredOutputQualificationError("synthetic provider failure")
        schema = response_format["json_schema"]
        assert isinstance(schema, dict)
        schema_body = schema["schema"]
        assert isinstance(schema_body, dict)
        properties = schema_body["properties"]
        assert isinstance(properties, dict)
        if "answer" in properties:
            content = json.dumps({"answer": f"OK-{index}"})
        else:
            content = json.dumps({"operation": "ZERO"})
        if self.wrapper_at is not None and index == self.wrapper_at:
            content = f"```json\n{content}\n```"
        return StructuredOutputCompletion(
            content=content,
            input_tokens=20 + index,
            output_tokens=4,
            response_id=f"fake-sopq-{index:02d}",
            finish_reason="stop",
        )


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "RelayLM Test")
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "seed.txt")
    _git(root, "commit", "-m", "seed")
    return root, _git(root, "rev-parse", "HEAD"), _git(root, "rev-parse", "HEAD^{tree}")


def _binding(**overrides: object) -> ExecutionBinding:
    values: dict[str, object] = {
        "model_identity": "model@artifact",
        "runtime_identity": "runtime@build",
        "hardware_identity": "gpu@class",
        "tokenizer_identity": "tokenizer@revision",
        "template_identity": "template@digest",
        "context_limit": 8192,
        "decoding_identity": "stream=false;overrides=omitted;response_format=schema",
        "reasoning_identity": "reasoning=on;request_override=omitted",
    }
    values.update(overrides)
    return ExecutionBinding(**values)  # type: ignore[arg-type]


def _identity(repo: Path, binding: ExecutionBinding) -> StructuredOutputQualificationIdentity:
    return StructuredOutputQualificationIdentity(
        repository_commit=_git(repo, "rev-parse", "HEAD"),
        repository_tree=_git(repo, "rev-parse", "HEAD^{tree}"),
        execution=binding,
    )


def _authorization(
    identity: StructuredOutputQualificationIdentity,
    *,
    authorized: bool = True,
) -> StructuredOutputExecutionAuthorization:
    return StructuredOutputExecutionAuthorization(
        authorization_id="deterministic-test-only",
        execution_repository_commit=identity.repository_commit,
        physical_execution_authorized=authorized,
    )


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        assert isinstance(value, dict)
        result.append(value)
    return result


def test_structured_output_schemas_and_response_formats_are_frozen():
    assert ANSWER_SCHEMA == {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    assert OPERATION_SCHEMA["required"] == ["operation"]
    operation_properties = OPERATION_SCHEMA["properties"]
    assert isinstance(operation_properties, dict)
    operation = operation_properties["operation"]
    assert isinstance(operation, dict)
    assert operation["enum"] == ["ZERO", "THINK", "RETRIEVE", "OBSERVE"]
    assert ANSWER_SCHEMA_DIGEST.startswith("sha256:")
    assert OPERATION_SCHEMA_DIGEST.startswith("sha256:")
    assert ANSWER_SCHEMA_DIGEST != OPERATION_SCHEMA_DIGEST
    assert ANSWER_RESPONSE_FORMAT_DIGEST.startswith("sha256:")
    assert OPERATION_RESPONSE_FORMAT_DIGEST.startswith("sha256:")
    for kind in ("answer", "operation"):
        response_format = response_format_for(kind)
        assert response_format["type"] == "json_schema"
        json_schema = response_format["json_schema"]
        assert isinstance(json_schema, dict)
        assert json_schema["strict"] is True


def test_qualification_plan_is_exactly_12_non_r2_calls():
    plan = qualification_plan()
    assert len(plan) == QUALIFICATION_CALL_COUNT == 12
    assert len({item.call_id for item in plan}) == 12
    assert sum(item.schema_kind == "answer" for item in plan) == 8
    assert sum(item.schema_kind == "operation" for item in plan) == 4
    assert sum(item.fixture_class == "A_RECONSIDER" for item in plan) == 2
    assert QUALIFICATION_PLAN_DIGEST.startswith("sha256:")
    serialized = json.dumps(
        [item.messages for item in plan],
        ensure_ascii=False,
        sort_keys=True,
    )
    for forbidden in (
        "hidden_regime",
        "expected_answer",
        "retrieval_packet",
        "observation_packet",
        "r2-",
    ):
        assert forbidden not in serialized


def test_strict_parsers_reject_wrappers_extras_duplicates_and_wrong_types():
    assert parse_answer('{"answer":"OK"}') == "OK"
    assert parse_operation('{"operation":"THINK"}') == "THINK"
    invalid_answers = (
        '```json\n{"answer":"OK"}\n```',
        '{"answer":7}',
        '{"answer":""}',
        '{"answer":"OK","extra":1}',
        '{"answer":"OK","answer":"NO"}',
    )
    for payload in invalid_answers:
        with pytest.raises(StructuredOutputQualificationError):
            parse_answer(payload)
    with pytest.raises(StructuredOutputQualificationError):
        parse_operation('{"operation":"OTHER"}')


def test_complete_fake_qualification_requires_all_12_calls(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    client = FakeStructuredClient()
    probe_calls: list[int] = []

    def probe() -> ExecutionBinding:
        probe_calls.append(1)
        return binding

    result = run_structured_output_qualification(
        artifact_root=artifact,
        repository_root=repo,
        identity=identity,
        authorization=_authorization(identity),
        live_binding_probe=probe,
        client=client,
        run_id="sopq-fake-complete",
    )

    assert result.status == "COMPLETED"
    assert result.verdict == "STRUCTURED_OUTPUT_PROTOCOL_QUALIFIED"
    assert result.provider_attempts == 12
    assert result.provider_completions == 12
    assert len(client.calls) == 12
    assert len(probe_calls) == 13
    state = _read_json(artifact / STATE_NAME)
    assert state["status"] == "COMPLETED"
    assert state["provider_attempts"] == 12
    assert state["provider_completions"] == 12
    assert state["plan_cursor"] == 12
    result_payload = _read_json(artifact / RESULT_NAME)
    assert result_payload["strict_whole_response_json"] == "12/12"
    assert result_payload["schema_validation"] == "12/12"
    assert result_payload["wrapper_or_prose_defects"] == 0
    manifest = _read_json(artifact / MANIFEST_NAME)
    assert manifest["r2_campaign_tasks"] == 0
    evidence = _read_jsonl(artifact / REQUEST_EVIDENCE_NAME)
    assert len(evidence) == 12
    assert all(item["kind"] == "model_exchange" for item in evidence)
    assert all("response_format" in item for item in evidence)


def test_wrapper_failure_is_durable_and_no_result_is_created(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    client = FakeStructuredClient(wrapper_at=2)

    with pytest.raises(
        StructuredOutputQualificationError,
        match="strict whole-response JSON",
    ):
        run_structured_output_qualification(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="sopq-wrapper-failure",
        )

    assert len(client.calls) == 3
    state = _read_json(artifact / STATE_NAME)
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 3
    assert state["provider_completions"] == 3
    failure = state["failure"]
    assert isinstance(failure, dict)
    assert failure["kind"] == "protocol_invalid"
    assert not (artifact / RESULT_NAME).exists()
    evidence = _read_jsonl(artifact / REQUEST_EVIDENCE_NAME)
    assert len(evidence) == 3
    assert evidence[-1]["kind"] == "model_exchange"
    response = evidence[-1]["response"]
    assert isinstance(response, dict)
    assert str(response["content"]).startswith("```json")


def test_provider_failure_counts_attempt_without_completion_and_stops(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    client = FakeStructuredClient(fail_at=2)

    with pytest.raises(
        StructuredOutputQualificationError,
        match="provider call failed",
    ):
        run_structured_output_qualification(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="sopq-provider-failure",
        )

    state = _read_json(artifact / STATE_NAME)
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 3
    assert state["provider_completions"] == 2
    assert len(client.calls) == 3
    assert not (artifact / RESULT_NAME).exists()


def test_binding_drift_stops_before_next_provider_attempt(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    drifted = _binding(runtime_identity="runtime@drift")
    identity = _identity(repo, binding)
    client = FakeStructuredClient()
    probes = iter((binding, binding, binding, drifted))

    with pytest.raises(
        StructuredOutputQualificationError,
        match="physical binding drift",
    ):
        run_structured_output_qualification(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity),
            live_binding_probe=lambda: next(probes),
            client=client,
            run_id="sopq-binding-drift",
        )

    assert len(client.calls) == 2
    state = _read_json(artifact / STATE_NAME)
    assert state["status"] == "INCOMPLETE"
    assert state["provider_attempts"] == 2
    assert state["provider_completions"] == 2
    assert not (artifact / RESULT_NAME).exists()


def test_false_authorization_fails_before_artifact_or_provider(tmp_path: Path):
    repo, _, _ = _repo(tmp_path)
    artifact = tmp_path / "artifact"
    binding = _binding()
    identity = _identity(repo, binding)
    client = FakeStructuredClient()

    with pytest.raises(
        StructuredOutputQualificationError,
        match="not authorized",
    ):
        run_structured_output_qualification(
            artifact_root=artifact,
            repository_root=repo,
            identity=identity,
            authorization=_authorization(identity, authorized=False),
            live_binding_probe=lambda: binding,
            client=client,
            run_id="sopq-no-auth",
        )

    assert not artifact.exists()
    assert client.calls == []


def test_openai_structured_client_sends_only_frozen_transport_controls():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert isinstance(body, dict)
        captured.update(body)
        return httpx.Response(
            200,
            json={
                "id": "resp-structured",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"answer":"5"}'},
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 5},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleStructuredOutputClient(
        base_url="http://example.test/v1",
        model="model",
        http_client=http_client,
    )
    completion = client.complete(
        qualification_plan()[0].messages,
        response_format=response_format_for("answer"),
    )
    assert completion.content == '{"answer":"5"}'
    assert captured["stream"] is False
    assert captured["response_format"] == response_format_for("answer")
    for forbidden in (
        "temperature",
        "top_p",
        "seed",
        "max_tokens",
        "stop",
        "tools",
    ):
        assert forbidden not in captured
    http_client.close()
