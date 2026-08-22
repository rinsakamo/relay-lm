from __future__ import annotations

from pathlib import Path

import yaml

from tools.repository_realization_dependencies import (
    main,
    realization_dependency_errors,
    realization_dependency_review_signals,
    realization_dependency_review_summary,
)


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
    depends_on: tuple[str, ...] = (),
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
    if depends_on:
        document["depends_on"] = list(depends_on)
    path = root / ".ai" / "authority" / f"{identifier}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=True), encoding="utf-8")


def _module(root: Path, name: str, content: str) -> str:
    relative = "src/" + name.replace(".", "/") + ".py"
    return _touch(root, relative, content)


def _declare_two_transitive_edges(root: Path) -> None:
    importer_one = _module(root, "relaylm.importer_one", "import relaylm.target_one\n")
    importer_two = _module(root, "relaylm.importer_two", "import relaylm.target_two\n")
    target_one = _module(root, "relaylm.target_one", "VALUE = 1\n")
    target_two = _module(root, "relaylm.target_two", "VALUE = 2\n")
    middle = _module(root, "relaylm.middle", "VALUE = 3\n")
    _declare(
        root,
        "runtime",
        implementation=(importer_one, importer_two),
        depends_on=("turn",),
    )
    _declare(root, "turn", implementation=(middle,), depends_on=("budget",))
    _declare(root, "budget", implementation=(target_one, target_two))


def test_shared_owner_explains_internal_import(tmp_path: Path) -> None:
    importer = _module(tmp_path, "relaylm.importer", "from relaylm.target import VALUE\n")
    target = _module(tmp_path, "relaylm.target", "VALUE = 1\n")
    _declare(tmp_path, "integration", implementation=(importer, target))

    assert realization_dependency_errors(tmp_path) == ()
    assert realization_dependency_review_signals(tmp_path) == ()


def test_direct_semantic_dependency_explains_internal_import(tmp_path: Path) -> None:
    importer = _module(tmp_path, "relaylm.importer", "from relaylm.target import VALUE\n")
    target = _module(tmp_path, "relaylm.target", "VALUE = 1\n")
    _declare(tmp_path, "provider", implementation=(importer,), depends_on=("state",))
    _declare(tmp_path, "state", implementation=(target,))

    assert realization_dependency_errors(tmp_path) == ()
    assert realization_dependency_review_signals(tmp_path) == ()


def test_transitive_semantic_reachability_is_review_signal_not_error(tmp_path: Path) -> None:
    importer = _module(tmp_path, "relaylm.importer", "import relaylm.target\n")
    target = _module(tmp_path, "relaylm.target", "VALUE = 1\n")
    middle = _module(tmp_path, "relaylm.middle", "VALUE = 2\n")
    _declare(tmp_path, "runtime", implementation=(importer,), depends_on=("turn",))
    _declare(tmp_path, "turn", implementation=(middle,), depends_on=("budget",))
    _declare(tmp_path, "budget", implementation=(target,))

    assert realization_dependency_errors(tmp_path) == ()
    assert realization_dependency_review_signals(tmp_path) == (
        "src/relaylm/importer.py -> src/relaylm/target.py: runtime realization "
        "dependency is transitive-only (importer owners: runtime; imported owners: budget)",
    )


def test_review_summary_groups_exact_owner_sets(tmp_path: Path) -> None:
    _declare_two_transitive_edges(tmp_path)

    assert realization_dependency_review_summary(tmp_path) == (
        "2 edge(s): runtime -> budget",
    )


