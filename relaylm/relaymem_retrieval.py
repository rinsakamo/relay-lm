"""RelayMEM Retrieval public runtime facade.

This is the one ordinary reader entry point, and it serves exactly one memory
authority per request. The immutable RT-1D reader decision the managed caller
carries selects it: Primary alone before the durable Primary reader fence,
neither authority from that fence until the exact finalized transfer receipt,
and Subjective alone afterwards. There is no dual read, no precedence, no
empty-result fallback, and no Primary fallback once Subjective is the ordinary
authority -- a missing, tampered, or unsupported decision releases nothing.
"""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from relaylm._subjective_mem_retrieval_runtime_projection import (
    SubjectiveMemRetrievalRuntimeProjectionSpec,
    acquire_subjective_mem_retrieval_runtime_projection,
)
from relaylm.config import RelayLMConfig
from relaylm.evidence_common import canonical_digest
from relaylm.evidence_store import EvidenceRecordStore
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)
from relaylm.relaymem_store import build_relaymem_store_diagnostics
from relaylm.routing import ResolvedRoute
from relaylm.subjective_mem_retrieval_cutover import (
    subjective_mem_retrieval_primary_reader_class,
)
from relaylm.subjective_mem_retrieval_selection import (
    SubjectiveMemRetrievalCanonicalPageBinding,
    select_subjective_mem_retrieval_handoff,
)
from relaylm.subjective_mem_retrieval_usage_ledger import (
    finalize_subjective_mem_retrieval_usage,
)
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

ORDINARY_MEMORY_AUTHORITY_KEY = "ordinary_memory_authority"
SUBJECTIVE_RUNTIME_KEY = "subjective_mem_retrieval_runtime"
SUBJECTIVE_ROUTE_SCHEMA = "relaylm.subjective_mem_retrieval_ordinary_route.v1"
SUBJECTIVE_IDEMPOTENCY_PREFIX = "smretrievaluse."
SUBJECTIVE_MEMORY_KINDS = ("episodic", "semantic")


