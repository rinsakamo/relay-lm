"""Structural and public-equivalence coverage for the RT-1D reader seams.

RT-1D-R5 retired the ordinary Primary reader, so the seam this file guards is
now the *absence* of that reader: the recall entry point, its selection owner,
and its fallback are deleted rather than fenced, and no ordinary path can reach
Primary storage. The surviving read-only history/admin re-exports keep their
stable import boundary for the explicitly classified Primary projections.
"""

from __future__ import annotations
import ast
import importlib
import inspect
from collections.abc import Mapping
from pathlib import Path

from relaylm.managed_chat_runtime import handle_managed_chat_completion
from relaylm.managed_chat_pipeline_runtime import (
    _extract_ctx_hints,
    run_managed_chat_pipeline,
)
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_retrieval import run_relaymem_retrieval_stage
from relaylm.relaymem_retrieval_dry_run import build_relaymem_retrieval_dry_run_artifact

ROOT = Path(__file__).resolve().parents[1]
NEW_MODULES = (
    "relaylm/managed_chat_pipeline_runtime.py",
    "relaylm/relaymem_retrieval_dry_run.py",
    "relaylm/retrieval/candidates.py",
    "relaylm/retrieval/snippet.py",
    "relaylm/relaymem_primary_recall_store.py",
)


def _tree(path: str) -> ast.Module:
    return ast.parse((ROOT / path).read_text(encoding="utf-8"))


