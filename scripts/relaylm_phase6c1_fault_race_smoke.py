#!/usr/bin/env python3
"""Focused Phase 6-C1 stale-recovery race and duplicate no-replace smoke."""
from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_primary_page_writer import apply_relaymem_primary_page_write
from scripts._relaylm_phase6c1_fault_fixtures import (
    FixtureBuildError,
    apply_queue_transition,
    build_exact_duplicate_page_fixture,
    build_expired_claim_fixture,
    read_canonical_queue_record,
)
from scripts.relaylm_phase6c1_fault_injection_smoke import (
    SmokeFailure,
    queue_request,
    require,
    require_public_safe,
    require_reason,
)


def test_competing_stale_recovery() -> None:
    with build_expired_claim_fixture() as fixture:
        root = fixture.queue_root
        record = fixture.canonical_record
        require(root is not None and isinstance(record, Mapping), "recovery_race_fixture_missing")
        operation = queue_request(
            record,
            "stale_recovery",
            lease_token=record["lease_token"],
        )
        first = apply_queue_transition(root, operation)
        require(first.status == "applied", "recovery_race_first_status")
        after_first = read_canonical_queue_record(fixture)
        second = apply_queue_transition(root, operation)
        require(second.status == "conflict", "recovery_race_second_status")
        require_reason(second, "record_revision_mismatch", "recovery_race_second_reason")
        require(read_canonical_queue_record(fixture) == after_first, "recovery_race_mutation")
        require_public_safe(first.to_log_dict(), fixture, "recovery_race_first_projection")
        require_public_safe(second.to_log_dict(), fixture, "recovery_race_second_projection")


def test_duplicate_does_not_replace() -> None:
    with build_exact_duplicate_page_fixture() as fixture:
        root = fixture.store_root
        require(root is not None, "duplicate_replace_store_missing")
        pages = list((root / "memory/mem/primary/projects").glob("*.md"))
        require(len(pages) == 1, "duplicate_replace_page_count")
        page = pages[0]
        before_bytes = page.read_bytes()
        before_stat = page.stat()
        repeated = apply_relaymem_primary_page_write(
            writer_handoff_artifact=fixture.private_artifacts["writer_handoff"],
            root_path=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        after_stat = page.stat()
        require(repeated["status"] == "already_applied", "duplicate_replace_status")
        require(page.read_bytes() == before_bytes, "duplicate_replace_bytes")
        require(
            (after_stat.st_ino, after_stat.st_mtime_ns)
            == (before_stat.st_ino, before_stat.st_mtime_ns),
            "duplicate_replace_metadata",
        )
        require_public_safe(repeated["projection"], fixture, "duplicate_replace_projection")


def main() -> int:
    require(len(sys.argv) == 1, "unexpected_arguments")
    test_competing_stale_recovery()
    test_duplicate_does_not_replace()
    print("Phase 6-C1 fault race smoke: ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeFailure, FixtureBuildError) as exc:
        print(f"Phase 6-C1 fault race smoke: failed:{exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception:
        print("Phase 6-C1 fault race smoke: failed:unexpected_error", file=sys.stderr)
        raise SystemExit(1)
