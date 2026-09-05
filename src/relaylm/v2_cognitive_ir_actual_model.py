from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from relaylm.v2_cognitive_ir_experiment import (
    REPRESENTATION_KINDS,
    neutralize_typed_payload,
    prepare_r0_representation_arms,
    semantic_digest,
)
from relaylm.v2_transfer_actual_model import ExperimentClient, ExperimentCompletion
from relaylm.v2_transfer_experiment import TransferFamily, VerificationResult


S2_FORMATION_CALLS_PER_FAMILY = 3
S2_TARGET_CALLS_PER_FAMILY = len(REPRESENTATION_KINDS)
S2_TOTAL_CALLS_PER_FAMILY = S2_FORMATION_CALLS_PER_FAMILY + S2_TARGET_CALLS_PER_FAMILY

_FORMATION_KINDS = (
    "P2_ORDINARY_SUMMARY",
    "P3_SEMANTIC_CACHE",
    "P4_MEMORY_PLUS_STRUCTURE",
)
_VECTOR_WIDTH = 4


class S2ExperimentError(ValueError):
    """The #2211 bounded S2 actual-model protocol was violated."""


def _json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_json_text(value).encode("utf-8")).hexdigest()


def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise S2ExperimentError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise S2ExperimentError(f"non-standard JSON numeric constant: {value}")


def _load_strict_json(text: str, *, label: str) -> object:
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_members,
            parse_constant=_reject_json_constant,
        )
    except S2ExperimentError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise S2ExperimentError(f"{label} is not valid JSON") from exc


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise S2ExperimentError(f"{label} must be an object")
    return value


def _source_packet(family: TransferFamily) -> dict[str, object]:
    return {
        "modulus": family.modulus,
        "examples": [
            {
                "input": list(example.input_values),
                "output": list(example.output_values),
            }
            for example in family.source_examples
        ],
    }


def build_s2_formation_messages(
    kind: str,
    family: TransferFamily,
) -> tuple[dict[str, str], ...]:
    if kind not in _FORMATION_KINDS:
        raise S2ExperimentError(f"unsupported S2 formation kind: {kind}")

    if kind == "P2_ORDINARY_SUMMARY":
        instruction = (
            "Produce a faithful concise recap of the observed episodes for possible later use. "
            "Preserve important conditions, recurring patterns, exceptions, and outcomes when "
            "they are supported by the observations. Do not assume evaluator-hidden rules. "
            "Return only one JSON object with exactly one non-empty string field named summary."
        )
    elif kind == "P3_SEMANTIC_CACHE":
        instruction = (
            "Produce a compact future-reusable semantic gist of the observed episodes. Infer "
            "regularities only when supported by the observations and preserve uncertainty where "
            "needed. Do not use special Memory, Structure, or Crystal role labels. Return only one "
            "JSON object with exactly one non-empty string field named gist."
        )
    else:
        instruction = (
            "Infer a reusable vector transformation hypothesis from the observed episodes. "
            "Return only one JSON object with exactly permutation, offsets, and modulus. "
            "permutation and offsets must each be integer arrays of length 4."
        )

    return (
        {"role": "system", "content": instruction},
        {"role": "user", "content": _json_text(_source_packet(family))},
    )


def _parse_text_representation(
    completion: ExperimentCompletion,
    *,
    key: str,
) -> str:
    payload = _require_mapping(
        _load_strict_json(completion.content, label=f"{key} formation"),
        label=f"{key} formation",
    )
    if set(payload) != {key}:
        raise S2ExperimentError(f"{key} formation must contain exactly {key}")
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise S2ExperimentError(f"{key} must be a non-empty string")
    return _json_text({key: value.strip()})