def test_cli_groups_review_signals_by_default_and_expands_on_request(
    tmp_path: Path,
    capsys,
) -> None:
    _declare_two_transitive_edges(tmp_path)

    assert main(["--root", str(tmp_path)]) == 0
    default_output = capsys.readouterr().out
    assert "review: 2 edge(s): runtime -> budget" in default_output
    assert "src/relaylm/importer_one.py" not in default_output
    assert "2 review signal(s) across 1 owner-pair cluster(s)" in default_output

    assert main(["--root", str(tmp_path), "--review-edges"]) == 0
    detailed_output = capsys.readouterr().out
    assert "src/relaylm/importer_one.py -> src/relaylm/target_one.py" in detailed_output
    assert "src/relaylm/importer_two.py -> src/relaylm/target_two.py" in detailed_output


def test_unexplained_disjoint_import_is_reported(tmp_path: Path) -> None:
    importer = _module(tmp_path, "relaylm.importer", "from relaylm.target import VALUE\n")
    target = _module(tmp_path, "relaylm.target", "VALUE = 1\n")
    _declare(tmp_path, "provider", implementation=(importer,))
    _declare(tmp_path, "state", implementation=(target,))

    assert realization_dependency_errors(tmp_path) == (
        "src/relaylm/importer.py -> src/relaylm/target.py: realization dependency is "
        "unexplained (importer owners: provider; imported owners: state)",
    )
    assert realization_dependency_review_signals(tmp_path) == ()


def test_external_imports_are_not_semantic_owner_edges(tmp_path: Path) -> None:
    importer = _module(tmp_path, "relaylm.importer", "import json\nimport httpx\n")
    _declare(tmp_path, "provider", implementation=(importer,))

    assert realization_dependency_errors(tmp_path) == ()


def test_package_marker_import_is_outside_production_module_audit(tmp_path: Path) -> None:
    _touch(tmp_path, "src/relaylm/__init__.py", "__version__ = '1'\n")
    importer = _module(tmp_path, "relaylm.importer", "from relaylm import __version__\n")
    _declare(tmp_path, "runtime", implementation=(importer,))

    assert realization_dependency_errors(tmp_path) == ()


def test_relative_submodule_import_is_resolved(tmp_path: Path) -> None:
    _touch(tmp_path, "src/relaylm/providers/__init__.py", "")
    importer = _module(tmp_path, "relaylm.providers.importer", "from . import target\n")
    target = _module(tmp_path, "relaylm.providers.target", "VALUE = 1\n")
    _declare(tmp_path, "provider", implementation=(importer,), depends_on=("state",))
    _declare(tmp_path, "state", implementation=(target,))

    assert realization_dependency_errors(tmp_path) == ()


def test_any_shared_importer_owner_may_explain_the_edge(tmp_path: Path) -> None:
    importer = _module(tmp_path, "relaylm.importer", "from relaylm.target import VALUE\n")
    target = _module(tmp_path, "relaylm.target", "VALUE = 1\n")
    _declare(tmp_path, "provider", implementation=(importer,))
    _declare(
        tmp_path,
        "turn",
        implementation=(importer,),
        depends_on=("state",),
    )
    _declare(tmp_path, "state", implementation=(target,))

    assert realization_dependency_errors(tmp_path) == ()


def test_type_checking_import_is_not_a_runtime_realization_edge(tmp_path: Path) -> None:
    importer = _module(
        tmp_path,
        "relaylm.importer",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from relaylm.target import Target\n",
    )
    target = _module(tmp_path, "relaylm.target", "class Target:\n    pass\n")
    _declare(tmp_path, "provider", implementation=(importer,))
    _declare(tmp_path, "state", implementation=(target,))

    assert realization_dependency_errors(tmp_path) == ()


def test_qualified_type_checking_import_is_not_a_runtime_realization_edge(
    tmp_path: Path,
) -> None:
    importer = _module(
        tmp_path,
        "relaylm.importer",
        "import typing\n"
        "if typing.TYPE_CHECKING:\n"
        "    import relaylm.target\n",
    )
    target = _module(tmp_path, "relaylm.target", "VALUE = 1\n")
    _declare(tmp_path, "provider", implementation=(importer,))
    _declare(tmp_path, "state", implementation=(target,))

    assert realization_dependency_errors(tmp_path) == ()
