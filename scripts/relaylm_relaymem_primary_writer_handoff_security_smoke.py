from __future__ import annotations

import tempfile
from pathlib import Path

from relaylm.relaymem_primary_writer_handoff import (
    build_relaymem_primary_writer_handoff_preflight,
)
from relaylm_relaymem_primary_writer_handoff_smoke import _artifact


def _run(candidate: dict, root: Path) -> dict:
    return build_relaymem_primary_writer_handoff_preflight(
        page_candidate_artifact=candidate,
        root_path=str(root),
        enabled=True,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        target_dir = root / "memory/mem/primary/projects"
        target_dir.mkdir(parents=True)

        traversal = _artifact()
        traversal["page_candidates"][0]["target_relative_path"] = "../escape.md"
        result = _run(traversal, root)
        assert "primary_page_candidate_target_path_invalid" in result["blocked_reasons"]

        secondary = _artifact()
        secondary["page_candidates"][0]["target_relative_path"] = (
            "memory/mem/secondary/projects/"
            + secondary["page_candidates"][0]["idempotency_key"]
            + ".md"
        )
        result = _run(secondary, root)
        assert "primary_page_candidate_target_path_mismatch" in result["blocked_reasons"]

        digest = _artifact()
        digest["page_candidates"][0]["page_digest"] = "0" * 64
        result = _run(digest, root)
        assert "primary_page_candidate_page_digest_mismatch" in result["blocked_reasons"]

        forbidden_content = _artifact()
        forbidden_content["page_candidates"][0]["raw_source_text"] = "secret"
        result = _run(forbidden_content, root)
        assert result["blocked_reasons"] == [
            "primary_page_candidate_artifact_forbidden_content_field"
        ]
        assert "secret" not in str(result["projection"])

        raw_history = _artifact()
        raw_history["page_candidates"][0]["raw_message_history_included"] = True
        result = _run(raw_history, root)
        assert (
            "primary_page_candidate_raw_message_history_included_invalid"
            in result["blocked_reasons"]
        )

        numeric_bool = _artifact()
        numeric_bool["page_candidates"][0]["writes_memory"] = 0
        result = _run(numeric_bool, root)
        assert "primary_page_candidate_writes_memory_invalid" in result["blocked_reasons"]

        arbitrary = _artifact()
        arbitrary["blocked_reasons"] = ["private/content/value"]
        result = _run(arbitrary, root)
        assert result["blocked_reasons"] == ["primary_page_candidate_artifact_blocked"]
        assert "private/content/value" not in str(result["projection"])

        conflict = _artifact()
        target = root / conflict["page_candidates"][0]["target_relative_path"]
        target.write_text("different", encoding="utf-8")
        result = _run(conflict, root)
        assert result["blocked_reasons"] == ["memory_store_target_conflict"]
        target.unlink()

        symlink_store_root = root / "symlink-store"
        external_target = root / "external-projects"
        external_target.mkdir()
        (symlink_store_root / "memory/mem/primary").mkdir(parents=True)
        (symlink_store_root / "memory/mem/primary/projects").symlink_to(
            external_target, target_is_directory=True
        )
        result = _run(_artifact(), symlink_store_root)
        assert result["blocked_reasons"] == ["memory_store_target_symlink_blocked"]

        missing_dir_root = root / "missing-layout"
        missing_dir_root.mkdir()
        result = _run(_artifact(), missing_dir_root)
        assert "memory_store_primary_target_directory_missing" in result["blocked_reasons"]

        malformed_page = _artifact()
        malformed_page["page_candidates"][0]["page_markdown"] = "\ud800"
        malformed_page["page_candidates"][0]["page_bytes"] = 0
        result = _run(malformed_page, root)
        assert "primary_page_candidate_page_utf8_invalid" in result["blocked_reasons"]

    print("RelayMEM Primary writer handoff security smoke passed")


if __name__ == "__main__":
    main()