def _parse_learned_rule(
    completion: ExperimentCompletion,
    *,
    expected_modulus: int,
) -> dict[str, object]:
    payload = _require_mapping(
        _load_strict_json(completion.content, label="reusable rule formation"),
        label="reusable rule formation",
    )
    if set(payload) != {"permutation", "offsets", "modulus"}:
        raise S2ExperimentError(
            "reusable rule formation must contain exactly permutation/offsets/modulus"
        )

    permutation = payload["permutation"]
    offsets = payload["offsets"]
    modulus = payload["modulus"]
    if not isinstance(permutation, list) or len(permutation) != _VECTOR_WIDTH:
        raise S2ExperimentError("permutation must be an integer array of length 4")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in permutation):
        raise S2ExperimentError("permutation must contain only integers")
    if tuple(sorted(permutation)) != tuple(range(_VECTOR_WIDTH)):
        raise S2ExperimentError("permutation must be a bijection")
    if not isinstance(offsets, list) or len(offsets) != _VECTOR_WIDTH:
        raise S2ExperimentError("offsets must be an integer array of length 4")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in offsets):
        raise S2ExperimentError("offsets must contain only integers")
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise S2ExperimentError("modulus must be an integer greater than one")
    if modulus != expected_modulus:
        raise S2ExperimentError("learned modulus disagrees with the public task protocol")
    if any(value < 0 or value >= modulus for value in offsets):
        raise S2ExperimentError("offsets must be inside the modulus")

    return {
        "permutation": list(permutation),
        "offsets": list(offsets),
        "modulus": modulus,
    }


