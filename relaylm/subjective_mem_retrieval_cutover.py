"""Content-free RT-1D cutover validation, rehearsal, and one-authority activation.

This module is the sole public semantic cutover owner and the sole public
compatibility surface. It owns the public binding, the requested-mode, result,
and decision schemas, semantic validation, the exact Primary reader and writer
authority decisions, and validation of the private owners' returned content-free
results.

Two private owners hold the mechanics, and the dependency direction is one-way:

```text
ordinary route / cutover facade
  -> relaylm._subjective_mem_retrieval_cutover_activation   durable mechanics
  -> relaylm._subjective_mem_retrieval_runtime_projection    ordinary projection
```

Neither private owner imports this facade, the configuration owner, request-path
owners, selection, the usage ledger, Primary owners, or RelayCTX, and neither is
a second semantic authority.

Configuration is a requested deployment mode and explicit safe locators only; it
never selects served authority. The allowed ordinary transition is exactly
Primary-only, then neither, then Subjective-only. There is no dual serving, no
precedence, no empty-result fallback, and no Primary fallback after the exact
finalized transfer receipt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from ._subjective_mem_retrieval_cutover_activation import (
    ACTIVATION_STEPS,
    CUTOVER_LOG_KEY,
    CUTOVER_LOG_KIND,
    CUTOVER_SCHEMA_VERSION,
    FORWARD_STATES,
    CutoverState,
    READER_FENCE_INDEX,
    RECEIPT_INDEX,
    RECOVERY_REQUIRED,
    WRITER_FENCE_INDEX,
    advance_cutover_chain,
    projection_generation_identity,
    reconstruct_cutover_chain,
    safe_token,
    sha256_digest,
)
from .config import RelayLMConfig
from .evidence_common import canonical_digest
from .evidence_store import EvidenceRecordStore
from .subjective_mem_retrieval_rehearsal import (
    READINESS_PREFIX,
    READINESS_SCHEMA,
    SubjectiveMemRetrievalRehearsalReadiness,
    SubjectiveMemRetrievalRehearsalSpecification,
    derive_subjective_mem_retrieval_rehearsal_readiness_id,
    evaluate_subjective_mem_retrieval_rehearsal,
    validate_subjective_mem_retrieval_rehearsal_readiness,
)

CUTOVER_AUTHORITY_DOMAIN = "relaylm.subjective_mem_retrieval"
CUTOVER_TRANSFERRED_SCOPE = "ordinary_memory_retrieval"

RequestedMode = Literal["primary_only", "rehearsal", "subjective_only"]
AuthorityClass = Literal["primary_only", "neither", "subjective_only"]
PrimaryWriterClass = Literal["permitted", "rejected"]
PrimaryReaderClass = Literal["primary_only", "neither", "subjective_only"]

REQUESTED_MODES = frozenset({"primary_only", "rehearsal", "subjective_only"})
AUTHORITY_CLASSES = frozenset({"primary_only", "neither", "subjective_only"})
PROBE_CLASSES = frozenset({"not_applicable", "subjective_only", "fail_closed"})

PRIMARY_WRITER_DECISION_SCHEMA_VERSION = 1
PRIMARY_READER_DECISION_SCHEMA_VERSION = 1
PRIMARY_WRITER_PERMITTED = "permitted"
PRIMARY_WRITER_REJECTED = "rejected"

_FORWARD_STATES = FORWARD_STATES
_TOKEN_FIELDS = (
    "evidence_space_id",
    "deployment_id",
    "scope_id",
    "policy_revision_id",
    "readiness_id",
)
_PROJECTION_GENERATION_FIELD = "projection_generation_id"
_DIGEST_FIELDS = (
    "bootstrap_main_sha",
    "resulting_main_sha",
    "projection_source_digest",
)
_BINDING_FIELDS = (
    "schema_version",
    "authority_domain",
    "transferred_scope",
    *_TOKEN_FIELDS,
    *_DIGEST_FIELDS,
    _PROJECTION_GENERATION_FIELD,
)
# Writes stay permitted only strictly before `primary_writer_fenced`.
_PRIMARY_WRITER_PERMITTED_STATES = _FORWARD_STATES[:WRITER_FENCE_INDEX]
_PRIMARY_WRITER_FENCED_REASON = "cutover_primary_writer_fenced"
_PRIMARY_READER_FENCED_REASON = "cutover_primary_reader_fenced"
_MAX_PRIMARY_WRITER_REASONS = 8
_MAX_DIAGNOSTIC_COUNT = 4096
_CUTOVER_CONFIG_PREFIX = "subjective_mem_retrieval_cutover_"
_CUTOVER_CONFIG_FIELDS = tuple(
    f"{_CUTOVER_CONFIG_PREFIX}{field}"
    for field in (
        "store_root", *_TOKEN_FIELDS, *_DIGEST_FIELDS, _PROJECTION_GENERATION_FIELD
    )
)
_PROJECTION_ROOT_FIELD = "subjective_mem_retrieval_projection_root"


class SubjectiveMemRetrievalCutoverError(ValueError):
    """Stable content-free validation failure."""


@dataclass(frozen=True, repr=False)
class SubjectiveMemRetrievalCutoverBinding:
    schema_version: int
    authority_domain: str
    transferred_scope: str
    evidence_space_id: str
    deployment_id: str
    scope_id: str
    policy_revision_id: str
    readiness_id: str
    bootstrap_main_sha: str
    resulting_main_sha: str
    projection_generation_id: str
    projection_source_digest: str

    def __post_init__(self) -> None:
        if self.schema_version != CUTOVER_SCHEMA_VERSION:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_binding_schema_unsupported"
            )
        if self.authority_domain != CUTOVER_AUTHORITY_DOMAIN:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_binding_authority_domain_mismatch"
            )
        if self.transferred_scope != CUTOVER_TRANSFERRED_SCOPE:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_binding_transferred_scope_mismatch"
            )
        if not all(safe_token(getattr(self, field)) for field in _TOKEN_FIELDS):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_binding_identifier_invalid"
            )
        if not all(sha256_digest(getattr(self, field)) for field in _DIGEST_FIELDS):
            raise SubjectiveMemRetrievalCutoverError("cutover_binding_digest_invalid")
        if not projection_generation_identity(self.projection_generation_id):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_binding_projection_generation_invalid"
            )

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> "SubjectiveMemRetrievalCutoverBinding":
        if type(value) is not dict or tuple(sorted(value)) != tuple(
            sorted(_BINDING_FIELDS)
        ):
            raise SubjectiveMemRetrievalCutoverError("cutover_binding_schema_invalid")
        try:
            return cls(**value)  # type: ignore[arg-type]
        except TypeError as exc:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_binding_schema_invalid"
            ) from exc

    def to_dict(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in _BINDING_FIELDS}

    def __repr__(self) -> str:
        return (
            "SubjectiveMemRetrievalCutoverBinding(content_free_identity_omitted=True)"
        )


@dataclass(frozen=True)
class SubjectiveMemRetrievalCutoverRequest:
    requested_mode: RequestedMode = "primary_only"

    def __post_init__(self) -> None:
        if self.requested_mode not in REQUESTED_MODES:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_requested_mode_unsupported"
            )


@dataclass(frozen=True)
class SubjectiveMemRetrievalCutoverDiagnostics:
    """One bounded content-free public projection of an exact durable state.

    Every fence and serving boolean is derived from, and re-proved against, the
    reconstructed state, so a diagnostic can never claim an authority the durable
    chain does not hold. No prose, query, prompt, path, private identifier,
    digest, or correlation material may appear here.
    """

    state_class: CutoverState
    generation_ready: bool
    candidate_count: int
    selected_count: int
    exclusion_count: int
    usage_finalized: bool
    reader_fence: bool
    writer_fence: bool
    probe_class: str
    recovery_required: bool
    subjective_serving: bool
    runtime_private_evidence_omitted: bool = True

    def __post_init__(self) -> None:
        if self.state_class not in {*_FORWARD_STATES, RECOVERY_REQUIRED}:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_state_invalid"
            )
        if any(
            type(value) is not bool
            for value in (
                self.generation_ready,
                self.usage_finalized,
                self.reader_fence,
                self.writer_fence,
                self.recovery_required,
                self.subjective_serving,
                self.runtime_private_evidence_omitted,
            )
        ):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_boolean_invalid"
            )
        self._validate_counts()
        if self.probe_class not in PROBE_CLASSES:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_probe_invalid"
            )
        if not self.runtime_private_evidence_omitted:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_private_evidence_invalid"
            )
        self._validate_authority()

    def _validate_counts(self) -> None:
        counts = (self.candidate_count, self.selected_count, self.exclusion_count)
        if any(
            type(value) is not int or not 0 <= value <= _MAX_DIAGNOSTIC_COUNT
            for value in counts
        ) or self.selected_count > self.candidate_count:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_counts_invalid"
            )

    def _validate_authority(self) -> None:
        recovery = self.state_class == RECOVERY_REQUIRED
        index = None if recovery else _FORWARD_STATES.index(self.state_class)
        if recovery != self.recovery_required:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_recovery_invalid"
            )
        expected = (
            (False, False, False)
            if index is None
            else (
                index >= READER_FENCE_INDEX,
                index >= WRITER_FENCE_INDEX,
                index >= RECEIPT_INDEX,
            )
        )
        if (self.reader_fence, self.writer_fence, self.subjective_serving) != expected:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_authority_invalid"
            )
        if self.usage_finalized and not self.subjective_serving:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_usage_invalid"
            )

    def to_dict(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in self.__dataclass_fields__}


@dataclass(frozen=True)
class SubjectiveMemRetrievalCutoverResult:
    requested_mode: RequestedMode
    authority_class: AuthorityClass
    state: CutoverState
    reasons: tuple[str, ...]
    diagnostics: SubjectiveMemRetrievalCutoverDiagnostics

    def __post_init__(self) -> None:
        if self.requested_mode not in REQUESTED_MODES:
            raise SubjectiveMemRetrievalCutoverError("cutover_result_mode_invalid")
        if self.authority_class not in AUTHORITY_CLASSES:
            raise SubjectiveMemRetrievalCutoverError("cutover_result_authority_invalid")
        if type(self.reasons) is not tuple or not all(
            safe_token(reason) for reason in self.reasons
        ):
            raise SubjectiveMemRetrievalCutoverError("cutover_result_reasons_invalid")
        if (
            type(self.diagnostics) is not SubjectiveMemRetrievalCutoverDiagnostics
            or self.diagnostics.state_class != self.state
        ):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_result_diagnostics_invalid"
            )
        if (self.authority_class == "subjective_only") != (
            self.diagnostics.subjective_serving
        ):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_result_serving_disagreement"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_mode": self.requested_mode,
            "authority_class": self.authority_class,
            "state": self.state,
            "reasons": list(self.reasons),
            "diagnostics": self.diagnostics.to_dict(),
        }


def evaluate_subjective_mem_retrieval_rehearsal_readiness(
    *,
    config: object,
    binding: object,
    source: object,
    projection_root: object,
    request: object,
    primary: object,
    subjective_latency_class: object,
) -> tuple[SubjectiveMemRetrievalRehearsalReadiness | None, tuple[str, ...]]:
    """Validate cutover authority, then delegate the disposable R3 proof."""

    if type(config) is not RelayLMConfig or type(binding) is not SubjectiveMemRetrievalCutoverBinding:
        return None, ("cutover_readiness_binding_invalid",)
    if config.subjective_mem_retrieval_cutover_mode != "rehearsal":
        return None, ("cutover_readiness_config_invalid",)
    try:
        binding.__post_init__()
        configured = _binding_from_config(config)
    except (AttributeError, SubjectiveMemRetrievalCutoverError, TypeError):
        return None, ("cutover_readiness_config_invalid",)
    if configured != binding:
        return None, ("cutover_readiness_config_binding_disagreement",)
    specification = _rehearsal_specification(binding)
    readiness, reasons = evaluate_subjective_mem_retrieval_rehearsal(
        specification=specification,
        source=source,
        projection_root=projection_root,
        request=request,
        primary=primary,
        subjective_latency_class=subjective_latency_class,
    )
    if readiness is None:
        return None, reasons
    reasons = _readiness_proof_reasons(binding, specification, readiness)
    return (None, reasons) if reasons else (readiness, ())


def _readiness_proof_reasons(
    binding: SubjectiveMemRetrievalCutoverBinding,
    specification: SubjectiveMemRetrievalRehearsalSpecification,
    readiness: object,
) -> tuple[str, ...]:
    """Independently re-derive and re-validate one complete readiness proof."""

    reasons = validate_subjective_mem_retrieval_rehearsal_readiness(
        specification=specification, readiness=readiness
    )
    if reasons:
        return reasons
    assert isinstance(readiness, SubjectiveMemRetrievalRehearsalReadiness)
    expected_id = _cutover_readiness_identity(
        binding_identity=specification.binding_identity,
        projection_generation_id=readiness.projection_generation_id,
        projection_source_digest=readiness.projection_source_digest,
        projection_manifest_digest=readiness.projection_manifest_digest,
        row_population_digest=readiness.row_population_digest,
        characterization_digest=readiness.characterization_digest,
    )
    if (
        readiness.readiness_id != binding.readiness_id
        or readiness.readiness_id != expected_id
        or readiness.binding_identity != specification.binding_identity
        or readiness.projection_generation_id != binding.projection_generation_id
        or readiness.projection_source_digest != binding.projection_source_digest
    ):
        return ("cutover_readiness_proof_disagreement",)
    return ()


def _rehearsal_specification(
    binding: SubjectiveMemRetrievalCutoverBinding,
) -> SubjectiveMemRetrievalRehearsalSpecification:
    """The one binding-owned coordinator specification every proof is judged by."""

    return SubjectiveMemRetrievalRehearsalSpecification(
        binding_identity=tuple(sorted(
            (field, getattr(binding, field))
            for field in _BINDING_FIELDS
            if field != "readiness_id"
        )),
        evidence_space_id=binding.evidence_space_id,
        projection_generation_id=binding.projection_generation_id,
        projection_source_digest=binding.projection_source_digest,
        readiness_id=binding.readiness_id,
    )


def subjective_mem_retrieval_rehearsal_readiness_id(
    binding: SubjectiveMemRetrievalCutoverBinding,
    projection: object,
    characterization: object,
) -> str:
    """Derive the binding-owned expected identity for an independently proven run."""

    specification = _rehearsal_specification(binding)
    return derive_subjective_mem_retrieval_rehearsal_readiness_id(
        binding_identity=specification.binding_identity,
        projection_generation_id=projection.manifest.projection_generation_id,
        projection_source_digest=projection.manifest.source_snapshot_digest,
        projection_manifest_digest=projection.manifest.manifest_digest,
        row_population_digest=canonical_digest(
            [row.row_digest for row in projection.rows]
        ),
        characterization_digest=canonical_digest(characterization.to_dict()),
    )


def _cutover_readiness_identity(**identities: object) -> str:
    """Independently re-derive the coordinator proof's complete identity."""

    body = {"schema": READINESS_SCHEMA, **identities}
    body["binding"] = dict(body.pop("binding_identity"))
    return f"{READINESS_PREFIX}{canonical_digest(body)}"


