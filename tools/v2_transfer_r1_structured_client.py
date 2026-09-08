from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json

import httpx

from relaylm.v2_transfer_actual_model import (
    ExperimentCompletion,
    StructureProposalError,
)
from tools.v2_cognitive_work_structured_output_qualification import (
    OpenAICompatibleStructuredOutputClient,
    QUALIFICATION_VERSION as SOPQ_QUALIFICATION_VERSION,
    StructuredOutputClient,
)


TRANSPORT_VERSION = "relaylm2-transfer-r1-structured-v1"
SOURCE_SCHEMA_NAME = "relaylm2_transfer_r1_source_structure_v1"
TARGET_SCHEMA_NAME = "relaylm2_transfer_r1_target_answer_v1"
CALL_SEQUENCE = ("source_structure", "target_answer", "target_answer", "target_answer")
_VECTOR_WIDTH = 4


class R1StructuredTransportError(StructureProposalError):
    """The R1 structured transport cannot satisfy its frozen call contract."""


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: object) -> str:
    payload = (
        value.encode("utf-8")
        if isinstance(value, str)
        else _canonical_json(value).encode("utf-8")
    )
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _validate_modulus(modulus: int) -> int:
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise R1StructuredTransportError("modulus must be an integer greater than one")
    return modulus


def source_structure_schema(modulus: int) -> dict[str, object]:
    modulus = _validate_modulus(modulus)
    return {
        "type": "object",
        "properties": {
            "permutation": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": _VECTOR_WIDTH - 1},
                "minItems": _VECTOR_WIDTH,
                "maxItems": _VECTOR_WIDTH,
            },
            "offsets": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": modulus - 1},
                "minItems": _VECTOR_WIDTH,
                "maxItems": _VECTOR_WIDTH,
            },
            "modulus": {"type": "integer", "enum": [modulus]},
        },
        "required": ["permutation", "offsets", "modulus"],
        "additionalProperties": False,
    }


def target_answer_schema(modulus: int) -> dict[str, object]:
    modulus = _validate_modulus(modulus)
    return {
        "type": "array",
        "items": {"type": "integer", "minimum": 0, "maximum": modulus - 1},
        "minItems": _VECTOR_WIDTH,
        "maxItems": _VECTOR_WIDTH,
    }


def _response_format(*, name: str, schema: Mapping[str, object]) -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": dict(schema),
        },
    }


def source_structure_response_format(modulus: int) -> dict[str, object]:
    return _response_format(
        name=SOURCE_SCHEMA_NAME,
        schema=source_structure_schema(modulus),
    )


def target_answer_response_format(modulus: int) -> dict[str, object]:
    return _response_format(
        name=TARGET_SCHEMA_NAME,
        schema=target_answer_schema(modulus),
    )


def transport_identity(modulus: int) -> dict[str, object]:
    modulus = _validate_modulus(modulus)
    source_schema = source_structure_schema(modulus)
    target_schema = target_answer_schema(modulus)
    source_format = source_structure_response_format(modulus)
    target_format = target_answer_response_format(modulus)
    return {
        "transport_version": TRANSPORT_VERSION,
        "qualified_mechanism": SOPQ_QUALIFICATION_VERSION,
        "modulus": modulus,
        "call_sequence": list(CALL_SEQUENCE),
        "source_schema_name": SOURCE_SCHEMA_NAME,
        "target_schema_name": TARGET_SCHEMA_NAME,
        "source_schema_digest": _sha256(source_schema),
        "target_schema_digest": _sha256(target_schema),
        "source_response_format_digest": _sha256(source_format),
        "target_response_format_digest": _sha256(target_format),
        "sequence_digest": _sha256(
            [
                source_format if kind == "source_structure" else target_format
                for kind in CALL_SEQUENCE
            ]
        ),
    }


class OpenAICompatibleR1StructuredClient:
    """Four-call R1 adapter over the already-qualified structured-output client.

    The #2157 R1 smoke has one frozen execution order: source learning followed
    by T0, T1, and T2 target probes. This adapter maps that declared order to
    explicit JSON-Schema response formats without inspecting prompt text or
    relaxing the existing #2157 parsers.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        modulus: int = 10,
        api_key: str | None = None,
        timeout: float = 120.0,
        http_client: httpx.Client | None = None,
        structured_client: StructuredOutputClient | None = None,
    ) -> None:
        self.modulus = _validate_modulus(modulus)
        if structured_client is not None:
            if any(
                value is not None
                for value in (base_url, model, api_key, http_client)
            ):
                raise R1StructuredTransportError(
                    "structured_client cannot be combined with provider constructor arguments"
                )
            self._client = structured_client
            self._owned_client = None
        else:
            if not isinstance(base_url, str) or not base_url.strip():
                raise R1StructuredTransportError("base_url must be non-empty")
            if not isinstance(model, str) or not model.strip():
                raise R1StructuredTransportError("model must be non-empty")
            owned = OpenAICompatibleStructuredOutputClient(
                base_url=base_url,
                model=model,
                api_key=api_key,
                timeout=timeout,
                http_client=http_client,
            )
            self._client = owned
            self._owned_client = owned
        self._call_index = 0

    @property
    def call_count(self) -> int:
        return self._call_index

    @property
    def identity(self) -> dict[str, object]:
        return transport_identity(self.modulus)

    def close(self) -> None:
        if self._owned_client is not None:
            self._owned_client.close()

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self._call_index >= len(CALL_SEQUENCE):
            raise R1StructuredTransportError(
                "R1 structured transport permits exactly four model calls"
            )
        kind = CALL_SEQUENCE[self._call_index]
        response_format = (
            source_structure_response_format(self.modulus)
            if kind == "source_structure"
            else target_answer_response_format(self.modulus)
        )
        # Advance before provider invocation. A material provider/protocol failure
        # consumes this sequence slot; the fail-closed host never retries it.
        self._call_index += 1
        completion = self._client.complete(
            messages,
            response_format=response_format,
        )
        return ExperimentCompletion(
            content=completion.content,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            response_id=completion.response_id,
        )
