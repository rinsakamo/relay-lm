from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from relaylm.v2_transfer_experiment import TransferFamily


REPRESENTATION_KINDS = (
    "P0_RAW_HISTORY",
    "P1_RETRIEVAL_ONLY",
    "P2_ORDINARY_SUMMARY",
    "P3_SEMANTIC_CACHE",
    "P4_MEMORY_PLUS_STRUCTURE",
    "P5_STRUCTURE_ONLY_RECONSTRUCTABLE",
    "P6_GENERIC_EQUAL_INFORMATION",
)

_FORBIDDEN_GENERIC_LABELS = ("memory", "structure", "crystal")
_VECTOR_WIDTH = 4


class CognitiveIRExperimentError(ValueError):
    """A #2211 representation fixture violates the declared causal contract."""


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


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CognitiveIRExperimentError(f"{label} must be an object")
    return value


def _require_int_list(value: object, *, label: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise CognitiveIRExperimentError(f"{label} must be an integer array")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise CognitiveIRExperimentError(f"{label} must be an integer array")
    return tuple(value)


def _validate_rule_semantics(payload: Mapping[str, object]) -> dict[str, object]:
    if set(payload) != {
        "operation",
        "permutation",
        "offsets",
        "modulus",
        "provenance_handles",
    }:
        raise CognitiveIRExperimentError("semantic payload has unexpected fields")
    if payload["operation"] != "affine_permutation":
        raise CognitiveIRExperimentError("semantic payload has unsupported operation")
    permutation = _require_int_list(payload["permutation"], label="permutation")
    offsets = _require_int_list(payload["offsets"], label="offsets")
    modulus = payload["modulus"]
    provenance = payload["provenance_handles"]
    if len(permutation) != _VECTOR_WIDTH or tuple(sorted(permutation)) != tuple(
        range(_VECTOR_WIDTH)
    ):
        raise CognitiveIRExperimentError("semantic payload has invalid permutation")
    if len(offsets) != _VECTOR_WIDTH:
        raise CognitiveIRExperimentError("semantic payload has invalid offsets")
    if isinstance(modulus, bool) or not isinstance(modulus, int) or modulus <= 1:
        raise CognitiveIRExperimentError("semantic payload has invalid modulus")
    if any(value < 0 or value >= modulus for value in offsets):
        raise CognitiveIRExperimentError("semantic payload offsets are outside modulus")
    if (
        not isinstance(provenance, list)
        or not provenance
        or any(not isinstance(item, str) or not item for item in provenance)
    ):
        raise CognitiveIRExperimentError("semantic payload has invalid provenance handles")
    return {
        "operation": "affine_permutation",
        "permutation": list(permutation),
        "offsets": list(offsets),
        "modulus": modulus,
        "provenance_handles": list(provenance),
    }


@dataclass(slots=True)
class RepresentationArm:
    kind: str
    serialized: str
    source_history_digest: str
    target_task_digest: str
    provenance_handles: tuple[str, ...]
    reconstruction_handles: tuple[str, ...]
    r0_oracle_upper_bound: bool
    empirical_claim_allowed: bool
    serialized_bytes: int

    def require_empirical_claim_eligibility(self) -> None:
        if not self.empirical_claim_allowed:
            raise CognitiveIRExperimentError(
                "R0 oracle fixture is mechanics-only and cannot support an empirical claim"
            )


@dataclass(frozen=True, slots=True)
class R0AdmissionReport:
    clean: bool
    typed_generic_semantic_equal: bool
    shared_source_identity: bool
    shared_target_identity: bool
    shared_provenance_identity: bool


def _source_records(family: TransferFamily) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    for index, example in enumerate(family.source_examples):
        content = {
            "index": index,
            "input": list(example.input_values),
            "output": list(example.output_values),
        }
        handle = f"src-{_digest(['source-episode', content])[:24]}"
        records.append(
            {
                "ref": handle,
                "input": content["input"],
                "output": content["output"],
            }
        )
    return tuple(records)


def _oracle_semantics(
    family: TransferFamily,
    provenance_handles: tuple[str, ...],
) -> dict[str, object]:
    return {
        "operation": "affine_permutation",
        "permutation": list(family.source_rule.permutation),
        "offsets": list(family.source_rule.offsets),
        "modulus": family.source_rule.modulus,
        "provenance_handles": list(provenance_handles),
    }


def _typed_payload(semantics: Mapping[str, object]) -> dict[str, object]:
    normalized = _validate_rule_semantics(semantics)
    return {
        "memory": {
            "origin_refs": normalized["provenance_handles"],
        },
        "structure": {
            "operation": normalized["operation"],
            "permutation": normalized["permutation"],
            "offsets": normalized["offsets"],
            "modulus": normalized["modulus"],
        },
    }


def neutralize_typed_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Deterministically remove privileged role labels without dropping meaning."""

    if set(payload) != {"memory", "structure"}:
        raise CognitiveIRExperimentError("typed payload must contain exactly memory/structure")
    memory = _require_mapping(payload["memory"], label="memory")
    structure = _require_mapping(payload["structure"], label="structure")
    if set(memory) != {"origin_refs"}:
        raise CognitiveIRExperimentError("typed memory payload has unexpected fields")
    if set(structure) != {"operation", "permutation", "offsets", "modulus"}:
        raise CognitiveIRExperimentError("typed structure payload has unexpected fields")

    semantics = _validate_rule_semantics(
        {
            "operation": structure["operation"],
            "permutation": structure["permutation"],
            "offsets": structure["offsets"],
            "modulus": structure["modulus"],
            "provenance_handles": memory["origin_refs"],
        }
    )
    return {
        "context": {"refs": semantics["provenance_handles"]},
        "relation": {
            "kind": semantics["operation"],
            "a": semantics["permutation"],
            "b": semantics["offsets"],
            "n": semantics["modulus"],
        },
    }


def decode_semantic_payload(kind: str, payload: Mapping[str, object]) -> dict[str, object]:
    if kind == "P4_MEMORY_PLUS_STRUCTURE":
        if set(payload) != {"memory", "structure"}:
            raise CognitiveIRExperimentError("typed payload has unexpected fields")
        memory = _require_mapping(payload["memory"], label="memory")
        structure = _require_mapping(payload["structure"], label="structure")
        if set(memory) != {"origin_refs"}:
            raise CognitiveIRExperimentError("typed memory payload has unexpected fields")
        if set(structure) != {"operation", "permutation", "offsets", "modulus"}:
            raise CognitiveIRExperimentError("typed structure payload has unexpected fields")
        return _validate_rule_semantics(
            {
                "operation": structure["operation"],
                "permutation": structure["permutation"],
                "offsets": structure["offsets"],
                "modulus": structure["modulus"],
                "provenance_handles": memory["origin_refs"],
            }
        )

    if kind == "P6_GENERIC_EQUAL_INFORMATION":
        if set(payload) != {"context", "relation"}:
            raise CognitiveIRExperimentError("generic payload has unexpected fields")
        context = _require_mapping(payload["context"], label="context")
        relation = _require_mapping(payload["relation"], label="relation")
        if set(context) != {"refs"}:
            raise CognitiveIRExperimentError("generic context payload has unexpected fields")
        if set(relation) != {"kind", "a", "b", "n"}:
            raise CognitiveIRExperimentError("generic relation payload has unexpected fields")
        return _validate_rule_semantics(
            {
                "operation": relation["kind"],
                "permutation": relation["a"],
                "offsets": relation["b"],
                "modulus": relation["n"],
                "provenance_handles": context["refs"],
            }
        )

    raise CognitiveIRExperimentError(f"semantic decoding is not defined for {kind}")


def semantic_digest(kind: str, payload: Mapping[str, object]) -> str:
    return _digest(["cognitive-ir-semantic-payload", decode_semantic_payload(kind, payload)])


def render_surface_variant(
    kind: str,
    payload: Mapping[str, object],
    *,
    variant: str,
) -> dict[str, object]:
    if variant == "neutral_keys":
        if kind != "P4_MEMORY_PLUS_STRUCTURE":
            raise CognitiveIRExperimentError("neutral_keys requires the typed representation")
        return neutralize_typed_payload(payload)
    if variant == "reordered":
        # JSON object order is declared semantically irrelevant for this R0 fixture.
        return {
            key: (
                dict(reversed(list(value.items())))
                if isinstance(value, Mapping)
                else value
            )
            for key, value in reversed(list(payload.items()))
        }
    raise CognitiveIRExperimentError(f"unsupported surface variant: {variant}")


def _make_arm(
    *,
    kind: str,
    payload: object,
    source_history_digest: str,
    target_task_digest: str,
    provenance_handles: tuple[str, ...],
    reconstruction_handles: tuple[str, ...] | None = None,
) -> RepresentationArm:
    serialized = _json_text(payload)
    return RepresentationArm(
        kind=kind,
        serialized=serialized,
        source_history_digest=source_history_digest,
        target_task_digest=target_task_digest,
        provenance_handles=provenance_handles,
        reconstruction_handles=(
            provenance_handles if reconstruction_handles is None else reconstruction_handles
        ),
        r0_oracle_upper_bound=True,
        empirical_claim_allowed=False,
        serialized_bytes=len(serialized.encode("utf-8")),
    )


def prepare_r0_representation_arms(
    family: TransferFamily,
) -> dict[str, RepresentationArm]:
    """Build mechanics-only R0 arms from one exact source/target family.

    The semantic cache and reusable-rule arms use evaluator-known source semantics only
    as an explicit oracle upper bound for representation-integrity tests. They are not
    evidence that a model can learn or benefit from those semantics.
    """

    records = _source_records(family)
    provenance_handles = tuple(record["ref"] for record in records)
    source_history_digest = _digest(["source-history", records])
    target_task_digest = family.public_target_digest
    semantics = _oracle_semantics(family, provenance_handles)
    typed = _typed_payload(semantics)
    generic = neutralize_typed_payload(typed)

    summary = {
        "recap": [
            {
                "input": record["input"],
                "output": record["output"],
            }
            for record in records
        ]
    }
    cache = {
        "r0_fixture": "oracle_upper_bound",
        "gist": {
            "kind": semantics["operation"],
            "a": semantics["permutation"],
            "b": semantics["offsets"],
            "n": semantics["modulus"],
        },
        "refs": list(provenance_handles),
    }
    structure_only = {
        "reusable_relation": {
            "kind": semantics["operation"],
            "a": semantics["permutation"],
            "b": semantics["offsets"],
            "n": semantics["modulus"],
        }
    }

    arms: dict[str, RepresentationArm] = {}
    arms["P0_RAW_HISTORY"] = _make_arm(
        kind="P0_RAW_HISTORY",
        payload={"records": list(records)},
        source_history_digest=source_history_digest,
        target_task_digest=target_task_digest,
        provenance_handles=provenance_handles,
    )
    arms["P1_RETRIEVAL_ONLY"] = _make_arm(
        kind="P1_RETRIEVAL_ONLY",
        payload={
            "records": list(records),
            "selected_refs": list(provenance_handles),
        },
        source_history_digest=source_history_digest,
        target_task_digest=target_task_digest,
        provenance_handles=provenance_handles,
    )
    arms["P2_ORDINARY_SUMMARY"] = _make_arm(
        kind="P2_ORDINARY_SUMMARY",
        payload=summary,
        source_history_digest=source_history_digest,
        target_task_digest=target_task_digest,
        provenance_handles=provenance_handles,
    )
    arms["P3_SEMANTIC_CACHE"] = _make_arm(
        kind="P3_SEMANTIC_CACHE",
        payload=cache,
        source_history_digest=source_history_digest,
        target_task_digest=target_task_digest,
        provenance_handles=provenance_handles,
    )
    arms["P4_MEMORY_PLUS_STRUCTURE"] = _make_arm(
        kind="P4_MEMORY_PLUS_STRUCTURE",
        payload=typed,
        source_history_digest=source_history_digest,
        target_task_digest=target_task_digest,
        provenance_handles=provenance_handles,
    )
    arms["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"] = _make_arm(
        kind="P5_STRUCTURE_ONLY_RECONSTRUCTABLE",
        payload=structure_only,
        source_history_digest=source_history_digest,
        target_task_digest=target_task_digest,
        provenance_handles=provenance_handles,
        reconstruction_handles=provenance_handles,
    )
    arms["P6_GENERIC_EQUAL_INFORMATION"] = _make_arm(
        kind="P6_GENERIC_EQUAL_INFORMATION",
        payload=generic,
        source_history_digest=source_history_digest,
        target_task_digest=target_task_digest,
        provenance_handles=provenance_handles,
    )
    return arms


def assert_r0_admission(
    arms: Mapping[str, RepresentationArm],
) -> R0AdmissionReport:
    if tuple(arms) != REPRESENTATION_KINDS:
        raise CognitiveIRExperimentError("R0 representation arm set is incomplete or reordered")

    source_identity = len({arm.source_history_digest for arm in arms.values()}) == 1
    target_identity = len({arm.target_task_digest for arm in arms.values()}) == 1
    provenance_identity = len({arm.provenance_handles for arm in arms.values()}) == 1
    if not source_identity:
        raise CognitiveIRExperimentError("representation arms do not share source history")
    if not target_identity:
        raise CognitiveIRExperimentError("representation arms do not share target task")
    if not provenance_identity:
        raise CognitiveIRExperimentError("representation arms do not share provenance handles")
    if any(not arm.r0_oracle_upper_bound or arm.empirical_claim_allowed for arm in arms.values()):
        raise CognitiveIRExperimentError("R0 oracle quarantine was weakened")

    typed = arms["P4_MEMORY_PLUS_STRUCTURE"]
    generic = arms["P6_GENERIC_EQUAL_INFORMATION"]
    try:
        typed_payload = _require_mapping(json.loads(typed.serialized), label="typed payload")
        generic_payload = _require_mapping(json.loads(generic.serialized), label="generic payload")
    except (json.JSONDecodeError, TypeError) as exc:
        raise CognitiveIRExperimentError("representation serialization is invalid JSON") from exc

    typed_generic_equal = semantic_digest(typed.kind, typed_payload) == semantic_digest(
        generic.kind,
        generic_payload,
    )
    if not typed_generic_equal:
        raise CognitiveIRExperimentError("typed/generic semantic mismatch")

    neutralized = neutralize_typed_payload(typed_payload)
    if neutralized != dict(generic_payload):
        raise CognitiveIRExperimentError("generic arm is not the deterministic neutralization of typed IR")
    generic_text = generic.serialized.lower()
    if any(label in generic_text for label in _FORBIDDEN_GENERIC_LABELS):
        raise CognitiveIRExperimentError("generic arm retains privileged ontology labels")

    p5 = arms["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"]
    if p5.reconstruction_handles != p5.provenance_handles:
        raise CognitiveIRExperimentError("Structure-only arm lost its reconstruction path")
    if any(handle in p5.serialized for handle in p5.provenance_handles):
        raise CognitiveIRExperimentError("Structure-only arm projected episode handles directly")

    return R0AdmissionReport(
        clean=True,
        typed_generic_semantic_equal=True,
        shared_source_identity=True,
        shared_target_identity=True,
        shared_provenance_identity=True,
    )