@dataclass(frozen=True, repr=False)
class SubjectiveMemRetrievalPrimaryWriterDecision:
    """The sole closed, immutable, content-free Primary writer authority."""

    schema_version: int
    state: CutoverState
    writer_class: PrimaryWriterClass
    recovery_required: bool
    reasons: tuple[str, ...]
    runtime_private_evidence_omitted: bool

    def __post_init__(self) -> None:
        fields = tuple(
            getattr(self, field, None) for field in type(self).__dataclass_fields__
        )
        schema_version, state, writer_class, recovery_required, reasons, omitted = fields
        if type(schema_version) is not int or schema_version != PRIMARY_WRITER_DECISION_SCHEMA_VERSION:
            raise _decision_invalid("schema_unsupported")
        if type(state) is not str or state not in (*_FORWARD_STATES, RECOVERY_REQUIRED):
            raise _decision_invalid("state_invalid")
        if type(writer_class) is not str or writer_class not in (PRIMARY_WRITER_PERMITTED, PRIMARY_WRITER_REJECTED):
            raise _decision_invalid("class_invalid")
        if type(recovery_required) is not bool or omitted is not True:
            raise _decision_invalid("boolean_invalid")
        if (
            type(reasons) is not tuple
            or len(reasons) > _MAX_PRIMARY_WRITER_REASONS
            or not all(safe_token(reason) for reason in reasons)
        ):
            raise _decision_invalid("reasons_invalid")
        if recovery_required != (state == RECOVERY_REQUIRED):
            raise _decision_invalid("recovery_mismatch")
        permitted = state in _PRIMARY_WRITER_PERMITTED_STATES
        if permitted != (writer_class == PRIMARY_WRITER_PERMITTED):
            raise _decision_invalid("class_state_mismatch")
        if permitted != (not reasons):
            raise _decision_invalid("reasons_invalid")

    def to_dict(self) -> dict[str, object]:
        value = {field: getattr(self, field) for field in self.__dataclass_fields__}
        return {**value, "reasons": list(self.reasons)}

    def __repr__(self) -> str:
        return f"SubjectiveMemRetrievalPrimaryWriterDecision({self.to_dict()})"


