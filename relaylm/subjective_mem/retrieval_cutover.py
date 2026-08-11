"""Content-free RT-1D cutover validation, activation, and Primary retirement.

This module is the sole public semantic cutover owner and the sole public
compatibility surface. It owns the public binding, the requested-mode, result,
and decision schemas, semantic validation, the exact Primary reader and writer
authority decisions, and validation of the private owners' returned results.

Two private owners hold the mechanics, and the dependency direction is one-way:

```text
ordinary route / cutover facade
  -> relaylm._subjective_mem_retrieval_cutover_activation   durable mechanics
  -> relaylm.subjective_mem.retrieval_runtime_projection    ordinary projection
```

Neither private owner imports this facade, and neither is a second semantic
authority: this module validates every value before a private owner is asked to
act, and validates every content-free result they return.

Configuration is a requested deployment mode and a safe locator tuple only; it
never selects served authority. The allowed ordinary transition is exactly
Primary-only, then neither, then Subjective-only. There is no dual serving, no
precedence, no empty-result fallback, and no Primary fallback after the exact
finalized transfer receipt.

RT-1D-R5 retired the temporary rehearsal and shadow-characterization execution
surfaces together, so no rehearsal readiness is evaluated, minted, or recorded
here any more. The durable `rehearsal_ready` records an already-activated chain
carries stay valid and reconstructible as historical evidence: retirement never
rewrites or invalidates an accepted R3/R4 record.

Retirement itself is admitted only over an exact finalized transfer receipt and
advances `post_transfer_validated` then `retirement_complete`, forward-only and
idempotently. Subjective alone serves throughout and afterwards; the ordinary
Primary reader, its selection, and its fallback are gone from this build rather
than merely fenced, so nothing can restore Primary to the ordinary read path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from .._subjective_mem_retrieval_cutover_activation import (
    ACTIVATION_STEPS,
    CUTOVER_LOG_KEY,
    CUTOVER_LOG_KIND,
    CUTOVER_SCHEMA_VERSION,
    FORWARD_STATES,
    READER_FENCE_INDEX,
    READINESS_INDEX,
    RECEIPT_INDEX,
    RECOVERY_REQUIRED,
    WRITER_FENCE_INDEX,
    advance_cutover_chain,
    projection_generation_identity,
    reconstruct_cutover_chain,
    safe_token,
    sha256_digest,
)
from .retrieval_runtime_projection import (
    subjective_mem_retrieval_runtime_projection_spec,
    verify_subjective_mem_retrieval_runtime_projection,
)
from ..config import RelayLMConfig
from ..evidence.common import canonical_json_bytes
from ..evidence.store import EvidenceRecordStore

CUTOVER_AUTHORITY_DOMAIN = "relaylm.subjective_mem_retrieval"
CUTOVER_TRANSFERRED_SCOPE = "ordinary_memory_retrieval"

CutoverState = Literal[
    "primary_stable",
    "rehearsal_ready",
    "transfer_intent",
    "primary_reader_fenced",
    "primary_writer_fenced",
    "subjective_generation_bound",
    "subjective_reader_enabled",
    "transfer_receipt_finalized",
    "post_transfer_validated",
    "retirement_complete",
    "recovery_required",
]
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
_CUTOVER_CONFIG_PREFIX = "subjective_mem_retrieval_cutover_"
_CUTOVER_CONFIG_FIELDS = tuple(
    f"{_CUTOVER_CONFIG_PREFIX}{field}"
    for field in (
        "store_root", *_TOKEN_FIELDS, *_DIGEST_FIELDS, _PROJECTION_GENERATION_FIELD
    )
)
_PROJECTION_ROOT_FIELD = "subjective_mem_retrieval_projection_root"
_REHEARSAL_ROOT_FIELD = "subjective_mem_retrieval_rehearsal_projection_root"
# The ordered retirement steps, recorded only over an exact finalized receipt.
# They extend the activation chain and never re-enter or rewrite it.
RETIREMENT_STEPS = (("post_transfer_validated",), ("retirement_complete",))
_MISSING = object()
# Exactly which root each requested mode requires, and which it prohibits.
_MODE_ROOTS: dict[str, tuple[str | None, tuple[str, ...]]] = {
    "primary_only": (None, (_PROJECTION_ROOT_FIELD, _REHEARSAL_ROOT_FIELD)),
    "rehearsal": (_REHEARSAL_ROOT_FIELD, (_PROJECTION_ROOT_FIELD,)),
    "subjective_only": (_PROJECTION_ROOT_FIELD, (_REHEARSAL_ROOT_FIELD,)),
}


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

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

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
    """One bounded content-free description of the exact reconstructed state."""

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
        self._validate_authority()

    def _validate_counts(self) -> None:
        if (self.candidate_count, self.selected_count, self.exclusion_count) != (
            0,
            0,
            0,
        ):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_counts_invalid"
            )
        if self.probe_class not in PROBE_CLASSES:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_probe_invalid"
            )

    def _validate_authority(self) -> None:
        """Every authority flag is derived from the exact state, never asserted."""

        recovery = self.state_class == RECOVERY_REQUIRED
        index = None if recovery else _FORWARD_STATES.index(self.state_class)
        expected = (
            recovery == self.recovery_required
            and self.reader_fence == (index is not None and index >= READER_FENCE_INDEX)
            and self.writer_fence == (index is not None and index >= WRITER_FENCE_INDEX)
            and self.subjective_serving
            == (index is not None and index >= RECEIPT_INDEX)
        )
        if not expected or self.usage_finalized or not self.runtime_private_evidence_omitted:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_authority_invalid"
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

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_mode": self.requested_mode,
            "authority_class": self.authority_class,
            "state": self.state,
            "reasons": list(self.reasons),
            "diagnostics": self.diagnostics.to_dict(),
        }


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

    Exactly one authority serves each request. The reader class is derived from
    the exact reconstructed durable state and nothing else: configuration is a
    deployment request, never authority.
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
            *_FORWARD_STATES,
            RECOVERY_REQUIRED,
        ):
            raise _reader_invalid("state_invalid")
        if type(self.reader_class) is not str or self.reader_class not in AUTHORITY_CLASSES:
            raise _reader_invalid("class_invalid")
        if (
            type(self.recovery_required) is not bool
            or self.runtime_private_evidence_omitted is not True
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
    cutover tuple binds ``primary_stable`` with no store, store root, binding,
    or durable read. Every other supported mode reconstructs the exact chain.
    Anything else fails closed.
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
    mode = config.subjective_mem_retrieval_cutover_mode
    if _mode_shape_reasons(config, mode):
        return RECOVERY_REQUIRED, (f"{prefix}_config_disagreement",)
    if mode == "primary_only":
        return "primary_stable", ()
    try:
        binding = _binding_from_config(config)
        store = EvidenceRecordStore(
            config.subjective_mem_retrieval_cutover_store_root or ""
        )
    except (SubjectiveMemRetrievalCutoverError, OSError, TypeError, ValueError):
        return RECOVERY_REQUIRED, (f"{prefix}_binding_invalid",)
    state, reasons = _reconstruct(store, binding.to_dict())
    if reasons or state == RECOVERY_REQUIRED:
        return RECOVERY_REQUIRED, reasons or (f"{prefix}_state_unsupported",)
    return state, ()


def _mode_shape_reasons(config: RelayLMConfig, mode: object) -> tuple[str, ...]:
    """Prove the configured tuple and roots are exactly what this mode requires."""

    if mode not in _MODE_ROOTS:
        return ("cutover_config_mode_unsupported",)
    values = tuple(getattr(config, field) for field in _CUTOVER_CONFIG_FIELDS)
    if mode == "primary_only":
        if any(value is not None for value in values):
            return ("cutover_config_tuple_disagreement",)
    elif any(value is None for value in values):
        return ("cutover_config_tuple_disagreement",)
    required, prohibited = _MODE_ROOTS[mode]
    if required is not None:
        value = getattr(config, required, _MISSING)
        # A field the configuration schema does not carry yet cannot be
        # required of it; the later configuration commit adds the field, and
        # this requirement becomes live the moment it exists.
        if value is not _MISSING and value is None:
            return ("cutover_config_root_missing",)
    for field in prohibited:
        value = getattr(config, field, _MISSING)
        if value is not _MISSING and value is not None:
            return ("cutover_config_root_prohibited",)
    return ()


def _reconstruct(
    store: EvidenceRecordStore, binding: dict[str, object]
) -> tuple[str, tuple[str, ...]]:
    """The one durable-chain read seam this owner uses.

    Keeping the read behind a named seam is what lets the ``primary_only``
    evidence prove no store is opened and no chain is read at all.
    """

    return reconstruct_cutover_chain(store, binding)


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
    """Return the one ordinary served authority the exact decision names.

    A missing, foreign-typed, or tampered decision releases nothing: it serves
    ``neither`` rather than silently restoring Primary.
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
    reader = _reader_class(state)
    return SubjectiveMemRetrievalPrimaryReaderDecision(
        PRIMARY_READER_DECISION_SCHEMA_VERSION,
        state,  # type: ignore[arg-type]
        reader,
        state == RECOVERY_REQUIRED,
        () if reader == "primary_only" else (reasons or (_PRIMARY_READER_FENCED_REASON,)),
        True,
    )


