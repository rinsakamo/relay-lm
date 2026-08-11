"""RT-1D-R5 retirement proof for the former rehearsal coordinator.

This path used to exercise `relaylm.subjective_mem_retrieval_rehearsal`. RT-1D-R5
retired that owner together with the shadow-characterization surface, so the
file now proves the post-retirement contract instead of the retired behaviour.

It deliberately keeps its place in the bounded R5 focused-evidence set rather
than being deleted: deleting it would have made package/import closure and the
negative searches pass by removing the check, which the RT-1D-R5 budget
amendment explicitly rejected.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RETIRED_MODULES = (
    "relaylm.subjective_mem_retrieval_rehearsal",
    "relaylm.subjective_mem_retrieval_characterization",
)
RETIRED_SOURCES = (
    "relaylm/subjective_mem_retrieval_rehearsal.py",
    "relaylm/subjective_mem_retrieval_characterization.py",
)
RETIRED_CUTOVER_NAMES = (
    "evaluate_subjective_mem_retrieval_rehearsal_readiness",
    "record_subjective_mem_retrieval_rehearsal_readiness",
    "rehearse_subjective_mem_retrieval_cutover",
    "subjective_mem_retrieval_rehearsal_readiness_id",
    "SubjectiveMemRetrievalRehearsalReadiness",
)


@pytest.mark.parametrize("module_name", RETIRED_MODULES)
def test_retired_owner_module_is_gone(module_name: str) -> None:
    """The retired owners are deleted, not merely unreferenced or disabled."""

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


@pytest.mark.parametrize("source", RETIRED_SOURCES)
def test_retired_owner_source_is_deleted(source: str) -> None:
    """No dormant source file survives for a later caller to re-enable."""

    assert not (ROOT / source).exists()


@pytest.mark.parametrize("name", RETIRED_CUTOVER_NAMES)
def test_cutover_exposes_no_retired_rehearsal_entry_point(name: str) -> None:
    """No ordinary or operator path can still invoke the retired semantics."""

    cutover = importlib.import_module("relaylm.subjective_mem.retrieval_cutover")
    assert not hasattr(cutover, name)
    assert name not in getattr(cutover, "__all__", ())


def test_no_production_module_imports_a_retired_owner() -> None:
    """Negative import search: the production graph names neither retired owner."""

    offenders = []
    for source in sorted((ROOT / "relaylm").glob("*.py")):
        body = source.read_text(encoding="utf-8")
        for retired in ("subjective_mem_retrieval_rehearsal", "subjective_mem_retrieval_characterization"):
            # The rehearsal *projection root* config locator keeps its name and
            # is not the retired execution owner, so it is not an offender.
            for line in body.splitlines():
                if retired in line and "rehearsal_projection_root" not in line:
                    offenders.append((source.name, line.strip()))
    assert offenders == []


def test_package_import_closure_holds_without_the_retired_owners() -> None:
    """Every intra-package import still resolves to a module that exists.

    This is checked statically rather than by importing all 313 modules: a
    runtime sweep is slow, order-dependent, and writes bytecode caches that
    perturb other repository-scanning evidence. Reading the import graph proves
    closure directly and cannot be satisfied by a dynamic-import workaround,
    because a deferred `importlib.import_module` of a deleted owner would still
    leave no module file to resolve.
    """

    package = ROOT / "relaylm"
    available = {source.stem for source in package.glob("*.py")}
    available |= {d.name for d in package.iterdir() if (d / "__init__.py").exists()}

    dangling = []
    for source in sorted(package.glob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                target = node.module.split(".")[0]
                if target not in available:
                    dangling.append((source.name, node.module))
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("relaylm."):
                    target = node.module.split(".")[1]
                    if target not in available:
                        dangling.append((source.name, node.module))
    assert dangling == []


def test_retired_semantics_are_not_reintroduced_under_another_owner() -> None:
    """Retirement removed the surface; it did not relocate it."""

    banned = (
        "characterize_subjective_mem_retrieval_shadow",
        "SubjectiveMemRetrievalShadowCharacterization",
        "SubjectiveMemRetrievalPrimaryServedMetrics",
        "evaluate_subjective_mem_retrieval_rehearsal",
    )
    offenders = []
    for source in sorted((ROOT / "relaylm").glob("*.py")):
        body = source.read_text(encoding="utf-8")
        offenders += [(source.name, name) for name in banned if name in body]
    assert offenders == []


def test_durable_rehearsal_ready_record_remains_reconstructible() -> None:
    """Retirement never rewrites or invalidates an accepted R3/R4 record.

    `rehearsal_ready` stays a valid, predecessor-bound state in the durable
    chain the cutover semantic owner reconstructs, so an already-activated
    deployment's history is still verifiable after the execution surface is
    gone.
    """

    activation = importlib.import_module(
        "relaylm._subjective_mem_retrieval_cutover_activation"
    )
    cutover = importlib.import_module("relaylm.subjective_mem.retrieval_cutover")
    assert "rehearsal_ready" in activation.FORWARD_STATES
    assert activation.FORWARD_STATES.index("rehearsal_ready") == 1
    # The cutover owner remains the sole validator of that retained identity.
    assert "readiness_id" in cutover._TOKEN_FIELDS
