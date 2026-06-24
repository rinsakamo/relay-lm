#!/usr/bin/env python3
from pathlib import Path


def replace(path: str, old: str, new: str, count: int = 1) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if body.count(old) < count:
        raise SystemExit(f"missing patch anchor in {path}: {old!r}")
    target.write_text(body.replace(old, new, count), encoding="utf-8")


replace(
    "relaylm/relaymem_primary_recall.py",
    '        "retrieval_attempted": attempted,\n        "selected_count": len(selected),',
    '        "retrieval_attempted": attempted,\n'
    '        "scene_type": _token(artifact.get("scene_type")) or "unknown",\n'
    '        "retrieval_scope": _token(artifact.get("retrieval_scope")) or "current_context_only",\n'
    '        "fallback_reason": _token(artifact.get("fallback_reason")),\n'
    '        "persistence_block": artifact.get("persistence_block") is True,\n'
    '        "ctx_block_present": artifact.get("ctx_block") is not None,\n'
    '        "selected_count": len(selected),',
)

replace(
    "relaylm/app.py",
    '''        ) = apply_relaymem_runtime_injection_phase(
            config=config,
            pipeline_context=pipeline_context,
            relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            compiled_payload=compiled_request.payload,
        )
        forwarded_payload, token_budget_truncation = apply_token_budget_truncation_phase(''',
    '''        ) = apply_relaymem_runtime_injection_phase(
            config=config,
            pipeline_context=pipeline_context,
            relaymem_retrieval_artifact=relaymem_retrieval_artifact,
            compiled_payload=compiled_request.payload,
        )
        relaymem_primary_recall_projection = relaymem_retrieval_artifact.get(
            "primary_recall_projection"
        )
        if isinstance(relaymem_primary_recall_projection, dict):
            relaymem_primary_recall_projection["injection_performed"] = (
                runtime_snippet_injection_result.get("applied") is True
                or runtime_ctx_injection_result.get("applied") is True
            )
            relaymem_primary_recall_projection["memory_used"] = (
                relaymem_primary_recall_projection["injection_performed"]
            )
        relaymem_diagnostics_artifact = {
            "artifact_version": "relaymem_retrieval_projection.v0",
            "diagnostics_only": True,
            "content_free": True,
            "primary_recall_projection": deepcopy(
                relaymem_primary_recall_projection
            )
            if isinstance(relaymem_primary_recall_projection, dict)
            else None,
        }
        forwarded_payload, token_budget_truncation = apply_token_budget_truncation_phase(''',
)

replace(
    "relaylm/app.py",
    '''            **runtime_artifact_diagnostics_kwargs(
                relayemo_artifact=relayemo_artifact,
                relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
                relayref_artifact=relayref_artifact,
                relaymem_retrieval_artifact=relaymem_retrieval_artifact,
                runtime_ctx_injection_result=runtime_ctx_injection_result,
                runtime_snippet_injection_result=runtime_snippet_injection_result,
            ),''',
    '''            **runtime_artifact_diagnostics_kwargs(
                relayemo_artifact=relayemo_artifact,
                relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
                relayref_artifact=relayref_artifact,
                relaymem_retrieval_artifact=relaymem_diagnostics_artifact,
                runtime_ctx_injection_result=runtime_ctx_injection_result,
                runtime_snippet_injection_result=runtime_snippet_injection_result,
            ),''',
)

replace(
    "relaylm/trace_runtime.py",
    '''    for key, value in supported:
        if value is not None:
            output[key] = value
    return output
''',
    '''    for key, value in supported:
        if value is not None:
            output[key] = value
    relaymem_diagnostics = diagnostics.relaymem_retrieval_artifact
    if isinstance(relaymem_diagnostics, dict):
        projection = relaymem_diagnostics.get("primary_recall_projection")
        if isinstance(projection, dict):
            output["relaymem_primary_recall_projection"] = projection
    return output
''',
)