def _decision_invalid(reason: str) -> SubjectiveMemRetrievalCutoverError:
    return SubjectiveMemRetrievalCutoverError(f"primary_writer_decision_{reason}")


def _reader_invalid(reason: str) -> SubjectiveMemRetrievalCutoverError:
    return SubjectiveMemRetrievalCutoverError(f"primary_reader_decision_{reason}")


def activate_subjective_mem_retrieval_cutover(
    *, config: object
) -> SubjectiveMemRetrievalCutoverResult:
    """The one governed production activation orchestration, forward-only.

    The order is fixed and has no shortcut. Activation is admitted only from an
    exact durable ``rehearsal_ready`` or a later supported state, so readiness
    is never minted here and configuration alone never stands in for it. While
    Primary may still serve, the exact current ordinary source and projection
    are acquired and verified against the configured binding. Only then does the
    durable chain advance, one create-or-verify transaction per step, with
    Subjective-reader enablement publishing atomically with the finalized
    transfer receipt.

    A preparation failure before transfer intent writes no cutover state at all
    and leaves Primary serving. A failure after intent leaves neither authority
    serving and recovery stays forward-only: nothing is repaired or rolled back,
    and a replay returns the same exact state without a second durable pair.
    """

    binding, state, reasons = _durable_binding(
        config, "subjective_only", "cutover_activation"
    )
    if binding is None:
        return _result("subjective_only", state, reasons)
    assert isinstance(config, RelayLMConfig)
    index = _FORWARD_STATES.index(state)
    if index >= RECEIPT_INDEX:
        return _result("subjective_only", state, ())
    if index < READINESS_INDEX:
        return _result(
            "subjective_only", state, ("cutover_activation_readiness_required",)
        )
    reasons = _activation_projection_reasons(config, binding)
    if reasons:
        return _result("subjective_only", state, reasons)
    store = EvidenceRecordStore(
        config.subjective_mem_retrieval_cutover_store_root or ""
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


def retire_subjective_mem_retrieval_cutover(
    *, config: object
) -> SubjectiveMemRetrievalCutoverResult:
    """Advance the exact durable chain through immediate Primary retirement.

    Retirement is not a second authority transfer: RT-1D-R4 already owns the
    only one. It is admitted only over an exact finalized transfer receipt, so
    a chain that has not reached ``transfer_receipt_finalized`` is refused
    rather than advanced, and configuration alone never stands in for the
    receipt.

    Subjective alone serves throughout. The ordinary Primary reader, its
    selection, and the shadow characterization/rehearsal execution surfaces are
    already gone from this build, so retirement records that fact durably
    rather than performing it: ``post_transfer_validated`` then
    ``retirement_complete``, one create-or-verify transaction per step.

    The write is idempotent and forward-only. A replay over an already-retired
    chain returns the same exact state without a second durable record, a
    partial or divergent chain fails closed as ``recovery_required``, and
    nothing restores Primary.
    """

    binding, state, reasons = _durable_binding(
        config, "subjective_only", "cutover_retirement"
    )
    if binding is None:
        return _result("subjective_only", state, reasons)
    assert isinstance(config, RelayLMConfig)
    if _FORWARD_STATES.index(state) < RECEIPT_INDEX:
        return _result(
            "subjective_only", state, ("cutover_retirement_receipt_required",)
        )
    store = EvidenceRecordStore(
        config.subjective_mem_retrieval_cutover_store_root or ""
    )
    for step in RETIREMENT_STEPS:
        if _FORWARD_STATES.index(state) >= _FORWARD_STATES.index(step[-1]):
            continue
        state, reasons = advance_cutover_chain(store, binding.to_dict(), step)
        if reasons or state == RECOVERY_REQUIRED:
            return _result(
                "subjective_only",
                RECOVERY_REQUIRED,
                reasons or ("cutover_retirement_failed",),
            )
    return _result("subjective_only", state, ())


def _durable_binding(
    config: object, mode: str, prefix: str
) -> tuple[SubjectiveMemRetrievalCutoverBinding | None, str, tuple[str, ...]]:
    """Admit only an exact tuple for this mode over a supported durable state."""

    requested = getattr(config, "subjective_mem_retrieval_cutover_mode", None)
    if type(config) is not RelayLMConfig or requested != mode:
        return None, "primary_stable", (f"{prefix}_mode_unsupported",)
    state, reasons = _state_from_config(config, prefix=prefix)
    if reasons or state == RECOVERY_REQUIRED:
        return None, RECOVERY_REQUIRED, reasons or (f"{prefix}_state_unsupported",)
    try:
        return _binding_from_config(config), state, ()
    except (SubjectiveMemRetrievalCutoverError, TypeError):
        return None, RECOVERY_REQUIRED, (f"{prefix}_binding_invalid",)


def _activation_projection_reasons(
    config: RelayLMConfig, binding: SubjectiveMemRetrievalCutoverBinding
) -> tuple[str, ...]:
    """Prove the exact current ordinary source and projection before any intent.

    The acquisition installs or exact-verifies the live bundle here, while
    Primary may still serve, so a drifted or unreachable source blocks the
    transfer instead of stranding it after intent.
    """

    characters = sorted(getattr(config, "characters", ()) or ())
    if len(characters) != 1:
        return ("cutover_activation_character_scope_ambiguous",)
    spec, store, reasons = subjective_mem_retrieval_runtime_projection_spec(
        evidence_root=getattr(config, "evidence_data_root", None),
        workspace_root=getattr(config, "subjective_mem_workspace_root", None),
        projection_root=getattr(config, _PROJECTION_ROOT_FIELD, None),
        evidence_space_id=binding.evidence_space_id,
        character_id=characters[0],
    )
    if spec is None or store is None:
        return reasons or ("cutover_activation_projection_unsupported",)
    acquired, reasons = verify_subjective_mem_retrieval_runtime_projection(
        store=store,
        spec=spec,
        expected_generation_id=binding.projection_generation_id,
        expected_source_digest=binding.projection_source_digest,
    )
    if acquired is None:
        return reasons or ("cutover_activation_projection_disagreement",)
    manifest = acquired.projection.manifest
    if (
        manifest.projection_generation_id != binding.projection_generation_id
        or manifest.source_snapshot_digest != binding.projection_source_digest
        or not acquired.projection.rows
    ):
        return ("cutover_activation_projection_disagreement",)
    return ()


def subjective_mem_retrieval_ordinary_token_budget(config: RelayLMConfig) -> int:
    """The one bounded ordinary Subjective token budget this deployment requests."""

    budget = config.memory.token_budget
    if not isinstance(budget, int) or budget <= 0:
        budget = config.memory.token_budget_hint
    return budget if isinstance(budget, int) and budget > 0 else 1


def _validate_inputs(store: object, binding: object, request: object) -> None:
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
    "activate_subjective_mem_retrieval_cutover",
    "primary_writer_decision_permits_write",
    "resolve_subjective_mem_retrieval_primary_reader_decision",
    "resolve_subjective_mem_retrieval_primary_writer_decision",
    "retire_subjective_mem_retrieval_cutover",
    "subjective_mem_retrieval_cutover_binding_from_config",
    "subjective_mem_retrieval_ordinary_token_budget",
    "subjective_mem_retrieval_primary_reader_class",
]