@dataclass(frozen=True, repr=False)
class SubjectiveMemRetrievalPrimaryReaderDecision:
    """The sole closed, immutable, content-free ordinary reader authority.

    The reader class is a pure function of the exact reconstructed durable
    state: Primary alone before the durable reader fence, neither authority from
    that fence until the exact finalized transfer receipt, and Subjective alone
    afterwards. There is no dual-read interval, no precedence, and no fallback
    in either direction.
    """

    schema_version: int
    state: CutoverState
    reader_class: PrimaryReaderClass
    recovery_required: bool
    reasons: tuple[str, ...]
    runtime_private_evidence_omitted: bool

    def __post_init__(self) -> None:
        if (
            type(self.schema_version) is not int
            or self.schema_version != PRIMARY_READER_DECISION_SCHEMA_VERSION
        ):
            raise _reader_invalid("schema_unsupported")
        if type(self.state) is not str or self.state not in (
            *_FORWARD_STATES, RECOVERY_REQUIRED
        ):
            raise _reader_invalid("state_invalid")
        if type(self.reader_class) is not str or self.reader_class not in AUTHORITY_CLASSES:
            raise _reader_invalid("class_invalid")
        if type(self.recovery_required) is not bool or (
            self.runtime_private_evidence_omitted is not True
        ):
            raise _reader_invalid("boolean_invalid")
        if (
            type(self.reasons) is not tuple
            or len(self.reasons) > _MAX_PRIMARY_WRITER_REASONS
            or not all(safe_token(reason) for reason in self.reasons)
        ):
            raise _reader_invalid("reasons_invalid")
        if self.recovery_required != (self.state == RECOVERY_REQUIRED):
            raise _reader_invalid("recovery_mismatch")
        if self.reader_class != _reader_class(self.state):
            raise _reader_invalid("class_state_mismatch")
        if (self.reader_class == "primary_only") != (not self.reasons):
            raise _reader_invalid("reasons_invalid")

    def to_dict(self) -> dict[str, object]:
        value = {field: getattr(self, field) for field in self.__dataclass_fields__}
        return {**value, "reasons": list(self.reasons)}

    def __repr__(self) -> str:
        return f"SubjectiveMemRetrievalPrimaryReaderDecision({self.to_dict()})"


