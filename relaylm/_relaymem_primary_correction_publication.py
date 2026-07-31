"""Canonical page publication and index/log convergence for Primary correction."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from ._relaymem_primary_page_writer_common import is_sha256
from .relaymem_primary_index_log_apply import apply_relaymem_primary_index_log_reconciliation
from .relaymem_primary_index_log_reconciliation import build_relaymem_primary_index_log_reconciliation_preflight
from .relaymem_primary_page_candidate import build_relaymem_governed_experience_summary, build_relaymem_primary_page_candidate_dry_run
from .relaymem_primary_write_preflight import build_relaymem_primary_write_preflight_dry_run
from .relaymem_primary_writer_handoff import build_relaymem_primary_writer_handoff_preflight
from ._relaymem_primary_correction_preflight import PrimaryCorrectionError

@dataclass(frozen=True)
class PublicationDependencies:
    apply_primary_page_write: Callable[..., dict[str, Any]]


def publish_prepared_successor(
    root: Path, prepared: Mapping[str, Any], *, fault_at: str | None,
    dependencies: PublicationDependencies,
) -> dict[str, str]:
    page_candidate = _build_page_candidate(prepared)
    successor_identity = _validate_successor_identity(page_candidate, prepared)
    receipt = _publish_page(root, page_candidate, dependencies)
    if fault_at == "after_successor_page_publication":
        raise PrimaryCorrectionError("reconciliation_required")
    _reconcile_index_and_log(root, receipt)
    if fault_at == "after_reconciliation":
        raise PrimaryCorrectionError("reconciliation_required")
    return {"result_physical_id": str(successor_identity),
            "result_canonical_digest": str(receipt["page_digest"])}


def _build_page_candidate(prepared: Mapping[str, Any]) -> Mapping[str, Any]:
    lineage = {
        "schema_version": "relaymem.primary_source_lineage.v0", "content_free": True,
        "content_included": False, "raw_text_included": False,
        "source_event_kind": prepared["source_event_kind"], "namespace": prepared["namespace"],
        "valid": True, "lineage_fingerprint": prepared["lineage_fingerprint"],
        "lineage_shape": {"source_event_id_present": True, "run_id_present": False,
            "session_id_present": False, "turn_index_present": False}, "blocked_reasons": [],
    }
    candidate = {"candidate_id": prepared["successor_candidate_id"],
        "source_event_kind": prepared["source_event_kind"], "memory_layer": "primary",
        "memory_kind": prepared["memory_kind"], "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory"}
    preflight = build_relaymem_primary_write_preflight_dry_run(
        candidates=[candidate], source_lineage_artifact=lineage, enabled=True,
        dry_run_only=False, apply_enabled=True)
    experience = build_relaymem_governed_experience_summary(
        candidate_id=str(prepared["successor_candidate_id"]),
        source_event_kind=str(prepared["source_event_kind"]), namespace=str(prepared["namespace"]),
        summary_text=str(prepared["corrected_summary"]), title=str(prepared["corrected_title"]))
    return build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight, source_lineage_artifact=lineage,
        governed_experience_artifact=experience, enabled=True, dry_run_only=False,
        apply_enabled=True)


def _validate_successor_identity(
    page_candidate: Mapping[str, Any], prepared: Mapping[str, Any]
) -> object:
    pages = page_candidate.get("page_candidates")
    if (not isinstance(pages, Sequence) or isinstance(pages, (str, bytes))
            or len(pages) != 1 or not isinstance(pages[0], Mapping)):
        raise PrimaryCorrectionError("target_corrupt")
    successor_identity = pages[0].get("idempotency_key")
    if successor_identity != prepared["successor_physical_id"]:
        raise PrimaryCorrectionError("operation_conflict")
    return successor_identity


def _publish_page(
    root: Path, page_candidate: Mapping[str, Any], dependencies: PublicationDependencies
) -> Mapping[str, Any]:
    handoff = build_relaymem_primary_writer_handoff_preflight(
        page_candidate_artifact=page_candidate, root_path=str(root), enabled=True,
        dry_run_only=False, apply_enabled=True)
    write_result = dependencies.apply_primary_page_write(
        writer_handoff_artifact=handoff, root_path=str(root), enabled=True,
        dry_run_only=False, apply_enabled=True)
    receipt = write_result.get("receipt")
    ready = isinstance(receipt, Mapping) and (write_result.get("durability_confirmed") is True or
        (write_result.get("status") == "already_applied" and write_result.get("idempotent_noop") is True
         and not write_result.get("blocked_reasons") and receipt.get("status") == "already_applied"
         and receipt.get("idempotent_noop") is True))
    if not ready:
        raise PrimaryCorrectionError("store_unavailable")
    return receipt


def _reconcile_index_and_log(root: Path, receipt: Mapping[str, Any]) -> None:
    reconciliation = build_relaymem_primary_index_log_reconciliation_preflight(
        receipt=receipt, root_path=str(root), enabled=True, dry_run_only=True)
    plan = reconciliation.get("plan")
    if not isinstance(plan, Mapping):
        raise PrimaryCorrectionError("reconciliation_required")
    result = apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=plan, root_path=str(root), enabled=True, dry_run_only=False,
        apply_enabled=True)
    if (result.get("index_reconciled") is not True or result.get("log_reconciled") is not True
            or result.get("durability_confirmed") is not True):
        raise PrimaryCorrectionError("reconciliation_required")
