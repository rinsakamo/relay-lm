"""Private RT-1D-R4 durable cutover mechanics.

This module owns only the durable authority chain: the ordered state list, the
durable record schema, chain reconstruction and validation, exact record and
predecessor binding, the content-free identity predicates, and create-or-verify
forward advancement. It owns no cutover semantics, configuration, request
schema, serving decision, selection, usage rule, or ordinary route behaviour.

The dependency direction is one-way. The public cutover facade
``relaylm.subjective_mem_retrieval_cutover`` depends on this module; this module
depends only on ``EvidenceRecordStore`` and the canonical content-free digest
helper. It must never import the facade, the configuration owner, request-path
owners, selection, the usage ledger, Primary owners, RelayCTX, the rehearsal
coordinator, or the characterization owner, and it is not a second semantic
authority: every value it accepts is already validated by the facade.

Forward advancement is create-or-verify and idempotent. Each authorized step is
one durable transaction, except that ``subjective_reader_enabled`` and
``transfer_receipt_finalized`` publish in a single atomic log write, so no
reconstructible chain can end at the first of that pair. A chain that does end
there is ``recovery_required``. Nothing is ever repaired, overwritten, or rolled
back: a divergent chain fails closed and recovery stays forward-only.
"""

from __future__ import annotations

from .evidence.common import canonical_digest
from .evidence.store import EvidenceRecordStore

CUTOVER_SCHEMA_VERSION = 1
CUTOVER_LOG_KIND = "subjective_mem_retrieval_cutover"
CUTOVER_LOG_KEY = "authority_chain"
RECOVERY_REQUIRED = "recovery_required"
TRANSACTION_PREFIX = "smretrievalcutover."

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

READINESS_INDEX = FORWARD_STATES.index("rehearsal_ready")
READER_FENCE_INDEX = FORWARD_STATES.index("primary_reader_fenced")
WRITER_FENCE_INDEX = FORWARD_STATES.index("primary_writer_fenced")
RECEIPT_INDEX = FORWARD_STATES.index("transfer_receipt_finalized")

# `primary_stable` is the chain's genesis record, not an authority transition:
# an absent log and a chain holding only that record are the same exact state.
# It is written as its own step so every later record stays predecessor-bound.
GENESIS_STEP = ("primary_stable",)

# The durable prefix a `rehearsal` deployment may record, and nothing later.
READINESS_STEPS = (GENESIS_STEP, ("rehearsal_ready",))