def _reader_class(state: str) -> PrimaryReaderClass:
    """Map one exact reconstructed state to the one ordinary served authority."""

    if state == RECOVERY_REQUIRED or state not in _FORWARD_STATES:
        return "neither"
    index = _FORWARD_STATES.index(state)
    if index < READER_FENCE_INDEX:
        return "primary_only"
    return "subjective_only" if index >= RECEIPT_INDEX else "neither"


def resolve_subjective_mem_retrieval_primary_writer_decision(
    config: RelayLMConfig,
) -> SubjectiveMemRetrievalPrimaryWriterDecision:
    """Resolve the one Primary writer decision this module alone owns.

    ``primary_only`` is explicit mode-derived authority: the complete empty
    cutover tuple binds ``primary_stable`` with no store, store root,
    binding, or durable read. ``rehearsal`` and ``subjective_only`` reconstruct
    the exact chain through the existing validation. Anything else fails closed.
    """
    state, reasons = _state_from_config(config, prefix="cutover_writer")
    return _writer_decision(state, reasons)


def resolve_subjective_mem_retrieval_primary_reader_decision(
    config: RelayLMConfig,
) -> SubjectiveMemRetrievalPrimaryReaderDecision:
    """Resolve the one ordinary reader decision this module alone owns.

    Configuration is a deployment request, never authority: requesting
    ``subjective_only`` without an exact finalized transfer receipt in the
    durable chain still yields ``neither``, and a missing, partial, stale,
    divergent, or unsupported tuple or chain fails closed.
    """
    state, reasons = _state_from_config(config, prefix="cutover_reader")
    return _reader_decision(state, reasons)


