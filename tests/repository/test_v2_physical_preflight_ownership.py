from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "tools" / "v2_physical_preflight.py"
SKILL = ROOT / ".ai" / "skills" / "physical-execution-preflight" / "SKILL.md"
REFERENCE = ROOT / "docs" / "reference" / "relaylm2-physical-execution-preflight.md"
TRANSFER_HOSTS = (
    ROOT / "tools" / "v2_transfer_r1_host.py",
    ROOT / "tools" / "v2_transfer_r2_host.py",
)
TYPED_HOSTS = (
    ROOT / "tools" / "v2_cognitive_work_r4_shift_host.py",
)


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_controller_preflight_cannot_import_host_owned_freeze_or_durability() -> None:
    imported = _imported_names(CONTROLLER)
    forbidden = {
        "freeze_experiment_identity",
        "FrozenExperimentIdentity",
        "DurableQuestionRun",
    }
    assert imported.isdisjoint(forbidden)
    source = CONTROLLER.read_text(encoding="utf-8")
    assert "freeze_experiment_identity(" not in source
    assert "DurableQuestionRun.start(" not in source
    assert "from_live_attestation(" not in source


def test_canonical_skill_and_reference_forbid_duplicate_controller_freeze() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    reference = REFERENCE.read_text(encoding="utf-8")
    for text in (skill, reference):
        assert "Controller observes and assembles. Host validates and freezes." in text
        assert "freeze_experiment_identity" in text
        assert "DurableQuestionRun.start" in text
        assert "provider" in text
    assert "Do **not** call `freeze_experiment_identity" in skill


def test_transfer_hosts_keep_authoritative_freeze_inside_host_boundary() -> None:
    for host in TRANSFER_HOSTS:
        source = host.read_text(encoding="utf-8")
        assert "freeze_experiment_identity(" in source
        assert "DurableQuestionRun.start(" in source
        assert "live_binding_probe" in source


def test_current_typed_cognitive_work_host_owns_final_live_binding_check() -> None:
    for host in TYPED_HOSTS:
        source = host.read_text(encoding="utf-8")
        assert "live_binding_probe" in source
        assert "binding" in source.lower()
        assert "freeze_experiment_identity(" not in source
        assert "DurableQuestionRun.start(" not in source
