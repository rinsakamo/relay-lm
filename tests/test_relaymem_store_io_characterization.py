"""Characterization: current Markdown/file persistence behavior of Primary MEM.

Locks the currently implemented invariants of the M3f page writer and the
M3g/M3h index/log reconciliation:

- page publication is atomic (temp file + O_EXCL + fsync + rename), leaves no
  temp droppings, and re-applying the identical handoff is an idempotent
  no-op;
- an existing target with different bytes is a fail-closed conflict, never an
  overwrite;
- coordinated index/log apply is single-writer (advisory lock), applies index
  before log, and a deterministic fault between the two leaves the store in
  the documented ``index_applied_log_pending`` state;
- the recovery audit classifies that state as retryable and a rebuilt
  preflight converges it; converged work re-applies as an idempotent no-op;
- a stale plan against an externally mutated control file fails closed.

These tests assert the Markdown store behavior exactly as implemented today
and make no claims about any future storage backend.
"""
from __future__ import annotations

import os

import pytest

from _relaymem_characterization_support import prepare_store, read_control_text
from relaylm import _relaymem_primary_index_log_apply_io as apply_io
from relaylm.portable_lock import acquire_portable_lock, release_portable_lock
from relaylm.relaymem_primary_index_log_apply import (
    apply_relaymem_primary_index_log_reconciliation,
)
from relaylm.relaymem_primary_index_log_reconciliation import (
    build_relaymem_primary_index_log_reconciliation_preflight,
)
from relaylm.relaymem_primary_index_log_recovery_audit import (
    audit_relaymem_primary_index_log_reconciliation_recovery,
)
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run,
)
from relaylm.relaymem_primary_page_writer import apply_relaymem_primary_page_write
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_source_lineage,
    build_relaymem_primary_write_preflight_dry_run,
)
from relaylm.relaymem_primary_writer_handoff import (
    build_relaymem_primary_writer_handoff_preflight,
)

NAMESPACE = "characterization-ns-io"