def _state_from_config(config: object, *, prefix: str) -> tuple[str, tuple[str, ...]]:
    """Reconstruct the exact durable state the configured tuple names."""

    if type(config) is not RelayLMConfig:
        return RECOVERY_REQUIRED, (f"{prefix}_config_invalid",)
    values = tuple(getattr(config, field) for field in _CUTOVER_CONFIG_FIELDS)
    projection_root = getattr(config, _PROJECTION_ROOT_FIELD, None)
    disagreement = (f"{prefix}_config_disagreement",)
    mode = config.subjective_mem_retrieval_cutover_mode
    if mode == "primary_only":
        if any(value is not None for value in values) or projection_root is not None:
            return RECOVERY_REQUIRED, disagreement
        return "primary_stable", ()
    if mode not in {"rehearsal", "subjective_only"} or any(
        value is None for value in values
    ):
        return RECOVERY_REQUIRED, disagreement
    if (projection_root is None) != (mode == "rehearsal"):
        return RECOVERY_REQUIRED, disagreement
    try:
        binding = _binding_from_config(config)
        store = EvidenceRecordStore(
            config.subjective_mem_retrieval_cutover_store_root or ""
        )
    except (SubjectiveMemRetrievalCutoverError, OSError, TypeError, ValueError):
        return RECOVERY_REQUIRED, (f"{prefix}_binding_invalid",)
    state, reasons = reconstruct_cutover_chain(store, binding.to_dict())
    if reasons or state == RECOVERY_REQUIRED:
        return RECOVERY_REQUIRED, reasons or (f"{prefix}_state_unsupported",)
    return state, ()


