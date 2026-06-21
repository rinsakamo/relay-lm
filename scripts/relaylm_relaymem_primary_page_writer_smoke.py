from __future__ import annotations

import json
import tempfile
from hashlib import sha256
from pathlib import Path

from relaylm.relaymem_primary_page_writer import apply_relaymem_primary_page_write


def _stable(parts: list[str]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _artifact(summary: str = "A bounded project event was remembered.") -> dict:
    namespace = "character:test"
    event_kind = "turn"
    lineage = sha256(b"m3e-lineage").hexdigest()
    candidate_id = "primary:test"
    memory_kind = "recent_project_event"
    category = "primary_projects"
    key = _stable([
        "relaymem-primary-write-preflight-v0",
        namespace,
        event_kind,
        lineage,
        candidate_id,
        event_kind,
        "primary",
        memory_kind,
        "free_to_update",
    ])
    metadata = {
        "summary": summary,
        "schema_version": "relaymem.primary_page.v0",
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "source_event_kind": event_kind,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": namespace,
        "lineage_fingerprint": lineage,
        "idempotency_key": key,
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
        "title": "Project event",
    }
    front = "\n".join(
        f"{name}: {json.dumps(str(value), ensure_ascii=False)}"
        for name, value in metadata.items()
    )
    page = f"---\n{front}\n---\n# Primary memory\n\n## Summary\n\n{summary}\n"
    data = page.encode("utf-8")
    target = f"memory/mem/primary/projects/{key}.md"
    handoff = {
        "schema_version": "relaymem.primary_writer_handoff.v0",
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "candidate_id": candidate_id,
        "source_event_kind": event_kind,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": namespace,
        "target_category": category,
        "target_relative_path": target,
        "lineage_fingerprint": lineage,
        "idempotency_key": key,
        "page_markdown": page,
        "page_bytes": len(data),
        "page_digest": sha256(data).hexdigest(),
        "preflight_status": "ready",
        "target_exists": False,
        "target_digest_matches": False,
        "idempotent_noop": False,
        "upstream_writer_handoff_eligible": True,
        "writer_apply_eligible": True,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "applied": False,
        "blocked_reasons": [],
    }
    projection_item = {
        "operation_index": 0,
        "source_event_kind": event_kind,
        "memory_layer": "primary",
        "memory_kind": memory_kind,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "target_category": category,
        "preflight_status": "ready",
        "target_exists": False,
        "target_digest_matches": False,
        "idempotent_noop": False,
        "writer_apply_eligible": True,
        "page_bytes": len(data),
    }
    projection = {
        "schema_version": "relaymem.primary_writer_handoff_projection.v0",
        "diagnostics_only": True,
        "content_free": True,
        "content_included": False,
        "store_root_path_included": False,
        "candidate_id_included": False,
        "namespace_included": False,
        "target_path_included": False,
        "lineage_fingerprint_included": False,
        "idempotency_key_included": False,
        "page_markdown_included": False,
        "page_digest_included": False,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "handoff_count": 1,
        "status_counts": {"ready": 1},
        "target_category_counts": {category: 1},
        "writer_apply_eligible_count": 1,
        "root_present": True,
        "target_parent_present": True,
        "target_exists": False,
        "target_digest_matches": False,
        "idempotent_noop": False,
        "blocked_reasons": [],
        "handoffs": [projection_item],
    }
    return {
        "schema_version": "relaymem.primary_writer_handoff_preflight.v0",
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "runtime_private_handoffs": True,
        "enabled": True,
        "dry_run_only": False,
        "apply_enabled": True,
        "write_apply_supported": False,
        "apply_allowed": False,
        "writes_memory": False,
        "updates_index": False,
        "updates_log": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "runtime_wired": False,
        "visible_response_changed": False,
        "store_root_configured": True,
        "page_candidate_valid": True,
        "handoff_count": 1,
        "handoffs": [handoff],
        "blocked_reasons": [],
        "projection": projection,
    }


def _root() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory()


def main() -> None:
    with _root() as temporary:
        root = Path(temporary)
        (root / "memory/mem/primary/projects").mkdir(parents=True)
        artifact = _artifact()
        target = root / artifact["handoffs"][0]["target_relative_path"]

        disabled = apply_relaymem_primary_page_write(
            writer_handoff_artifact=artifact,
            root_path=str(root),
        )
        assert disabled["status"] == "disabled"
        assert disabled["writes_memory"] is False
        assert not target.exists()

        dry_run = apply_relaymem_primary_page_write(
            writer_handoff_artifact=artifact,
            root_path=str(root),
            enabled=True,
        )
        assert dry_run["status"] == "dry_run_ready"
        assert dry_run["receipt"]["status"] == "dry_run_ready"
        assert dry_run["writes_memory"] is False
        assert not target.exists()

        applied = apply_relaymem_primary_page_write(
            writer_handoff_artifact=artifact,
            root_path=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert applied["status"] == "applied"
        assert applied["writes_memory"] is True
        assert applied["page_applied"] is True
        assert applied["durability_confirmed"] is True
        assert applied["updates_index"] is False
        assert applied["updates_log"] is False
        assert target.read_text(encoding="utf-8") == artifact["handoffs"][0]["page_markdown"]
        assert not list(target.parent.glob(".relaymem-*.tmp"))

        repeated = apply_relaymem_primary_page_write(
            writer_handoff_artifact=artifact,
            root_path=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert repeated["status"] == "already_applied"
        assert repeated["writes_memory"] is False
        assert repeated["idempotent_noop"] is True
        assert repeated["durability_confirmed"] is False
        assert repeated["receipt"]["page_digest"] == artifact["handoffs"][0]["page_digest"]

        projection = applied["projection"]
        for forbidden in (
            str(root),
            artifact["handoffs"][0]["candidate_id"],
            artifact["handoffs"][0]["namespace"],
            artifact["handoffs"][0]["target_relative_path"],
            artifact["handoffs"][0]["idempotency_key"],
            artifact["handoffs"][0]["page_digest"],
            artifact["handoffs"][0]["page_markdown"],
        ):
            assert forbidden not in str(projection)

    print("RelayMEM Primary page writer smoke passed")


if __name__ == "__main__":
    main()
