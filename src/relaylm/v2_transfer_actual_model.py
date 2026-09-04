from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Protocol

import httpx

from relaylm.v2_interventions import ProjectionPolicy, ProjectionResult, ResourceVector, project_scope
from relaylm.v2_semantics import (
    Apply,
    Literal,
    ObservationInput,
    Proposal,
    SemanticTransactionStore,
    TransactionRequest,
    apply,
    literal,
    semantic_id,
)
from relaylm.v2_transfer_experiment import TransferFamily, VerificationResult


_SOURCE_STRUCTURE_SYMBOL = "learned_transfer_structure_hypothesis"
_VECTOR_WIDTH = 4


class StructureProposalError(ValueError):
    """R1 experiment input or model output cannot satisfy the declared contract."""


@dataclass(frozen=True, slots=True)
class ExperimentCompletion:
    content: str
    input_tokens: int
    output_tokens: int
    response_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str) or not self.content.strip():
            raise StructureProposalError("model completion content must be non-empty")
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise StructureProposalError(f"{name} must be a non-negative integer")
        if self.response_id is not None and (
            not isinstance(self.response_id, str) or not self.response_id.strip()
        ):
            raise StructureProposalError("response_id must be null or a non-empty string")


class ExperimentClient(Protocol):
    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion: ...


@dataclass(frozen=True, slots=True)
class StructureHypothesis:
    permutation: tuple[int, ...]
    offsets: tuple[int, ...]
    modulus: int

    def __post_init__(self) -> None:
        if isinstance(self.modulus, bool) or not isinstance(self.modulus, int):
            raise StructureProposalError("modulus must be an integer")
        if self.modulus <= 1:
            raise StructureProposalError("modulus must be greater than one")
        if len(self.permutation) != _VECTOR_WIDTH:
            raise StructureProposalError("permutation has the wrong width")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in self.permutation):
            raise StructureProposalError("permutation entries must be integers")
        if tuple(sorted(self.permutation)) != tuple(range(_VECTOR_WIDTH)):
            raise StructureProposalError("permutation must be a bijection")
        if len(self.offsets) != _VECTOR_WIDTH:
            raise StructureProposalError("offsets have the wrong width")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in self.offsets):
            raise StructureProposalError("offset entries must be integers")
        if any(value < 0 or value >= self.modulus for value in self.offsets):
            raise StructureProposalError("offset entries must be inside the modulus")

    def to_mapping(self) -> dict[str, object]:
        return {
            "permutation": list(self.permutation),
            "offsets": list(self.offsets),
            "modulus": self.modulus,
        }


@dataclass(frozen=True, slots=True)
class SourceLearningResult:
    store: SemanticTransactionStore
    structure_id: str
    source_evidence_ids: tuple[str, ...]
    hypothesis: StructureHypothesis
    completion: ExperimentCompletion
    resource_cost: ResourceVector


@dataclass(slots=True)
class R1Arm:
    store: SemanticTransactionStore
    projection_policy: ProjectionPolicy
    projection: ProjectionResult
    source_structure_id: str
    target_local_id: str


@dataclass(slots=True)
class R1ArmSet:
    t0: R1Arm
    t1: R1Arm
    t2: R1Arm


@dataclass(frozen=True, slots=True)
class TargetPrompt:
    messages: tuple[dict[str, str], ...]
    task_packet: dict[str, object]
    task_digest: str
    reusable_structure: dict[str, object] | None


@dataclass(frozen=True, slots=True)
class TargetProbeResult:
    completion: ExperimentCompletion
    verification: VerificationResult
    prompt: TargetPrompt
    resource_cost: ResourceVector


def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StructureProposalError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise StructureProposalError(f"non-standard JSON numeric constant: {value}")


def _load_strict_json(text: str, *, label: str) -> object:
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_members,
            parse_constant=_reject_json_constant,
        )
    except StructureProposalError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise StructureProposalError(f"{label} is not valid JSON") from exc


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise StructureProposalError(f"{label} must be an object")
    return value