def _binding_from_config(config: RelayLMConfig) -> SubjectiveMemRetrievalCutoverBinding:
    return SubjectiveMemRetrievalCutoverBinding(
        schema_version=CUTOVER_SCHEMA_VERSION,
        authority_domain=CUTOVER_AUTHORITY_DOMAIN,
        transferred_scope=CUTOVER_TRANSFERRED_SCOPE,
        **{
            field: getattr(config, f"{_CUTOVER_CONFIG_PREFIX}{field}")
            for field in (*_TOKEN_FIELDS, *_DIGEST_FIELDS, _PROJECTION_GENERATION_FIELD)
        },
    )


def subjective_mem_retrieval_cutover_binding_from_config(
    config: object,
) -> SubjectiveMemRetrievalCutoverBinding | None:
    """Return the exact configured binding, or ``None`` for any partial tuple."""

    if type(config) is not RelayLMConfig or any(
        getattr(config, field) is None for field in _CUTOVER_CONFIG_FIELDS
    ):
        return None
    try:
        return _binding_from_config(config)
    except (SubjectiveMemRetrievalCutoverError, TypeError):
        return None


def primary_writer_decision_permits_write(decision: object) -> bool:
    """Return True only for the exact immutable decision that permits writes.

    Missing, foreign-typed, tampered, rejected, and recovery-required values
    all fail closed here -- the only place a downstream module may ask.
    """
    if type(decision) is not SubjectiveMemRetrievalPrimaryWriterDecision:
        return False
    try:
        decision.__post_init__()
    except SubjectiveMemRetrievalCutoverError:
        return False
    return (
        decision.writer_class == PRIMARY_WRITER_PERMITTED
        and not decision.recovery_required
    )