@pytest.fixture()
def store(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    prepare_store(root)
    return root


def _writer_handoff(store, *, candidate_id="cand-io", summary="io test summary"):
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="manual_import",
        source_event_id=f"characterization-{candidate_id}",
        namespace=NAMESPACE,
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
        namespace=NAMESPACE,
        summary_text=summary,
        title="io title",
    )
    candidate = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )
    return build_relaymem_primary_writer_handoff_preflight(
        page_candidate_artifact=candidate,
        root_path=str(store),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def _write(store, handoff):
    return apply_relaymem_primary_page_write(
        writer_handoff_artifact=handoff,
        root_path=str(store),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def _reconciliation_plan(store, receipt):
    preflight = build_relaymem_primary_index_log_reconciliation_preflight(
        receipt=receipt,
        root_path=str(store),
        enabled=True,
        dry_run_only=True,
    )
    assert preflight.get("plan") is not None, preflight
    return preflight["plan"]


def _apply_reconciliation(store, plan):
    return apply_relaymem_primary_index_log_reconciliation(
        plan_artifact=plan,
        root_path=str(store),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


class TestAtomicPageWrite:
    def test_page_publish_is_durable_and_leaves_no_temp_files(self, store):
        result = _write(store, _writer_handoff(store))
        assert result["status"] == "applied"
        assert result["page_applied"] is True
        assert result["durability_confirmed"] is True
        assert result["cleanup_complete"] is True
        assert list(store.rglob("*.tmp")) == []
        page = store / "memory" / "mem" / "primary" / "projects"
        assert len(list(page.glob("*.md"))) == 1

    def test_identical_rewrite_is_idempotent_noop(self, store):
        handoff = _writer_handoff(store)
        _write(store, handoff)
        replay = _write(store, handoff)
        assert replay["status"] == "already_applied"
        assert replay["page_applied"] is False
        assert replay["idempotent_noop"] is True

    def test_divergent_existing_target_is_a_fail_closed_conflict(self, store):
        handoff = _writer_handoff(store)
        _write(store, handoff)
        page = next((store / "memory" / "mem" / "primary").rglob("*.md"))
        page.write_text("externally mutated bytes", encoding="utf-8")

        result = _write(store, handoff)
        assert result["status"] == "blocked"
        assert "primary_page_writer_target_conflict" in result["blocked_reasons"]
        # The writer never overwrites the divergent target.
        assert page.read_text(encoding="utf-8") == "externally mutated bytes"


class TestIndexLogReconciliation:
    def test_lock_holder_excludes_concurrent_apply(self, store):
        write = _write(store, _writer_handoff(store))
        plan = _reconciliation_plan(store, write["receipt"])

        fd = os.open(str(store / "memory" / "mem"), os.O_RDONLY)
        try:
            acquire_portable_lock(fd, mode="exclusive", blocking=False)
            result = _apply_reconciliation(store, plan)
        finally:
            release_portable_lock(fd)
            os.close(fd)
        assert result["status"] == "blocked"
        assert (
            "primary_reconciliation_apply_lock_unavailable"
            in result["blocked_reasons"]
        )
        # Neither control file was touched while excluded.
        assert read_control_text(store, "index.md") == "# Index\n"
        assert read_control_text(store, "log.md") == "# Log\n"

    def test_fault_between_index_and_log_leaves_documented_partial_state(
        self, store, monkeypatch
    ):
        write = _write(store, _writer_handoff(store))
        plan = _reconciliation_plan(store, write["receipt"])
        original_replace = apply_io.os.replace

        def fail_log_replace(src, dst, *args, **kwargs):
            if str(dst).endswith("log.md"):
                raise OSError("characterization injected log replace failure")
            return original_replace(src, dst, *args, **kwargs)

        monkeypatch.setattr(apply_io.os, "replace", fail_log_replace)
        fault = _apply_reconciliation(store, plan)
        monkeypatch.undo()

        # Current behavior: the index entry is durable, the log append is
        # pending, and the receipt says so instead of claiming success.
        assert fault["status"] == "index_applied_log_pending"
        assert fault["index_reconciled"] is True
        assert fault["log_reconciled"] is False
        assert (
            "primary_reconciliation_apply_log_replace_failed"
            in fault["blocked_reasons"]
        )
        key = str(write["receipt"]["idempotency_key"])
        assert key in read_control_text(store, "index.md")
        assert key not in read_control_text(store, "log.md")

        # The read-only recovery audit classifies the state as retryable.
        audit = audit_relaymem_primary_index_log_reconciliation_recovery(
            receipt=fault["receipt"],
            root_path=str(store),
            enabled=True,
            dry_run_only=True,
        )
        assert audit["status"] == "retry_reconciliation"
        assert audit["blocked_reasons"] == []

        # A rebuilt preflight resumes and converges; the already-applied index
        # side is an idempotent no-op.
        resume_plan = _reconciliation_plan(store, write["receipt"])
        converged = _apply_reconciliation(store, resume_plan)
        assert converged["status"] == "applied"
        assert converged["index_reconciled"] is True
        assert converged["log_reconciled"] is True
        assert converged["index_idempotent_noop"] is True
        assert key in read_control_text(store, "log.md")

    def test_converged_plan_reapplies_as_idempotent_noop(self, store):
        write = _write(store, _writer_handoff(store))
        plan = _reconciliation_plan(store, write["receipt"])
        first = _apply_reconciliation(store, plan)
        assert first["status"] == "applied"

        replay = _apply_reconciliation(store, plan)
        assert replay["status"] == "already_applied"
        assert replay["index_idempotent_noop"] is True
        assert replay["log_idempotent_noop"] is True
        assert replay["blocked_reasons"] == []

    def test_stale_plan_against_mutated_control_fails_closed(self, store):
        write = _write(store, _writer_handoff(store))
        plan = _reconciliation_plan(store, write["receipt"])
        index = store / "memory" / "mem" / "index.md"
        index.write_text("# Index\nexternally appended line\n", encoding="utf-8")

        result = _apply_reconciliation(store, plan)
        assert result["status"] == "blocked"
        assert result["index_reconciled"] is False
        assert result["blocked_reasons"]
        # The mutated control file is left exactly as found.
        assert (
            index.read_text(encoding="utf-8")
            == "# Index\nexternally appended line\n"
        )
