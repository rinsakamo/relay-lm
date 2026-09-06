from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import permutations
import json
from typing import Mapping, Protocol

import httpx

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from relaylm.v2_transfer_experiment import PublicExample, VectorRule


CALIBRATION_LABEL = "relaylm2-cognitive-ir-calibration-v1"
CALIBRATION_DIFFICULTIES = (
    "D0_OFFSET_ONLY_RANDOM",
    "D1_PERMUTATION_ONLY_RANDOM",
    "D2_FULL_DIAGNOSTIC",
    "D3_FULL_RANDOM",
)
CALIBRATION_PROBES = ("C0_APPLICATION_ONLY", "C1_FORMATION_ONLY", "C2_END_TO_END")
CALIBRATION_SEED_COUNT = 6
CALIBRATION_MODULUS = 10
CALIBRATION_VECTOR_WIDTH = 4
CALIBRATION_CLAIM_STATUS = "NON_CITABLE_S2_CALIBRATION"


class CalibrationError(ValueError):
    """The #2211 calibration contract cannot be satisfied."""


class StructuredCalibrationClient(Protocol):
    provider_attempts: int
    provider_completions: int

    @property
    def transport_identity(self) -> Mapping[str, object]: ...

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion: ...


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _seed_bytes(seed: int, label: str) -> bytes:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if not isinstance(label, str) or not label:
        raise TypeError("seed label must be non-empty")
    return hashlib.sha256(f"{CALIBRATION_LABEL}|{seed}|{label}".encode("utf-8")).digest()


def calibration_seeds() -> tuple[int, ...]:
    values = []
    for index in range(CALIBRATION_SEED_COUNT):
        raw = hashlib.sha256(f"{CALIBRATION_LABEL}|seed|{index}".encode("utf-8")).digest()
        values.append(int.from_bytes(raw[:4], "big") & 0x7FFFFFFF)
    seeds = tuple(values)
    if len(set(seeds)) != CALIBRATION_SEED_COUNT or 2211 in seeds:
        raise AssertionError("calibration seed rule produced an invalid seed set")
    return seeds


CALIBRATION_SEEDS = calibration_seeds()


def _vector(seed: int, label: str, *, modulus: int = CALIBRATION_MODULUS) -> tuple[int, ...]:
    raw = _seed_bytes(seed, label)
    return tuple(raw[index] % modulus for index in range(CALIBRATION_VECTOR_WIDTH))


def _non_identity_permutation(seed: int, label: str) -> tuple[int, ...]:
    order = tuple(
        sorted(
            range(CALIBRATION_VECTOR_WIDTH),
            key=lambda index: _seed_bytes(seed, f"{label}:perm:{index}"),
        )
    )
    identity = tuple(range(CALIBRATION_VECTOR_WIDTH))
    if order == identity:
        return order[1:] + order[:1]
    return order


def _independent_offsets(seed: int, label: str) -> tuple[int, ...]:
    return tuple(
        _seed_bytes(seed, f"{label}:offset:{index}")[0] % CALIBRATION_MODULUS
        for index in range(CALIBRATION_VECTOR_WIDTH)
    )


def _rule_for_difficulty(seed: int, difficulty: str) -> VectorRule:
    identity = tuple(range(CALIBRATION_VECTOR_WIDTH))
    zeros = (0,) * CALIBRATION_VECTOR_WIDTH
    if difficulty == "D0_OFFSET_ONLY_RANDOM":
        return VectorRule(identity, _independent_offsets(seed, difficulty), CALIBRATION_MODULUS)
    if difficulty == "D1_PERMUTATION_ONLY_RANDOM":
        return VectorRule(
            _non_identity_permutation(seed, difficulty),
            zeros,
            CALIBRATION_MODULUS,
        )
    if difficulty in {"D2_FULL_DIAGNOSTIC", "D3_FULL_RANDOM"}:
        return VectorRule(
            _non_identity_permutation(seed, difficulty),
            _independent_offsets(seed, difficulty),
            CALIBRATION_MODULUS,
        )
    raise CalibrationError(f"unsupported calibration difficulty: {difficulty}")


