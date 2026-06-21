"""Contract smoke for the current Phase 6-B durable RelaySLP queue boundary."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/architecture/phase6b0_relayslp_durable_queue_contract.md"
B1_HANDOFF_PATH = ROOT / "docs/architecture/phase6b1_relayslp_dispatch_preflight.md"
CURRENT_TARGET_PATH = ROOT / "docs/architecture/relaymem_slp_current_target.md"
ARCHITECTURE_INDEX_PATH = ROOT / "docs/architecture/README.md"
A2_HELPER_PATH = ROOT / "relaylm/relaymem_slp_response_handoff.py"
B1_HELPER_PATH = ROOT / "relaylm/relaymem_slp_dispatch_preflight.py"
B1_WORKFLOW_PATH = ROOT / ".github/workflows/relaymem-slp-dispatch-preflight-smoke.yml"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _require_all(text: str, values: tuple[str, ...], *, label: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, f"{label} missing required values: {missing}"


def _section(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    assert start_index >= 0, f"missing section start: {start}"
    end_index = text.find(end, start_index + len(start))
    assert end_index >= 0, f"missing section end: {end}"
    return text[start_index:end_index]


def main() -> None:
    contract = _read(CONTRACT_PATH)
    b1_handoff = _read(B1_HANDOFF_PATH)
    current_target = _read(CURRENT_TARGET_PATH)
    architecture_index = _read(ARCHITECTURE_INDEX_PATH)
    a2_helper = _read(A2_HELPER_PATH)
    b1_helper = _read(B1_HELPER_PATH)
    b1_workflow = _read(B1_WORKFLOW_PATH)

    _require_all(
        contract,
        (
            "relaylm_authority: phase6b0_relayslp_durable_queue",
            "Phase 6-B0 remains the authoritative durable-queue design",
            "Phase 6-B1 now implements",
            "Phase 6-B2: gated atomic create-if-absent durable enqueue",
            "relaymem.slp_enqueue_candidate.v0",
            "relaymem.slp_durable_job.v0",
            "relaymem.slp_queue_status_projection.v0",
            "no queue I/O",
        ),
        label="B0 current boundary",
    )

    _require_all(
        contract,
        (
            "Dispatch idempotency",
            "memory-write idempotency",
            "must not be reused as a memory-write key",
            "must not be accepted as a dispatch key",
            "owned by Phase 6 / RelayRUN orchestration",
            "owned by RelayMEM persistence preflight and apply",
        ),
        label="idempotency ownership",
    )

    _require_all(
        contract,
        (
            "`PipelineNodeResult`",
            "public projection fields",
            "trace or audit records",
            "frontend metadata",
            "visible response text",
            "the original A1 public projection",
            "caller-supplied dictionaries that merely resemble the candidate",
            "Unknown fields, missing fields, wrong types, nested substitutions",
            "B2 must consume that validated B1 artifact",
        ),
        label="protected A2 consumption",
    )

    _require_all(
        contract,
        (
            "dispatch_key_version",
            "candidate_schema_version",
            "candidate_kind",
            "trigger_mode",
            "processing_stage",
            "source_event_kind",
            "run_id",
            "turn_index",
            "session_id presence marker and value",
            "namespace",
            "source_count",
            "source_lineage_fingerprint",
        ),
        label="dispatch identity inputs",
    )

    excluded = _section(
        contract,
        "The derivation must not include:",
        "Operational status fields may change",
    )
    _require_all(
        excluded,
        (
            "wall-clock timestamps",
            "random UUIDs",
            "queue paths",
            "record revision",
            "attempt count",
            "claim or lease metadata",
            "retry class or retry outcome",
            "memory-write idempotency keys",
            "raw content",
        ),
        label="dispatch identity exclusions",
    )

    _require_all(
        contract,
        (
            "The A2 candidate does not contain a retry classification.",
            "retry_class = unclassified",
            "failure_class = none",
            "B1 must not recover `retry_class` from the A1 projection",
            "attempt_count = 0",
            "claim_generation = 0",
        ),
        label="B1 initialization",
    )

    _require_all(
        contract,
        (
            "queued",
            "claimed",
            "succeeded",
            "failed",
            "cancelled",
            "dead_letter",
            "create -> queued",
            "queued -> claimed",
            "claimed -> succeeded",
            "claimed -> failed",
            "claimed -> queued",
            "validated retry release or stale-lease recovery",
            "No transition is allowed out of `succeeded`, `failed`, `cancelled`, or `dead_letter`.",
            "compare-and-swap semantics",
            "claim_generation",
            "lease_token",
        ),
        label="queue state machine",
    )

    _require_all(
        contract,
        (
            "increments `attempt_count`",
            "increments `claim_generation`",
            "Lease renewal must compare-and-swap",
            "A retry-release transition is structurally distinct from terminal failure.",
            "preserve the dispatch identity and attempt count",
            "terminal-state immutability",
            "create-if-absent",
            "enqueued_new",
            "duplicate_existing",
            "blocked_collision",
            "blocked_corrupt",
            "write_failed",
            "Same key plus different key-input fields is not a duplicate",
            "must not be silently repaired",
            "expired `claimed` records are not automatically executed",
        ),
        label="future enqueue and recovery invariants",
    )

    _require_all(
        contract,
        (
            "Queue persistence failure must not",
            "change the HTTP success already selected",
            "rewrite or append visible text",
            "delay stream completion while waiting for persistence",
            "create a synchronous memory-write fallback",
        ),
        label="visible-response independence",
    )

    projection = _section(
        contract,
        "## Public status projection",
        "## Visible-response independence",
    )
    _require_all(
        projection,
        (
            "content-free",
            "job and dispatch identifiers",
            "run, turn, session, and namespace values",
            "lineage fingerprints",
            "claim owner and lease token",
            "memory-write idempotency keys",
            "raw content of any kind",
        ),
        label="public projection exclusions",
    )

    _require_all(
        b1_handoff,
        (
            "relaylm_authority: phase6b1_relayslp_dispatch_preflight",
            "Phase 6-B1 is implemented",
            "relaymem.slp_dispatch_preflight.v0",
            "relaymem.slp_durable_job.v0",
            "relaymem.slp_queue_status_projection.v0",
            "relaymem.slp_dispatch_key.v0",
            "relaymem.slp_job_id.v0",
            "Phase 6-B2 should consume only an exact validated B1 result",
        ),
        label="B1 handoff",
    )

    _require_all(
        current_target,
        (
            "Phase 6-B1 now implements",
            "It performs no queue I/O or enqueue.",
            "The next bounded Phase 6 implementation is Phase 6-B2",
        ),
        label="current-target alignment",
    )

    for link in (
        "phase6b0_relayslp_durable_queue_contract.md",
        "phase6b1_relayslp_dispatch_preflight.md",
    ):
        assert link in architecture_index, f"architecture index missing {link}"

    _require_all(
        a2_helper,
        (
            '_CANDIDATE_SCHEMA = "relaymem.slp_enqueue_candidate.v0"',
            '"dispatch_idempotency_key": ""',
            '"memory_write_idempotency_key": ""',
            '"runtime_private": True',
        ),
        label="A2 compatibility",
    )

    _require_all(
        b1_helper,
        (
            '_RESULT_SCHEMA = "relaymem.slp_dispatch_preflight.v0"',
            '_DURABLE_JOB_SCHEMA = "relaymem.slp_durable_job.v0"',
            '_PROJECTION_SCHEMA = "relaymem.slp_queue_status_projection.v0"',
            '_DISPATCH_KEY_VERSION = "relaymem.slp_dispatch_key.v0"',
            '_JOB_ID_VERSION = "relaymem.slp_job_id.v0"',
            "exact_a2_handoff_result_required",
            '"retry_class": "unclassified"',
            '"queue_io_performed": False',
        ),
        label="B1 helper compatibility",
    )

    _require_all(
        b1_workflow,
        (
            "relaylm/relaymem_slp_dispatch_preflight.py",
            "scripts/relaylm_phase6b1_dispatch_preflight_smoke.py",
            "scripts/relaylm_phase6b1_dispatch_preflight_security_smoke.py",
            "python -m compileall -q",
            "PYTHONPATH=. python",
        ),
        label="B1 workflow",
    )

    print("Phase 6-B durable RelaySLP queue contract smoke passed through B1")


if __name__ == "__main__":
    main()
