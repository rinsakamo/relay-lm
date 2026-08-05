"""Private RT-1D-R4 durable cutover activation mechanics.

Accepted by ``docs/architecture/subjective-mem-retrieval-projection-hard-
cutover.md``: own only the durable mechanics of the one authority transfer —
the state list, the durable record schema, exact predecessor binding, chain
reconstruction and validation, create-or-verify forward advancement, and the
one atomic publication of Subjective-reader enablement together with the
finalized transfer receipt.

This owner is not a semantic authority. It evaluates no configuration, no
requested mode, no reader or writer decision, no readiness proof, and no
public result; ``relaylm.subjective_mem_retrieval_cutover`` alone owns those
and hands this module one already validated binding. The dependency direction
is one-way — the cutover facade imports this module, and this module imports
only ``EvidenceRecordStore`` and the canonical content-free digest helpers. It
never imports the facade, the configuration owner, request-path owners,
selection, the usage ledger, Primary owners, or RelayCTX.

Durability is the existing ``EvidenceRecordStore`` per-evidence-space
transaction with its create-or-verify and prepared-transaction recovery
semantics. No second lock, durable root, transaction journal, or recovery
model is introduced, and a divergent chain is never repaired or overwritten:
recovery after transfer intent is forward-only.
"""
from __future__ import annotations

from typing import Literal

from .evidence_common import canonical_digest
from .evidence_store import EvidenceRecordStore

CUTOVER_SCHEMA_VERSION = 1
CUTOVER_LOG_KIND = "subjective_mem_retrieval_cutover"
CUTOVER_LOG_KEY = "authority_chain"
CUTOVER_TRANSACTION_PREFIX = "smretrievalcutovertx_"
PROJECTION_GENERATION_PREFIX = "smretrievalgen_"

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
RECOVERY_REQUIRED = "recovery_required"