def _random_examples(
    seed: int,
    label: str,
    *,
    rule: VectorRule,
    salt: int,
) -> tuple[PublicExample, ...]:
    values = []
    for index in range(4):
        input_values = _vector(seed, f"{label}:salt:{salt}:example:{index}")
        values.append(PublicExample(input_values, rule.apply(input_values)))
    return tuple(values)


def _diagnostic_examples(seed: int, *, rule: VectorRule) -> tuple[PublicExample, ...]:
    inputs: list[tuple[int, ...]] = [(0, 0, 0, 0)]
    for index in range(CALIBRATION_VECTOR_WIDTH):
        scale = 1 + (_seed_bytes(seed, f"diagnostic-scale:{index}")[0] % 9)
        vector = [0] * CALIBRATION_VECTOR_WIDTH
        vector[index] = scale
        inputs.append(tuple(vector))
    return tuple(PublicExample(values, rule.apply(values)) for values in inputs)


def _candidate_rules(
    difficulty: str,
    examples: tuple[PublicExample, ...],
) -> tuple[VectorRule, ...]:
    if not examples:
        return ()
    identity = tuple(range(CALIBRATION_VECTOR_WIDTH))
    if difficulty == "D0_OFFSET_ONLY_RANDOM":
        candidate_permutations = (identity,)
    else:
        candidate_permutations = tuple(permutations(range(CALIBRATION_VECTOR_WIDTH)))

    candidates: list[VectorRule] = []
    first = examples[0]
    for permutation in candidate_permutations:
        if difficulty == "D1_PERMUTATION_ONLY_RANDOM":
            offsets = (0,) * CALIBRATION_VECTOR_WIDTH
        else:
            offsets = tuple(
                (
                    first.output_values[index]
                    - first.input_values[permutation[index]]
                )
                % CALIBRATION_MODULUS
                for index in range(CALIBRATION_VECTOR_WIDTH)
            )
        candidate = VectorRule(tuple(permutation), offsets, CALIBRATION_MODULUS)
        if all(candidate.apply(item.input_values) == item.output_values for item in examples):
            candidates.append(candidate)
    return tuple(candidates)


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    seed: int
    difficulty: str
    rule: VectorRule
    examples: tuple[PublicExample, ...]
    query: tuple[int, ...]

    @property
    def expected_output(self) -> tuple[int, ...]:
        return self.rule.apply(self.query)

    def public_examples(self) -> list[dict[str, object]]:
        return [
            {"input": list(example.input_values), "output": list(example.output_values)}
            for example in self.examples
        ]


def generate_calibration_case(*, seed: int, difficulty: str) -> CalibrationCase:
    if difficulty not in CALIBRATION_DIFFICULTIES:
        raise CalibrationError(f"unsupported calibration difficulty: {difficulty}")
    rule = _rule_for_difficulty(seed, difficulty)
    if difficulty == "D2_FULL_DIAGNOSTIC":
        examples = _diagnostic_examples(seed, rule=rule)
    else:
        examples = ()
        for salt in range(32):
            candidate = _random_examples(seed, difficulty, rule=rule, salt=salt)
            if _candidate_rules(difficulty, candidate) == (rule,):
                examples = candidate
                break
        if not examples:
            raise CalibrationError("failed to generate an identifiable calibration case")
    if _candidate_rules(difficulty, examples) != (rule,):
        raise CalibrationError("calibration examples do not identify exactly one legal rule")
    query = _vector(seed, f"{difficulty}:query")
    return CalibrationCase(seed=seed, difficulty=difficulty, rule=rule, examples=examples, query=query)


def _integer_array_schema(*, minimum: int, maximum: int) -> dict[str, object]:
    return {
        "type": "array",
        "items": {"type": "integer", "minimum": minimum, "maximum": maximum},
        "minItems": CALIBRATION_VECTOR_WIDTH,
        "maxItems": CALIBRATION_VECTOR_WIDTH,
    }