def subjective_mem_retrieval_primary_reader_class(decision: object) -> PrimaryReaderClass:
    """Return the one served authority class of an exact immutable reader decision.

    Missing, foreign-typed, and tampered values fail closed to ``neither`` here --
    the only place the ordinary route may ask -- so no caller can obtain Primary
    or Subjective serving from anything but a valid decision.
    """
    if type(decision) is not SubjectiveMemRetrievalPrimaryReaderDecision:
        return "neither"
    try:
        decision.__post_init__()
    except SubjectiveMemRetrievalCutoverError:
        return "neither"
    return decision.reader_class


def _writer_decision(
    state: str, reasons: tuple[str, ...]
) -> SubjectiveMemRetrievalPrimaryWriterDecision:
    recovery = state == RECOVERY_REQUIRED
    permitted = state in _PRIMARY_WRITER_PERMITTED_STATES and not recovery
    return SubjectiveMemRetrievalPrimaryWriterDecision(
        PRIMARY_WRITER_DECISION_SCHEMA_VERSION,
        state,  # type: ignore[arg-type]
        PRIMARY_WRITER_PERMITTED if permitted else PRIMARY_WRITER_REJECTED,
        recovery,
        () if permitted else (reasons or (_PRIMARY_WRITER_FENCED_REASON,)),
        True,
    )


def _reader_decision(
    state: str, reasons: tuple[str, ...]
) -> SubjectiveMemRetrievalPrimaryReaderDecision:
    reader_class = _reader_class(state)
    return SubjectiveMemRetrievalPrimaryReaderDecision(
        PRIMARY_READER_DECISION_SCHEMA_VERSION,
        state,  # type: ignore[arg-type]
        reader_class,
        state == RECOVERY_REQUIRED,
        () if reader_class == "primary_only" else (reasons or (_PRIMARY_READER_FENCED_REASON,)),
        True,
    )


def _decision_invalid(reason: str) -> SubjectiveMemRetrievalCutoverError:
    return SubjectiveMemRetrievalCutoverError(f"primary_writer_decision_{reason}")


def _reader_invalid(reason: str) -> SubjectiveMemRetrievalCutoverError:
    return SubjectiveMemRetrievalCutoverError(f"primary_reader_decision_{reason}")


def rehearse_subjective_mem_retrieval_cutover(
    *,
    store: EvidenceRecordStore,
    binding: SubjectiveMemRetrievalCutoverBinding,
    request: SubjectiveMemRetrievalCutoverRequest,
) -> SubjectiveMemRetrievalCutoverResult:
    """Reconstruct and validate only; never commit or authorize Subjective serving."""
    _validate_inputs(store, binding, request)
    if request.requested_mode == "subjective_only":
        raise SubjectiveMemRetrievalCutoverError("cutover_rehearsal_mode_unsupported")
    state, reasons = reconstruct_cutover_chain(store, binding.to_dict())
    if state not in {"primary_stable", "rehearsal_ready"} or reasons:
        return _result(
            request.requested_mode,
            RECOVERY_REQUIRED,
            reasons or ("cutover_state_not_r1_supported",),
        )
    if request.requested_mode == "rehearsal":
        return _result("rehearsal", "rehearsal_ready", ())
    return _result("primary_only", state, ())


def activate_subjective_mem_retrieval_cutover(
    *,
    store: EvidenceRecordStore,
    binding: SubjectiveMemRetrievalCutoverBinding,
    request: SubjectiveMemRetrievalCutoverRequest,
    readiness: object,
) -> SubjectiveMemRetrievalCutoverResult:
    """Perform the one governed authority transfer, forward-only and idempotent.

    The exact readiness proof is revalidated against this binding before any
    durable write. Each step is one create-or-verify durable transaction, and
    Subjective-reader enablement publishes atomically with the finalized transfer
    receipt, so no reconstructible state ever holds only the first. A replay
    after a lost response returns the same exact state and writes nothing new;
    a divergent chain fails closed and is never repaired or rolled back.
    """
    _validate_inputs(store, binding, request)
    if request.requested_mode != "subjective_only":
        raise SubjectiveMemRetrievalCutoverError("cutover_activation_mode_unsupported")
    reasons = _readiness_proof_reasons(
        binding, _rehearsal_specification(binding), readiness
    )
    if reasons:
        return _result("subjective_only", RECOVERY_REQUIRED, reasons)
    state, reasons = reconstruct_cutover_chain(store, binding.to_dict())
    if reasons or state == RECOVERY_REQUIRED:
        return _result(
            "subjective_only",
            RECOVERY_REQUIRED,
            reasons or ("cutover_activation_state_unsupported",),
        )
    for step in ACTIVATION_STEPS:
        if _FORWARD_STATES.index(state) >= _FORWARD_STATES.index(step[-1]):
            continue
        state, reasons = advance_cutover_chain(store, binding.to_dict(), step)
        if reasons or state == RECOVERY_REQUIRED:
            return _result(
                "subjective_only",
                RECOVERY_REQUIRED,
                reasons or ("cutover_activation_failed",),
            )
    return _result("subjective_only", state, ())


