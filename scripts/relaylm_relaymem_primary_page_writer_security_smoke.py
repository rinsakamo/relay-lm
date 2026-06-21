from __future__ import annotations

import json
import tempfile
from hashlib import sha256
from pathlib import Path

from relaylm.relaymem_primary_page_writer import apply_relaymem_primary_page_write
from relaylm_relaymem_primary_page_writer_smoke import _artifact


def _apply(artifact: dict, root: Path) -> dict:
    return apply_relaymem_primary_page_write(
        writer_handoff_artifact=artifact,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        parent = root / "memory/mem/primary/projects"
        parent.mkdir(parents=True)

        conflict = _artifact()
        target = root / conflict["handoffs"][0]["target_relative_path"]
        target.write_text("different", encoding="utf-8")
        result = _apply(conflict, root)
        assert result["status"] == "blocked"
        assert result["blocked_reasons"] == ["primary_page_writer_target_conflict"]
        assert target.read_text(encoding="utf-8") == "different"
        target.unlink()

        forged = _artifact()
        handoff = forged["handoffs"][0]
        forged_key = "f" * 64
        handoff["idempotency_key"] = forged_key
        handoff["target_relative_path"] = f"memory/mem/primary/projects/{forged_key}.md"
        old_line = next(
            line
            for line in handoff["page_markdown"].splitlines()
            if line.startswith("idempotency_key: ")
        )
        handoff["page_markdown"] = handoff["page_markdown"].replace(
            old_line, f"idempotency_key: {json.dumps(forged_key)}"
        )
        encoded = handoff["page_markdown"].encode("utf-8")
        handoff["page_bytes"] = len(encoded)
        handoff["page_digest"] = sha256(encoded).hexdigest()
        forged["projection"]["handoffs"][0]["page_bytes"] = len(encoded)
        result = _apply(forged, root)
        assert "primary_writer_handoff_idempotency_key_mismatch" in result[
            "blocked_reasons"
        ]
        assert not (parent / f"{forged_key}.md").exists()

        traversal = _artifact()
        traversal["handoffs"][0]["target_relative_path"] = "../escape.md"
        result = _apply(traversal, root)
        assert "primary_writer_handoff_target_path_invalid" in result["blocked_reasons"]
        assert not (root.parent / "escape.md").exists()

        unknown = _artifact()
        unknown["handoffs"][0]["secret_payload"] = "secret"
        result = _apply(unknown, root)
        assert result["blocked_reasons"] == ["primary_writer_handoff_fields_mismatch"]
        assert "secret" not in str(result["projection"])

        raw = _artifact()
        raw["handoffs"][0]["raw_source_text"] = "secret"
        result = _apply(raw, root)
        assert result["blocked_reasons"] == [
            "primary_writer_handoff_artifact_forbidden_content_field",
            "primary_writer_handoff_fields_mismatch",
        ]
        assert "secret" not in str(result["projection"])

        projection_leak = _artifact()
        projection_leak["projection"]["page_markdown"] = "secret"
        result = _apply(projection_leak, root)
        assert result["blocked_reasons"] == [
            "primary_writer_handoff_projection_fields_mismatch",
            "primary_writer_handoff_projection_content_field_present",
        ]
        assert "secret" not in str(result["projection"])

        numeric_bool = _artifact()
        numeric_bool["handoffs"][0]["writer_apply_eligible"] = 1
        result = _apply(numeric_bool, root)
        assert "primary_writer_handoff_writer_apply_eligible_invalid" in result[
            "blocked_reasons"
        ]

        symlink_root = root / "symlink-root"
        real_root = root / "real-root"
        (real_root / "memory/mem/primary/projects").mkdir(parents=True)
        symlink_root.symlink_to(real_root, target_is_directory=True)
        result = _apply(_artifact(), symlink_root)
        assert result["blocked_reasons"] == ["memory_store_root_symlink_blocked"]

        symlink_parent_root = root / "symlink-parent-root"
        (symlink_parent_root / "memory/mem/primary").mkdir(parents=True)
        external = root / "external"
        external.mkdir()
        (symlink_parent_root / "memory/mem/primary/projects").symlink_to(
            external, target_is_directory=True
        )
        result = _apply(_artifact(), symlink_parent_root)
        assert result["blocked_reasons"] == ["memory_store_target_symlink_blocked"]

        target_symlink_artifact = _artifact()
        symlink_target = (
            root / target_symlink_artifact["handoffs"][0]["target_relative_path"]
        )
        external_file = root / "outside.md"
        external_file.write_text("outside", encoding="utf-8")
        symlink_target.symlink_to(external_file)
        result = _apply(target_symlink_artifact, root)
        assert result["blocked_reasons"] == ["memory_store_target_symlink_blocked"]
        assert external_file.read_text(encoding="utf-8") == "outside"
        symlink_target.unlink()

        missing = root / "missing-root"
        missing.mkdir()
        result = _apply(_artifact(), missing)
        assert result["blocked_reasons"] == [
            "memory_store_primary_target_directory_missing"
        ]

    print("RelayMEM Primary page writer security smoke passed")


if __name__ == "__main__":
    main()
