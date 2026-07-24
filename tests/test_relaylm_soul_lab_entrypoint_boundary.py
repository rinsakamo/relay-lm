"""Focused regression for the supported RelayLM and SOUL Lab launch boundary."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from relaylm_repo_inventory import invocations  # noqa: E402


def test_relaylm_uses_installed_soul_lab_entrypoint_and_keeps_core_fallback() -> None:
    records = invocations.collect_all()

    console_records = [
        record
        for record in records
        if record.root_id == "console_script:relaylm"
    ]
    assert len(console_records) == 1
    assert (
        console_records[0].command_or_symbol
        == "relaylm -> relaylm.soul_lab_app:main"
    )

    assert not any(
        record.root_kind == "python_dash_m"
        and record.source_path == "relaylm/soul_lab_app.py"
        for record in records
    )

    core_fallback_records = [
        record
        for record in records
        if record.root_id == "python_dash_m:relaylm/app.py"
    ]
    assert len(core_fallback_records) == 1
    assert core_fallback_records[0].command_or_symbol == "python -m relaylm.app"