FORWARD_STATES = (
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
RECORD_FIELDS = (
    "schema_version",
    "state",
    "predecessor_state",
    "predecessor_digest",
    "binding",
    "binding_digest",
    "record_digest",
)

READER_FENCE_INDEX = FORWARD_STATES.index("primary_reader_fenced")
WRITER_FENCE_INDEX = FORWARD_STATES.index("primary_writer_fenced")
READER_ENABLED_INDEX = FORWARD_STATES.index("subjective_reader_enabled")
RECEIPT_INDEX = FORWARD_STATES.index("transfer_receipt_finalized")

# Every step is one durable transaction. The Subjective reader is enabled only
# together with the finalized transfer receipt, so no externally reconstructible
# chain can ever end at ``subjective_reader_enabled``.
ACTIVATION_STEPS: tuple[tuple[str, ...], ...] = (
    ("rehearsal_ready",),
    ("transfer_intent",),
    ("primary_reader_fenced",),
    ("primary_writer_fenced",),
    ("subjective_generation_bound",),
    ("subjective_reader_enabled", "transfer_receipt_finalized"),
)


def reconstruct_cutover_chain(
    store: EvidenceRecordStore, binding_body: dict[str, object]
) -> tuple[str, tuple[str, ...]]:
    """Reconstruct the exact durable state of one cutover authority chain."""

    space = binding_body.get("evidence_space_id")
    if type(store) is not EvidenceRecordStore or type(space) is not str:
        return RECOVERY_REQUIRED, ("cutover_store_invalid",)
    try:
        with store.transaction(space) as transaction:
            inventory = transaction.list_logs(log_kind=CUTOVER_LOG_KIND, limit=2)
    except (OSError, RuntimeError, ValueError):
        return RECOVERY_REQUIRED, ("cutover_store_read_failed",)
    return chain_state(inventory, binding_body)


def chain_state(
    inventory: tuple[tuple[str, list[dict]], ...], binding_body: dict[str, object]
) -> tuple[str, tuple[str, ...]]:
    """Classify one bounded log inventory as exactly one reconstructed state."""

    if not inventory:
        return "primary_stable", ()
    if len(inventory) != 1 or inventory[0][0] != CUTOVER_LOG_KEY:
        return RECOVERY_REQUIRED, ("cutover_multiple_chains",)
    return validate_chain(inventory[0][1], binding_body)


def validate_chain(
    records: object, binding_body: dict[str, object]
) -> tuple[str, tuple[str, ...]]:
    """Validate the complete predecessor-linked chain and return its last state.

    A chain that ends at ``subjective_reader_enabled`` is refused: the reader
    enablement and the finalized transfer receipt publish in one transaction, so
    that state is never a legitimate reconstructible end.
    """

    if type(records) is not list or not records or len(records) > len(FORWARD_STATES):
        return RECOVERY_REQUIRED, ("cutover_chain_length_invalid",)
    binding_digest = canonical_digest(binding_body)
    previous_digest: str | None = None
    seen: set[str] = set()
    for index, record in enumerate(records):
        reason = validate_record(
            record, index, binding_body, binding_digest, previous_digest, seen
        )
        if reason:
            return RECOVERY_REQUIRED, (reason,)
        previous_digest = record["record_digest"]
        seen.add(record["state"])
    state = records[-1]["state"]
    if state == "subjective_reader_enabled":
        return RECOVERY_REQUIRED, ("cutover_activation_pair_incomplete",)
    return state, ()


def validate_record(
    record: object,
    index: int,
    binding_body: dict[str, object],
    binding_digest: str,
    previous_digest: str | None,
    seen: set[str],
) -> str | None:
    """Prove one durable record is the exact successor of its predecessor."""

    if type(record) is not dict or tuple(sorted(record)) != tuple(sorted(RECORD_FIELDS)):
        return "cutover_record_schema_invalid"
    state = record.get("state")
    if record.get("schema_version") != CUTOVER_SCHEMA_VERSION:
        return "cutover_record_schema_unsupported"
    if state != FORWARD_STATES[index] or state in seen:
        return "cutover_record_predecessor_invalid"
    expected_predecessor = None if index == 0 else FORWARD_STATES[index - 1]
    if (
        record.get("predecessor_state") != expected_predecessor
        or record.get("predecessor_digest") != previous_digest
    ):
        return "cutover_record_predecessor_invalid"
    if (
        record.get("binding") != binding_body
        or record.get("binding_digest") != binding_digest
    ):
        return "cutover_record_binding_mismatch"
    unsigned = {field: record[field] for field in RECORD_FIELDS if field != "record_digest"}
    if record.get("record_digest") != canonical_digest(unsigned):
        return "cutover_record_digest_invalid"
    return None


def build_record(
    *,
    state: str,
    predecessor_state: str | None,
    predecessor_digest: str | None,
    binding_body: dict[str, object],
    binding_digest: str,
) -> dict[str, object]:
    """Build one durable record bound to its exact predecessor and binding.

    The ``transfer_receipt_finalized`` record is the finalized transfer receipt
    itself: its ``record_digest`` binds the complete predecessor chain — durable
    intent, both Primary fences, and the exact Subjective generation binding —
    together with the whole content-free binding, so it authorizes only the
    exact generation and source state finalized at activation.
    """

    record = {
        "schema_version": CUTOVER_SCHEMA_VERSION,
        "state": state,
        "predecessor_state": predecessor_state,
        "predecessor_digest": predecessor_digest,
        "binding": binding_body,
        "binding_digest": binding_digest,
    }
    return {**record, "record_digest": canonical_digest(record)}


def extend_chain(
    records: list[dict], step: tuple[str, ...], binding_body: dict[str, object]
) -> list[dict]:
    """Append one step's records to an already validated chain."""

    binding_digest = canonical_digest(binding_body)
    extended = list(records)
    for state in step:
        previous = extended[-1] if extended else None
        extended.append(
            build_record(
                state=state,
                predecessor_state=previous["state"] if previous else None,
                predecessor_digest=previous["record_digest"] if previous else None,
                binding_body=binding_body,
                binding_digest=binding_digest,
            )
        )
    return extended


def advance_cutover_chain(
    store: EvidenceRecordStore,
    binding_body: dict[str, object],
    step: tuple[str, ...],
) -> tuple[str, tuple[str, ...]]:
    """Create-or-verify exactly one forward step under one evidence-space lock.

    The whole chain is rewritten as one atomic log write, so a two-state step
    can never be observed half-applied. Replaying an already applied step is a
    deterministic no-op that returns the same reconstructed state, and a chain
    that already advanced past this step is left untouched.
    """

    space = binding_body.get("evidence_space_id")
    if type(store) is not EvidenceRecordStore or type(space) is not str:
        return RECOVERY_REQUIRED, ("cutover_store_invalid",)
    if step not in ACTIVATION_STEPS:
        return RECOVERY_REQUIRED, ("cutover_activation_step_unsupported",)
    try:
        with store.transaction(space) as transaction:
            inventory = transaction.list_logs(log_kind=CUTOVER_LOG_KIND, limit=2)
            state, reasons = chain_state(inventory, binding_body)
            if reasons or state == RECOVERY_REQUIRED:
                return RECOVERY_REQUIRED, reasons or ("cutover_state_unsupported",)
            if FORWARD_STATES.index(state) >= FORWARD_STATES.index(step[-1]):
                return state, ()
            if FORWARD_STATES.index(state) + 1 != FORWARD_STATES.index(step[0]):
                return RECOVERY_REQUIRED, ("cutover_activation_step_out_of_order",)
            records = list(inventory[0][1]) if inventory else []
            planned = _planned_chain(records, step, binding_body)
            result = transaction.commit(
                transaction_id=_transaction_id(planned),
                records=(),
                logs=((CUTOVER_LOG_KIND, CUTOVER_LOG_KEY, tuple(planned)),),
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return RECOVERY_REQUIRED, ("cutover_store_write_failed",)
    if result.status == "collision":
        return RECOVERY_REQUIRED, result.reasons or ("cutover_activation_conflict",)
    if result.status not in {"created", "duplicate_existing"}:
        return RECOVERY_REQUIRED, result.reasons or ("cutover_activation_failed",)
    return planned[-1]["state"], ()


def _planned_chain(
    records: list[dict], step: tuple[str, ...], binding_body: dict[str, object]
) -> list[dict]:
    """Return the exact chain this step publishes.

    An absent chain reconstructs as ``primary_stable``, so the first step also
    publishes the states the chain has never recorded.
    """

    opening = FORWARD_STATES.index(step[0])
    return extend_chain(
        records, FORWARD_STATES[len(records) : opening] + step, binding_body
    )


def _transaction_id(records: list[dict]) -> str:
    """One stable content-free transaction identity for this exact chain."""

    return CUTOVER_TRANSACTION_PREFIX + canonical_digest(
        {
            "schema": CUTOVER_LOG_KIND,
            "record_digests": [record["record_digest"] for record in records],
        }
    )


def safe_token(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 128
        and all(character.isalnum() or character in "._-" for character in value)
    )


def sha256_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def projection_generation_identity(value: object) -> bool:
    return (
        type(value) is str
        and value.startswith(PROJECTION_GENERATION_PREFIX)
        and sha256_digest(value[len(PROJECTION_GENERATION_PREFIX) :])
    )


__all__ = [
    "ACTIVATION_STEPS",
    "CUTOVER_LOG_KEY",
    "CUTOVER_LOG_KIND",
    "CUTOVER_SCHEMA_VERSION",
    "FORWARD_STATES",
    "READER_ENABLED_INDEX",
    "READER_FENCE_INDEX",
    "RECEIPT_INDEX",
    "RECORD_FIELDS",
    "RECOVERY_REQUIRED",
    "WRITER_FENCE_INDEX",
    "advance_cutover_chain",
    "build_record",
    "chain_state",
    "extend_chain",
    "projection_generation_identity",
    "reconstruct_cutover_chain",
    "safe_token",
    "sha256_digest",
    "validate_chain",
    "validate_record",
]
