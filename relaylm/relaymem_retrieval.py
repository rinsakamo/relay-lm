"""RelayMEM Retrieval public runtime facade."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any
from relaylm.config import RelayLMConfig
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)
from relaylm.relaymem_store import build_relaymem_store_diagnostics
from relaylm.routing import ResolvedRoute
from relaylm._relaymem_retrieval_candidates import (
    _attach_evidence_metadata_to_ctx_block_candidate,
)
from relaylm._relaymem_retrieval_snippet import (
    _build_ctx_block_snippet_candidate,
    _build_snippet_apply_readiness,
    _build_snippet_runtime_injection_plan,
)
from relaylm.relaymem_retrieval_dry_run import (
    _term_hints,
    build_relaymem_retrieval_dry_run_artifact,
)


def run_relaymem_retrieval_stage(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    relaymem_configured_store_root: str | None,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
    relayint_intent_artifact: Mapping[str, Any] | None,
    messages: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stage entry point for the RelayMEM retrieval stage.

    Runs the RelayMEM retrieval dry-run artifact build. Scans and reads the
    RelayMEM store on disk (``build_relaymem_store_diagnostics``, then the
    retrieval candidate discovery and, when scope-eligible, the Primary MEM
    recall revalidation) and returns the two plain result objects unchanged;
    none of these callees touch ``PipelineContext`` or any ``ContextVar``.

    This is a blocking, synchronous callable by design:
    ``handle_managed_chat_completion`` invokes it via
    ``run_stage(..., offload=True, ...)`` so it runs on a worker thread
    through ``asyncio.to_thread``, exactly as it did when this body lived
    inline (as ``_run_relaymem_retrieval_stage``) in
    ``managed_chat_runtime.py``.
    """

    relaymem_scoped_store_root = resolve_relaymem_character_store_root(
        relaymem_configured_store_root,
        route.character_id,
    )
    relaymem_store_diagnostics = build_relaymem_store_diagnostics(
        root_path=relaymem_scoped_store_root,
        store_enabled=config.memory.store_enabled,
        retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
    )
    relaymem_retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
        relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
        relayint_intent_artifact=relayint_intent_artifact,
        messages=messages,
        token_budget=_resolve_relaymem_retrieval_token_budget(config),
        store_diagnostics=relaymem_store_diagnostics,
        max_candidates=config.memory.candidate_limit,
        ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
        snippet_extraction_enabled=config.memory.snippet_extraction_enabled,
        snippet_dry_run_only=config.memory.snippet_dry_run_only,
        snippet_apply_enabled=config.memory.snippet_apply_enabled,
        snippet_budget=config.memory.snippet_budget,
        max_snippet_chars=config.memory.max_snippet_chars,
        max_snippet_candidates=config.memory.max_snippet_candidates,
    )
    if _relaymem_primary_recall_scope_allowed(relaymem_store_diagnostics):
        relaymem_retrieval_artifact = apply_relaymem_primary_recall_scope(
            relaymem_retrieval_artifact,
            scoped_store_root=relaymem_scoped_store_root,
            expected_namespace=route.memory_namespace,
            max_snippet_chars=config.memory.max_snippet_chars,
            max_snippet_candidates=config.memory.max_snippet_candidates,
            snippet_budget=config.memory.snippet_budget,
            chars_per_token=config.memory.chars_per_token,
        )
    return relaymem_store_diagnostics, relaymem_retrieval_artifact


def _relaymem_primary_recall_scope_allowed(
    store_diagnostics: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(store_diagnostics, Mapping):
        return True
    compatibility = store_diagnostics.get("layout_compatibility")
    if (
        store_diagnostics.get("root_present") is True
        and isinstance(compatibility, Mapping)
        and compatibility.get("target_primary_secondary_present") is False
    ):
        return False
    return True


def _resolve_relaymem_retrieval_token_budget(config: RelayLMConfig) -> int | None:
    if config.memory.token_budget is not None:
        return config.memory.token_budget
    if (
        isinstance(config.memory.token_budget_hint, int)
        and config.memory.token_budget_hint > 0
    ):
        return config.memory.token_budget_hint
    return None
