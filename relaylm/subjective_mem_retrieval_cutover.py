"""Content-free RT-1D cutover validation and read-only rehearsal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from .config import RelayLMConfig
from .evidence_common import canonical_digest, canonical_json_bytes
from .evidence_store import EvidenceRecordStore

CUTOVER_SCHEMA_VERSION = 1
CUTOVER_AUTHORITY_DOMAIN = "relaylm.subjective_mem_retrieval"
CUTOVER_TRANSFERRED_SCOPE = "ordinary_memory_retrieval"
CUTOVER_LOG_KIND = "subjective_mem_retrieval_cutover"
CUTOVER_LOG_KEY = "authority_chain"

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
RequestedMode = Literal["primary_only", "rehearsal"]
PrimaryWriterClass = Literal["permitted", "rejected"]
PRIMARY_WRITER_DECISION_SCHEMA_VERSION = 1
PRIMARY_WRITER_PERMITTED = "permitted"
PRIMARY_WRITER_REJECTED = "rejected"
_FORWARD_STATES = (
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
)
_TOKEN_FIELDS = (
    "evidence_space_id",
    "deployment_id",
    "scope_id",
    "policy_revision_id",
    "readiness_id",
)
_DIGEST_FIELDS = (
    "bootstrap_main_sha",
    "resulting_main_sha",
    "projection_generation_id",
    "projection_source_digest",
)
_BINDING_FIELDS = (
    "schema_version",
    "authority_domain",
    "transferred_scope",
    *_TOKEN_FIELDS,
    *_DIGEST_FIELDS,
)
_RECORD_FIELDS = (
    "schema_version",
    "state",
    "predecessor_state",
    "predecessor_digest",
    "binding",
    "binding_digest",
    "record_digest",
)
# Writes stay permitted only strictly before `primary_writer_fenced`.
_WRITER_FENCE_INDEX = _FORWARD_STATES.index("primary_writer_fenced")
_PRIMARY_WRITER_PERMITTED_STATES = _FORWARD_STATES[:_WRITER_FENCE_INDEX]
_PRIMARY_WRITER_FENCED_REASON = "cutover_primary_writer_fenced"
_MAX_PRIMARY_WRITER_REASONS = 8
_CUTOVER_CONFIG_PREFIX = "subjective_mem_retrieval_cutover_"
_CUTOVER_CONFIG_FIELDS = tuple(
    f"{_CUTOVER_CONFIG_PREFIX}{field}"
    for field in ("store_root", *_TOKEN_FIELDS, *_DIGEST_FIELDS)
)


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
        if not all(_safe_token(getattr(self, field)) for field in _TOKEN_FIELDS):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_binding_identifier_invalid"
            )
        if not all(_sha256(getattr(self, field)) for field in _DIGEST_FIELDS):
            raise SubjectiveMemRetrievalCutoverError("cutover_binding_digest_invalid")

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
        if self.requested_mode not in {"primary_only", "rehearsal"}:
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_requested_mode_unsupported"
            )


@dataclass(frozen=True)
class SubjectiveMemRetrievalCutoverDiagnostics:
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
        if self.state_class not in {*_FORWARD_STATES, "recovery_required"}:
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
        if (self.candidate_count, self.selected_count, self.exclusion_count) != (
            0,
            0,
            0,
        ):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_counts_invalid"
            )
        if self.probe_class != "not_applicable":
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_probe_invalid"
            )
        if (
            any(
                (
                    self.usage_finalized,
                    self.reader_fence,
                    self.writer_fence,
                    self.subjective_serving,
                )
            )
            or not self.runtime_private_evidence_omitted
        ):
            raise SubjectiveMemRetrievalCutoverError(
                "cutover_diagnostics_r1_authority_invalid"
            )

    def to_dict(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in self.__dataclass_fields__}


@dataclass(frozen=True)
class SubjectiveMemRetrievalCutoverResult:
    requested_mode: RequestedMode
    authority_class: Literal["primary_only", "neither"]
    state: CutoverState
    reasons: tuple[str, ...]
    diagnostics: SubjectiveMemRetrievalCutoverDiagnostics

    def __post_init__(self) -> None:
        if self.requested_mode not in {"primary_only", "rehearsal"}:
            raise SubjectiveMemRetrievalCutoverError("cutover_result_mode_invalid")
        if self.authority_class not in {"primary_only", "neither"}:
            raise SubjectiveMemRetrievalCutoverError("cutover_result_authority_invalid")
        if type(self.reasons) is not tuple or not all(
            _safe_token(reason) for reason in self.reasons
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
        if type(state) is not str or state not in (*_FORWARD_STATES, "recovery_required"):
            raise _decision_invalid("state_invalid")
        if type(writer_class) is not str or writer_class not in (PRIMARY_WRITER_PERMITTED, PRIMARY_WRITER_REJECTED):
            raise _decision_invalid("class_invalid")
        if type(recovery_required) is not bool or omitted is not True:
            raise _decision_invalid("boolean_invalid")
        if (
            type(reasons) is not tuple
            or len(reasons) > _MAX_PRIMARY_WRITER_REASONS
            or not all(_safe_token(reason) for reason in reasons)
        ):
            raise _decision_invalid("reasons_invalid")
        if recovery_required != (state == "recovery_required"):
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


def resolve_subjective_mem_retrieval_primary_writer_decision(
    config: RelayLMConfig,
) -> SubjectiveMemRetrievalPrimaryWriterDecision:
    """Resolve the one Primary writer decision this module alone owns.

    ``primary_only`` is explicit mode-derived authority: the complete empty
    cutover tuple binds ``primary_stable`` with no store, store root,
    binding, or durable read. ``rehearsal`` reconstructs the exact chain
    through the existing validation. Anything else fails closed.
    """
    if type(config) is not RelayLMConfig:
        return _writer_decision("recovery_required", ("cutover_writer_config_invalid",))
    values = tuple(getattr(config, field) for field in _CUTOVER_CONFIG_FIELDS)
    disagreement = ("cutover_writer_config_disagreement",)
    mode = config.subjective_mem_retrieval_cutover_mode
    if mode == "primary_only":
        if any(value is not None for value in values):
            return _writer_decision("recovery_required", disagreement)
        return _writer_decision("primary_stable", ())
    if mode != "rehearsal" or any(value is None for value in values):
        return _writer_decision("recovery_required", disagreement)
    try:
        binding = SubjectiveMemRetrievalCutoverBinding(
            schema_version=CUTOVER_SCHEMA_VERSION,
            authority_domain=CUTOVER_AUTHORITY_DOMAIN,
            transferred_scope=CUTOVER_TRANSFERRED_SCOPE,
            **{
                field: getattr(config, f"{_CUTOVER_CONFIG_PREFIX}{field}")
                for field in (*_TOKEN_FIELDS, *_DIGEST_FIELDS)
            },
        )
        store = EvidenceRecordStore(
            config.subjective_mem_retrieval_cutover_store_root or ""
        )
    except (SubjectiveMemRetrievalCutoverError, OSError, TypeError, ValueError):
        return _writer_decision("recovery_required", ("cutover_writer_binding_invalid",))
    state, reasons = _reconstruct(store, binding)
    if reasons or state == "recovery_required":
        unsupported = ("cutover_writer_state_unsupported",)
        return _writer_decision("recovery_required", reasons or unsupported)
    return _writer_decision(state, ())


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


def _writer_decision(
    state: CutoverState, reasons: tuple[str, ...]
) -> SubjectiveMemRetrievalPrimaryWriterDecision:
    recovery = state == "recovery_required"
    permitted = state in _PRIMARY_WRITER_PERMITTED_STATES and not recovery
    return SubjectiveMemRetrievalPrimaryWriterDecision(
        PRIMARY_WRITER_DECISION_SCHEMA_VERSION,
        state,
        PRIMARY_WRITER_PERMITTED if permitted else PRIMARY_WRITER_REJECTED,
        recovery,
        () if permitted else (reasons or (_PRIMARY_WRITER_FENCED_REASON,)),
        True,
    )


def _decision_invalid(reason: str) -> SubjectiveMemRetrievalCutoverError:
    return SubjectiveMemRetrievalCutoverError(f"primary_writer_decision_{reason}")


def rehearse_subjective_mem_retrieval_cutover(
    *,
    store: EvidenceRecordStore,
    binding: SubjectiveMemRetrievalCutoverBinding,
    request: SubjectiveMemRetrievalCutoverRequest,
) -> SubjectiveMemRetrievalCutoverResult:
    """Reconstruct and validate only; never commit or authorize Subjective serving."""
    if type(store) is not EvidenceRecordStore:
        raise SubjectiveMemRetrievalCutoverError("cutover_store_invalid")
    if type(binding) is not SubjectiveMemRetrievalCutoverBinding:
        raise SubjectiveMemRetrievalCutoverError("cutover_binding_invalid")
    if type(request) is not SubjectiveMemRetrievalCutoverRequest:
        raise SubjectiveMemRetrievalCutoverError("cutover_request_invalid")
    state, reasons = _reconstruct(store, binding)
    if state not in {"primary_stable", "rehearsal_ready"} or reasons:
        return _result(
            request.requested_mode,
            "recovery_required",
            reasons or ("cutover_state_not_r1_supported",),
        )
    if request.requested_mode == "rehearsal":
        return _result("rehearsal", "rehearsal_ready", ())
    return _result("primary_only", state, ())


def _reconstruct(
    store: EvidenceRecordStore, binding: SubjectiveMemRetrievalCutoverBinding
) -> tuple[CutoverState, tuple[str, ...]]:
    try:
        with store.transaction(binding.evidence_space_id) as transaction:
            inventory = transaction.list_logs(log_kind=CUTOVER_LOG_KIND, limit=2)
    except (OSError, RuntimeError, ValueError):
        return "recovery_required", ("cutover_store_read_failed",)
    if not inventory:
        return "primary_stable", ()
    if len(inventory) != 1 or inventory[0][0] != CUTOVER_LOG_KEY:
        return "recovery_required", ("cutover_multiple_chains",)
    return _validate_chain(inventory[0][1], binding)


def _validate_chain(
    records: list[dict], binding: SubjectiveMemRetrievalCutoverBinding
) -> tuple[CutoverState, tuple[str, ...]]:
    if not records or len(records) > len(_FORWARD_STATES):
        return "recovery_required", ("cutover_chain_length_invalid",)
    expected_binding = binding.to_dict()
    expected_binding_digest = canonical_digest(expected_binding)
    previous_digest: str | None = None
    seen: set[str] = set()
    for index, record in enumerate(records):
        reason = _validate_record(
            record,
            index,
            expected_binding,
            expected_binding_digest,
            previous_digest,
            seen,
        )
        if reason:
            return "recovery_required", (reason,)
        previous_digest = record["record_digest"]
        seen.add(record["state"])
    return records[-1]["state"], ()


def _validate_record(
    record: object,
    index: int,
    binding: dict[str, object],
    binding_digest: str,
    previous_digest: str | None,
    seen: set[str],
) -> str | None:
    if type(record) is not dict or tuple(sorted(record)) != tuple(
        sorted(_RECORD_FIELDS)
    ):
        return "cutover_record_schema_invalid"
    state = record.get("state")
    if record.get("schema_version") != CUTOVER_SCHEMA_VERSION:
        return "cutover_record_schema_unsupported"
    if state != _FORWARD_STATES[index] or state in seen:
        return "cutover_record_predecessor_invalid"
    expected_predecessor = None if index == 0 else _FORWARD_STATES[index - 1]
    if (
        record.get("predecessor_state") != expected_predecessor
        or record.get("predecessor_digest") != previous_digest
    ):
        return "cutover_record_predecessor_invalid"
    if (
        record.get("binding") != binding
        or record.get("binding_digest") != binding_digest
    ):
        return "cutover_record_binding_mismatch"
    unsigned = {
        field: record[field] for field in _RECORD_FIELDS if field != "record_digest"
    }
    if record.get("record_digest") != canonical_digest(unsigned):
        return "cutover_record_digest_invalid"
    return None


def _result(
    mode: RequestedMode, state: CutoverState, reasons: tuple[str, ...]
) -> SubjectiveMemRetrievalCutoverResult:
    recovery = state == "recovery_required"
    diagnostics = SubjectiveMemRetrievalCutoverDiagnostics(
        state,
        state == "rehearsal_ready",
        0,
        0,
        0,
        False,
        False,
        False,
        "not_applicable",
        recovery,
        False,
    )
    return SubjectiveMemRetrievalCutoverResult(
        mode, "neither" if recovery else "primary_only", state, reasons, diagnostics
    )


def _safe_token(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and all(character.isalnum() or character in "._-" for character in value)
    )


def _sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


__all__ = [
    "CUTOVER_AUTHORITY_DOMAIN",
    "CUTOVER_LOG_KEY",
    "CUTOVER_LOG_KIND",
    "CUTOVER_SCHEMA_VERSION",
    "CUTOVER_TRANSFERRED_SCOPE",
    "PRIMARY_WRITER_DECISION_SCHEMA_VERSION",
    "PRIMARY_WRITER_PERMITTED",
    "PRIMARY_WRITER_REJECTED",
    "SubjectiveMemRetrievalCutoverBinding",
    "SubjectiveMemRetrievalCutoverDiagnostics",
    "SubjectiveMemRetrievalCutoverError",
    "SubjectiveMemRetrievalCutoverRequest",
    "SubjectiveMemRetrievalCutoverResult",
    "SubjectiveMemRetrievalPrimaryWriterDecision",
    "primary_writer_decision_permits_write",
    "rehearse_subjective_mem_retrieval_cutover",
    "resolve_subjective_mem_retrieval_primary_writer_decision",
]
