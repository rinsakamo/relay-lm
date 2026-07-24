"""Focused regression for the supported local-worker invocation boundary."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from relaylm_repo_inventory import invocations  # noqa: E402


def test_worker_uses_only_canonical_installed_entrypoint() -> None:
    records = invocations.collect_all()
    console_records = [
        record
        for record in records
        if record.root_id == "console_script:relaylm-worker"
    ]

    assert len(console_records) == 1
    assert (
        console_records[0].command_or_symbol
        == "relaylm-worker -> relaylm.cli.worker:main"
    )
    assert not any(
        record.root_kind == "python_dash_m"
        and record.source_path == "relaylm/cli/worker.py"
        for record in records
    )
    assert not any(
        record.source_path == "relaylm/local_worker_cli.py"
        for record in records
    )
