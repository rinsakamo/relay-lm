from __future__ import annotations

import json

import httpx
import pytest

from relaylm.v2_transfer_actual_model import (
    prepare_r1_arms,
    run_source_learning,
    run_target_probe,
)
from relaylm.v2_transfer_experiment import generate_transfer_family
from tools.v2_cognitive_work_structured_output_qualification import (
    QUALIFICATION_VERSION as SOPQ_QUALIFICATION_VERSION,
    StructuredOutputCompletion,
)
from tools.v2_transfer_r1_structured_client import (
    CALL_SEQUENCE,
    OpenAICompatibleR1StructuredClient,
    R1StructuredTransportError,
    SOURCE_SCHEMA_NAME,
    TARGET_SCHEMA_NAME,
    TRANSPORT_VERSION,
    source_structure_response_format,
    source_structure_schema,
    target_answer_response_format,
    target_answer_schema,
    transport_identity,
)


class FakeStructuredClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[
            tuple[tuple[dict[str, str], ...], dict[str, object]]
        ] = []

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        response_format: dict[str, object],
    ) -> StructuredOutputCompletion:
        self.calls.append((messages, response_format))
        if not self.responses:
            raise AssertionError("unexpected structured-output call")
        return StructuredOutputCompletion(
            content=self.responses.pop(0),
            input_tokens=19,
            output_tokens=7,
            response_id=f"fake-{len(self.calls)}",
            finish_reason="stop",
        )


def _source_response(family) -> str:
    return json.dumps(
        {
            "permutation": list(family.source_rule.permutation),
            "offsets": list(family.source_rule.offsets),
            "modulus": family.source_rule.modulus,
        },
        separators=(",", ":"),
    )


def _target_response(family, step_index: int = 0) -> str:
    return json.dumps(
        list(family.expected_output(step_index)),
        separators=(",", ":"),
    )


def test_r1_structured_schemas_preserve_existing_raw_output_shapes():
    source = source_structure_schema(10)
    target = target_answer_schema(10)

    assert source == {
        "type": "object",
        "properties": {
            "permutation": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": 3},
                "minItems": 4,
                "maxItems": 4,
            },
            "offsets": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": 9},
                "minItems": 4,
                "maxItems": 4,
            },
            "modulus": {"type": "integer", "enum": [10]},
        },
        "required": ["permutation", "offsets", "modulus"],
        "additionalProperties": False,
    }
    assert target == {
        "type": "array",
        "items": {"type": "integer", "minimum": 0, "maximum": 9},
        "minItems": 4,
        "maxItems": 4,
    }

    source_format = source_structure_response_format(10)
    target_format = target_answer_response_format(10)
    assert source_format["type"] == "json_schema"
    assert source_format["json_schema"]["name"] == SOURCE_SCHEMA_NAME
    assert source_format["json_schema"]["strict"] is True
    assert target_format["type"] == "json_schema"
    assert target_format["json_schema"]["name"] == TARGET_SCHEMA_NAME
    assert target_format["json_schema"]["strict"] is True


def test_r1_structured_transport_identity_freezes_qualified_mechanism_and_sequence():
    identity = transport_identity(10)

    assert identity["transport_version"] == TRANSPORT_VERSION
    assert identity["qualified_mechanism"] == SOPQ_QUALIFICATION_VERSION
    assert identity["modulus"] == 10
    assert identity["call_sequence"] == list(CALL_SEQUENCE)
    assert CALL_SEQUENCE == (
        "source_structure",
        "target_answer",
        "target_answer",
        "target_answer",
    )
    for key in (
        "source_schema_digest",
        "target_schema_digest",
        "source_response_format_digest",
        "target_response_format_digest",
        "sequence_digest",
    ):
        assert identity[key].startswith("sha256:")


def test_r1_structured_adapter_drives_existing_source_learning_and_target_parsers():
    family = generate_transfer_family(seed=2334, regime="shared")
    target = _target_response(family)
    underlying = FakeStructuredClient(
        [_source_response(family), target, target, target]
    )
    client = OpenAICompatibleR1StructuredClient(
        structured_client=underlying,
        modulus=family.modulus,
    )

    learned = run_source_learning(client, family)
    arms = prepare_r1_arms(family, learned)
    probes = [
        run_target_probe(
            client,
            arm,
            family,
            step_index=0,
            examples_visible=0,
        )
        for arm in (arms.t0, arms.t1, arms.t2)
    ]

    assert learned.hypothesis.permutation == family.source_rule.permutation
    assert learned.hypothesis.offsets == family.source_rule.offsets
    assert all(probe.verification.correct for probe in probes)
    assert client.call_count == 4
    assert len(underlying.calls) == 4
    assert underlying.calls[0][1] == source_structure_response_format(family.modulus)
    assert all(
        response_format == target_answer_response_format(family.modulus)
        for _, response_format in underlying.calls[1:]
    )


def test_r1_structured_adapter_rejects_fifth_call_without_touching_provider():
    family = generate_transfer_family(seed=2335, regime="shared")
    target = _target_response(family)
    underlying = FakeStructuredClient(
        [_source_response(family), target, target, target]
    )
    client = OpenAICompatibleR1StructuredClient(
        structured_client=underlying,
        modulus=family.modulus,
    )
    messages = ({"role": "user", "content": "x"},)

    for _ in range(4):
        client.complete(messages)
    with pytest.raises(R1StructuredTransportError, match="exactly four"):
        client.complete(messages)

    assert len(underlying.calls) == 4


def test_r1_structured_adapter_reuses_qualified_http_client_without_decoding_overrides():
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        assert set(body) == {"model", "messages", "stream", "response_format"}
        assert body["model"] == "test-model"
        assert body["stream"] is False
        assert body["response_format"] == source_structure_response_format(10)
        return httpx.Response(
            200,
            json={
                "id": "cmpl-r1-structured",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"permutation":[0,1,2,3],'
                                '"offsets":[0,0,0,0],"modulus":10}'
                            ),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 5},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleR1StructuredClient(
        base_url="http://provider.invalid/v1",
        model="test-model",
        modulus=10,
        http_client=http_client,
    )
    completion = client.complete(
        (
            {"role": "system", "content": "infer"},
            {"role": "user", "content": "examples"},
        )
    )

    assert completion.response_id == "cmpl-r1-structured"
    assert completion.input_tokens == 11
    assert completion.output_tokens == 5
    assert len(seen) == 1


def test_r1_structured_adapter_rejects_ambiguous_constructor_or_modulus():
    fake = FakeStructuredClient([])
    with pytest.raises(R1StructuredTransportError, match="cannot be combined"):
        OpenAICompatibleR1StructuredClient(
            structured_client=fake,
            base_url="http://provider.invalid/v1",
            modulus=10,
        )
    with pytest.raises(R1StructuredTransportError, match="modulus"):
        OpenAICompatibleR1StructuredClient(
            structured_client=fake,
            modulus=1,
        )
