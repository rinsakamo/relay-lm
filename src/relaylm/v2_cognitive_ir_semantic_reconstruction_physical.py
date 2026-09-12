from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import re
import time
from typing import Protocol

from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    ARCHITECTURE_CONSEQUENCE,
    ARMS,
    CONTEXT_LIMIT,
    FAMILY_COUNT,
    MAX_OUTPUT_TOKENS,
    PARALLEL_SEMANTIC_SLOTS,
    PREREGISTRATION_LABEL,
    REASONING,
    REQUEST_SEED,
    SEMANTIC_COMPLETIONS,
    TEMPERATURE,
    ReconstructionCost,
    ReconstructionScore,
    ReconstructionVerdict,
    build_reconstruction_messages,
    classify_result,
    paired_table,
    prepare_mechanism_control,
    preregistered_seeds,
    score_reconstruction,
    semantic_call_plan,
    validate_repository_binding,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion


PHYSICAL_ADAPTER_ISSUE = 2723
INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL = 2
SCIENTIFIC_INPUT_TOKEN_REQUESTS = (
    SEMANTIC_COMPLETIONS * INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL
)
MATERIAL_SCHEMA = "relaylm2-cognitive-ir-semantic-reconstruction-material-v1"
CLAIM = "SEMANTIC_RECONSTRUCTION_ACCESSIBILITY_PROBE"
CITABLE_WHEN_CLEAN = True

_HEX_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SemanticReconstructionPhysicalBindingError(ValueError):
    """The #2723 physical-adapter binding cannot proceed truthfully."""


