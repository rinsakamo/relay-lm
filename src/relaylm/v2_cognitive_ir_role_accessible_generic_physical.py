from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Protocol

from relaylm.v2_cognitive_ir_role_accessible_generic import (
    ARCHITECTURE_CONSEQUENCE,
    CONFIRMATORY_CONTRASTS,
    CONTEXT_LIMIT,
    DESCRIPTIVE_ONLY_CONTRAST,
    FAMILY_COUNT,
    FORBIDDEN_RESCUE_COUNTS,
    LEGACY_SURFACE,
    MAX_OUTPUT_TOKENS,
    PARALLEL_SEMANTIC_SLOTS,
    PHYSICAL_EXECUTION_AUTHORIZED,
    REASONING,
    REQUEST_SEED,
    ROLE_FUNCTIONAL_SURFACE,
    SCIENTIFIC_INPUT_TOKEN_REQUESTS,
    SEMANTIC_PROVIDER_CALLS,
    STREAM,
    SURFACES,
    TEMPERATURE,
    TYPED_SURFACE,
    ConfirmatoryContrast,
    PairedTable,
    RoleAccessibleRepresentations,
    _generate_shared_family as _repository_generate_shared_family,
    build_formation_messages,
    build_target_messages as _build_target_prompt,
    confirmatory_analysis,
    descriptive_typed_vs_legacy,
    generate_synthetic_shared_family as _repository_generate_synthetic_shared_family,
    parse_learned_rule_completion,
    prepare_synthetic_representations,
    preregistered_seeds,
    semantic_call_plan,
    validate_repository_binding,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import TransferFamily, VerificationResult

PHYSICAL_ADAPTER_ISSUE = 2904
MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS = 2
CLAIM = "ROLE_ACCESSIBILITY_CONTROLLED_DOWNSTREAM_USE_PROBE"
_CONTROL_SENTINEL_SEED = 91_2904_000_000_001

_HEX_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class RoleAccessibleGenericPhysicalError(ValueError):
    """The #2904 E5-RA1 physical adapter cannot proceed truthfully."""


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
                raise RoleAccessibleGenericPhysicalError(
                    f"{name} must be a lowercase 40-hex identity"
                )
        for name in ("artifact_sha256", "chat_template_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                raise RoleAccessibleGenericPhysicalError(
                    f"{name} must be a lowercase sha256 digest"
                )
        for name in ("model", "build_info", "model_path", "model_ftype"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise RoleAccessibleGenericPhysicalError(f"{name} must be non-empty")
        if self.context_limit != CONTEXT_LIMIT:
            raise RoleAccessibleGenericPhysicalError(
                f"consumer context must be exactly {CONTEXT_LIMIT}"
            )
        if self.total_slots != PARALLEL_SEMANTIC_SLOTS:
            raise RoleAccessibleGenericPhysicalError(
                "consumer must expose exactly one semantic slot"
            )
        if self.context_shift_enabled is not False:
            raise RoleAccessibleGenericPhysicalError("context shift must be disabled")
        if self.max_output_tokens != MAX_OUTPUT_TOKENS:
            raise RoleAccessibleGenericPhysicalError("max output token contract drifted")
        if self.temperature != TEMPERATURE:
            raise RoleAccessibleGenericPhysicalError("temperature contract drifted")
        if self.reasoning != REASONING:
            raise RoleAccessibleGenericPhysicalError("reasoning contract drifted")
        if self.request_seed is not None:
            raise RoleAccessibleGenericPhysicalError(
                "request seed must remain omitted/null"
            )
        if self.semantic_parallelism != PARALLEL_SEMANTIC_SLOTS:
            raise RoleAccessibleGenericPhysicalError(
                "semantic parallelism contract drifted"
            )


def freeze_consumer_identity(
    *,
    repository_commit: str,
    repository_tree: str,
    model: str,
    runtime_attestation: Mapping[str, object],
) -> FrozenConsumerIdentity:
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
    if not isinstance(runtime_attestation, Mapping) or set(runtime_attestation) != required:
        raise RoleAccessibleGenericPhysicalError("runtime attestation shape drifted")
    if runtime_attestation["model_alias"] != model:
        raise RoleAccessibleGenericPhysicalError(
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


def generate_synthetic_shared_family(seed: int) -> TransferFamily:
    return _repository_generate_synthetic_shared_family(seed)


def generate_scientific_shared_family(
    *, index: int, seed: int, frozen_identity: FrozenConsumerIdentity
) -> TransferFamily:
    if not isinstance(frozen_identity, FrozenConsumerIdentity):
        raise RoleAccessibleGenericPhysicalError(
            "scientific E5-RA1 material requires E5 FrozenConsumerIdentity"
        )
    frozen_identity.validate()
    seeds = preregistered_seeds()
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < FAMILY_COUNT:
        raise RoleAccessibleGenericPhysicalError(
            "scientific E5-RA1 family index must be 0..23"
        )
    if isinstance(seed, bool) or not isinstance(seed, int) or seed != seeds[index]:
        raise RoleAccessibleGenericPhysicalError(
            "scientific E5-RA1 seed does not match preregistered family index"
        )
    return _repository_generate_shared_family(seed)


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


def provenance_handles(family: TransferFamily) -> tuple[str, ...]:
    handles: list[str] = []
    for index, example in enumerate(family.source_examples):
        content = {
            "index": index,
            "input": list(example.input_values),
            "output": list(example.output_values),
        }
        handles.append(f"src-{_digest(['source-episode', content])[:24]}")
    if not handles:
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 source provenance must not be empty"
        )
    return tuple(handles)


def prepare_physical_representations(
    *, learned_rule: Mapping[str, object], family: TransferFamily
) -> RoleAccessibleRepresentations:
    if _CONTROL_SENTINEL_SEED in set(preregistered_seeds()):
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 transform sentinel collides with preregistration"
        )
    return prepare_synthetic_representations(
        seed=_CONTROL_SENTINEL_SEED,
        learned_rule=learned_rule,
        provenance_handles=provenance_handles(family),
    )


def build_target_messages(
    surface: str,
    prepared: RoleAccessibleRepresentations,
    family: TransferFamily,
) -> tuple[dict[str, str], ...]:
    """Adapt the frozen #2900 target prompt to the S3 transport message boundary."""

    return _build_target_prompt(surface, prepared, family).messages


def physical_call_plan() -> tuple[str, ...]:
    plan = tuple(
        f"role-accessible-generic:{index}:{seed}:{label}"
        for index, seed, label in semantic_call_plan()
    )
    if len(plan) != SEMANTIC_PROVIDER_CALLS or len(set(plan)) != SEMANTIC_PROVIDER_CALLS:
        raise RoleAccessibleGenericPhysicalError("E5-RA1 physical call plan drifted")
    return plan


class RoleAccessibleGenericClient(Protocol):
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion: ...

    def require_complete_plan(self) -> None: ...


@dataclass(frozen=True, slots=True)
class FormationRecord:
    family_index: int
    family_seed: int
    raw_completion: str
    learned_rule: Mapping[str, object]
    input_tokens: int
    output_tokens: int
    response_id: str | None


@dataclass(frozen=True, slots=True)
class DownstreamCell:
    family_index: int
    family_seed: int
    surface: str
    semantic_digest: str
    serialized_representation: str
    raw_completion: str
    verification: VerificationResult
    input_tokens: int
    output_tokens: int
    response_id: str | None
    finish_reason: str = "stop"


@dataclass(frozen=True, slots=True)
class RoleAccessibleGenericCampaignResult:
    classification: str
    statistical_status: str
    citable_for_downstream_claim: bool
    architecture_consequence: str
    formations: tuple[FormationRecord, ...]
    cells: tuple[DownstreamCell, ...]
    confirmatory: Mapping[str, ConfirmatoryContrast] | None
    descriptive_typed_vs_legacy: PairedTable | None
    semantic_equal_families: int
    wire_shape_valid: int
    semantic_domain_valid: int
    surface_exact_totals: Mapping[str, int]
    semantic_calls: int
    provider_completions: int
    input_token_requests: int
    input_token_completions: int
    completed: bool
    measurement_admitted: bool
    failure: str | None


FamilyFactory = Callable[[int, int, FrozenConsumerIdentity], TransferFamily]


def _official_family_factory(
    index: int, seed: int, identity: FrozenConsumerIdentity
) -> TransferFamily:
    return generate_scientific_shared_family(
        index=index, seed=seed, frozen_identity=identity
    )


def _classification(
    contrasts: Mapping[str, ConfirmatoryContrast],
) -> tuple[str, str]:
    h1 = contrasts[CONFIRMATORY_CONTRASTS[0]].holm_reject
    h2 = contrasts[CONFIRMATORY_CONTRASTS[1]].holm_reject
    if h1 and h2:
        return (
            "MULTIPLE_TYPED_AND_ROLE_ACCESSIBILITY_COMPONENTS_DETECTED",
            "CONFIRMATORY_DIFFERENCES_DETECTED",
        )
    if h1:
        return (
            "TYPED_PACKAGING_DIFFERENCE_DETECTED_AFTER_ROLE_ACCESSIBILITY_CONTROL",
            "CONFIRMATORY_DIFFERENCE_DETECTED",
        )
    if h2:
        return (
            "ROLE_ACCESSIBILITY_DOWNSTREAM_DIFFERENCE_DETECTED",
            "CONFIRMATORY_DIFFERENCE_DETECTED",
        )
    return (
        "NO_DECLARED_TYPED_OR_ROLE_ACCESSIBILITY_GAP_DETECTED_AT_THIS_RESOLUTION",
        "UNDERDETERMINED",
    )


def _surface_totals(cells: list[DownstreamCell]) -> dict[str, int]:
    return {
        surface: sum(
            cell.surface == surface and cell.verification.correct for cell in cells
        )
        for surface in SURFACES
    }


def _result(
    *,
    classification: str,
    statistical_status: str,
    citable: bool,
    formations: list[FormationRecord],
    cells: list[DownstreamCell],
    confirmatory: Mapping[str, ConfirmatoryContrast] | None,
    descriptive: PairedTable | None,
    semantic_equal_families: int,
    client: RoleAccessibleGenericClient,
    completed: bool,
    admitted: bool,
    failure: str | None,
) -> RoleAccessibleGenericCampaignResult:
    wire_shape_valid = sum(
        cell.verification.parsed_output is not None
        and cell.verification.error is None
        for cell in cells
    )
    return RoleAccessibleGenericCampaignResult(
        classification=classification,
        statistical_status=statistical_status,
        citable_for_downstream_claim=citable,
        architecture_consequence=ARCHITECTURE_CONSEQUENCE,
        formations=tuple(formations),
        cells=tuple(cells),
        confirmatory=confirmatory,
        descriptive_typed_vs_legacy=descriptive,
        semantic_equal_families=semantic_equal_families,
        wire_shape_valid=wire_shape_valid,
        semantic_domain_valid=wire_shape_valid,
        surface_exact_totals=_surface_totals(cells),
        semantic_calls=int(client.provider_attempts),
        provider_completions=int(client.provider_completions),
        input_token_requests=int(client.input_count_attempts),
        input_token_completions=int(client.input_count_completions),
        completed=completed,
        measurement_admitted=admitted,
        failure=failure,
    )


def _spent(client: RoleAccessibleGenericClient) -> bool:
    return bool(client.input_count_attempts or client.provider_attempts)


def _failure_after_spend(
    *,
    exc: Exception,
    formations: list[FormationRecord],
    cells: list[DownstreamCell],
    semantic_equal_families: int,
    client: RoleAccessibleGenericClient,
) -> RoleAccessibleGenericCampaignResult:
    return _result(
        classification="MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND",
        statistical_status="UNDERDETERMINED",
        citable=False,
        formations=formations,
        cells=cells,
        confirmatory=None,
        descriptive=None,
        semantic_equal_families=semantic_equal_families,
        client=client,
        completed=False,
        admitted=False,
        failure=f"{type(exc).__name__}: {exc}",
    )


def run_role_accessible_generic_campaign(
    client: RoleAccessibleGenericClient,
    *,
    frozen_identity: FrozenConsumerIdentity,
    family_factory: FamilyFactory | None = None,
) -> RoleAccessibleGenericCampaignResult:
    validate_physical_adapter_binding()
    frozen_identity.validate()
    factory = family_factory or _official_family_factory

    formations: list[FormationRecord] = []
    cells: list[DownstreamCell] = []
    h1_outcomes: list[tuple[bool, bool]] = []
    h2_outcomes: list[tuple[bool, bool]] = []
    typed_vs_legacy: list[tuple[bool, bool]] = []
    semantic_equal_families = 0

    for index, seed in enumerate(preregistered_seeds()):
        try:
            family = factory(index, seed, frozen_identity)
        except Exception as exc:
            if _spent(client):
                return _failure_after_spend(
                    exc=exc,
                    formations=formations,
                    cells=cells,
                    semantic_equal_families=semantic_equal_families,
                    client=client,
                )
            raise

        formation_qid = f"role-accessible-generic:{index}:{seed}:FORM_P4"
        try:
            formation = client.complete_named(
                formation_qid,
                build_formation_messages(family),
                output_kind="rule",
            )
            learned_rule = parse_learned_rule_completion(
                formation,
                expected_modulus=family.modulus,
            )
            prepared = prepare_physical_representations(
                learned_rule=learned_rule,
                family=family,
            )
        except Exception as exc:
            if _spent(client):
                return _failure_after_spend(
                    exc=exc,
                    formations=formations,
                    cells=cells,
                    semantic_equal_families=semantic_equal_families,
                    client=client,
                )
            raise

        formations.append(
            FormationRecord(
                family_index=index,
                family_seed=seed,
                raw_completion=formation.content,
                learned_rule=dict(learned_rule),
                input_tokens=formation.input_tokens,
                output_tokens=formation.output_tokens,
                response_id=formation.response_id,
            )
        )
        semantic_equal_families += 1
        outcomes: dict[str, bool] = {}

        for surface in SURFACES:
            question_id = f"role-accessible-generic:{index}:{seed}:{surface}"
            try:
                completion = client.complete_named(
                    question_id,
                    build_target_messages(surface, prepared, family),
                    output_kind="vector",
                )
            except Exception as exc:
                if _spent(client):
                    return _failure_after_spend(
                        exc=exc,
                        formations=formations,
                        cells=cells,
                        semantic_equal_families=semantic_equal_families,
                        client=client,
                    )
                raise

            verification = family.verify_response(0, completion.content)
            cells.append(
                DownstreamCell(
                    family_index=index,
                    family_seed=seed,
                    surface=surface,
                    semantic_digest=prepared.semantic_digest,
                    serialized_representation=prepared.serialized_by_surface[surface],
                    raw_completion=completion.content,
                    verification=verification,
                    input_tokens=completion.input_tokens,
                    output_tokens=completion.output_tokens,
                    response_id=completion.response_id,
                )
            )
            outcomes[surface] = verification.correct

        if set(outcomes) != set(SURFACES):
            raise AssertionError("E5-RA1 surface outcome ledger drifted")
        h1_outcomes.append(
            (outcomes[TYPED_SURFACE], outcomes[ROLE_FUNCTIONAL_SURFACE])
        )
        h2_outcomes.append(
            (outcomes[ROLE_FUNCTIONAL_SURFACE], outcomes[LEGACY_SURFACE])
        )
        typed_vs_legacy.append(
            (outcomes[TYPED_SURFACE], outcomes[LEGACY_SURFACE])
        )

    client.require_complete_plan()

    wire_shape_valid = sum(
        cell.verification.parsed_output is not None
        and cell.verification.error is None
        for cell in cells
    )
    admitted = (
        len(formations) == FAMILY_COUNT
        and len(cells) == FAMILY_COUNT * len(SURFACES)
        and semantic_equal_families == FAMILY_COUNT
        and int(client.provider_attempts) == SEMANTIC_PROVIDER_CALLS
        and int(client.provider_completions) == SEMANTIC_PROVIDER_CALLS
        and int(client.input_count_attempts) == SCIENTIFIC_INPUT_TOKEN_REQUESTS
        and int(client.input_count_completions) == SCIENTIFIC_INPUT_TOKEN_REQUESTS
        and wire_shape_valid == FAMILY_COUNT * len(SURFACES)
        and not any(FORBIDDEN_RESCUE_COUNTS.values())
    )
    if not admitted:
        return _result(
            classification="INVALID_BEFORE_PHYSICAL_EXECUTION",
            statistical_status="UNDERDETERMINED",
            citable=False,
            formations=formations,
            cells=cells,
            confirmatory=None,
            descriptive=None,
            semantic_equal_families=semantic_equal_families,
            client=client,
            completed=True,
            admitted=False,
            failure="measurement admission failed",
        )

    contrasts = confirmatory_analysis(
        h1_typed_vs_role_functional=h1_outcomes,
        h2_role_functional_vs_legacy=h2_outcomes,
    )
    descriptive = descriptive_typed_vs_legacy(typed_vs_legacy)
    classification, statistical_status = _classification(contrasts)
    return _result(
        classification=classification,
        statistical_status=statistical_status,
        citable=True,
        formations=formations,
        cells=cells,
        confirmatory=contrasts,
        descriptive=descriptive,
        semantic_equal_families=semantic_equal_families,
        client=client,
        completed=True,
        admitted=True,
        failure=None,
    )


def validate_physical_adapter_binding() -> None:
    validate_repository_binding()
    if PHYSICAL_ADAPTER_ISSUE != 2904:
        raise RoleAccessibleGenericPhysicalError("E5-RA1 physical adapter owner drifted")
    if FAMILY_COUNT != 24 or SEMANTIC_PROVIDER_CALLS != 96:
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 24-family/96-call contract drifted"
        )
    if SCIENTIFIC_INPUT_TOKEN_REQUESTS != 192:
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 192-request input-token contract drifted"
        )
    if MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS != 2:
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 pre-material counter contract drifted"
        )
    if len(CONFIRMATORY_CONTRASTS) != 2:
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 confirmatory contrast pair drifted"
        )
    if DESCRIPTIVE_ONLY_CONTRAST != "T_VS_L_DESCRIPTIVE_ONLY":
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 descriptive-only contrast drifted"
        )
    if CONTEXT_LIMIT != 8192 or MAX_OUTPUT_TOKENS != 1024:
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 context/output envelope drifted"
        )
    if (
        TEMPERATURE != 0.0
        or REASONING != "none"
        or REQUEST_SEED is not None
        or STREAM is not False
        or PARALLEL_SEMANTIC_SLOTS != 1
    ):
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 decoding/parallelism envelope drifted"
        )
    if PHYSICAL_EXECUTION_AUTHORIZED is not False:
        raise RoleAccessibleGenericPhysicalError(
            "physical adapter must not authorize THIS RUN"
        )
    if ARCHITECTURE_CONSEQUENCE != "NONE":
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 architecture consequence drifted"
        )
    expected = tuple(
        f"role-accessible-generic:{index}:{seed}:{label}"
        for index, seed, label in semantic_call_plan()
    )
    if physical_call_plan() != expected:
        raise RoleAccessibleGenericPhysicalError(
            "E5-RA1 physical call plan drifted"
        )


__all__ = [
    "CLAIM",
    "FrozenConsumerIdentity",
    "FormationRecord",
    "DownstreamCell",
    "RoleAccessibleGenericCampaignResult",
    "RoleAccessibleGenericPhysicalError",
    "build_target_messages",
    "freeze_consumer_identity",
    "generate_scientific_shared_family",
    "generate_synthetic_shared_family",
    "physical_call_plan",
    "prepare_physical_representations",
    "run_role_accessible_generic_campaign",
    "validate_physical_adapter_binding",
]
