from __future__ import annotations

import tempfile
from hashlib import sha256
from pathlib import Path

from relaylm.relaymem_primary_writer_handoff import (
    build_relaymem_primary_writer_handoff_preflight,
)
from relaylm_relaymem_primary_writer_handoff_smoke import _artifact


def _run(artifact: dict, root: Path, **kwargs: object) -> dict:
    return build_relaymem_primary_writer_handoff_preflight(
        page_candidate_artifact=artifact,
        root_path=str(root),
        enabled=True,
        **kwargs,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "memory/mem/primary/projects").mkdir(parents=True)

        metadata_mismatch = _artifact()
        page = metadata_mismatch["page_candidates"][0]
        page["page_markdown"] = page["page_markdown"].replace(
            'memory_kind: "recent_project_event"',
            'memory_kind: "relationship_moment"',
        )
        page["page_bytes"] = len(page["page_markdown"].encode("utf-8"))
        page["page_digest"] = sha256(page["page_markdown"].encode("utf-8")).hexdigest()
        result = _run(metadata_mismatch, root)
        assert "primary_page_candidate_page_memory_kind_mismatch" in result["blocked_reasons"]

        title_newline = _artifact()
        page = title_newline["page_candidates"][0]
        page["page_markdown"] = page["page_markdown"].replace(
            'title: "Project event"',
            'title: "Project\\nEvent"',
        )
        page["page_bytes"] = len(page["page_markdown"].encode("utf-8"))
        page["page_digest"] = sha256(page["page_markdown"].encode("utf-8")).hexdigest()
        result = _run(title_newline, root)
        assert "primary_page_candidate_page_title_invalid" in result["blocked_reasons"]

        front_matter_key = _artifact()
        page = front_matter_key["page_candidates"][0]
        page["page_markdown"] = page["page_markdown"].replace(
            'content_role: "evidence"\n', ""
        )
        page["page_bytes"] = len(page["page_markdown"].encode("utf-8"))
        page["page_digest"] = sha256(page["page_markdown"].encode("utf-8")).hexdigest()
        result = _run(front_matter_key, root)
        assert "primary_page_candidate_page_front_matter_keys_invalid" in result["blocked_reasons"]

        noncanonical = _artifact()
        noncanonical["page_candidates"][0]["candidate_id"] = " primary:test "
        result = _run(noncanonical, root)
        assert "primary_page_candidate_candidate_id_invalid" in result["blocked_reasons"]

        upstream_not_eligible = _artifact()
        result = _run(
            upstream_not_eligible,
            root,
            dry_run_only=False,
            apply_enabled=True,
        )
        assert result["blocked_reasons"] == [
            "primary_page_candidate_writer_handoff_not_eligible"
        ]

        invalid_root = build_relaymem_primary_writer_handoff_preflight(
            page_candidate_artifact=_artifact(),
            root_path="bad\nroot",
            enabled=True,
        )
        assert invalid_root["blocked_reasons"] == ["memory_store_root_invalid"]

        malformed_existing = _artifact()
        target = root / malformed_existing["page_candidates"][0]["target_relative_path"]
        target.write_bytes(b"\xff")
        result = _run(malformed_existing, root)
        assert result["blocked_reasons"] == ["memory_store_target_malformed_utf8"]

    print("RelayMEM Primary writer handoff review smoke passed")


if __name__ == "__main__":
    main()
