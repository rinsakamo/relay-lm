from __future__ import annotations

from pathlib import Path

import yaml


TOOL_PATH = Path(__file__).resolve().parents[2] / "tools" / "repository_code_ownership.py"


def _load_checker():
    assert TOOL_PATH.is_file(), "production code ownership validator is not implemented"
    from tools.repository_code_ownership import production_code_coverage_errors

    return production_code_coverage_errors


def _touch(root: Path, relative: str, content: str = "surface\n") -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return relative


def _declare(
    root: Path,
    identifier: str,
    *,
    implementation: tuple[str, ...] = (),
) -> None:
    canonical = _touch(root, f"docs/contracts/{identifier}.md")
    document: dict[str, object] = {
        "schema_version": 1,
        "id": identifier,
        "summary": f"Authority for {identifier}.",
        "canonical_surfaces": [canonical],
    }
    if implementation:
        document["implementation"] = list(implementation)
    path = root / ".ai" / "authority" / f"{identifier}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=True), encoding="utf-8")


def test_ownerless_production_python_module_is_reported(tmp_path: Path) -> None:
    module = _touch(tmp_path, "src/relaylm/feature.py", "VALUE = 1\n")
    _declare(tmp_path, "core_architecture")

    errors = _load_checker()(tmp_path)

    assert errors == (f"{module}: production module has no semantic owner",)


def test_declared_production_python_module_is_covered(tmp_path: Path) -> None:
    module = _touch(tmp_path, "src/relaylm/feature.py", "VALUE = 1\n")
    _declare(tmp_path, "core_architecture", implementation=(module,))

    assert _load_checker()(tmp_path) == ()


def test_package_markers_do_not_require_an_implementation_owner(tmp_path: Path) -> None:
    _touch(tmp_path, "src/relaylm/__init__.py", "")
    _touch(tmp_path, "src/relaylm/providers/__init__.py", "")
    _declare(tmp_path, "core_architecture")

    assert _load_checker()(tmp_path) == ()


def test_shared_implementation_still_satisfies_coverage(tmp_path: Path) -> None:
    module = _touch(tmp_path, "src/relaylm/turn.py", "VALUE = 1\n")
    _declare(tmp_path, "cognitive_turn", implementation=(module,))
    _declare(tmp_path, "cognitive_budget", implementation=(module,))

    assert _load_checker()(tmp_path) == ()