@dataclass(frozen=True, slots=True)
class S2Representation:
    kind: str
    serialized: str
    provenance_handles: tuple[str, ...]
    reconstruction_handles: tuple[str, ...]
    formation_completion: ExperimentCompletion | None
    formation_calls: int
    formation_input_tokens: int
    formation_output_tokens: int
    empirical_source: str = "model_or_direct"
    r0_oracle_upper_bound: bool = False

    @property
    def serialized_bytes(self) -> int:
        return len(self.serialized.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class S2TargetPrompt:
    messages: tuple[dict[str, str], ...]
    task_packet: dict[str, object]
    task_digest: str


@dataclass(frozen=True, slots=True)
class S2ArmProbe:
    kind: str
    representation: S2Representation
    completion: ExperimentCompletion
    verification: VerificationResult
    target_task_digest: str
    target_calls: int = 1

    @property
    def formation_calls(self) -> int:
        return self.representation.formation_calls

    @property
    def formation_input_tokens(self) -> int:
        return self.representation.formation_input_tokens

    @property
    def formation_output_tokens(self) -> int:
        return self.representation.formation_output_tokens

    @property
    def target_input_tokens(self) -> int:
        return self.completion.input_tokens

    @property
    def target_output_tokens(self) -> int:
        return self.completion.output_tokens

    @property
    def projected_bytes(self) -> int:
        return self.representation.serialized_bytes

    @property
    def total_calls(self) -> int:
        return self.formation_calls + self.target_calls

    @property
    def total_input_tokens(self) -> int:
        return self.formation_input_tokens + self.target_input_tokens

    @property
    def total_output_tokens(self) -> int:
        return self.formation_output_tokens + self.target_output_tokens


@dataclass(frozen=True, slots=True)
class S2SmokeResult:
    arms: dict[str, S2ArmProbe]
    provider_calls: int
    physical_provider_calls: int
    non_citable: bool = True


def _derived_representation(
    *,
    kind: str,
    payload: object,
    provenance_handles: tuple[str, ...],
    completion: ExperimentCompletion | None,
    formation_calls: int,
    reconstruction_handles: tuple[str, ...] | None = None,
) -> S2Representation:
    input_tokens = 0 if completion is None else completion.input_tokens
    output_tokens = 0 if completion is None else completion.output_tokens
    return S2Representation(
        kind=kind,
        serialized=_json_text(payload),
        provenance_handles=provenance_handles,
        reconstruction_handles=(
            provenance_handles if reconstruction_handles is None else reconstruction_handles
        ),
        formation_completion=completion,
        formation_calls=formation_calls,
        formation_input_tokens=input_tokens,
        formation_output_tokens=output_tokens,
    )


def form_s2_representations(
    client: ExperimentClient,
    family: TransferFamily,
) -> dict[str, S2Representation]:
    """Form one matched representation set without evaluator-supplied rule semantics.

    P2, P3, and P4 each spend one provider call on the exact same public source packet.
    P5 and P6 are deterministic derivatives of the single P4 learned-rule completion so
    the typed-vs-generic comparison does not confound semantic extraction with syntax.
    """

    r0 = prepare_r0_representation_arms(family)
    provenance_handles = r0["P0_RAW_HISTORY"].provenance_handles

    summary_completion = client.complete(
        build_s2_formation_messages("P2_ORDINARY_SUMMARY", family)
    )
    cache_completion = client.complete(
        build_s2_formation_messages("P3_SEMANTIC_CACHE", family)
    )
    typed_completion = client.complete(
        build_s2_formation_messages("P4_MEMORY_PLUS_STRUCTURE", family)
    )

    summary_serialized = _parse_text_representation(summary_completion, key="summary")
    cache_serialized = _parse_text_representation(cache_completion, key="gist")
    learned = _parse_learned_rule(typed_completion, expected_modulus=family.modulus)

    typed_payload = {
        "memory": {"origin_refs": list(provenance_handles)},
        "structure": {
            "operation": "affine_permutation",
            "permutation": learned["permutation"],
            "offsets": learned["offsets"],
            "modulus": learned["modulus"],
        },
    }
    generic_payload = neutralize_typed_payload(typed_payload)
    if semantic_digest("P4_MEMORY_PLUS_STRUCTURE", typed_payload) != semantic_digest(
        "P6_GENERIC_EQUAL_INFORMATION",
        generic_payload,
    ):
        raise S2ExperimentError("P4/P6 deterministic neutralization changed semantic payload")

    structure_only_payload = {
        "reusable_relation": {
            "kind": "affine_permutation",
            "a": learned["permutation"],
            "b": learned["offsets"],
            "n": learned["modulus"],
        }
    }

    representations: dict[str, S2Representation] = {}
    representations["P0_RAW_HISTORY"] = _derived_representation(
        kind="P0_RAW_HISTORY",
        payload=_load_strict_json(r0["P0_RAW_HISTORY"].serialized, label="P0 R0 payload"),
        provenance_handles=provenance_handles,
        completion=None,
        formation_calls=0,
    )
    representations["P1_RETRIEVAL_ONLY"] = _derived_representation(
        kind="P1_RETRIEVAL_ONLY",
        payload=_load_strict_json(
            r0["P1_RETRIEVAL_ONLY"].serialized,
            label="P1 R0 payload",
        ),
        provenance_handles=provenance_handles,
        completion=None,
        formation_calls=0,
    )
    representations["P2_ORDINARY_SUMMARY"] = S2Representation(
        kind="P2_ORDINARY_SUMMARY",
        serialized=summary_serialized,
        provenance_handles=provenance_handles,
        reconstruction_handles=provenance_handles,
        formation_completion=summary_completion,
        formation_calls=1,
        formation_input_tokens=summary_completion.input_tokens,
        formation_output_tokens=summary_completion.output_tokens,
    )
    representations["P3_SEMANTIC_CACHE"] = S2Representation(
        kind="P3_SEMANTIC_CACHE",
        serialized=cache_serialized,
        provenance_handles=provenance_handles,
        reconstruction_handles=provenance_handles,
        formation_completion=cache_completion,
        formation_calls=1,
        formation_input_tokens=cache_completion.input_tokens,
        formation_output_tokens=cache_completion.output_tokens,
    )
    representations["P4_MEMORY_PLUS_STRUCTURE"] = _derived_representation(
        kind="P4_MEMORY_PLUS_STRUCTURE",
        payload=typed_payload,
        provenance_handles=provenance_handles,
        completion=typed_completion,
        formation_calls=1,
    )
    representations["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"] = _derived_representation(
        kind="P5_STRUCTURE_ONLY_RECONSTRUCTABLE",
        payload=structure_only_payload,
        provenance_handles=provenance_handles,
        reconstruction_handles=provenance_handles,
        completion=typed_completion,
        formation_calls=1,
    )
    representations["P6_GENERIC_EQUAL_INFORMATION"] = _derived_representation(
        kind="P6_GENERIC_EQUAL_INFORMATION",
        payload=generic_payload,
        provenance_handles=provenance_handles,
        completion=typed_completion,
        formation_calls=1,
    )

    if tuple(representations) != REPRESENTATION_KINDS:
        raise S2ExperimentError("S2 representation set is incomplete or reordered")
    if len({rep.provenance_handles for rep in representations.values()}) != 1:
        raise S2ExperimentError("S2 representations do not share provenance identity")
    if any(rep.r0_oracle_upper_bound for rep in representations.values()):
        raise S2ExperimentError("R0 oracle semantics leaked into S2 representations")
    return representations


def build_s2_target_messages(
    representation: S2Representation,
    family: TransferFamily,
    *,
    step_index: int,
    examples_visible: int,
) -> S2TargetPrompt:
    if isinstance(step_index, bool) or not isinstance(step_index, int):
        raise S2ExperimentError("step_index must be an integer")
    if step_index < 0 or step_index >= len(family.target_steps):
        raise S2ExperimentError("step_index is outside the target trajectory")
    step = family.target_steps[step_index]
    if isinstance(examples_visible, bool) or not isinstance(examples_visible, int):
        raise S2ExperimentError("examples_visible must be an integer")
    if examples_visible < 0 or examples_visible > len(step.examples):
        raise S2ExperimentError("examples_visible is outside the declared evidence range")

    prior_context = _load_strict_json(
        representation.serialized,
        label=f"{representation.kind} representation",
    )
    task_packet = {
        "instruction": "Infer the vector transformation and return only a JSON integer array.",
        "examples": [
            {
                "input": list(example.input_values),
                "output": list(example.output_values),
            }
            for example in step.examples[:examples_visible]
        ],
        "query": list(step.query),
    }
    task_digest = _digest(["s2-target-task", task_packet])
    user_packet = {
        "prior_context": prior_context,
        "task": task_packet,
    }
    messages = (
        {
            "role": "system",
            "content": (
                "Solve the formal vector task. prior_context is fallible material derived from "
                "earlier observations; use it when useful, but current target examples override "
                "it on conflict. Return only one JSON integer array of length 4."
            ),
        },
        {"role": "user", "content": _json_text(user_packet)},
    )
    return S2TargetPrompt(messages=messages, task_packet=task_packet, task_digest=task_digest)


def run_s2_smoke(
    client: ExperimentClient,
    family: TransferFamily,
    *,
    step_index: int = 0,
    examples_visible: int = 0,
) -> S2SmokeResult:
    """Run one bounded NON_CITABLE representation-protocol smoke.

    The smoke establishes provider/parser/task/representation viability only. It must not
    be promoted into a citable Crystallization, Memory, Structure, or architecture claim.
    """

    representations = form_s2_representations(client, family)
    arms: dict[str, S2ArmProbe] = {}
    task_digests: set[str] = set()

    for kind in REPRESENTATION_KINDS:
        representation = representations[kind]
        prompt = build_s2_target_messages(
            representation,
            family,
            step_index=step_index,
            examples_visible=examples_visible,
        )
        completion = client.complete(prompt.messages)
        verification = family.verify_response(step_index, completion.content)
        arms[kind] = S2ArmProbe(
            kind=kind,
            representation=representation,
            completion=completion,
            verification=verification,
            target_task_digest=prompt.task_digest,
        )
        task_digests.add(prompt.task_digest)

    if tuple(arms) != REPRESENTATION_KINDS:
        raise S2ExperimentError("S2 target arm set is incomplete or reordered")
    if len(task_digests) != 1:
        raise S2ExperimentError("S2 target task differs across representation arms")

    return S2SmokeResult(
        arms=arms,
        provider_calls=S2_TOTAL_CALLS_PER_FAMILY,
        physical_provider_calls=S2_TOTAL_CALLS_PER_FAMILY,
        non_citable=True,
    )
