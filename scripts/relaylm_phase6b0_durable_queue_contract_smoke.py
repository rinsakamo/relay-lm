"""Contract smoke for the docs-only Phase 6-B0 durable RelaySLP queue boundary."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs/architecture/phase6b0_relayslp_durable_queue_contract.md"
A2_CONTRACT_PATH = (
    ROOT / "docs/architecture/phase6a2_relayslp_response_handoff_contract.md"
)
CURRENT_TARGET_PATH = ROOT / "docs/architecture/relaymem_slp_current_target.md"
PIPELINE_PLAN_PATH = ROOT / "docs/architecture/pipeline_implementation_plan.md"
PROJECT_STATUS_PATH = ROOT / "docs/PROJECT_STATUS.md"
ARCHITECTURE_INDEX_PATH = ROOT / "docs/architecture/README.md"
A2_HELPER_PATH = ROOT / "relaylm/relaymem_slp_response_handoff.py"
WORKFLOW_PATH = (
    ROOT / ".github/workflows/relaymem-slp-durable-queue-contract-smoke.yml"
)


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
    a2_contract = _read(A2_CONTRACT_PATH)
    current_target = _read(CURRENT_TARGET_PATH)
    pipeline_plan = _read(PIPELINE_PLAN_PATH)
    project_status = _read(PROJECT_STATUS_PATH)
    architecture_index = _read(ARCHITECTURE_INDEX_PATH)
    a2_helper = _read(A2_HELPER_PATH)
    workflow = _read(WORKFLOW_PATH)

    _require_all(
        contract,
        (
            "relaylm_authority: phase6b0_relayslp_durable_queue",
            "Phase 6-B0 is a design and contract boundary only.",
            "relaymem.slp_enqueue_candidate.v0",
            "relaymem.slp_durable_job.v0",
            "relaymem.slp_queue_status_projection.v0",
            "Phase 6-B1",
            "default-off, dry-run-only",
            "no queue I/O",
        ),
        label="B0 contract boundary",
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
            "PipelineNodeResult",
            "public projection fields",
            "trace or audit records",
            "frontend metadata",
            "visible response text",
            "the original A1 public projection",
            "caller-supplied dictionaries that merely resemble the candidate",
            "Unknown fields, missing fields, wrong types, nested substitutions",
            "B2 must consume that validated B1 artifact",
        ),
        label="private A2 candidate consumption",
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

    excluded_derivation_inputs = _section(
        contract,
        "The derivation must not include:",
        "Operational status fields may change",
    )
    _require_all(
        excluded_derivation_inputs,
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
        label="retry metadata provenance",
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
            "increment `attempt_count`",
            "increment `claim_generation`",
            "Lease renewal must compare-and-swap",
            "A retry-release transition is structurally distinct from terminal failure.",
            "preserve the dispatch identity and attempt count",
            "terminal-state immutability",
        ),
        label="claim retry and terminal invariants",
    )

    _require_all(
        contract,
        (
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
        label="atomic enqueue and recovery",
    )

    _require_all(
        contract,
        (
            "Queue persistence failure must never replace, delay, invalidate, or downgrade",
            "change the HTTP success already selected",
            "rewrite or append visible text",
            "delay stream completion while waiting for persistence",
            "create a synchronous memory-write fallback",
        ),
        label="visible response independence",
    )

    public_projection = _section(
        contract,
        "## Public status projection",
        "## Visible-response independence",
    )
    _require_all(
        public_projection,
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
        contract,
        (
            "does not implement:",
            "Python queue helpers",
            "dispatch-key generation",
            "filesystem or database I/O",
            "worker or scheduler execution",
            "memory-write preflight or apply",
            "RelaySOUL mutation",
            "TTS, audio, Live2D, avatar, or lip-sync processing",
        ),
        label="B0 non-goals",
    )

    contract_link = "phase6b0_relayslp_durable_queue_contract.md"
    for label, document in (
        ("architecture index", architecture_index),
        ("A2 contract", a2_contract),
        ("RelayMEM/SLP current-target", current_target),
        ("pipeline implementation plan", pipeline_plan),
        ("project status", project_status),
    ):
        assert contract_link in document, f"{label} does not link the B0 contract"

    _require_all(
        current_target,
        (
            "B0 is design-only",
            "adds no producer, key generation, queue I/O",
            "The next bounded implementation is Phase 6-B1",
        ),
        label="current-target status alignment",
    )
    _require_all(
        pipeline_plan,
        (
            "Phase 6-B0 durable queue contract and state-machine design: complete",
            "Phase 6-B1 dry-run job-record and dispatch-idempotency preflight helper",
            "B0 remains design-only",
            "### Phase 6-B1: job-record and dispatch-idempotency preflight — next",
        ),
        label="pipeline sequencing alignment",
    )
    _require_all(
        project_status,
        (
            "B0 design contract complete",
            "Phase 6-B0 durable RelaySLP queue contract",
            "Phase 6-B1: default-off, dry-run-only job-record and dispatch-idempotency preflight helper",
            "B0 defines these boundaries but does not implement them.",
        ),
        label="project status alignment",
    )

    _require_all(
        a2_helper,
        (
            '_CANDIDATE_SCHEMA = "relaymem.slp_enqueue_candidate.v0"',
            '"dispatch_idempotency_key": ""',
            '"memory_write_idempotency_key": ""',
            '"runtime_private": True',
        ),
        label="A2 candidate compatibility",
    )
    a2_candidate_class = _section(
        a2_helper,
        "class RelayMEMSLPEnqueueCandidate:",
        "class RelayMEMSLPSourceProjection:",
    )
    assert "retry_class" not in a2_candidate_class, (
        "B0 retry initialization must be revisited if A2 begins carrying retry_class"
    )

    tracked_paths = (
        "docs/architecture/phase6b0_relayslp_durable_queue_contract.md",
        "docs/architecture/phase6a2_relayslp_response_handoff_contract.md",
        "docs/architecture/relaymem_slp_current_target.md",
        "docs/architecture/pipeline_implementation_plan.md",
        "docs/PROJECT_STATUS.md",
        "docs/architecture/README.md",
        "relaylm/relaymem_slp_response_handoff.py",
        "scripts/relaylm_phase6b0_durable_queue_contract_smoke.py",
        ".github/workflows/relaymem-slp-durable-queue-contract-smoke.yml",
    )
    _require_all(workflow, tracked_paths, label="workflow path coverage")
    _require_all(
        workflow,
        (
            "python -m compileall -q",
            "PYTHONPATH=. python",
            "scripts/relaylm_phase6b0_durable_queue_contract_smoke.py",
        ),
        label="workflow commands",
    )

    print("Phase 6-B0 durable RelaySLP queue contract smoke passed")


if __name__ == "__main__":
    main()
