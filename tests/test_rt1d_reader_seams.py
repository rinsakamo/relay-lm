"""Structural and public-equivalence coverage for the RT-1D-S1 reader seams."""

from __future__ import annotations
import ast
import inspect
from collections.abc import Mapping
from pathlib import Path

from relaylm.managed_chat_runtime import handle_managed_chat_completion
from relaylm.managed_chat_pipeline_runtime import (
    _extract_ctx_hints,
    run_managed_chat_pipeline,
)
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)
from relaylm.relaymem_retrieval import (
    build_relaymem_retrieval_dry_run_artifact,
    run_relaymem_retrieval_stage,
)

ROOT = Path(__file__).resolve().parents[1]
NEW_MODULES = (
    "relaylm/managed_chat_pipeline_runtime.py",
    "relaylm/relaymem_retrieval_dry_run.py",
    "relaylm/_relaymem_retrieval_candidates.py",
    "relaylm/_relaymem_retrieval_snippet.py",
    "relaylm/relaymem_primary_recall_selection.py",
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
    assert list(inspect.signature(apply_relaymem_primary_recall_scope).parameters) == [
        "retrieval_artifact",
        "scoped_store_root",
        "expected_namespace",
        "max_snippet_chars",
        "max_snippet_candidates",
        "snippet_budget",
        "chars_per_token",
        "primary_reader_decision",
    ]
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
        "relaylm/_relaymem_retrieval_candidates.py",
        "relaylm/_relaymem_retrieval_snippet.py",
    ):
        assert "relaylm.relaymem_retrieval" not in _imports(path)
    assert "relaylm.relaymem_primary_recall" not in _imports(
        "relaylm/relaymem_primary_recall_selection.py"
    )
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
    assert (
        _function(
            "relaylm/relaymem_primary_recall.py", "apply_relaymem_primary_recall_scope"
        ).end_lineno
        - _function(
            "relaylm/relaymem_primary_recall.py", "apply_relaymem_primary_recall_scope"
        ).lineno
        + 1
        <= 80
    )


def test_primary_recall_fails_closed_without_exact_primary_reader_authority() -> None:
    """This owner enforces the fence itself, not by upstream convention."""

    for decision in (None, "primary_only", object()):
        fenced = apply_relaymem_primary_recall_scope(
            {"selected_mem_candidates": [{"memory_id": "m1"}]},
            scoped_store_root=None,
            expected_namespace=None,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
            primary_reader_decision=decision,
        )
        runtime = fenced["primary_recall_runtime"]
        assert runtime["content_included"] is False
        assert runtime["selected_memories"] == []
        assert runtime["primary_store_read"] is False


def test_primary_empty_input_shape_remains_fail_closed() -> None:
    result = apply_relaymem_primary_recall_scope(
        None,
        scoped_store_root=None,
        expected_namespace=None,
        max_snippet_chars=512,
        max_snippet_candidates=3,
        snippet_budget=512,
        primary_reader_decision=None,
    )
    assert result["primary_recall_runtime"]["content_included"] is False
    assert result["primary_recall_runtime"]["selected_memories"] == []
    assert result["primary_recall_projection"]["retrieval_attempted"] is False
    assert (
        "character_store_scope_unavailable"
        in result["primary_recall_projection"]["blocked_reason_ids"]
    )
