"""Regression coverage for final invocation inventory hardening."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from relaylm_repo_inventory.cli import _run_scan  # noqa: E402


def test_literal_tuple_subprocess_loop_is_expanded() -> None:
    payload = _run_scan({"invocations"})
    commands = {
        record["command_or_symbol"]
        for record in payload["invocations"]
        if record["root_kind"] == "subprocess_child"
        and record["source_path"]
        == "scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py"
    }
    assert {
        "python scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py",
        "python scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py",
        "python scripts/relaylm_documentation_current_boundary_smoke.py",
    } <= commands
    assert "unresolved subprocess invocation" not in commands


def test_dynamic_import_inventory_uses_ast_calls_only() -> None:
    payload = _run_scan({"invocations"})
    dynamic = [
        record
        for record in payload["invocations"]
        if record["root_kind"] == "dynamic_import"
    ]
    assert dynamic
    assert all(
        record["source_path"] != "scripts/relaylm_repo_inventory/invocations.py"
        for record in dynamic
    )
    assert all("_DYNAMIC_IMPORT_RE" not in record["command_or_symbol"] for record in dynamic)
    assert any(
        record["source_path"] == "scripts/relaylm_package_import_purity_smoke.py"
        for record in dynamic
    )


def test_literal_children_relink_storage_roots() -> None:
    payload = _run_scan({"storage", "invocations"})
    record = next(
        item
        for item in payload["storage"]
        if item["source_path"]
        == "scripts/relaylm_documentation_current_boundary_smoke.py"
    )
    assert any(
        root.startswith(
            "subprocess_child:scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py"
        )
        for root in record["invocation_roots"]
    )