def _validate_inputs(
    store: object, binding: object, request: object
) -> None:
    """Refuse anything that is not one exact store, binding, and request triple."""

    if type(store) is not EvidenceRecordStore:
        raise SubjectiveMemRetrievalCutoverError("cutover_store_invalid")
    if type(binding) is not SubjectiveMemRetrievalCutoverBinding:
        raise SubjectiveMemRetrievalCutoverError("cutover_binding_invalid")
    if type(request) is not SubjectiveMemRetrievalCutoverRequest:
        raise SubjectiveMemRetrievalCutoverError("cutover_request_invalid")


def _result(
    mode: RequestedMode, state: str, reasons: tuple[str, ...]
) -> SubjectiveMemRetrievalCutoverResult:
    recovery = state == RECOVERY_REQUIRED
    index = None if recovery else _FORWARD_STATES.index(state)
    serving = index is not None and index >= RECEIPT_INDEX
    diagnostics = SubjectiveMemRetrievalCutoverDiagnostics(
        state,  # type: ignore[arg-type]
        state == "rehearsal_ready" or serving,
        0,
        0,
        0,
        False,
        index is not None and index >= READER_FENCE_INDEX,
        index is not None and index >= WRITER_FENCE_INDEX,
        "subjective_only" if serving else ("fail_closed" if recovery else "not_applicable"),
        recovery,
        serving,
    )
    return SubjectiveMemRetrievalCutoverResult(
        mode, _reader_class(state), state, reasons, diagnostics  # type: ignore[arg-type]
    )


__all__ = [
    "AUTHORITY_CLASSES",
    "CUTOVER_AUTHORITY_DOMAIN",
    "CUTOVER_LOG_KEY",
    "CUTOVER_LOG_KIND",
    "CUTOVER_SCHEMA_VERSION",
    "CUTOVER_TRANSFERRED_SCOPE",
    "PRIMARY_READER_DECISION_SCHEMA_VERSION",
    "PRIMARY_WRITER_DECISION_SCHEMA_VERSION",
    "PRIMARY_WRITER_PERMITTED",
    "PRIMARY_WRITER_REJECTED",
    "PROBE_CLASSES",
    "REQUESTED_MODES",
    "SubjectiveMemRetrievalCutoverBinding",
    "SubjectiveMemRetrievalCutoverDiagnostics",
    "SubjectiveMemRetrievalCutoverError",
    "SubjectiveMemRetrievalCutoverRequest",
    "SubjectiveMemRetrievalCutoverResult",
    "SubjectiveMemRetrievalPrimaryReaderDecision",
    "SubjectiveMemRetrievalPrimaryWriterDecision",
    "SubjectiveMemRetrievalRehearsalReadiness",
    "activate_subjective_mem_retrieval_cutover",
    "evaluate_subjective_mem_retrieval_rehearsal_readiness",
    "primary_writer_decision_permits_write",
    "rehearse_subjective_mem_retrieval_cutover",
    "resolve_subjective_mem_retrieval_primary_reader_decision",
    "resolve_subjective_mem_retrieval_primary_writer_decision",
    "subjective_mem_retrieval_cutover_binding_from_config",
    "subjective_mem_retrieval_primary_reader_class",
    "subjective_mem_retrieval_rehearsal_readiness_id",
]
