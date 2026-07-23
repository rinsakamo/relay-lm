from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "relaylm_generate_scripts_inventory.py"
SPEC = importlib.util.spec_from_file_location(
    "relaylm_generate_scripts_inventory_under_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


@pytest.mark.parametrize(
    ("name", "expected"),
    (
        ("_relaylm_crash_child.py", "helper-shaped"),
        ("phase5c4a_cache_fixture.py", "helper-shaped"),
        ("phase5c4a_smoke_support.py", "helper-shaped"),
        ("relaylm_o3_always_on_local_scheduler_smoke.py", "smoke-named"),
        ("relaylm_generate_scripts_inventory.py", "other"),
    ),
)
def test_filename_signal_is_shape_only(name: str, expected: str) -> None:
    assert inventory.filename_signal(name) == expected


def test_generate_keeps_reference_facts_separate_from_filename_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = tmp_path / "scripts"
    workflows = tmp_path / ".github" / "workflows"
    docs = tmp_path / "docs"
    inventory_path = docs / "smoke" / "scripts_inventory.md"
    scripts.mkdir(parents=True)
    workflows.mkdir(parents=True)
    inventory_path.parent.mkdir(parents=True)

    fixture = scripts / "phase5c4a_cache_fixture.py"
    support = scripts / "phase5c4a_smoke_support.py"
    smoke = scripts / "relaylm_demo_smoke.py"
    tool = scripts / "relaylm_demo_tool.py"
    consolidated = scripts / "relaylm_ci_consolidated_smoke.py"
    for path in (fixture, support, smoke, tool, consolidated):
        path.write_text("pass\n", encoding="utf-8")

    (workflows / "scripts.yml").write_text(
        "\n".join(
            (
                "python scripts/phase5c4a_cache_fixture.py",
                "python scripts/phase5c4a_smoke_support.py",
                "python scripts/relaylm_demo_smoke.py",
            )
        ),
        encoding="utf-8",
    )
    (docs / "runbook.md").write_text(
        "Use relaylm_demo_smoke.py for the explicit process check.\n",
        encoding="utf-8",
    )
    inventory_path.write_text(
        "This generated inventory must be excluded from reference detection.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(inventory, "ROOT", tmp_path)
    monkeypatch.setattr(inventory, "INVENTORY_PATH", inventory_path)
    monkeypatch.setattr(
        inventory.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="a" * 40 + "\n"),
    )

    rendered = inventory.generate()

    assert "| script | CI-referenced | docs-referenced | filename signal |" in rendered
    assert "| `phase5c4a_cache_fixture.py` | yes | no | helper-shaped |" in rendered
    assert "| `phase5c4a_smoke_support.py` | yes | no | helper-shaped |" in rendered
    assert "| `relaylm_demo_smoke.py` | yes | yes | smoke-named |" in rendered
    assert "| `relaylm_demo_tool.py` | no | no | other |" in rendered
    assert "active smoke" not in rendered
    assert "phase-completion evidence" not in rendered
    assert "does not classify responsibility, lifecycle, or retention" in rendered
