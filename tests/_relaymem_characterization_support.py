"""Shared support for RelayMEM / RelaySLP characterization tests.

The characterization tests lock the currently implemented invariants around
Primary MEM formation, SLP queue lifecycle, lifecycle mutation (Correct /
Forget / Pin / Held), retrieval exclusion, namespace isolation, and the
current Markdown/file persistence behavior.  They intentionally describe what
the code does today, not the target architecture.

Existing canonical smoke fixtures are reused: ``scripts/`` is added to
``sys.path`` so the same store-preparation and formation helpers exercised by
the dedicated smokes back these pytest tests as well.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _relaylm_phase_i3_test_support import (  # noqa: E402
    form_primary_memory,
)
from relaylm_phase6c1_primary_worker_test_support import (  # noqa: E402
    prepare_store,
)

from relaylm.relaymem_primary_write_preflight import (  # noqa: E402
    build_relaymem_primary_source_lineage,
)
from relaylm.relaymem_slp_dispatch_preflight import (  # noqa: E402
    build_relaymem_slp_dispatch_preflight,
)
from relaylm.relaymem_slp_durable_enqueue import (  # noqa: E402
    enqueue_relaymem_slp_durable_job,
)
from relaylm.relaymem_slp_job_admission import (  # noqa: E402
    build_relaymem_slp_job_admission_preflight,
)
from relaylm.relaymem_slp_response_handoff import (  # noqa: E402
    build_relaymem_slp_response_finalization_handoff,
)

__all__ = [
    "REPO_ROOT",
    "assert_mapping",
    "build_dispatch_preflight_ready",
    "eligibility_of",
    "enqueue_durable_job",
    "form_primary_memory",
    "held_candidate_template",
    "prepare_store",
    "queue_files",
    "read_control_text",
]


def build_dispatch_preflight_ready(
    *,
    namespace: str,
    run_id: str,
    session_id: str | None = "char-session-1",
    turn_index: int = 3,
    source_event_kind: str = "turn",
    persistence_policy_status: str = "allowed",
):
    """Compose one exact A1 admission -> A2 handoff -> B1 dispatch chain.

    Mirrors ``prepare_relaymem_slp_runtime_enqueue`` in
    ``relaylm/relaymem_slp_runtime_enqueue.py`` without requiring a full
    finalized-turn protected source result.
    """

    lineage = build_relaymem_primary_source_lineage(
        source_event_kind=source_event_kind,
        source_event_id=f"characterization-{run_id}",
        run_id=run_id,
        session_id=session_id,
        turn_index=turn_index,
        namespace=namespace,
    )
    admission = build_relaymem_slp_job_admission_preflight(
        enabled=True,
        dry_run_only=True,
        enqueue_enabled=False,
        trigger_mode="turn_end",
        processing_stage="primary_formation",
        run_id=run_id,
        turn_index=turn_index,
        session_id=session_id,
        namespace=namespace,
        source_event_kind=source_event_kind,
        source_lineage_artifact=lineage,
        source_count=1,
        visible_response_finalized=True,
        runtime_terminal_status="completed",
        persistence_policy_status=persistence_policy_status,
    )
    handoff = build_relaymem_slp_response_finalization_handoff(
        admission,
        enabled=True,
        dry_run_only=True,
        response_finalized=True,
    )
    dispatch = build_relaymem_slp_dispatch_preflight(
        handoff,
        enabled=True,
        dry_run_only=True,
    )
    return admission, handoff, dispatch


def enqueue_durable_job(dispatch, queue_root: Path):
    """Apply one exact B2 durable enqueue against ``queue_root``."""

    return enqueue_relaymem_slp_durable_job(
        dispatch,
        queue_root=str(queue_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def queue_files(queue_root: Path) -> list[Path]:
    return sorted(
        item for item in queue_root.iterdir() if item.is_file()
    )


def read_control_text(store_root: Path, name: str) -> str:
    return (store_root / "memory" / "mem" / name).read_text(encoding="utf-8")


def eligibility_of(
    store_root: Path, *, namespace: str, physical_id: str, candidate_namespace: str | None = None
):
    """Load one fresh eligibility index (fresh-process analog) and evaluate."""

    from relaylm.relaymem_primary_retrieval_eligibility import (
        load_primary_retrieval_eligibility_index,
    )

    index = load_primary_retrieval_eligibility_index(store_root, namespace=namespace)
    if candidate_namespace is None:
        return index.evaluate(physical_id)
    return index.evaluate(physical_id, candidate_namespace=candidate_namespace)


def held_candidate_template(**updates: Any) -> dict[str, Any]:
    """One valid I-7 held outcome candidate (shape from the I-7A/B contract)."""

    from relaylm.relaymem_held_governance_contract import (
        HELD_OUTCOME_CANDIDATE_SCHEMA,
    )

    value: dict[str, Any] = {
        "schema_version": HELD_OUTCOME_CANDIDATE_SCHEMA,
        "runtime_private": True,
        "content_included": False,
        "candidate_id": "held-characterization-1",
        "operation_id": "held-characterization-op-1",
        "character_id": "char-a",
        "namespace": "ns-a",
        "scope": "primary_formation",
        "status": "held",
        "queue_state": "claimed",
        "source_authority": "primary_worker_outcome",
        "source_evidence_digest": "a" * 64,
        "source_evidence_present": True,
        "source_evidence_corrupt": False,
        "source_evidence_ambiguous": False,
        "source_content_included": False,
        "related_primary_memory_id": None,
        "related_primary_expected_revision": None,
        "related_primary_physical_id": None,
    }
    value.update(updates)
    return value


def assert_mapping(value: object) -> Mapping[str, Any]:
    assert isinstance(value, Mapping), value
    return value