# The ordered `subjective_only` steps. The final pair publishes atomically, so
# Subjective reader enablement and the finalized transfer receipt are one
# authority transition rather than two observable ones.
ACTIVATION_STEPS = READINESS_STEPS + (
    ("transfer_intent",),
    ("primary_reader_fenced",),
    ("primary_writer_fenced",),
    ("subjective_generation_bound",),
    ("subjective_reader_enabled", "transfer_receipt_finalized"),
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
_GENERATION_PREFIX = "smretrievalgen_"


def reconstruct_cutover_chain(
    store: object, binding: object
) -> tuple[str, tuple[str, ...]]:
    """Read and validate the one durable chain this exact binding names."""

    if type(store) is not EvidenceRecordStore or type(binding) is not dict:
        return RECOVERY_REQUIRED, ("cutover_chain_input_invalid",)
    space = binding.get("evidence_space_id")
    if type(space) is not str or not space:
        return RECOVERY_REQUIRED, ("cutover_chain_input_invalid",)
    try:
        with store.transaction(space) as transaction:
            inventory = transaction.list_logs(log_kind=CUTOVER_LOG_KIND, limit=2)
    except (OSError, RuntimeError, ValueError):
        return RECOVERY_REQUIRED, ("cutover_store_read_failed",)
    return chain_state(inventory, binding)


def chain_state(inventory: object, binding: dict) -> tuple[str, tuple[str, ...]]:
    """Classify one bounded log inventory as an exact chain state."""

    if not inventory:
        return "primary_stable", ()
    if len(inventory) != 1 or inventory[0][0] != CUTOVER_LOG_KEY:
        return RECOVERY_REQUIRED, ("cutover_multiple_chains",)
    return validate_chain(inventory[0][1], binding)


def validate_chain(records: object, binding: dict) -> tuple[str, tuple[str, ...]]:
    """Prove every record is exact, ordered, predecessor-bound, and unique."""

    if type(records) is not list or not records or len(records) > len(FORWARD_STATES):
        return RECOVERY_REQUIRED, ("cutover_chain_length_invalid",)
    binding_digest = canonical_digest(binding)
    previous_digest: str | None = None
    seen: set[str] = set()
    for index, record in enumerate(records):
        reason = validate_record(
            record, index, binding, binding_digest, previous_digest, seen
        )
        if reason:
            return RECOVERY_REQUIRED, (reason,)
        previous_digest = record["record_digest"]
        seen.add(record["state"])
    final = records[-1]["state"]
    if final == "subjective_reader_enabled":
        # The atomic pair can never be observed half-published.
        return RECOVERY_REQUIRED, ("cutover_activation_pair_incomplete",)
    return final, ()


def validate_record(
    record: object,
    index: int,
    binding: dict,
    binding_digest: str,
    previous_digest: str | None,
    seen: set,
) -> str | None:
    """Return the one content-free reason this record is not exact, or None."""

    if type(record) is not dict or tuple(sorted(record)) != tuple(
        sorted(_RECORD_FIELDS)
    ):
        return "cutover_record_schema_invalid"
    if record.get("schema_version") != CUTOVER_SCHEMA_VERSION:
        return "cutover_record_schema_unsupported"
    state = record.get("state")
    if index >= len(FORWARD_STATES) or state != FORWARD_STATES[index] or state in seen:
        return "cutover_record_predecessor_invalid"
    expected_predecessor = None if index == 0 else FORWARD_STATES[index - 1]
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


def build_record(
    state: str,
    index: int,
    binding: dict,
    binding_digest: str,
    previous_digest: str | None,
) -> dict:
    """Derive one exact predecessor-bound durable record."""

    unsigned = {
        "schema_version": CUTOVER_SCHEMA_VERSION,
        "state": state,
        "predecessor_state": None if index == 0 else FORWARD_STATES[index - 1],
        "predecessor_digest": previous_digest,
        "binding": binding,
        "binding_digest": binding_digest,
    }
    return {**unsigned, "record_digest": canonical_digest(unsigned)}


def extend_chain(records: list, binding: dict, step: tuple[str, ...]) -> list | None:
    """Append exactly one authorized step, or None when it is not next."""

    binding_digest = canonical_digest(binding)
    extended = list(records)
    previous_digest = extended[-1]["record_digest"] if extended else None
    for state in step:
        index = len(extended)
        if index >= len(FORWARD_STATES) or FORWARD_STATES[index] != state:
            return None
        record = build_record(state, index, binding, binding_digest, previous_digest)
        extended.append(record)
        previous_digest = record["record_digest"]
    return extended


def advance_cutover_chain(
    store: object, binding: object, step: tuple[str, ...]
) -> tuple[str, tuple[str, ...]]:
    """Create-or-verify exactly one authorized step under one held lock.

    A replay of an already-recorded step is a deterministic no-op that returns
    the same exact state without a second durable write. A chain that has moved
    beyond the step is left untouched. Anything divergent fails closed.
    """

    if type(store) is not EvidenceRecordStore or type(binding) is not dict:
        return RECOVERY_REQUIRED, ("cutover_chain_input_invalid",)
    space = binding.get("evidence_space_id")
    if type(space) is not str or not space or not step:
        return RECOVERY_REQUIRED, ("cutover_chain_input_invalid",)
    try:
        with store.transaction(space) as transaction:
            return _advance_locked(transaction, binding, step)
    except (OSError, RuntimeError, ValueError):
        return RECOVERY_REQUIRED, ("cutover_store_write_failed",)


def _advance_locked(
    transaction: object, binding: dict, step: tuple[str, ...]
) -> tuple[str, tuple[str, ...]]:
    """Resolve the exact chain, then commit only a genuinely next step."""

    inventory = transaction.list_logs(log_kind=CUTOVER_LOG_KIND, limit=2)
    state, reasons = chain_state(inventory, binding)
    if reasons or state == RECOVERY_REQUIRED:
        return RECOVERY_REQUIRED, reasons or ("cutover_chain_unsupported",)
    records = list(inventory[0][1]) if inventory else []
    if len(records) > FORWARD_STATES.index(step[-1]):
        # Already recorded by an earlier invocation; never write a second pair.
        # Record count, not state index, decides: an absent log and a chain
        # holding only the genesis record are both `primary_stable`.
        return state, ()
    extended = extend_chain(records, binding, step)
    if extended is None:
        return RECOVERY_REQUIRED, ("cutover_chain_step_not_next",)
    result = transaction.commit(
        transaction_id=_transaction_id(extended),
        records=(),
        logs=((CUTOVER_LOG_KIND, CUTOVER_LOG_KEY, tuple(extended)),),
    )
    if getattr(result, "status", None) not in {"created", "duplicate_existing"}:
        return RECOVERY_REQUIRED, ("cutover_chain_commit_failed",)
    return extended[-1]["state"], ()


def _transaction_id(records: list) -> str:
    """One stable content-free transaction identity for this exact chain."""

    return TRANSACTION_PREFIX + canonical_digest(
        [record["record_digest"] for record in records]
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
        and value.startswith(_GENERATION_PREFIX)
        and sha256_digest(value[len(_GENERATION_PREFIX) :])
    )


__all__ = [
    "ACTIVATION_STEPS",
    "CUTOVER_LOG_KEY",
    "CUTOVER_LOG_KIND",
    "CUTOVER_SCHEMA_VERSION",
    "FORWARD_STATES",
    "READER_FENCE_INDEX",
    "READINESS_INDEX",
    "READINESS_STEPS",
    "RECEIPT_INDEX",
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