RULE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "permutation": {
            **_integer_array_schema(minimum=0, maximum=CALIBRATION_VECTOR_WIDTH - 1),
            "uniqueItems": True,
        },
        "offsets": _integer_array_schema(minimum=0, maximum=CALIBRATION_MODULUS - 1),
        "modulus": {"type": "integer", "const": CALIBRATION_MODULUS},
    },
    "required": ["permutation", "offsets", "modulus"],
    "additionalProperties": False,
}

ANSWER_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "answer": _integer_array_schema(minimum=0, maximum=CALIBRATION_MODULUS - 1),
    },
    "required": ["answer"],
    "additionalProperties": False,
}

END_TO_END_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        **RULE_SCHEMA["properties"],  # type: ignore[dict-item]
        "answer": _integer_array_schema(minimum=0, maximum=CALIBRATION_MODULUS - 1),
    },
    "required": ["permutation", "offsets", "modulus", "answer"],
    "additionalProperties": False,
}


def _rule_mapping(rule: VectorRule) -> dict[str, object]:
    return {
        "permutation": list(rule.permutation),
        "offsets": list(rule.offsets),
        "modulus": rule.modulus,
    }


def build_calibration_messages(
    case: CalibrationCase,
    probe: str,
) -> tuple[dict[str, str], ...]:
    if probe == "C0_APPLICATION_ONLY":
        system = (
            "Apply the explicit vector transformation exactly. The rule maps output position i "
            "to input[permutation[i]] plus offsets[i], modulo modulus. Return only the response "
            "required by the supplied JSON schema."
        )
        payload = {"rule": _rule_mapping(case.rule), "query": list(case.query)}
    elif probe == "C1_FORMATION_ONLY":
        system = (
            "Infer the one reusable vector transformation consistent with all examples. The rule "
            "maps output position i to input[permutation[i]] plus offsets[i], modulo modulus. "
            "Return only the response required by the supplied JSON schema."
        )
        payload = {"modulus": case.rule.modulus, "examples": case.public_examples()}
    elif probe == "C2_END_TO_END":
        system = (
            "Infer the one reusable vector transformation consistent with all examples, then apply "
            "that inferred rule to the query. The rule maps output position i to "
            "input[permutation[i]] plus offsets[i], modulo modulus. Return only the response "
            "required by the supplied JSON schema."
        )
        payload = {
            "modulus": case.rule.modulus,
            "examples": case.public_examples(),
            "query": list(case.query),
        }
    else:
        raise CalibrationError(f"unsupported calibration probe: {probe}")
    return (
        {"role": "system", "content": system},
        {"role": "user", "content": _json_text(payload)},
    )


def schema_for_probe(probe: str) -> tuple[str, Mapping[str, object]]:
    if probe == "C0_APPLICATION_ONLY":
        return "relaylm2_calibration_application", ANSWER_SCHEMA
    if probe == "C1_FORMATION_ONLY":
        return "relaylm2_calibration_formation", RULE_SCHEMA
    if probe == "C2_END_TO_END":
        return "relaylm2_calibration_end_to_end", END_TO_END_SCHEMA
    raise CalibrationError(f"unsupported calibration probe: {probe}")