audit = Path("relaylm/audit_projection.py")
body = audit.read_text(encoding="utf-8")
anchor = '''_RUNTIME_INJECTION = _mapping(
    {
        "schema_version": _bounded_token,
        "status": _optional(_bounded_token),
        "reason": _optional(_lower_token),
        "applied": _optional(_bool),
        "applied_to_response": _optional(_bool),
        "blocked": _optional(_bool),
        "blocked_reasons": _optional(_REASON_LIST),
        "inserted_chars": _optional(_non_negative_int),
        "inserted_message_role": _optional(_enum("system", "developer", "user")),
        "diagnostics_only": _optional(_bool),
        "content_free": _optional(_bool),
    }
)


TOP_LEVEL_PROJECTORS'''
replacement = '''_RUNTIME_INJECTION = _mapping(
    {
        "schema_version": _bounded_token,
        "status": _optional(_bounded_token),
        "reason": _optional(_lower_token),
        "applied": _optional(_bool),
        "applied_to_response": _optional(_bool),
        "blocked": _optional(_bool),
        "blocked_reasons": _optional(_REASON_LIST),
        "inserted_chars": _optional(_non_negative_int),
        "inserted_message_role": _optional(_enum("system", "developer", "user")),
        "diagnostics_only": _optional(_bool),
        "content_free": _optional(_bool),
    }
)

_PRIMARY_RECALL_LAYER_COUNTS = _exact_string_int_map(frozenset({"primary"}))
_PRIMARY_RECALL_PROJECTION = _mapping(
    {
        "schema_version": _enum("relaymem.primary_recall_projection.v0"),
        "diagnostics_only": _bool,
        "content_free": _bool,
        "content_included": _bool,
        "memory_text_included": _bool,
        "title_or_summary_included": _bool,
        "character_value_included": _bool,
        "namespace_value_included": _bool,
        "runtime_identifier_values_included": _bool,
        "path_values_included": _bool,
        "digest_values_included": _bool,
        "lineage_values_included": _bool,
        "idempotency_values_included": _bool,
        "backend_prompt_included": _bool,
        "retrieval_attempted": _bool,
        "scene_type": _bounded_token,
        "retrieval_scope": _bounded_token,
        "fallback_reason": _optional(_lower_token),
        "persistence_block": _bool,
        "ctx_block_present": _bool,
        "selected_count": _non_negative_int,
        "selected_layer_counts": _PRIMARY_RECALL_LAYER_COUNTS,
        "character_scope_resolved": _bool,
        "namespace_scope_valid": _bool,
        "scope_matched": _bool,
        "injection_candidate_present": _bool,
        "injection_performed": _optional(_bool),
        "estimated_chars": _non_negative_int,
        "estimated_tokens": _non_negative_int,
        "memory_used": _bool,
        "blocked_reason_ids": _REASON_LIST,
    }
)


TOP_LEVEL_PROJECTORS'''
if anchor not in body:
    raise SystemExit("audit projection insertion anchor missing")
body = body.replace(anchor, replacement, 1)
body = body.replace(
    '    "runtime_snippet_injection_result": _RUNTIME_INJECTION,\n}',
    '    "runtime_snippet_injection_result": _RUNTIME_INJECTION,\n'
    '    "relaymem_primary_recall_projection": _PRIMARY_RECALL_PROJECTION,\n'
    '}',
    1,
)
audit.write_text(body, encoding="utf-8")

replace(
    "docs/README.md",
    "The next product boundary is next-turn recall and scope isolation, followed by real SOUL Lab observation.",
    "Next-turn recall and scope isolation are complete. The next product boundary is real SOUL Lab observation; queue scanning, daemon lifecycle, and the pre-enqueue crash window remain separate later work.",
)
replace(
    "docs/architecture/phase6_async_relayslp_bounded_slice.md",
    "Phase 6 is product-complete for I1 only when a later turn retrieves and uses the formed Primary MEM in the correct scope and the separate visible-response-to-background-publication crash window is resolved or formally bounded.",
    "Phase I-1 now proves that a later ordinary turn retrieves and uses the formed Primary MEM in the correct character/namespace scope. The wider I1 durability story still requires the separate visible-response-to-background-publication crash window to be resolved or formally bounded.",
)
