from __future__ import annotations

from pathlib import Path

from tools.repository_implementation_integrity import scan_python_source, scan_repository


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _codes(source: str) -> set[str]:
    return {violation.code for violation in scan_python_source(source=source)}


def test_private_runtime_attribute_replacement_is_rejected() -> None:
    assert _codes('setattr(provider, "_client", replacement)') == {"RGI002"}


def test_production_test_instrumentation_import_is_rejected() -> None:
    assert _codes("from unittest.mock import patch") == {"RGI001"}
    assert _codes("import pytest") == {"RGI001"}


def test_module_and_import_hook_injection_are_rejected() -> None:
    assert _codes('import sys\nsys.modules["relaylm.bridge"] = replacement') == {"RGI003"}
    assert _codes("import sys\nsys.meta_path.insert(0, finder)") == {"RGI004"}


def test_import_system_attribute_and_slice_replacement_are_rejected() -> None:
    assert _codes('import sys\nsetattr(sys, "modules", replacement)') == {"RGI003"}
    assert _codes('import sys\ndelattr(sys, "path_hooks")') == {"RGI004"}
    assert _codes("import sys\nsys.meta_path[:] = [finder]") == {"RGI004"}
    assert _codes("from sys import path_hooks\npath_hooks[:] = [hook]") == {"RGI004"}


def test_production_monkeypatch_dependency_is_rejected() -> None:
    assert _codes("def run(monkeypatch):\n    monkeypatch.setattr(target, 'value', 1)") == {"RGI005"}


def test_public_dynamic_attribute_assignment_is_not_blanket_banned() -> None:
    assert scan_python_source(source='setattr(record, "value", 1)') == ()


def test_test_tree_is_outside_production_scan_scope(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "safe.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_safe.py").write_text(
        "def test_safe(monkeypatch):\n    monkeypatch.setattr(object(), 'value', 1)\n",
        encoding="utf-8",
    )

    assert scan_repository(tmp_path) == ()


def test_current_production_tree_has_no_detectable_runtime_substitution() -> None:
    assert scan_repository(REPOSITORY_ROOT) == ()
