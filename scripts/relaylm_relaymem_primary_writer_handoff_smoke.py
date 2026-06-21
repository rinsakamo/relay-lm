from __future__ import annotations

import json
import tempfile
from hashlib import sha256
from pathlib import Path

from relaylm.relaymem_primary_writer_handoff import (
    build_relaymem_primary_writer_handoff_preflight,
)


def _artifact(
    *,
    upstream_eligible: bool = False,
    summary: str = "A bounded project event was remembered.",
) -> dict:
    idempotency_key = sha256(b"m3d-idempotency").hexdigest()
    lineage_fingerprint = sha256(b"m3d-lineage").hexdigest()
    metadata = {
        "summary": summary,
        "schema_version": "relaymem.primary_page.v0",
        "memory_layer": "primary",
        "memory_kind": "recent_project_event",
        "source_event_kind": "turn",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": "character:test",
        "lineage_fingerprint": lineage_fingerprint,
        "idempotency_key": idempotency_key,
        "summary_origin": "trusted_in_process_summary",
        "content_role": "evidence",
        "title": "Project event",
    }
    front = "\n".join(
        f"{key}: {json.dumps(str(value), ensure_ascii=False)}"
        for key, value in metadata.items()
    )
    page = f"---\n{front}\n---\n# Primary memory\n\n## Summary\n\n{summary.strip()}\n"
    encoded = page.encode("utf-8")
    candidate = {
        "schema_version": "relaymem.primary_page_candidate.v0",
        "runtime_private": True,
        "content_included": True,
        "raw_source_text_included": False,
        "raw_message_history_included": False,
        "raw_affect_estimates_included": False,
        "candidate_id": "primary:test",
        "source_event_kind": "turn",
        "memory_layer": "primary",
        "memory_kind": "recent_project_event",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": "character:test",
        "target_category": "primary_projects",
        "target_relative_path": f"memory/mem/primary/projects/{idempotency_key}.md",
        "lineage_fingerprint": lineage_fingerprint,
        "idempotency_key": idempotency_key,
        "summary_origin": "trusted_in_process_summary",
        "summary_chars": len(summary),
        "page_markdown": page,
        "page_bytes": len(encoded),
        "page_digest": sha256(encoded).hexdigest(),
        "status": "ready",
        "writer_handoff_eligible": upstream_eligible,
        "writes_memory": False,
        "applied": False,
        "blocked_reasons": [],
    }
    return {
        "schema_version": "relaymem.primary_page_candidate_dry_run.v0",
        "diagnostics_only": True,
        "helper_only": True,
        "read_only": True,
        "runtime_private_candidates": True,
        "enabled": True,
        "dry_run_only": not upstream_eligible,
        "apply_enabled": upstream_eligible,
        "write_apply_supported": False,
        "apply_allowed": False,
        "writes_memory": False,
        "mutates_soul": False,
        "invokes_slp": False,
        "lab_api_exposed": False,
        "page_candidate_count": 1,
        "page_candidates": [candidate],
        "blocked_reasons": [],
        "projection": {},
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        target_dir = root / "memory/mem/primary/projects"
        target_dir.mkdir(parents=True)

        disabled = build_relaymem_primary_writer_handoff_preflight(
            page_candidate_artifact=_artifact(),
            root_path=str(root),
        )
        assert disabled["handoff_count"] == 0
        assert "primary_writer_handoff_disabled" in disabled["blocked_reasons"]

        dry_run = build_relaymem_primary_writer_handoff_preflight(
            page_candidate_artifact=_artifact(),
            root_path=str(root),
            enabled=True,
        )
        assert dry_run["handoff_count"] == 1
        handoff = dry_run["handoffs"][0]
        assert handoff["preflight_status"] == "ready"
        assert handoff["writer_apply_eligible"] is False
        assert dry_run["writes_memory"] is False
        assert dry_run["projection"]["page_markdown_included"] is False
        assert "page_markdown" not in dry_run["projection"]["handoffs"][0]

        apply_ready = build_relaymem_primary_writer_handoff_preflight(
            page_candidate_artifact=_artifact(upstream_eligible=True),
            root_path=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert apply_ready["handoff_count"] == 1
        assert apply_ready["handoffs"][0]["writer_apply_eligible"] is True
        assert apply_ready["writes_memory"] is False

        candidate = _artifact(upstream_eligible=True)
        page = candidate["page_candidates"][0]
        existing = root / page["target_relative_path"]
        existing.write_text(page["page_markdown"], encoding="utf-8")
        idempotent = build_relaymem_primary_writer_handoff_preflight(
            page_candidate_artifact=candidate,
            root_path=str(root),
            enabled=True,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert idempotent["handoff_count"] == 1
        assert idempotent["handoffs"][0]["preflight_status"] == "already_applied"
        assert idempotent["handoffs"][0]["idempotent_noop"] is True
        assert idempotent["handoffs"][0]["writer_apply_eligible"] is False

    print("RelayMEM Primary writer handoff smoke passed")


if __name__ == "__main__":
    main()