def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise CalibrationError(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def _load_object(text: str, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except CalibrationError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CalibrationError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise CalibrationError(f"{label} must be a JSON object")
    return value


def _parse_int_array(value: object, *, label: str, maximum: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != CALIBRATION_VECTOR_WIDTH:
        raise CalibrationError(f"{label} must contain exactly four integers")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise CalibrationError(f"{label} must contain only integers")
    parsed = tuple(value)
    if any(item < 0 or item > maximum for item in parsed):
        raise CalibrationError(f"{label} contains an out-of-range value")
    return parsed


def _parse_rule(value: Mapping[str, object], *, exact_keys: set[str]) -> VectorRule:
    if set(value) != exact_keys:
        raise CalibrationError("structured rule output has unexpected keys")
    permutation = _parse_int_array(
        value.get("permutation"),
        label="permutation",
        maximum=CALIBRATION_VECTOR_WIDTH - 1,
    )
    offsets = _parse_int_array(
        value.get("offsets"),
        label="offsets",
        maximum=CALIBRATION_MODULUS - 1,
    )
    modulus = value.get("modulus")
    if modulus != CALIBRATION_MODULUS:
        raise CalibrationError("structured rule output has the wrong modulus")
    try:
        return VectorRule(permutation, offsets, CALIBRATION_MODULUS)
    except (TypeError, ValueError) as exc:
        raise CalibrationError("structured rule output is not a legal vector rule") from exc


@dataclass(frozen=True, slots=True)
class CalibrationCellResult:
    seed: int
    difficulty: str
    application_correct: bool
    formation_correct: bool
    end_to_end_rule_correct: bool
    end_to_end_answer_correct: bool
    input_tokens: int
    output_tokens: int

    @property
    def end_to_end_joint_correct(self) -> bool:
        return self.end_to_end_rule_correct and self.end_to_end_answer_correct


@dataclass(frozen=True, slots=True)
class CalibrationDifficultySummary:
    difficulty: str
    sample_count: int
    application_correct: int
    formation_correct: int
    end_to_end_joint_correct: int
    admitted: bool

    @property
    def application_rate(self) -> float:
        return self.application_correct / self.sample_count

    @property
    def formation_rate(self) -> float:
        return self.formation_correct / self.sample_count

    @property
    def end_to_end_rate(self) -> float:
        return self.end_to_end_joint_correct / self.sample_count


@dataclass(frozen=True, slots=True)
class CalibrationMatrixResult:
    cells: tuple[CalibrationCellResult, ...]
    summaries: tuple[CalibrationDifficultySummary, ...]
    selected_difficulty: str | None
    provider_calls: int
    claim_status: str = CALIBRATION_CLAIM_STATUS
    citable: bool = False

    @property
    def total_input_tokens(self) -> int:
        return sum(cell.input_tokens for cell in self.cells)

    @property
    def total_output_tokens(self) -> int:
        return sum(cell.output_tokens for cell in self.cells)

    def to_mapping(self) -> dict[str, object]:
        return {
            "claim_status": self.claim_status,
            "citable": self.citable,
            "provider_calls": self.provider_calls,
            "selected_difficulty": self.selected_difficulty,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "seed_rule": CALIBRATION_LABEL,
            "seeds": list(CALIBRATION_SEEDS),
            "difficulties": list(CALIBRATION_DIFFICULTIES),
            "probes": list(CALIBRATION_PROBES),
            "summaries": [
                {
                    "difficulty": item.difficulty,
                    "sample_count": item.sample_count,
                    "application_correct": item.application_correct,
                    "formation_correct": item.formation_correct,
                    "end_to_end_joint_correct": item.end_to_end_joint_correct,
                    "application_rate": item.application_rate,
                    "formation_rate": item.formation_rate,
                    "end_to_end_rate": item.end_to_end_rate,
                    "admitted": item.admitted,
                }
                for item in self.summaries
            ],
            "cells": [
                {
                    "seed": cell.seed,
                    "difficulty": cell.difficulty,
                    "application_correct": cell.application_correct,
                    "formation_correct": cell.formation_correct,
                    "end_to_end_rule_correct": cell.end_to_end_rule_correct,
                    "end_to_end_answer_correct": cell.end_to_end_answer_correct,
                    "end_to_end_joint_correct": cell.end_to_end_joint_correct,
                    "input_tokens": cell.input_tokens,
                    "output_tokens": cell.output_tokens,
                }
                for cell in self.cells
            ],
        }


def summarize_calibration(
    cells: tuple[CalibrationCellResult, ...],
) -> tuple[tuple[CalibrationDifficultySummary, ...], str | None]:
    summaries: list[CalibrationDifficultySummary] = []
    for difficulty in CALIBRATION_DIFFICULTIES:
        group = tuple(cell for cell in cells if cell.difficulty == difficulty)
        if len(group) != CALIBRATION_SEED_COUNT:
            raise CalibrationError("calibration matrix has an incomplete difficulty cell")
        application_correct = sum(cell.application_correct for cell in group)
        formation_correct = sum(cell.formation_correct for cell in group)
        end_to_end_correct = sum(cell.end_to_end_joint_correct for cell in group)
        sample_count = len(group)
        application_rate = application_correct / sample_count
        formation_rate = formation_correct / sample_count
        end_to_end_rate = end_to_end_correct / sample_count
        admitted = (
            application_rate >= 0.90
            and 0.40 <= formation_rate <= 0.90
            and 0.20 <= end_to_end_rate <= 0.80
        )
        summaries.append(
            CalibrationDifficultySummary(
                difficulty=difficulty,
                sample_count=sample_count,
                application_correct=application_correct,
                formation_correct=formation_correct,
                end_to_end_joint_correct=end_to_end_correct,
                admitted=admitted,
            )
        )
    selected = next(
        (item.difficulty for item in reversed(summaries) if item.admitted),
        None,
    )
    return tuple(summaries), selected


def _run_probe(
    client: StructuredCalibrationClient,
    case: CalibrationCase,
    probe: str,
) -> ExperimentCompletion:
    schema_name, schema = schema_for_probe(probe)
    return client.complete_structured(
        build_calibration_messages(case, probe),
        schema_name=schema_name,
        schema=schema,
    )


def run_calibration_matrix(client: StructuredCalibrationClient) -> CalibrationMatrixResult:
    cells: list[CalibrationCellResult] = []
    initial_attempts = client.provider_attempts
    initial_completions = client.provider_completions
    for difficulty in CALIBRATION_DIFFICULTIES:
        for seed in CALIBRATION_SEEDS:
            case = generate_calibration_case(seed=seed, difficulty=difficulty)
            application = _run_probe(client, case, "C0_APPLICATION_ONLY")
            formation = _run_probe(client, case, "C1_FORMATION_ONLY")
            end_to_end = _run_probe(client, case, "C2_END_TO_END")

            application_payload = _load_object(
                application.content,
                label="application calibration output",
            )
            if set(application_payload) != {"answer"}:
                raise CalibrationError("application calibration output has unexpected keys")
            application_answer = _parse_int_array(
                application_payload["answer"],
                label="application answer",
                maximum=CALIBRATION_MODULUS - 1,
            )

            formation_payload = _load_object(
                formation.content,
                label="formation calibration output",
            )
            formation_rule = _parse_rule(
                formation_payload,
                exact_keys={"permutation", "offsets", "modulus"},
            )

            e2e_payload = _load_object(
                end_to_end.content,
                label="end-to-end calibration output",
            )
            e2e_rule = _parse_rule(
                e2e_payload,
                exact_keys={"permutation", "offsets", "modulus", "answer"},
            )
            e2e_answer = _parse_int_array(
                e2e_payload["answer"],
                label="end-to-end answer",
                maximum=CALIBRATION_MODULUS - 1,
            )
            cells.append(
                CalibrationCellResult(
                    seed=seed,
                    difficulty=difficulty,
                    application_correct=application_answer == case.expected_output,
                    formation_correct=formation_rule == case.rule,
                    end_to_end_rule_correct=e2e_rule == case.rule,
                    end_to_end_answer_correct=e2e_answer == case.expected_output,
                    input_tokens=(
                        application.input_tokens
                        + formation.input_tokens
                        + end_to_end.input_tokens
                    ),
                    output_tokens=(
                        application.output_tokens
                        + formation.output_tokens
                        + end_to_end.output_tokens
                    ),
                )
            )

    expected_calls = len(CALIBRATION_DIFFICULTIES) * len(CALIBRATION_SEEDS) * len(CALIBRATION_PROBES)
    attempts = client.provider_attempts - initial_attempts
    completions = client.provider_completions - initial_completions
    if attempts != expected_calls or completions != expected_calls:
        raise CalibrationError(
            "completed calibration matrix must use exactly the frozen provider-call budget"
        )
    summaries, selected = summarize_calibration(tuple(cells))
    return CalibrationMatrixResult(
        cells=tuple(cells),
        summaries=summaries,
        selected_difficulty=selected,
        provider_calls=expected_calls,
    )


@dataclass(frozen=True, slots=True)
class OpenAICompatibleStructuredTransportIdentity:
    model: str
    timeout_seconds: float
    max_tokens: int
    temperature: float
    seed: int | None
    structured_output: bool = True
    api: str = "openai-chat-completions-json-schema-v1"

    def to_mapping(self) -> dict[str, object]:
        return {
            "api": self.api,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "seed": self.seed,
            "structured_output": self.structured_output,
        }


class OpenAICompatibleStructuredCalibrationClient:
    """OpenAI-compatible JSON-schema client used only by #2211 calibration."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 300.0,
        max_tokens: int = 128,
        temperature: int | float = 0.0,
        seed: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise CalibrationError("provider base_url must be non-empty")
        if not isinstance(model, str) or not model.strip():
            raise CalibrationError("provider model must be non-empty")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise CalibrationError("timeout_seconds must be numeric")
        if timeout_seconds <= 0:
            raise CalibrationError("timeout_seconds must be positive")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
            raise CalibrationError("max_tokens must be a positive integer")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise CalibrationError("temperature must be numeric")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise CalibrationError("seed must be an integer or null")
        if api_key is not None and not isinstance(api_key, str):
            raise TypeError("api_key must be a string or null")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = float(timeout_seconds)
        self.max_tokens = max_tokens
        self.temperature = float(temperature)
        self.seed = seed
        self.provider_attempts = 0
        self.provider_completions = 0
        self._client = http_client or httpx.Client(timeout=self.timeout_seconds)
        self._owns_client = http_client is None

    @property
    def transport_identity(self) -> dict[str, object]:
        return OpenAICompatibleStructuredTransportIdentity(
            model=self.model,
            timeout_seconds=self.timeout_seconds,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            seed=self.seed,
        ).to_mapping()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def complete_structured(
        self,
        messages: tuple[dict[str, str], ...],
        *,
        schema_name: str,
        schema: Mapping[str, object],
    ) -> ExperimentCompletion:
        if not messages:
            raise CalibrationError("messages must not be empty")
        if not isinstance(schema_name, str) or not schema_name.strip():
            raise CalibrationError("schema_name must be non-empty")
        normalized_messages: list[dict[str, str]] = []
        for message in messages:
            if set(message) != {"role", "content"}:
                raise CalibrationError("each message must contain exactly role/content")
            role = message["role"]
            content = message["content"]
            if role not in {"system", "user", "assistant"}:
                raise CalibrationError("unsupported message role")
            if not isinstance(content, str) or not content:
                raise CalibrationError("message content must be non-empty")
            normalized_messages.append({"role": role, "content": content})

        body: dict[str, object] = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": dict(schema),
                },
            },
        }
        if self.seed is not None:
            body["seed"] = self.seed
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.provider_attempts += 1
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
        except httpx.HTTPError as exc:
            raise StructureProposalError(f"provider request failed: {exc}") from exc
        if not response.is_success:
            raise StructureProposalError(
                f"provider request failed with status {response.status_code}"
            )
        try:
            envelope = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise StructureProposalError("provider response is not valid JSON") from exc
        if not isinstance(envelope, Mapping):
            raise StructureProposalError("provider response must be an object")
        choices = envelope.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise StructureProposalError("provider response must contain exactly one choice")
        choice = choices[0]
        if not isinstance(choice, Mapping):
            raise StructureProposalError("provider choice must be an object")
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None and finish_reason != "stop":
            raise StructureProposalError("provider choice did not finish with stop")
        message = choice.get("message")
        if not isinstance(message, Mapping):
            raise StructureProposalError("provider message must be an object")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise StructureProposalError("provider message content must be non-empty")
        usage = envelope.get("usage")
        if not isinstance(usage, Mapping):
            raise StructureProposalError("provider usage must be an object")
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        for label, value in (
            ("prompt_tokens", prompt_tokens),
            ("completion_tokens", completion_tokens),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise StructureProposalError(f"{label} must be a non-negative integer")
        response_id = envelope.get("id")
        if response_id is not None and not isinstance(response_id, str):
            raise StructureProposalError("provider response id must be a string or null")
        self.provider_completions += 1
        return ExperimentCompletion(
            content=content,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            response_id=response_id,
        )
