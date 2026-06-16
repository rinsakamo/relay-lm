"""Build content-free PipelineNodeResult records from existing artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from relaylm.pipeline_context import PipelineContext
from relaylm.pipeline_node_result import PipelineNodeResult, build_pipeline_node_result


_INPUT_SIDE_DIRECT_NODE_NAMES = frozenset(
    {
        "client_message_canonicalization",
        "client_history_exclusion_apply",
    }
)


def record_phase45_node_results(
    pipeline_context: PipelineContext,
    *,
    relayref_artifact: Mapping[str, Any] | None,
    relayint_fast_path_dry_run: Mapping[str, Any] | None,
    relayint_quick_clarification_preflight: Mapping[str, Any] | None,
    relayint_quick_clarification_apply_plan: Mapping[str, Any] | None,
    runtime_ctx_injection_result: Mapping[str, Any] | None,
    runtime_snippet_injection_result: Mapping[str, Any] | None,
    token_budget_truncation: Mapping[str, Any] | None,
    relayctx_short_term_runtime_injection_apply_result: Mapping[str, Any] | None,
) -> None:
    """Record Phase 4.5 diagnostics without copying request or response content.

    Synthesized input/Repack records are inserted after directly recorded
    input-side nodes and before downstream nodes such as ``relayctx_unpack`` so
    trace order follows the pipeline even though Phase 4.5 synthesis still
    occurs at request end.
    """

    existing = {result.node_name for result in pipeline_context.node_results}
    synthesized: list[PipelineNodeResult] = []

    if "relayint_reference_repair" not in existing:
        synthesized.append(
            build_pipeline_node_result(
                node_name="relayint_reference_repair",
                status="diagnostic_only",
                decision=_text(_get(relayref_artifact, "mode")) or "none",
                diagnostics={
                    "diagnostics_only": True,
                    "content_free": True,
                    "source_node_alias": "relayint_reference_repair",
                    "compatibility_source_node": "relayref",
                    "artifact_present": isinstance(relayref_artifact, Mapping),
                    "unresolved_reference_detected": (
                        _get(relayref_artifact, "unresolved_reference_detected") is True
                    ),
                    "apply_allowed": _get(relayref_artifact, "apply_allowed") is True,
                },
                artifacts=_summaries((("relayref_artifact", relayref_artifact),)),
            )
        )

    if "relayint_quick_clarification" not in existing:
        quick_artifacts = (
            ("relayint_fast_path_dry_run", relayint_fast_path_dry_run),
            (
                "relayint_quick_clarification_preflight",
                relayint_quick_clarification_preflight,
            ),
            (
                "relayint_quick_clarification_apply_plan",
                relayint_quick_clarification_apply_plan,
            ),
        )
        quick_present = any(isinstance(value, Mapping) for _, value in quick_artifacts)
        synthesized.append(
            build_pipeline_node_result(
                node_name="relayint_quick_clarification",
                status="diagnostic_only" if quick_present else "skipped",
                decision=(
                    "apply_plan_recorded"
                    if isinstance(relayint_quick_clarification_apply_plan, Mapping)
                    else "preflight_recorded"
                    if isinstance(relayint_quick_clarification_preflight, Mapping)
                    else "fast_path_recorded"
                    if isinstance(relayint_fast_path_dry_run, Mapping)
                    else "disabled"
                ),
                blocked_reasons=(
                    _strings(
                        relayint_quick_clarification_apply_plan.get(
                            "apply_block_reasons"
                        )
                    )
                    if isinstance(relayint_quick_clarification_apply_plan, Mapping)
                    else _strings(
                        relayint_quick_clarification_preflight.get(
                            "quick_clarification_block_reasons"
                        )
                    )
                    if isinstance(relayint_quick_clarification_preflight, Mapping)
                    else []
                ),
                diagnostics={
                    "diagnostics_only": True,
                    "content_free": True,
                    "fast_path_present": isinstance(
                        relayint_fast_path_dry_run, Mapping
                    ),
                    "preflight_present": isinstance(
                        relayint_quick_clarification_preflight, Mapping
                    ),
                    "apply_plan_present": isinstance(
                        relayint_quick_clarification_apply_plan, Mapping
                    ),
                    "candidate_action": _text(
                        _get(relayint_fast_path_dry_run, "candidate_action")
                    ),
                    "preflight_applicable": (
                        _get(
                            relayint_quick_clarification_preflight,
                            "preflight_applicable",
                        )
                        is True
                    ),
                    "apply_allowed": (
                        _get(
                            relayint_quick_clarification_apply_plan,
                            "apply_allowed",
                        )
                        is True
                    ),
                },
                artifacts=_summaries(quick_artifacts),
            )
        )

    if "relayctx_repack" not in existing:
        repack_artifacts = (
            ("runtime_ctx_injection_result", runtime_ctx_injection_result),
            ("runtime_snippet_injection_result", runtime_snippet_injection_result),
            ("token_budget_truncation", token_budget_truncation),
            (
                "relayctx_short_term_runtime_injection_apply_result",
                relayctx_short_term_runtime_injection_apply_result,
            ),
        )
        summaries = _summaries(repack_artifacts)
        applied = any(
            _get(value, "applied") is True
            for _, value in repack_artifacts
            if isinstance(value, Mapping)
        )
        synthesized.append(
            build_pipeline_node_result(
                node_name="relayctx_repack",
                status="applied" if applied else "diagnostic_only" if summaries else "skipped",
                decision=(
                    "payload_mutation_applied"
                    if applied
                    else "diagnostics_recorded"
                    if summaries
                    else "no_repack_artifact"
                ),
                blocked_reasons=_repack_reasons(repack_artifacts),
                diagnostics={
                    "diagnostics_only": not applied,
                    "content_free": True,
                    "payload_mutation_applied": applied,
                    "last_mutating_step": pipeline_context.last_mutating_step,
                    "phase_artifact_count": len(summaries),
                },
                artifacts=summaries,
            )
        )

    if synthesized:
        insertion_index = _synthesized_insertion_index(pipeline_context.node_results)
        pipeline_context.node_results[insertion_index:insertion_index] = synthesized


def _summaries(
    artifacts: Sequence[tuple[str, Mapping[str, Any] | None]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name, artifact in artifacts:
        if not isinstance(artifact, Mapping):
            continue
        result.append(
            {
                "artifact_name": name,
                "schema_version": _text(artifact.get("schema_version")),
                "present": True,
                "applied": artifact.get("applied") is True,
                "diagnostics_only": artifact.get("diagnostics_only") is True,
                "content_free": artifact.get("content_free") is True,
            }
        )
    return result


def _repack_reasons(
    artifacts: Sequence[tuple[str, Mapping[str, Any] | None]],
) -> list[str]:
    result: list[str] = []
    for _, artifact in artifacts:
        if not isinstance(artifact, Mapping):
            continue
        for reason in _strings(artifact.get("blocked_reasons")):
            if reason not in result:
                result.append(reason)
        reason = _text(artifact.get("blocked_reason"))
        if reason and reason not in result:
            result.append(reason)
    return result


def _synthesized_insertion_index(results: Sequence[PipelineNodeResult]) -> int:
    index = 0
    while index < len(results) and results[index].node_name in _INPUT_SIDE_DIRECT_NODE_NAMES:
        index += 1
    return index


def _get(mapping: Mapping[str, Any] | None, key: str) -> Any:
    return mapping.get(key) if isinstance(mapping, Mapping) else None


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [item for item in value if isinstance(item, str) and item]
