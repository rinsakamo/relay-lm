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
        ("relaylm_fault_fixtures.py", "helper-shaped"),
        ("relaylm_local_helpers.py", "helper-shaped"),
        ("phase5c4a_smoke_support.py", "helper-shaped"),
        ("relaylm_platform_supports.py", "helper-shaped"),
        ("relaylm_o3_always_on_local_scheduler_smoke.py", "smoke-named"),
        ("relaylm_generate_scripts_inventory.py", "other"),
    ),
)
def test_filename_signal_is_shape_only(name: str, expected: str) -> None:
    assert inventory.filename_signal(name) == expected


def test_generate_keeps_mechanical_signals_separate_from_reviewed_responsibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = tmp_path / "scripts"
    workflows = tmp_path / ".github" / "workflows"
    docs = tmp_path / "docs"
    records = tmp_path / "records" / "repository"
    inventory_path = docs / "smoke" / "scripts_inventory.md"
    registry_path = records / "asset_classification_v1.yaml"
    scripts.mkdir(parents=True)
    workflows.mkdir(parents=True)
    inventory_path.parent.mkdir(parents=True)
    records.mkdir(parents=True)

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
    registry_path.write_text(
        """\
records:
  - asset_id: demo.fixture
    paths: [scripts/phase5c4a_cache_fixture.py]
    responsibility: ordinary_test
  - asset_id: demo.smoke
    paths: [scripts/relaylm_demo_smoke.py]
    responsibility: process_smoke
  - asset_id: ignored.non_script
    paths: [docs/runbook.md]
    responsibility: repository_validation
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(inventory, "ROOT", tmp_path)
    monkeypatch.setattr(inventory, "INVENTORY_PATH", inventory_path)
    monkeypatch.setattr(inventory, "CLASSIFICATION_REGISTRY_PATH", registry_path)
    monkeypatch.setattr(
        inventory.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="a" * 40 + "\n"),
    )

    rendered = inventory.generate()

    assert (
        "| script | CI-referenced | docs-referenced | filename signal | "
        "reviewed responsibility |"
    ) in rendered
    assert (
        "| `phase5c4a_cache_fixture.py` | yes | no | helper-shaped | ordinary_test |"
        in rendered
    )
    assert (
        "| `phase5c4a_smoke_support.py` | yes | no | helper-shaped | unclassified |"
        in rendered
    )
    assert (
        "| `relaylm_demo_smoke.py` | yes | yes | smoke-named | process_smoke |"
        in rendered
    )
    assert (
        "| `relaylm_demo_tool.py` | no | no | other | unclassified |"
        in rendered
    )
    assert "active smoke" not in rendered
    assert "phase-completion evidence" not in rendered
    assert "does not classify responsibility, lifecycle, or retention" in rendered
    assert "copied only from exact script paths" in rendered
    assert "2 with a reviewed responsibility" in rendered
    assert "--output generated/scripts_inventory.md" in rendered
    assert "--output docs/smoke/scripts_inventory.md" not in rendered


def test_conflicting_reviewed_responsibilities_fail_closed(tmp_path: Path) -> None:
    registry_path = tmp_path / "asset_classification_v1.yaml"
    registry_path.write_text(
        """\
records:
  - asset_id: first
    paths: [scripts/relaylm_demo.py]
    responsibility: ordinary_test
  - asset_id: second
    paths: [scripts/relaylm_demo.py]
    responsibility: process_smoke
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "conflicting reviewed responsibilities for "
            "scripts/relaylm_demo.py: ordinary_test vs process_smoke"
        ),
    ):
        inventory.load_reviewed_responsibilities(registry_path)
