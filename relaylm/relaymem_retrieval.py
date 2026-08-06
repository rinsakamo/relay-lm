"""RelayMEM Retrieval public runtime facade and sole ordinary routing boundary.

Exactly one ordinary memory authority serves each request, and which one is
named by the immutable RT-1D reader decision the managed caller carries in. The
reader class is resolved and validated here before any memory authority is
touched, so the Primary reader fence dominates this read path rather than being
applied to results afterwards:

- ``primary_only`` runs only the existing Primary retrieval path;
- ``neither`` touches no memory authority at all;
- ``subjective_only`` never resolves a Primary root, runs no Primary discovery,
  recall, or fallback, and releases Subjective evidence only from the sealed
  admitted handoff the usage ledger returns after durable finalization.

A refused, failed, or empty Subjective result continues without durable-memory
context. There is no dual read, precedence, empty-result fallback, stale-
projection fallback, or Primary fallback in either direction.
"""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any
from relaylm.config import RelayLMConfig
from relaylm._subjective_mem_retrieval_runtime_projection import (
    subjective_mem_retrieval_runtime_projection_spec,
    verify_subjective_mem_retrieval_runtime_projection,
)
from relaylm.evidence_common import canonical_digest
from relaylm.subjective_mem_retrieval import (
    SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
    SubjectiveMemRetrievalBoundary,
    SubjectiveMemRetrievalRequest,
    validate_subjective_mem_retrieval_request,
)
from relaylm.subjective_mem_retrieval_cutover import (
    subjective_mem_retrieval_ordinary_token_budget,
    subjective_mem_retrieval_primary_reader_class,
)
from relaylm.subjective_mem_retrieval_selection import (
    SubjectiveMemRetrievalCanonicalPageBinding,
    select_subjective_mem_retrieval_handoff,
)
from relaylm.subjective_mem_retrieval_usage_ledger import (
    finalize_subjective_mem_retrieval_usage,
)
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

ORDINARY_MEMORY_AUTHORITY_KEY = "ordinary_memory_authority"
SUBJECTIVE_RUNTIME_KEY = "subjective_mem_retrieval_runtime"
SUBJECTIVE_ROUTE_SCHEMA = "relaylm.subjective_mem_retrieval_ordinary_route.v1"
FENCED_ARTIFACT_SCHEMA = "relaylm.subjective_mem_retrieval_fenced_artifact.v1"
SUBJECTIVE_IDEMPOTENCY_PREFIX = "smretrievaluse."
_MEMORY_KINDS = ("episodic", "semantic")


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

    The exact reader authority is resolved first and dominates this read path:
    only ``primary_only`` reaches Primary storage at all, so no root
    resolution, store diagnostics, candidate discovery, snippet extraction, or
    recall revalidation runs for ``neither`` or ``subjective_only``. Those
    receive one bounded fenced artifact instead, and ``subjective_only``
    additionally serves the exact live Subjective generation.

    This is a blocking, synchronous callable by design:
    ``run_managed_chat_pipeline`` invokes it via
    ``run_stage(..., offload=True, ...)`` so it runs on a worker thread
    through ``asyncio.to_thread``, exactly as it did when this body lived
    inline (as ``_run_relaymem_retrieval_stage``) in
    ``managed_chat_runtime.py``.
    """

    authority = subjective_mem_retrieval_primary_reader_class(primary_reader_decision)
    if authority != "primary_only":
        return _fenced_stage_result(
            authority,
            config=config,
            route=route,
            messages=messages,
            request_correlation=request_correlation,
        )
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
            primary_reader_decision=primary_reader_decision,
        )
    relaymem_retrieval_artifact[ORDINARY_MEMORY_AUTHORITY_KEY] = authority
    return relaymem_store_diagnostics, relaymem_retrieval_artifact


def _fenced_stage_result(
    authority: str,
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    messages: Sequence[Mapping[str, Any]],
    request_correlation: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Answer a fenced request without touching Primary storage at all."""

    subjective = (
        _subjective_ordinary_scope(
            config=config,
            route=route,
            messages=messages,
            request_correlation=request_correlation,
        )
        if authority == "subjective_only"
        else None
    )
    return _fenced_store_diagnostics(authority), _fenced_artifact(
        authority, subjective=subjective
    )


def _fenced_store_diagnostics(authority: str) -> dict[str, Any]:
    """One bounded content-free stand-in for the unread Primary store."""

    return {
        "schema": FENCED_ARTIFACT_SCHEMA,
        "content_free": True,
        ORDINARY_MEMORY_AUTHORITY_KEY: authority,
        "primary_reader_fenced": True,
        "primary_store_read": False,
    }


def _fenced_artifact(
    authority: str, *, subjective: dict[str, Any] | None
) -> dict[str, Any]:
    """One bounded fenced artifact carrying no Primary-derived material at all.

    The inert apply decisions and null candidate slots keep the existing
    RelayCTX injection contract shape without any Primary candidate, snippet,
    evidence envelope, or recall content, because no Primary owner ran. The
    Primary-fence diagnostics are content-free unconditionally, but the
    whole-artifact classification is truthful: a successful Subjective release
    carries runtime-private grounding evidence, so it is content-bearing.
    """

    released = subjective is not None and subjective.get("content_included") is True
    artifact: dict[str, Any] = {
        "schema": FENCED_ARTIFACT_SCHEMA,
        "content_free": not released,
        "runtime_private": released,
        "primary_reader_fenced": True,
        "primary_store_read": False,
        "primary_fence_content_free": True,
        "apply_decision": "not_eligible",
        "snippet_apply_decision": "not_eligible",
        "ctx_block": None,
        "ctx_block_candidate": None,
        "ctx_block_snippet_candidate": None,
        "selected_mem_candidates": [],
        "blocked_reason_ids": ["cutover_primary_reader_fenced"],
    }
    if subjective is not None:
        artifact[SUBJECTIVE_RUNTIME_KEY] = subjective
    artifact[ORDINARY_MEMORY_AUTHORITY_KEY] = authority
    return artifact