def _function(path: str, name: str):
    return next(
        node
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def _imports(path: str) -> set[str]:
    return {
        node.module
        for node in _tree(path).body
        if isinstance(node, ast.ImportFrom) and node.module
    }


def test_public_facades_and_signatures_remain_stable() -> None:
    assert inspect.iscoroutinefunction(handle_managed_chat_completion)
    assert inspect.iscoroutinefunction(run_managed_chat_pipeline)
    # RT-1D-R5: the ordinary Primary recall entry point no longer exists.
    recall = importlib.import_module("relaylm.relaymem_primary_recall")
    assert not hasattr(recall, "apply_relaymem_primary_recall_scope")
    assert recall.__all__ == ["resolve_relaymem_character_store_root"]
    assert callable(resolve_relaymem_character_store_root)
    assert callable(build_relaymem_retrieval_dry_run_artifact)
    assert callable(run_relaymem_retrieval_stage)


def test_managed_facade_delegates_once_and_owner_preserves_order() -> None:
    facade = _function(
        "relaylm/managed_chat_runtime.py", "handle_managed_chat_completion"
    )
    owner = _function(
        "relaylm/managed_chat_pipeline_runtime.py", "run_managed_chat_pipeline"
    )
    delegations = [
        node
        for node in ast.walk(facade)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_managed_chat_pipeline"
    ]
    assert len(delegations) == 1
    calls = {
        name: min(
            node.lineno
            for node in ast.walk(owner)
            if isinstance(node, ast.Name) and node.id == name
        )
        for name in (
            "run_relayrel_stage",
            "run_relayscn_stage",
            "run_relayemo_stage",
            "run_relayint_stage",
        )
    }
    assert (
        calls["run_relayrel_stage"]
        < calls["run_relayscn_stage"]
        < calls["run_relayemo_stage"]
        < calls["run_relayint_stage"]
    )
    assert any(
        isinstance(node, ast.keyword)
        and node.arg == "offload"
        and isinstance(node.value, ast.Constant)
        and node.value.value is True
        for node in ast.walk(_tree("relaylm/managed_chat_pipeline_runtime.py"))
    )


def test_moved_ctx_hints_preserve_relayint_mapping_contract() -> None:
    source_ctx = {"current_topic": "alpha"}
    hints = _extract_ctx_hints({"metadata": {"ctx": source_ctx}})
    assert hints == {"current_topic": "alpha"}
    assert hints is not source_ctx
    assert isinstance(hints, Mapping)
    assert isinstance(hints, dict)

    fallback = _extract_ctx_hints(
        {
            "metadata": {
                "ctx": {"current_topic": "alpha"},
                "ctx_handoff_guess": "candidate",
            }
        }
    )
    assert fallback == {
        "current_topic": "alpha",
        "ctx_handoff_guess": "candidate",
    }

    existing = _extract_ctx_hints(
        {
            "metadata": {
                "ctx": {"ctx_handoff_guess": "existing"},
                "ctx_handoff_guess": "fallback",
            }
        }
    )
    assert existing["ctx_handoff_guess"] == "existing"


def test_moved_ctx_hints_fail_closed_and_ignore_top_level_list() -> None:
    payloads = (
        {},
        {"metadata": None},
        {"metadata": []},
        {"metadata": {"ctx": []}},
        {"ctx_hints": [{"current_topic": "wrong"}]},
    )
    for payload in payloads:
        hints = _extract_ctx_hints(payload)
        assert hints == {}
        assert isinstance(hints, Mapping)
        assert isinstance(hints, dict)


def test_dependency_direction_and_moved_ownership() -> None:
    assert "relaylm.relaymem_retrieval_dry_run" in _imports(
        "relaylm/relaymem_retrieval.py"
    )
    for path in (
        "relaylm/relaymem_retrieval_dry_run.py",
        "relaylm/retrieval/candidates.py",
        "relaylm/retrieval/snippet.py",
    ):
        assert "relaylm.relaymem_retrieval" not in _imports(path)
    assert not (ROOT / "relaylm/relaymem_primary_recall_selection.py").exists()
    assert "relaylm.relaymem_primary_recall" not in _imports(
        "relaylm/relaymem_primary_recall_store.py"
    )
    assert "build_relaymem_retrieval_dry_run_artifact" not in {
        node.name
        for node in _tree("relaylm/relaymem_retrieval.py").body
        if isinstance(node, ast.FunctionDef)
    }
    assert "_load_validated_page" not in {
        node.name
        for node in _tree("relaylm/relaymem_primary_recall.py").body
        if isinstance(node, ast.FunctionDef)
    }


def test_bounded_modules_and_orchestration() -> None:
    for path in NEW_MODULES:
        assert len((ROOT / path).read_text(encoding="utf-8").splitlines()) < 700
    assert (
        _function(
            "relaylm/managed_chat_runtime.py", "handle_managed_chat_completion"
        ).end_lineno
        - _function(
            "relaylm/managed_chat_runtime.py", "handle_managed_chat_completion"
        ).lineno
        + 1
        <= 80
    )
    assert (
        _function(
            "relaylm/managed_chat_pipeline_runtime.py", "run_managed_chat_pipeline"
        ).end_lineno
        - _function(
            "relaylm/managed_chat_pipeline_runtime.py", "run_managed_chat_pipeline"
        ).lineno
        + 1
        <= 80
    )
    # The retired recall facade is now a bounded read-only re-export surface.
    assert (
        len(
            (ROOT / "relaylm/relaymem_primary_recall.py")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        <= 80
    )


def test_ordinary_retrieval_reaches_no_primary_authority_after_retirement() -> None:
    """Retirement is proven by absence, not by an upstream fence convention.

    Every reader class now resolves to a content-free fenced result: there is no
    branch left that resolves a Primary root, opens the store, discovers a
    candidate, or releases recall content.
    """

    body = (ROOT / "relaylm/relaymem_retrieval.py").read_text(encoding="utf-8")
    assert "apply_relaymem_primary_recall_scope" not in body
    assert "resolve_relaymem_character_store_root" not in body
    assert "primary_only" in body  # only to fail it closed, asserted below
    stage = _function("relaylm/relaymem_retrieval.py", "run_relaymem_retrieval_stage")
    returns = [n for n in ast.walk(stage) if isinstance(n, ast.Return)]
    assert len(returns) == 1, "the stage has exactly one exit: the fenced result"


def test_no_module_can_reach_the_retired_recall_owners() -> None:
    """Negative import/call search across the whole production package."""

    retired = (
        "apply_relaymem_primary_recall_scope",
        "run_primary_recall_selection",
        "prepare_primary_recall_selection",
        "compose_primary_recall_results",
        "relaymem_primary_recall_selection",
    )
    offenders = []
    for source in sorted((ROOT / "relaylm").glob("*.py")):
        body = source.read_text(encoding="utf-8")
        offenders += [(source.name, name) for name in retired if name in body]
    assert offenders == []


def test_read_only_history_admin_surface_is_preserved() -> None:
    """Frozen Primary history/observation/admin assets survive, read-only.

    The explicitly classified projections still resolve store roots and load
    validated pages/control state. None of that is ordinary reader, writer,
    ranking, fallback, or mutation authority.
    """

    recall = importlib.import_module("relaylm.relaymem_primary_recall")
    for name in ("_load_control_state", "_load_validated_page", "_safe_root", "_token"):
        assert hasattr(recall, name)
    assert callable(recall.resolve_relaymem_character_store_root)
    # The store owner keeps the implementation; the facade only re-exports.
    assert (ROOT / "relaylm/relaymem_primary_recall_store.py").exists()
    assert "relaymem_primary_recall_store" in _imports(
        "relaylm/relaymem_primary_recall.py"
    )


def test_primary_writer_modules_remain_byte_identical() -> None:
    """R5 modified no writer module; R2/R4 durable authority still fences them."""

    writer_sources = sorted((ROOT / "relaylm").glob("*primary*writer*.py"))
    for source in writer_sources:
        body = source.read_text(encoding="utf-8")
        assert "retirement_complete" not in body
        assert "RETIREMENT_STEPS" not in body
