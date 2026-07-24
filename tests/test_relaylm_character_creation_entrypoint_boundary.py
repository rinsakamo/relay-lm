"""Focused regression for the supported character creation CLI invocation boundary."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from relaylm_repo_inventory import invocations  # noqa: E402


def test_character_creation_commands_use_only_canonical_installed_entrypoints() -> None:
    records = invocations.collect_all()
    expected_targets = {
        "console_script:relaylm-character-create": (
            "relaylm-character-create -> relaylm.character_creation_cli:main_create"
        ),
        "console_script:relaylm-character-template-validate": (
            "relaylm-character-template-validate -> relaylm.character_creation_cli:main_validate"
        ),
    }

    for root_id, expected_target in expected_targets.items():
        console_records = [record for record in records if record.root_id == root_id]
        assert len(console_records) == 1
        assert console_records[0].command_or_symbol == expected_target

    assert not any(
        record.root_kind == "python_dash_m"
        and record.source_path == "relaylm/character_creation_cli.py"
        for record in records
    )
