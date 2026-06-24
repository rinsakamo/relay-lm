#!/usr/bin/env python3
from pathlib import Path


def replace(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if old not in body:
        raise SystemExit(f"missing patch anchor in {path}: {old!r}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


adapter = Path("relaylm/relaymem_primary_recall.py")
body = adapter.read_text(encoding="utf-8")
anchor = '''def _safe_root(value: object) -> Path | None:
'''
helper = '''def build_relaymem_primary_recall_compat_projection(
    retrieval_artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Project legacy flat-store M2 status without changing retrieval semantics.

    Flat M1/M2 layouts predate character partitions. They remain readable for
    compatibility, but are never reported as character/namespace scoped I1
    recall. Only bounded counts and gate status are exposed publicly.
    """

    artifact = dict(retrieval_artifact or {})
    raw_candidates = artifact.get("selected_mem_candidates")
    candidates = (
        raw_candidates
        if isinstance(raw_candidates, Sequence)
        and not isinstance(raw_candidates, (str, bytes, bytearray))
        else []
    )
    primary_candidates = [
        item
        for item in candidates
        if isinstance(item, Mapping) and item.get("memory_layer") == "primary"
    ]

    def metric(item: Mapping[str, Any], key: str) -> int:
        value = item.get(key)
        return value if type(value) is int and value >= 0 else 0

    estimated_chars = sum(metric(item, "estimated_chars") for item in primary_candidates)
    estimated_tokens = sum(metric(item, "estimated_tokens") for item in primary_candidates)
    return {
        "schema_version": PROJECTION_SCHEMA,
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "memory_text_included": False,
        "title_or_summary_included": False,
        "character_value_included": False,
        "namespace_value_included": False,
        "runtime_identifier_values_included": False,
        "path_values_included": False,
        "digest_values_included": False,
        "lineage_values_included": False,
        "idempotency_values_included": False,
        "backend_prompt_included": False,
        "retrieval_attempted": isinstance(retrieval_artifact, Mapping),
        "scene_type": _token(artifact.get("scene_type")) or "unknown",
        "retrieval_scope": _token(artifact.get("retrieval_scope")) or "current_context_only",
        "fallback_reason": _token(artifact.get("fallback_reason")),
        "persistence_block": artifact.get("persistence_block") is True,
        "ctx_block_present": artifact.get("ctx_block") is not None,
        "selected_count": len(primary_candidates),
        "selected_layer_counts": {"primary": len(primary_candidates)},
        "character_scope_resolved": False,
        "namespace_scope_valid": False,
        "scope_matched": False,
        "injection_candidate_present": bool(primary_candidates),
        "injection_performed": False,
        "estimated_chars": estimated_chars,
        "estimated_tokens": estimated_tokens,
        "memory_used": False,
        "blocked_reason_ids": ["legacy_flat_store_compatibility"],
    }


'''
if anchor not in body:
    raise SystemExit("adapter insertion anchor missing")
body = body.replace(anchor, helper + anchor, 1)
body = body.replace(
    '    "apply_relaymem_primary_recall_scope",\n    "resolve_relaymem_character_store_root",',
    '    "apply_relaymem_primary_recall_scope",\n'
    '    "build_relaymem_primary_recall_compat_projection",\n'
    '    "resolve_relaymem_character_store_root",',
    1,
)
adapter.write_text(body, encoding="utf-8")

replace(
    "relaylm/app.py",
    "import os\nimport uuid\n",
    "import os\nfrom pathlib import Path\nimport uuid\n",
)
replace(
    "relaylm/app.py",
    '''from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)
''',
    '''from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    build_relaymem_primary_recall_compat_projection,
    resolve_relaymem_character_store_root,
)
''',
)
replace(
    "relaylm/app.py",
    '''        relaymem_scoped_store_root = resolve_relaymem_character_store_root(
            config.memory.root_path,
            route.character_id,
        )
        relaymem_store_diagnostics = build_relaymem_store_diagnostics(
            root_path=relaymem_scoped_store_root,
''',
    '''        relaymem_configured_store_root = config.memory.root_path
        relaymem_character_partition_present = False
        if (
            isinstance(relaymem_configured_store_root, str)
            and relaymem_configured_store_root
        ):
            character_partition = (
                Path(relaymem_configured_store_root) / "characters"
            )
            relaymem_character_partition_present = (
                character_partition.exists() or character_partition.is_symlink()
            )
        if relaymem_character_partition_present:
            relaymem_scoped_store_root = (
                resolve_relaymem_character_store_root(
                    relaymem_configured_store_root,
                    route.character_id,
                )
            )
        else:
            relaymem_scoped_store_root = relaymem_configured_store_root

        relaymem_store_diagnostics = build_relaymem_store_diagnostics(
            root_path=relaymem_scoped_store_root,
''',
)
replace(
    "relaylm/app.py",
    '''        relaymem_retrieval_artifact = apply_relaymem_primary_recall_scope(
            relaymem_retrieval_artifact,
            scoped_store_root=relaymem_scoped_store_root,
            expected_namespace=route.memory_namespace,
            max_snippet_chars=config.memory.max_snippet_chars,
            max_snippet_candidates=config.memory.max_snippet_candidates,
            snippet_budget=config.memory.snippet_budget,
            chars_per_token=config.memory.chars_per_token,
        )
''',
    '''        if relaymem_character_partition_present:
            relaymem_retrieval_artifact = apply_relaymem_primary_recall_scope(
                relaymem_retrieval_artifact,
                scoped_store_root=relaymem_scoped_store_root,
                expected_namespace=route.memory_namespace,
                max_snippet_chars=config.memory.max_snippet_chars,
                max_snippet_candidates=config.memory.max_snippet_candidates,
                snippet_budget=config.memory.snippet_budget,
                chars_per_token=config.memory.chars_per_token,
            )
        else:
            relaymem_retrieval_artifact["primary_recall_projection"] = (
                build_relaymem_primary_recall_compat_projection(
                    relaymem_retrieval_artifact
                )
            )
''',
)
