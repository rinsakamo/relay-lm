"""Security and fail-closed smoke for Phase I-1 scoped Primary MEM recall."""
from __future__ import annotations

import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path

from relaylm._relaymem_primary_page_writer_common import stable_hash
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)
from relaylm_phase6c1_primary_worker_test_support import prepare_store

CHARACTER = "security-a"
OTHER_CHARACTER = "security-b"
NAMESPACE = "security-namespace-canary"
SUMMARY = "好きな飲み物 は 紅茶 です。"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def broad_artifact(
    path: str,
    *,
    decision: str = "eligible_but_not_applied",
    duplicate: bool = False,
) -> dict[str, object]:
    candidate = {
        "path": path,
        "source": "mem_page",
        "reason": "keyword_match",
        "estimated_chars": len(SUMMARY),
        "estimated_tokens": 8,
        "memory_layer": "primary",
        "layout_profile": "target_primary_secondary",
        "applied_to_ctx": False,
    }
    return {
        "artifact_version": "relaymem_retrieval.v0",
        "snippet_apply_decision": decision,
        "selected_mem_candidates": (
            [candidate, dict(candidate)] if duplicate else [candidate]
        ),
    }


def write_memory(root: Path) -> str:
    identity = sha256(b"phase-i1-security-memory").hexdigest()
    lineage = sha256(b"phase-i1-security-lineage").hexdigest()
    relative = f"memory/mem/primary/relationships/{identity}.md"
    metadata = {
        "summary": SUMMARY,
        "schema_version": "relaymem.primary_page.v0",
        "memory_layer": "primary",
        "memory_kind": "relationship_moment",
        "source_event_kind": "turn",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": NAMESPACE,
        "lineage_fingerprint": lineage,
        "idempotency_key": identity,
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
        "title": "飲み物",
    }
    page = (
        "---\n"
        + "\n".join(
            f"{key}: {json.dumps(str(value), ensure_ascii=False)}"
            for key, value in metadata.items()
        )
        + f"\n---\n# Primary memory\n\n## Summary\n\n{SUMMARY}\n"
    )
    page_path = root / relative
    page_path.write_text(page, encoding="utf-8")
    digest = sha256(page.encode("utf-8")).hexdigest()
    index_id = stable_hash(
        ("relaymem-primary-index-entry-v0", identity, digest, relative)
    )
    log_id = stable_hash(
        ("relaymem-primary-log-entry-v0", identity, digest, relative)
    )
    index_entry = {
        "schema_version": "relaymem.primary_index_entry.v0",
        "entry_id": index_id,
        "page_relative_path": relative,
        "memory_layer": "primary",
        "memory_kind": "relationship_moment",
        "target_category": "primary_relationships",
        "namespace": NAMESPACE,
        "source_event_kind": "turn",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "idempotency_key": identity,
        "page_digest": digest,
    }
    log_entry = {
        "schema_version": "relaymem.primary_log_entry.v0",
        "entry_id": log_id,
        "index_entry_id": index_id,
        "operation": "primary_page_published",
        "page_relative_path": relative,
        "memory_layer": "primary",
        "memory_kind": "relationship_moment",
        "target_category": "primary_relationships",
        "namespace": NAMESPACE,
        "source_event_kind": "turn",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "lineage_fingerprint": lineage,
        "idempotency_key": identity,
        "page_digest": digest,
    }
    (root / "memory/mem/index.md").write_text(
        "# Index\n<!-- relaymem-primary-index-entry-v0 "
        + json.dumps(
            index_entry,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + " -->\n",
        encoding="utf-8",
    )
    (root / "memory/mem/log.md").write_text(
        "# Log\n<!-- relaymem-primary-log-entry-v0 "
        + json.dumps(
            log_entry,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + " -->\n",
        encoding="utf-8",
    )
    return relative


def apply_scope(
    value: dict[str, object],
    root: Path,
    namespace: str = NAMESPACE,
    max_chars: int = 512,
    token_budget: int = 512,
) -> dict[str, object]:
    return apply_relaymem_primary_recall_scope(
        value,
        scoped_store_root=str(root),
        expected_namespace=namespace,
        max_snippet_chars=max_chars,
        max_snippet_candidates=3,
        snippet_budget=token_budget,
        chars_per_token=4,
    )


def assert_public_projection_content_free(projection: object) -> None:
    text = repr(projection)
    for forbidden in (
        SUMMARY,
        NAMESPACE,
        "security-a",
        "security-b",
        "memory/mem/",
        "idempotency_key",
        "lineage_fingerprint",
        "page_digest",
    ):
        require(forbidden not in text, (forbidden, text))


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        first_value = resolve_relaymem_character_store_root(str(base), CHARACTER)
        other_value = resolve_relaymem_character_store_root(str(base), OTHER_CHARACTER)
        require(first_value is not None and other_value is not None, "scope resolver")
        first = Path(first_value)
        other = Path(other_value)
        prepare_store(first)
        prepare_store(other)
        relative = write_memory(first)

        valid = apply_scope(broad_artifact(relative, duplicate=True), first)
        runtime = valid["primary_recall_runtime"]
        projection = valid["primary_recall_projection"]
        require(runtime["selected_count"] == 1, runtime)
        require(projection["selected_count"] == 1, projection)
        require(valid["snippet_runtime_injection_plan"]["preview_text"], valid)
        require(
            "primary_recall_duplicate_identity_deduped"
            in runtime["blocked_reason_ids"],
            runtime,
        )
        assert_public_projection_content_free(projection)

        wrong_namespace = apply_scope(
            broad_artifact(relative),
            first,
            "wrong-namespace",
        )
        require(
            wrong_namespace["primary_recall_projection"]["selected_count"] == 0,
            wrong_namespace["primary_recall_projection"],
        )
        wrong_character = apply_scope(broad_artifact(relative), other)
        require(
            wrong_character["primary_recall_projection"]["selected_count"] == 0,
            wrong_character["primary_recall_projection"],
        )
        blocked_scene = apply_scope(
            broad_artifact(relative, decision="blocked_scene_policy"),
            first,
        )
        require(
            blocked_scene["primary_recall_projection"]["selected_count"] == 0,
            blocked_scene["primary_recall_projection"],
        )
        bounded_chars = apply_scope(broad_artifact(relative), first, max_chars=4)
        require(
            bounded_chars["primary_recall_projection"]["selected_count"] == 0,
            bounded_chars["primary_recall_projection"],
        )
        bounded_tokens = apply_scope(
            broad_artifact(relative),
            first,
            token_budget=1,
        )
        require(
            bounded_tokens["primary_recall_projection"]["selected_count"] == 0,
            bounded_tokens["primary_recall_projection"],
        )

        availability_only = broad_artifact(relative)
        availability_only["selected_mem_candidates"][0]["reason"] = (
            "candidate_available"
        )
        unrelated = apply_scope(availability_only, first)
        require(
            unrelated["primary_recall_projection"]["selected_count"] == 0,
            unrelated["primary_recall_projection"],
        )

        page = first / relative
        original_page = page.read_bytes()
        page.write_bytes(original_page + b"corrupt")
        corrupt = apply_scope(broad_artifact(relative), first)
        require(
            corrupt["primary_recall_projection"]["selected_count"] == 0,
            corrupt["primary_recall_projection"],
        )
        page.write_bytes(original_page)

        index = first / "memory/mem/index.md"
        original_index = index.read_text(encoding="utf-8")
        index.write_text("# Index\n", encoding="utf-8")
        mismatch = apply_scope(broad_artifact(relative), first)
        require(
            mismatch["primary_recall_projection"]["selected_count"] == 0,
            mismatch["primary_recall_projection"],
        )
        index.write_text(original_index, encoding="utf-8")

        if hasattr(os, "symlink"):
            real = page.with_suffix(".real.md")
            page.rename(real)
            try:
                page.symlink_to(real.name)
                linked = apply_scope(broad_artifact(relative), first)
                require(
                    linked["primary_recall_projection"]["selected_count"] == 0,
                    linked["primary_recall_projection"],
                )
            finally:
                if page.is_symlink():
                    page.unlink()
                real.rename(page)

    print("Phase I-1 scoped Primary MEM recall security smoke passed")


if __name__ == "__main__":
    main()