@dataclass(frozen=True, slots=True)
class FrozenConsumerIdentity:
    repository_commit: str
    repository_tree: str
    model: str
    upstream_revision: str
    build_info: str
    model_path: str
    model_ftype: str
    artifact_sha256: str
    chat_template_sha256: str
    context_limit: int
    total_slots: int
    context_shift_enabled: bool
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    temperature: float = TEMPERATURE
    reasoning: str = REASONING
    request_seed: int | None = REQUEST_SEED
    semantic_parallelism: int = PARALLEL_SEMANTIC_SLOTS

    def validate(self) -> None:
        for name in ("repository_commit", "repository_tree", "upstream_revision"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _HEX_REVISION_RE.fullmatch(value):
                raise SemanticReconstructionPhysicalBindingError(
                    f"{name} must be a lowercase 40-hex identity"
                )
        for name in ("artifact_sha256", "chat_template_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                raise SemanticReconstructionPhysicalBindingError(
                    f"{name} must be a lowercase sha256 digest"
                )
        for name in ("model", "build_info", "model_path", "model_ftype"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise SemanticReconstructionPhysicalBindingError(
                    f"{name} must be non-empty"
                )
        if self.context_limit != CONTEXT_LIMIT:
            raise SemanticReconstructionPhysicalBindingError(
                f"consumer context must be exactly {CONTEXT_LIMIT}"
            )
        if self.total_slots != PARALLEL_SEMANTIC_SLOTS:
            raise SemanticReconstructionPhysicalBindingError(
                "consumer must expose exactly one semantic slot"
            )
        if self.context_shift_enabled is not False:
            raise SemanticReconstructionPhysicalBindingError(
                "context shift must be disabled"
            )
        if self.max_output_tokens != MAX_OUTPUT_TOKENS:
            raise SemanticReconstructionPhysicalBindingError(
                "max output token contract drifted"
            )
        if self.temperature != TEMPERATURE:
            raise SemanticReconstructionPhysicalBindingError(
                "temperature contract drifted"
            )
        if self.reasoning != REASONING:
            raise SemanticReconstructionPhysicalBindingError(
                "reasoning contract drifted"
            )
        if self.request_seed is not None:
            raise SemanticReconstructionPhysicalBindingError(
                "request seed must remain omitted/null"
            )
        if self.semantic_parallelism != PARALLEL_SEMANTIC_SLOTS:
            raise SemanticReconstructionPhysicalBindingError(
                "semantic parallelism contract drifted"
            )


def freeze_consumer_identity(
    *,
    repository_commit: str,
    repository_tree: str,
    model: str,
    runtime_attestation: Mapping[str, object],
) -> FrozenConsumerIdentity:
    if not isinstance(runtime_attestation, Mapping):
        raise SemanticReconstructionPhysicalBindingError(
            "runtime attestation must be an object"
        )
    required = {
        "upstream_revision",
        "build_info",
        "model_alias",
        "model_path",
        "model_ftype",
        "artifact_sha256",
        "chat_template_sha256",
        "context_limit",
        "total_slots",
        "context_shift_enabled",
    }
    if set(runtime_attestation) != required:
        raise SemanticReconstructionPhysicalBindingError(
            "runtime attestation shape drifted"
        )
    if runtime_attestation["model_alias"] != model:
        raise SemanticReconstructionPhysicalBindingError(
            "runtime model alias differs from request model"
        )
    identity = FrozenConsumerIdentity(
        repository_commit=repository_commit,
        repository_tree=repository_tree,
        model=model,
        upstream_revision=str(runtime_attestation["upstream_revision"]),
        build_info=str(runtime_attestation["build_info"]),
        model_path=str(runtime_attestation["model_path"]),
        model_ftype=str(runtime_attestation["model_ftype"]),
        artifact_sha256=str(runtime_attestation["artifact_sha256"]),
        chat_template_sha256=str(runtime_attestation["chat_template_sha256"]),
        context_limit=int(runtime_attestation["context_limit"]),
        total_slots=int(runtime_attestation["total_slots"]),
        context_shift_enabled=bool(runtime_attestation["context_shift_enabled"]),
    )
    identity.validate()
    return identity


def _material_digest(seed: int, purpose: str) -> bytes:
    return hashlib.sha256(
        f"{PREREGISTRATION_LABEL}|material-v1|{seed}|{purpose}".encode("utf-8")
    ).digest()


def _canonical_payload_for_seed(seed: int) -> dict[str, object]:
    ranked = sorted(
        range(4),
        key=lambda coordinate: (
            _material_digest(seed, f"active-rank:{coordinate}"),
            coordinate,
        ),
    )
    active = set(ranked[:3])
    offsets = [
        1 + (_material_digest(seed, f"offset:{coordinate}")[0] % 3)
        if coordinate in active
        else 0
        for coordinate in range(4)
    ]
    provenance = [
        "h_"
        + hashlib.sha256(
            f"{MATERIAL_SCHEMA}|{seed}|provenance|0".encode("utf-8")
        ).hexdigest()[:24]
    ]
    return {
        "operation": "affine_permutation",
        "permutation": [0, 1, 2, 3],
        "offsets": offsets,
        "modulus": 10,
        "provenance_handles": provenance,
    }


def generate_synthetic_canonical_payload(seed: int) -> dict[str, object]:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise SemanticReconstructionPhysicalBindingError(
            "synthetic seed must be a non-negative integer"
        )
    if seed in set(preregistered_seeds()):
        raise SemanticReconstructionPhysicalBindingError(
            "synthetic helper must not materialize a preregistered scientific seed"
        )
    return _canonical_payload_for_seed(seed)


def generate_scientific_canonical_payload(
    *,
    index: int,
    seed: int,
    frozen_identity: FrozenConsumerIdentity,
) -> dict[str, object]:
    if not isinstance(frozen_identity, FrozenConsumerIdentity):
        raise SemanticReconstructionPhysicalBindingError(
            "scientific family generation requires FrozenConsumerIdentity"
        )
    frozen_identity.validate()
    seeds = preregistered_seeds()
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < FAMILY_COUNT
    ):
        raise SemanticReconstructionPhysicalBindingError(
            "scientific family index must be 0..15"
        )
    if isinstance(seed, bool) or not isinstance(seed, int) or seed != seeds[index]:
        raise SemanticReconstructionPhysicalBindingError(
            "scientific family seed does not match preregistered index"
        )
    return _canonical_payload_for_seed(seed)


def physical_call_plan() -> tuple[str, ...]:
    plan = tuple(
        f"semantic-reconstruction:{index}:{seed}:{arm}"
        for index, seed, arm in semantic_call_plan()
    )
    if len(plan) != SEMANTIC_COMPLETIONS or len(set(plan)) != SEMANTIC_COMPLETIONS:
        raise SemanticReconstructionPhysicalBindingError(
            "physical semantic call plan drifted"
        )
    return plan


class SemanticReconstructionClient(Protocol):
    provider_attempts: int
    input_count_attempts: int

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion: ...

    def require_complete_plan(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ReconstructionCell:
    family_index: int
    family_seed: int
    arm: str
    semantic_digest: str
    canonical_truth: Mapping[str, object]
    serialized_representation: str
    raw_completion: str
    score: ReconstructionScore
    cost: ReconstructionCost


@dataclass(frozen=True, slots=True)
class SemanticReconstructionCampaignResult:
    classification: str
    statistical_status: str
    p_value: float | None
    architecture_consequence: str
    cells: tuple[ReconstructionCell, ...]
    paired: Mapping[str, int] | None
    semantic_calls: int
    input_token_requests: int
    completed: bool
    failure: str | None


FamilyFactory = Callable[
    [int, int, FrozenConsumerIdentity],
    Mapping[str, object],
]


def _official_family_factory(
    index: int,
    seed: int,
    identity: FrozenConsumerIdentity,
) -> Mapping[str, object]:
    return generate_scientific_canonical_payload(
        index=index,
        seed=seed,
        frozen_identity=identity,
    )


def _campaign_result(
    *,
    verdict: ReconstructionVerdict,
    cells: list[ReconstructionCell],
    paired: Mapping[str, int] | None,
    client: SemanticReconstructionClient,
    completed: bool,
    failure: str | None,
) -> SemanticReconstructionCampaignResult:
    semantic_calls = getattr(client, "provider_attempts", len(cells))
    input_requests = getattr(
        client,
        "input_count_attempts",
        semantic_calls * INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL,
    )
    return SemanticReconstructionCampaignResult(
        classification=verdict.classification,
        statistical_status=verdict.statistical_status,
        p_value=verdict.p_value,
        architecture_consequence=verdict.architecture_consequence,
        cells=tuple(cells),
        paired=paired,
        semantic_calls=int(semantic_calls),
        input_token_requests=int(input_requests),
        completed=completed,
        failure=failure,
    )


def run_semantic_reconstruction_campaign(
    client: SemanticReconstructionClient,
    *,
    frozen_identity: FrozenConsumerIdentity,
    family_factory: FamilyFactory | None = None,
) -> SemanticReconstructionCampaignResult:
    validate_repository_binding()
    frozen_identity.validate()
    factory = family_factory or _official_family_factory
    cells: list[ReconstructionCell] = []
    paired_outcomes: list[tuple[bool, bool]] = []

    for index, seed in enumerate(preregistered_seeds()):
        canonical = factory(index, seed, frozen_identity)
        control = prepare_mechanism_control(canonical)
        arm_outcomes: list[bool] = []
        for arm in ARMS:
            question_id = f"semantic-reconstruction:{index}:{seed}:{arm}"
            serialized = control.serialized_by_arm[arm]
            started = time.monotonic()
            try:
                completion = client.complete_named(
                    question_id,
                    build_reconstruction_messages(serialized),
                    output_kind="text",
                )
            except Exception as exc:
                attempts = int(getattr(client, "provider_attempts", len(cells)))
                if attempts <= len(cells):
                    raise
                verdict = classify_result(
                    None,
                    protocol_failure_after_spend=True,
                )
                return _campaign_result(
                    verdict=verdict,
                    cells=cells,
                    paired=None,
                    client=client,
                    completed=False,
                    failure=f"{type(exc).__name__}: {exc}",
                )
            elapsed = time.monotonic() - started
            score = score_reconstruction(
                completion.content,
                control.canonical_truth,
            )
            cost = ReconstructionCost(
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
                model_calls=1,
                wall_clock_seconds=elapsed,
                representation_bytes=len(serialized.encode("utf-8")),
                representation_tokens=None,
            )
            cost.validate()
            cells.append(
                ReconstructionCell(
                    family_index=index,
                    family_seed=seed,
                    arm=arm,
                    semantic_digest=control.semantic_digest,
                    canonical_truth=dict(control.canonical_truth),
                    serialized_representation=serialized,
                    raw_completion=completion.content,
                    score=score,
                    cost=cost,
                )
            )
            arm_outcomes.append(score.full_payload_exact)
        if len(arm_outcomes) != 2:
            raise AssertionError("semantic reconstruction arm ledger drifted")
        paired_outcomes.append((arm_outcomes[0], arm_outcomes[1]))

    client.require_complete_plan()
    if len(cells) != SEMANTIC_COMPLETIONS:
        raise SemanticReconstructionPhysicalBindingError(
            "campaign did not complete exactly 32 semantic cells"
        )
    table = paired_table(paired_outcomes)
    verdict = classify_result(table)
    return _campaign_result(
        verdict=verdict,
        cells=cells,
        paired={
            "both_correct": table.both_correct,
            "p4_only": table.p4_only,
            "p6_only": table.p6_only,
            "both_wrong": table.both_wrong,
        },
        client=client,
        completed=True,
        failure=None,
    )


def validate_physical_adapter_binding() -> None:
    validate_repository_binding()
    if PHYSICAL_ADAPTER_ISSUE != 2723:
        raise SemanticReconstructionPhysicalBindingError(
            "physical adapter owner drifted"
        )
    if SCIENTIFIC_INPUT_TOKEN_REQUESTS != 64:
        raise SemanticReconstructionPhysicalBindingError(
            "scientific input-token request ledger drifted"
        )
    if CLAIM != "SEMANTIC_RECONSTRUCTION_ACCESSIBILITY_PROBE":
        raise SemanticReconstructionPhysicalBindingError("claim label drifted")
    if CITABLE_WHEN_CLEAN is not True:
        raise SemanticReconstructionPhysicalBindingError(
            "clean completed probe must remain eligible for scoped Level-D import"
        )
    if ARCHITECTURE_CONSEQUENCE != "NONE":
        raise SemanticReconstructionPhysicalBindingError(
            "architecture consequence drifted"
        )
    if physical_call_plan() != tuple(
        f"semantic-reconstruction:{index}:{seed}:{arm}"
        for index, seed, arm in semantic_call_plan()
    ):
        raise SemanticReconstructionPhysicalBindingError("call plan drifted")
