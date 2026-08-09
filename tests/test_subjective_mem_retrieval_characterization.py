"""RT-1D-R5 retirement proof for the former shadow-characterization owner.

This path used to exercise `relaylm.subjective_mem_retrieval_characterization`,
the temporary RT-1C Primary-vs-Subjective comparison surface. RT-1D-R5 retired
it together with the rehearsal coordinator, so the file now proves that no live
shadow-characterization execution surface, ordinary path, or operator path
survives anywhere in the build.

It keeps its place in the bounded R5 focused-evidence set rather than being
deleted, so the retirement stays checked rather than merely uncontradicted.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The exact symbols the retired owner used to export. None may reappear under
# any owner: retirement removed the semantics rather than relocating them.
RETIRED_SYMBOLS = (
    "SUBJECTIVE_MEM_RETRIEVAL_CHARACTERIZATION_SCHEMA",
    "RETRIEVAL_LATENCY_CLASSES",
    "RETRIEVAL_LEAKAGE_OUTCOME_ADMITTED",
    "SubjectiveMemRetrievalPrimaryServedMetrics",
    "SubjectiveMemRetrievalShadowCharacterization",
    "characterize_subjective_mem_retrieval_shadow",
    "validate_subjective_mem_retrieval_selection_projection",
)


def test_characterization_owner_module_is_gone() -> None:
    """The temporary shadow owner is deleted, not disabled or kept dormant."""

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("relaylm.subjective_mem_retrieval_characterization")


def test_characterization_source_is_deleted() -> None:
    assert not (ROOT / "relaylm/subjective_mem_retrieval_characterization.py").exists()


@pytest.mark.parametrize("symbol", RETIRED_SYMBOLS)
def test_retired_symbol_is_absent_from_every_production_module(symbol: str) -> None:
    """Negative direct-call/import search across the whole production package."""

    offenders = [
        source.name
        for source in sorted((ROOT / "relaylm").glob("*.py"))
        if symbol in source.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_no_shadow_comparison_survives_in_the_ordinary_read_path() -> None:
    """Ordinary Retrieval compares nothing: Subjective alone serves.

    The ordinary route may still *pass* the Subjective selection owner its
    `shadow` flag, but only ever as `False`. It never requests a shadow
    selection and never names a characterization or Primary-served metric.
    """

    body = (ROOT / "relaylm/relaymem_retrieval.py").read_text(encoding="utf-8")
    for marker in ("characteriz", "primary_served", "primary_metrics"):
        assert marker not in body.lower()
    assert "shadow=True" not in body
    assert "shadow=False" in body


def test_retirement_left_no_alternate_characterization_evaluator() -> None:
    """No replacement owner, registry, helper, or compatibility shim appeared.

    Prose that records the retired boundary is fine; executable characterization
    is not. This looks for a definition, import, or call rather than a mention.
    """

    offenders = []
    for source in sorted((ROOT / "relaylm").glob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("characterize"):
                    offenders.append((source.name, f"def {node.name}"))
            elif isinstance(node, ast.ClassDef):
                if node.name.startswith("SubjectiveMemRetrievalShadow"):
                    offenders.append((source.name, f"class {node.name}"))
            elif isinstance(node, ast.ImportFrom):
                if "characterization" in (node.module or ""):
                    offenders.append((source.name, f"from {node.module}"))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "characterization" in alias.name:
                        offenders.append((source.name, f"import {alias.name}"))
    assert offenders == []
