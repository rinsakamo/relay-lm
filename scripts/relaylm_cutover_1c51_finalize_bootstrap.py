#!/usr/bin/env python3
"""Temporary connector-finalization helper for Cutover 1C-51."""

from pathlib import Path

receipt_path = Path("docs/evidence/migrations/cutover-1c51-phase55b2.md")
receipt = receipt_path.read_text(encoding="utf-8")
old_receipt = "- Fail-closed enforcement: `scripts/relaylm_phase55b2_handoff_cutover_guard.py`, to be compiled and executed by `.github/workflows/documentation-current-boundary-smoke.yml`"
new_receipt = "- Fail-closed enforcement: `scripts/relaylm_phase55b2_handoff_cutover_guard.py`, compiled and executed by `.github/workflows/documentation-current-boundary-smoke.yml`"
if receipt.count(old_receipt) != 1:
    raise SystemExit("unexpected local receipt connector-finalization state")
receipt_path.write_text(receipt.replace(old_receipt, new_receipt, 1), encoding="utf-8")

ledger_path = Path("docs/evidence/migrations/documentation-hard-cutover-receipt.md")
ledger = ledger_path.read_text(encoding="utf-8")
marker = "### C1C51-001 — Phase 5.5-B2 request-runtime stream suppression wiring handoff"
if ledger.count(marker) != 1:
    raise SystemExit("unexpected C1C51 marker count")
prefix, block = ledger.split(marker, 1)
old_ledger = "  guard_integrated_into_existing_documentation_boundary_workflow: pending_connector_finalization"
new_ledger = "  guard_integrated_into_existing_documentation_boundary_workflow: true"
if block.count(old_ledger) != 1:
    raise SystemExit("unexpected central ledger connector-finalization state")
ledger_path.write_text(prefix + marker + block.replace(old_ledger, new_ledger, 1), encoding="utf-8")