def _subjective_ordinary_scope(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
    messages: Sequence[Mapping[str, Any]],
    request_correlation: str,
) -> dict[str, Any]:
    """Release exact Subjective evidence, but only after durable finalization.

    The order is fixed and has no shortcut: acquire and exact-verify the live
    projection the finalized transfer receipt bound, select only exact current
    eligible revisions from it, then finalize the content-free usage events
    durably. Only the sealed admitted handoff the ledger returns can release
    grounding evidence, so a refused selection, a failed finalization, or any
    store, source, generation, or binding disagreement releases nothing and
    never falls back to Primary MEM or to a stale bundle.
    """

    acquired, store, reasons = _acquire_live_projection(config, route)
    if acquired is None or store is None:
        return _subjective_runtime([], reasons)
    request, reasons = _subjective_request(
        config, route, acquired, messages, request_correlation
    )
    if request is None:
        return _subjective_runtime([], reasons)
    pages = tuple(
        SubjectiveMemRetrievalCanonicalPageBinding(image)
        for image in acquired.canonical_page_images
    )
    handoff, projection = select_subjective_mem_retrieval_handoff(
        request=request,
        manifest=acquired.projection.manifest,
        rows=acquired.projection.rows,
        canonical_pages=pages,
        shadow=False,
    )
    if handoff is None or not handoff.ranked_row_digests:
        return _subjective_runtime(
            [], () if handoff is not None else projection.blocked_reason_classes
        )
    admitted, outcome = finalize_subjective_mem_retrieval_usage(
        store=store,
        evidence_space_id=config.subjective_mem_retrieval_cutover_evidence_space_id,
        request=request,
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


def _acquire_live_projection(config: RelayLMConfig, route: ResolvedRoute):
    """Acquire and exact-verify the one live generation the receipt bound."""

    spec, store, reasons = subjective_mem_retrieval_runtime_projection_spec(
        evidence_root=config.evidence_data_root,
        workspace_root=config.subjective_mem_workspace_root,
        projection_root=config.subjective_mem_retrieval_projection_root,
        evidence_space_id=config.subjective_mem_retrieval_cutover_evidence_space_id,
        character_id=route.character_id,
    )
    if spec is None or store is None:
        return None, None, reasons
    acquired, reasons = verify_subjective_mem_retrieval_runtime_projection(
        store=store,
        spec=spec,
        expected_generation_id=(
            config.subjective_mem_retrieval_cutover_projection_generation_id
        ),
        expected_source_digest=(
            config.subjective_mem_retrieval_cutover_projection_source_digest
        ),
    )
    return (acquired, store, reasons) if acquired is not None else (None, None, reasons)


def _subjective_request(
    config: RelayLMConfig,
    route: ResolvedRoute,
    acquired: object,
    messages: Sequence[Mapping[str, Any]],
    request_correlation: str,
):
    """Bind one exact request to the verified generation, source, and scope."""

    manifest = acquired.projection.manifest
    request = SubjectiveMemRetrievalRequest(
        character_id=route.character_id,
        workspace_authority_digest=acquired.source.workspace_authority_digest,
        admitted_scope_binding_digest=acquired.source.admitted_scope_binding_digest,
        query_plan_digest=_request_digest("query_plan", sorted(_term_hints(messages))),
        request_correlation_digest=_request_digest(
            "request_correlation", request_correlation
        ),
        projection_generation_id=manifest.projection_generation_id,
        projection_manifest_digest=manifest.manifest_digest,
        memory_kinds=_MEMORY_KINDS,
        candidate_limit=config.memory.candidate_limit,
        token_budget=subjective_mem_retrieval_ordinary_token_budget(config),
        policy_revision=SUBJECTIVE_MEM_RETRIEVAL_POLICY_REVISION,
        boundary=SubjectiveMemRetrievalBoundary(),
    )
    reasons = validate_subjective_mem_retrieval_request(request)
    return (None, reasons) if reasons else (request, ())


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


def _request_digest(kind: str, value: object) -> str:
    """Digest one bounded request identity; no raw query or prompt ever persists."""

    return canonical_digest(
        {
            "schema": SUBJECTIVE_ROUTE_SCHEMA,
            "kind": kind,
            "value": value if isinstance(value, (list, str)) else "",
        }
    )


def _occurred_at() -> str:
    """One whole-second UTC occurrence time for this request's usage events.

    The durable slot and transaction identities bind the request correlation and
    the exact selected row rather than this value, so a response-lost replay in
    a later second still resolves the same slot and admits the same evidence.
    """

    stamp = datetime.now(timezone.utc).replace(microsecond=0)
    return stamp.isoformat().replace("+00:00", "Z")


def _idempotency_key(request_correlation: object) -> str:
    return SUBJECTIVE_IDEMPOTENCY_PREFIX + _request_digest(
        "idempotency",
        request_correlation if isinstance(request_correlation, str) else "",
    )


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