def _require_token_count(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StructureProposalError(f"{label} must be a non-negative integer")
    return value


class OpenAICompatibleExperimentClient:
    """Minimal Chat Completions adapter used only by the bounded R1 experiment."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120.0,
        temperature: int | float | None = None,
        top_p: int | float | None = None,
        seed: int | None = None,
        max_tokens: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise StructureProposalError("provider base_url must be non-empty")
        if not isinstance(model, str) or not model.strip():
            raise StructureProposalError("provider model must be non-empty")
        if api_key is not None and not isinstance(api_key, str):
            raise TypeError("api_key must be a string or null")
        for name, value in (("temperature", temperature), ("top_p", top_p)):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise StructureProposalError(f"{name} must be numeric or null")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise StructureProposalError("seed must be an integer or null")
        if max_tokens is not None and (
            isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0
        ):
            raise StructureProposalError("max_tokens must be a positive integer or null")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.top_p = top_p
        self.seed = seed
        self.max_tokens = max_tokens
        self._client = http_client or httpx.Client(timeout=timeout)
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if not messages:
            raise StructureProposalError("messages must not be empty")
        normalized_messages: list[dict[str, str]] = []
        for message in messages:
            if set(message) != {"role", "content"}:
                raise StructureProposalError("each message must contain exactly role/content")
            role = message["role"]
            content = message["content"]
            if role not in {"system", "user", "assistant"}:
                raise StructureProposalError("unsupported message role")
            if not isinstance(content, str) or not content:
                raise StructureProposalError("message content must be a non-empty string")
            normalized_messages.append({"role": role, "content": content})

        body: dict[str, object] = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False,
        }
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if self.top_p is not None:
            body["top_p"] = self.top_p
        if self.seed is not None:
            body["seed"] = self.seed
        if self.max_tokens is not None:
            body["max_tokens"] = self.max_tokens

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
        except httpx.HTTPError as exc:
            raise StructureProposalError(f"provider request failed: {exc}") from exc
        if not response.is_success:
            raise StructureProposalError(f"provider request failed with status {response.status_code}")

        try:
            text = response.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StructureProposalError("provider response is not UTF-8") from exc
        envelope = _require_mapping(
            _load_strict_json(text, label="provider response"),
            label="provider response",
        )
        choices = envelope.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise StructureProposalError("provider response must contain exactly one choice")
        choice = _require_mapping(choices[0], label="provider choice")
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None and finish_reason != "stop":
            raise StructureProposalError("provider choice did not finish with stop")
        message = _require_mapping(choice.get("message"), label="provider message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise StructureProposalError("provider message content must be non-empty")

        usage = _require_mapping(envelope.get("usage"), label="provider usage")
        input_tokens = _require_token_count(usage.get("prompt_tokens"), label="prompt_tokens")
        output_tokens = _require_token_count(
            usage.get("completion_tokens"),
            label="completion_tokens",
        )
        response_id = envelope.get("id")
        if response_id is not None and not isinstance(response_id, str):
            raise StructureProposalError("provider response id must be a string or null")
        return ExperimentCompletion(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response_id=response_id,
        )


def build_source_learning_messages(family: TransferFamily) -> tuple[dict[str, str], ...]:
    payload = {
        "modulus": family.modulus,
        "examples": [
            {
                "input": list(example.input_values),
                "output": list(example.output_values),
            }
            for example in family.source_examples
        ],
    }
    return (
        {
            "role": "system",
            "content": (
                "Infer a reusable vector transformation hypothesis from the observed examples. "
                "Return only one JSON object with exactly permutation, offsets, and modulus. "
                "permutation and offsets must each be integer arrays of length 4."
            ),
        },
        {
            "role": "user",
            "content": _json_bytes(payload).decode("utf-8"),
        },
    )


def _source_observations(family: TransferFamily) -> tuple[ObservationInput, ...]:
    observations: list[ObservationInput] = []
    for index, example in enumerate(family.source_examples):
        observations.append(
            ObservationInput(
                slot=f"source-example-{index}",
                time=f"2000-01-01T00:00:{index:02d}+00:00",
                source="synthetic-transfer-source",
                payload=_json_bytes(
                    {
                        "input": list(example.input_values),
                        "output": list(example.output_values),
                    }
                ).decode("utf-8"),
            )
        )
    return tuple(observations)


def _parse_structure_hypothesis(text: str, *, expected_modulus: int) -> StructureHypothesis:
    value = _require_mapping(
        _load_strict_json(text, label="Structure proposal"),
        label="Structure proposal",
    )
    if set(value) != {"permutation", "offsets", "modulus"}:
        raise StructureProposalError(
            "Structure proposal must contain exactly permutation/offsets/modulus"
        )
    permutation = value["permutation"]
    offsets = value["offsets"]
    modulus = value["modulus"]
    if not isinstance(permutation, list) or not isinstance(offsets, list):
        raise StructureProposalError("permutation and offsets must be arrays")
    hypothesis = StructureHypothesis(tuple(permutation), tuple(offsets), modulus)
    if hypothesis.modulus != expected_modulus:
        raise StructureProposalError("Structure proposal modulus disagrees with task protocol")
    return hypothesis


def _hypothesis_expr(hypothesis: StructureHypothesis) -> Apply:
    return apply(
        _SOURCE_STRUCTURE_SYMBOL,
        apply("permutation", *(literal(value) for value in hypothesis.permutation)),
        apply("offsets", *(literal(value) for value in hypothesis.offsets)),
        apply("modulus", literal(hypothesis.modulus)),
    )


def _literal_int(expr: object, *, label: str) -> int:
    if not isinstance(expr, Literal):
        raise StructureProposalError(f"{label} must contain integer literals")
    value = expr.value
    if isinstance(value, bool) or not isinstance(value, int):
        raise StructureProposalError(f"{label} must contain integer literals")
    return value


def _hypothesis_from_expr(expr: object) -> StructureHypothesis:
    if not isinstance(expr, Apply) or expr.symbol != _SOURCE_STRUCTURE_SYMBOL or len(expr.args) != 3:
        raise StructureProposalError("canonical source Structure has unexpected shape")
    permutation_expr, offsets_expr, modulus_expr = expr.args
    if (
        not isinstance(permutation_expr, Apply)
        or permutation_expr.symbol != "permutation"
        or not isinstance(offsets_expr, Apply)
        or offsets_expr.symbol != "offsets"
        or not isinstance(modulus_expr, Apply)
        or modulus_expr.symbol != "modulus"
        or len(modulus_expr.args) != 1
    ):
        raise StructureProposalError("canonical source Structure has unexpected fields")
    return StructureHypothesis(
        tuple(
            _literal_int(item, label="permutation")
            for item in permutation_expr.args
        ),
        tuple(_literal_int(item, label="offsets") for item in offsets_expr.args),
        _literal_int(modulus_expr.args[0], label="modulus"),
    )


def run_source_learning(
    client: ExperimentClient,
    family: TransferFamily,
) -> SourceLearningResult:
    store = SemanticTransactionStore()
    observations = _source_observations(family)
    observation_result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=observations,
        )
    )
    source_evidence_ids = observation_result.observation_records

    completion = client.complete(build_source_learning_messages(family))
    hypothesis = _parse_structure_hypothesis(
        completion.content,
        expected_modulus=family.modulus,
    )
    expr = _hypothesis_expr(hypothesis)
    proposal_result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            proposals=(
                Proposal(
                    expr=expr,
                    existing_provenance_support=source_evidence_ids,
                ),
            ),
        )
    )
    decision = proposal_result.decisions[0]
    if decision.status != "accepted" or decision.semantic_id is None:
        raise StructureProposalError(f"Structure proposal was not accepted: {decision.reason}")
    structure_id = semantic_id(expr)
    if structure_id != decision.semantic_id:
        raise StructureProposalError("accepted Structure identity mismatch")
    return SourceLearningResult(
        store=store,
        structure_id=structure_id,
        source_evidence_ids=source_evidence_ids,
        hypothesis=hypothesis,
        completion=completion,
        resource_cost=ResourceVector(
            calls=1,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
        ),
    )


def _clone_store(store: SemanticTransactionStore) -> SemanticTransactionStore:
    return SemanticTransactionStore.from_snapshot(store.canonical_snapshot())


def _validate_source_learning_lineage(
    family: TransferFamily,
    learned: SourceLearningResult,
) -> None:
    if learned.structure_id not in learned.store.active_generation().active_roots:
        raise StructureProposalError("learned source Structure is not active")

    evidence_ids = learned.source_evidence_ids
    expected_observations = _source_observations(family)
    if (
        not evidence_ids
        or len(evidence_ids) != len(expected_observations)
        or len(set(evidence_ids)) != len(evidence_ids)
    ):
        raise StructureProposalError("source Evidence lineage does not match the source task")

    for record_id, expected in zip(evidence_ids, expected_observations, strict=True):
        record = learned.store.provenance.get(record_id)
        if (
            record is None
            or record.origin != "observed"
            or record.source != expected.source
            or record.time != expected.time
            or record.payload_ref is None
            or learned.store.payloads.get(record.payload_ref) != expected.payload
        ):
            raise StructureProposalError("source Evidence lineage does not match the source task")

    try:
        canonical_hypothesis = _hypothesis_from_expr(
            learned.store.expr_for_id(learned.structure_id)
        )
    except (KeyError, StructureProposalError) as exc:
        raise StructureProposalError("learned Structure is not a valid canonical hypothesis") from exc
    if canonical_hypothesis != learned.hypothesis or canonical_hypothesis.modulus != family.modulus:
        raise StructureProposalError("learned Structure hypothesis does not match canonical cognition")

    producers = [
        record
        for record in learned.store.provenance.values()
        if record.origin == "endogenous"
        and any(
            link.relation == "produces"
            and link.target == f"sem:{learned.structure_id}"
            for link in record.links
        )
    ]
    if len(producers) != 1:
        raise StructureProposalError("learned Structure source Evidence lineage is ambiguous")
    support_targets = {
        link.target for link in producers[0].links if link.relation == "supports"
    }
    if support_targets != set(evidence_ids):
        raise StructureProposalError("learned Structure source Evidence lineage is incomplete")


def _make_r1_arm(
    *,
    base: SemanticTransactionStore,
    allow_cross_task: bool,
    source_structure_id: str,
    target_local_id: str,
) -> R1Arm:
    store = _clone_store(base)
    policy = ProjectionPolicy(
        local_roots=(target_local_id,),
        cross_task_roots=(source_structure_id,),
        allow_cross_task=allow_cross_task,
    )
    projection = project_scope(store, policy)
    return R1Arm(
        store=store,
        projection_policy=policy,
        projection=projection,
        source_structure_id=source_structure_id,
        target_local_id=target_local_id,
    )


def prepare_r1_arms(family: TransferFamily, learned: SourceLearningResult) -> R1ArmSet:
    _validate_source_learning_lineage(family, learned)
    base = _clone_store(learned.store)
    target_local = apply("r1_target_task", literal(family.public_target_digest))
    result = base.transact(
        TransactionRequest(
            base_generation=base.current_generation,
            proposals=(Proposal(target_local),),
        )
    )
    decision = result.decisions[0]
    if decision.status != "accepted" or decision.semantic_id is None:
        raise StructureProposalError("failed to establish target-local R1 root")
    target_local_id = semantic_id(target_local)
    return R1ArmSet(
        t0=_make_r1_arm(
            base=base,
            allow_cross_task=False,
            source_structure_id=learned.structure_id,
            target_local_id=target_local_id,
        ),
        t1=_make_r1_arm(
            base=base,
            allow_cross_task=True,
            source_structure_id=learned.structure_id,
            target_local_id=target_local_id,
        ),
        t2=_make_r1_arm(
            base=base,
            allow_cross_task=True,
            source_structure_id=learned.structure_id,
            target_local_id=target_local_id,
        ),
    )


def render_target_prompt(
    arm: R1Arm,
    family: TransferFamily,
    *,
    step_index: int,
    examples_visible: int,
) -> TargetPrompt:
    if isinstance(step_index, bool) or not isinstance(step_index, int):
        raise StructureProposalError("step_index must be an integer")
    if step_index < 0 or step_index >= len(family.target_steps):
        raise StructureProposalError("step_index is outside the target trajectory")
    step = family.target_steps[step_index]
    if isinstance(examples_visible, bool) or not isinstance(examples_visible, int):
        raise StructureProposalError("examples_visible must be an integer")
    if examples_visible < 0 or examples_visible > len(step.examples):
        raise StructureProposalError("examples_visible is outside the declared evidence range")

    task_packet: dict[str, object] = {
        "instruction": "Infer the transformation and return only a JSON integer array.",
        "examples": [
            {
                "input": list(example.input_values),
                "output": list(example.output_values),
            }
            for example in step.examples[:examples_visible]
        ],
        "query": list(step.query),
    }
    task_digest = _digest(["r1-target-task", task_packet])

    reusable_structure: dict[str, object] | None = None
    if arm.source_structure_id in arm.projection.projected_roots:
        expr = arm.store.expr_for_id(arm.source_structure_id)
        reusable_structure = _hypothesis_from_expr(expr).to_mapping()

    user_payload = {
        "reusable_structure": reusable_structure,
        "task": task_packet,
    }
    messages = (
        {
            "role": "system",
            "content": (
                "Solve the vector transformation task. A reusable_structure, when present, "
                "is a fallible prior learned from earlier observations, not guaranteed truth. "
                "Prefer supplied task examples when they conflict. Return only a JSON integer array."
            ),
        },
        {
            "role": "user",
            "content": _json_bytes(user_payload).decode("utf-8"),
        },
    )
    return TargetPrompt(
        messages=messages,
        task_packet=task_packet,
        task_digest=task_digest,
        reusable_structure=reusable_structure,
    )


def run_target_probe(
    client: ExperimentClient,
    arm: R1Arm,
    family: TransferFamily,
    *,
    step_index: int,
    examples_visible: int,
) -> TargetProbeResult:
    before = arm.store.canonical_snapshot()
    provenance_before = tuple(sorted(arm.store.provenance))
    prompt = render_target_prompt(
        arm,
        family,
        step_index=step_index,
        examples_visible=examples_visible,
    )
    completion = client.complete(prompt.messages)
    verification = family.verify_response(step_index, completion.content)
    if arm.store.canonical_snapshot() != before:
        raise StructureProposalError("target probe mutated canonical cognition")
    if tuple(sorted(arm.store.provenance)) != provenance_before:
        raise StructureProposalError("target probe mutated provenance")
    return TargetProbeResult(
        completion=completion,
        verification=verification,
        prompt=prompt,
        resource_cost=ResourceVector(
            calls=1,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
        ),
    )