def run_relaymem_retrieval_stage(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    relaymem_configured_store_root: str | None,
    relayscn_scene_policy_artifact: Mapping[str, Any] | None,
    relayint_intent_artifact: Mapping[str, Any] | None,
    messages: Sequence[Mapping[str, Any]],
    primary_reader_decision: object,
    request_correlation: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stage entry point for the RelayMEM retrieval stage.

    Runs the RelayMEM retrieval dry-run artifact build, then releases evidence
    from exactly the one authority ``primary_reader_decision`` names. Scans and
    reads the RelayMEM store on disk and, for ``subjective_only``, the Subjective
    evidence store, canonical workspace, and disposable live projection bundle;
    none of these callees touch ``PipelineContext`` or any ``ContextVar``.

    This is a blocking, synchronous callable by design:
    ``handle_managed_chat_completion`` invokes it via
    ``run_stage(..., offload=True, ...)`` so it runs on a worker thread
    through ``asyncio.to_thread``, exactly as it did when this body lived
    inline (as ``_run_relaymem_retrieval_stage``) in
    ``managed_chat_runtime.py``.
    """

    authority = subjective_mem_retrieval_primary_reader_class(primary_reader_decision)
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
    if authority == "primary_only" and _relaymem_primary_recall_scope_allowed(
        relaymem_store_diagnostics
    ):
        relaymem_retrieval_artifact = apply_relaymem_primary_recall_scope(
            relaymem_retrieval_artifact,
            scoped_store_root=relaymem_scoped_store_root,
            expected_namespace=route.memory_namespace,
            max_snippet_chars=config.memory.max_snippet_chars,
            max_snippet_candidates=config.memory.max_snippet_candidates,
            snippet_budget=config.memory.snippet_budget,
            chars_per_token=config.memory.chars_per_token,
        )
    elif authority == "subjective_only":
        relaymem_retrieval_artifact[SUBJECTIVE_RUNTIME_KEY] = (
            apply_subjective_mem_retrieval_ordinary_scope(
                config=config,
                route=route,
                messages=messages,
                request_correlation=request_correlation,
            )
        )
    relaymem_retrieval_artifact[ORDINARY_MEMORY_AUTHORITY_KEY] = authority
    return relaymem_store_diagnostics, relaymem_retrieval_artifact


def apply_subjective_mem_retrieval_ordinary_scope(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    messages: Sequence[Mapping[str, Any]],
    request_correlation: str,
) -> dict[str, Any]:
    """Release exact Subjective evidence, but only after durable usage finalization.

    The order is fixed and has no shortcut: acquire the exact source and its
    trusted live projection, select only exact-current eligible revisions, then
    finalize the content-free usage events durably. Only the sealed admitted
    handoff the ledger returns can release grounding evidence, so a refused
    selection, a failed finalization, or any store, source, generation, or
    binding disagreement releases nothing and never falls back to Primary MEM,
    a stale bundle, or a cache-only counter.
    """

    spec, store, reasons = _subjective_request(
        config, route, messages, request_correlation
    )
    if spec is None or store is None:
        return _subjective_runtime([], reasons)
    acquired, reasons = acquire_subjective_mem_retrieval_runtime_projection(
        store=store, spec=spec
    )
    if acquired is None:
        return _subjective_runtime([], reasons)
    if not _receipt_bound_generation(config, acquired):
        return _subjective_runtime([], ("subjective_mem_retrieval_source_drift",))
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=acquired.request,
        manifest=acquired.projection.manifest,
        rows=acquired.projection.rows,
        canonical_pages=tuple(
            SubjectiveMemRetrievalCanonicalPageBinding(image)
            for image in acquired.canonical_page_images
        ),
        shadow=False,
    )
    if handoff is None or not handoff.ranked_row_digests:
        return _subjective_runtime(
            [], () if handoff is not None else projection.blocked_reason_classes
        )
    admitted, outcome = finalize_subjective_mem_retrieval_usage(
        store=store,
        evidence_space_id=spec.evidence_space_id,
        request=acquired.request,
        manifest=acquired.projection.manifest,
        rows=acquired.projection.rows,
        handoff=handoff,
        occurred_at=_occurred_at(),
        idempotency_key=_idempotency_key(request_correlation),
    )
    if admitted is None:
        return _subjective_runtime([], outcome.blocked_reason_classes)
    return _subjective_runtime(
        list(admitted.release_grounding_evidence()), (), usage_finalized=True
    )


def _subjective_request(
    config: RelayLMConfig,
    route: ResolvedRoute,
    messages: Sequence[Mapping[str, Any]],
    request_correlation: str,
) -> tuple[
    SubjectiveMemRetrievalRuntimeProjectionSpec | None,
    EvidenceRecordStore | None,
    tuple[str, ...],
]:
    """Bind one bounded content-free acquisition request to this exact route.

    Configuration only locates the evidence space, canonical workspace, and
    disposable live projection root. It grants no serving authority: the caller
    reaches this function only for an exact finalized durable reader decision.
    """

    locators = (
        config.evidence_data_root,
        config.subjective_mem_workspace_root,
        config.subjective_mem_retrieval_projection_root,
        config.subjective_mem_retrieval_cutover_evidence_space_id,
        route.character_id,
    )
    if any(not isinstance(value, str) or not value for value in locators):
        return None, None, ("subjective_mem_retrieval_route_locator_missing",)
    evidence_root, workspace_root, projection_root, space, character_id = locators
    try:
        store = EvidenceRecordStore(str(evidence_root))
    except (OSError, TypeError, ValueError):
        return None, None, ("subjective_mem_retrieval_route_store_unavailable",)
    return (
        SubjectiveMemRetrievalRuntimeProjectionSpec(
            evidence_space_id=str(space),
            workspace_root=str(workspace_root),
            projection_root=str(projection_root),
            character_id=str(character_id),
            query_plan_digest=_request_digest("query_plan", sorted(_term_hints(messages))),
            request_correlation_digest=_request_digest(
                "request_correlation", request_correlation
            ),
            memory_kinds=SUBJECTIVE_MEMORY_KINDS,
            candidate_limit=max(1, min(64, int(config.memory.candidate_limit))),
            token_budget=max(1, min(8192, _subjective_token_budget(config))),
        ),
        store,
        (),
    )


def _receipt_bound_generation(config: RelayLMConfig, acquired: object) -> bool:
    """Prove the acquired generation is the exact one the transfer receipt bound.

    The finalized receipt authorizes only the exact generation and source state
    finalized at activation. Drift afterwards never silently rebinds the live
    projection, never falls back, and never restores Primary: it fails closed
    pending separately governed exact state convergence.
    """

    return (
        acquired.projection.manifest.projection_generation_id
        == config.subjective_mem_retrieval_cutover_projection_generation_id
        and acquired.source.source_snapshot_digest
        == config.subjective_mem_retrieval_cutover_projection_source_digest
    )


def _request_digest(kind: str, value: object) -> str:
    """Digest one bounded request identity; no raw query or prompt ever persists."""

    return canonical_digest(
        {
            "schema": SUBJECTIVE_ROUTE_SCHEMA,
            "kind": kind,
            "value": value if isinstance(value, (list, str)) else "",
        }
    )


def _subjective_runtime(
    selected: list[dict[str, Any]],
    reasons: tuple[str, ...],
    *,
    usage_finalized: bool = False,
) -> dict[str, Any]:
    """One runtime-private release record; its public counters stay content-free."""

    return {
        "schema": SUBJECTIVE_ROUTE_SCHEMA,
        "runtime_private": True,
        "request_local": True,
        "served_authority": "subjective_mem",
        "content_included": bool(selected),
        "selected_count": len(selected),
        "selected_memories": selected,
        "usage_event_recorded": usage_finalized,
        "primary_fallback_performed": False,
        "blocked_reason_classes": list(reasons),
    }


def _occurred_at() -> str:
    """One whole-second UTC occurrence time for this request's usage events.

    The durable slot identity binds the request correlation and the exact
    selected row, so a replay is either an exact duplicate that admits the same
    evidence or a fail-closed conflict. It is never a second durable pair.
    """

    stamp = datetime.now(timezone.utc).replace(microsecond=0)
    return stamp.isoformat().replace("+00:00", "Z")


def _idempotency_key(request_correlation: object) -> str:
    return SUBJECTIVE_IDEMPOTENCY_PREFIX + _request_digest(
        "idempotency",
        request_correlation if isinstance(request_correlation, str) else "",
    )


def _subjective_token_budget(config: RelayLMConfig) -> int:
    budget = _resolve_relaymem_retrieval_token_budget(config)
    return budget if isinstance(budget, int) and budget > 0 else 1


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
