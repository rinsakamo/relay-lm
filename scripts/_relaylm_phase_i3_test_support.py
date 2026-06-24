"""Canonical Primary MEM fixture support for Phase I-3 security/fault smokes."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from relaylm.relaymem_primary_index_log_apply import apply_relaymem_primary_index_log_reconciliation
from relaylm.relaymem_primary_index_log_reconciliation import build_relaymem_primary_index_log_reconciliation_preflight
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run,
)
from relaylm.relaymem_primary_page_writer import apply_relaymem_primary_page_write
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_source_lineage,
    build_relaymem_primary_write_preflight_dry_run,
)
from relaylm.relaymem_primary_writer_handoff import build_relaymem_primary_writer_handoff_preflight
from relaylm.soul_lab_observation_projection import (
    build_lab_recent_memory_projection,
    resolve_lab_observation_scope,
)
from relaylm_phase6c1_primary_worker_test_support import prepare_store
from relaylm_phase_i1_two_turn_primary_recall_smoke import write_config


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def form_primary_memory(
    store_root: Path,
    *,
    namespace: str,
    candidate_id: str,
    title: str,
    summary: str,
) -> str:
    index = store_root / "memory" / "mem" / "index.md"
    log = store_root / "memory" / "mem" / "log.md"
    if not index.exists() and not log.exists():
        prepare_store(store_root)
    require(index.is_file() and log.is_file(), "canonical_control_state_missing")
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="manual_import",
        source_event_id=f"phase-i3-{candidate_id}",
        namespace=namespace,
    )
    preflight = build_relaymem_primary_write_preflight_dry_run(
        candidates=[{
            "candidate_id": candidate_id,
            "source_event_kind": "manual_import",
            "memory_layer": "primary",
            "memory_kind": "recent_project_event",
            "promotion_policy": "free_to_update",
            "safety_scope": "ordinary_memory",
        }],
        source_lineage_artifact=lineage,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    experience = build_relaymem_governed_experience_summary(
        candidate_id=candidate_id,
        source_event_kind="manual_import",
        namespace=namespace,
        summary_text=summary,
        title=title,
    )
    candidate = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    pages = candidate.get("page_candidates")
    require(
        isinstance(pages, Sequence)
        and not isinstance(pages, (str, bytes))
        and len(pages) == 1
        and isinstance(pages[0], Mapping),
        candidate,
    )
    memory_id = str(pages[0]["idempotency_key"])
    handoff = build_relaymem_primary_writer_handoff_preflight(
        page_candidate_artifact=candidate,
        root_path=str(store_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    write = apply_relaymem_primary_page_write(
        writer_handoff_artifact=handoff,
        root_path=str(store_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    require(write.get("durability_confirmed") is True, write)
    reconciliation = build_relaymem_primary_index_log_reconciliation_preflight(
        receipt=write.get("receipt"),
        root_path=str(store_root),
        enabled=True,
        dry_run_only=True,
    )
    apply = apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=reconciliation.get("plan"),
        root_path=str(store_root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    require(apply.get("index_reconciled") is True, apply)
    require(apply.get("log_reconciled") is True, apply)
    return memory_id


def recent_memory(app: Any, *, character_id: str, namespace: str):
    scope = resolve_lab_observation_scope(
        app.state.relaylm_config,
        character_id=character_id,
        namespace=namespace,
    )
    projection = build_lab_recent_memory_projection(scope, limit=20)
    require(len(projection.items) == 1, projection.model_dump())
    return projection.items[0]


__all__ = ["form_primary_memory", "recent_memory", "require", "write_config"]
