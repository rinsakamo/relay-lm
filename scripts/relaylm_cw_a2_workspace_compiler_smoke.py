"""CW-A2 workspace compiler projection smoke."""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from relaylm.character_workspace import (
    EXPECTED_ARTIFACTS,
    REQUIRED_SOURCE_FILENAMES,
    build_character_workspace_compiler_projection,
    compile_character_workspace,
)


def _write_required_sources(root: Path) -> None:
    for filename in REQUIRED_SOURCE_FILENAMES:
        source_name = filename.removesuffix(".md")
        root.joinpath(filename).write_text(
            f"# {source_name}\n\nstatus:: active\n\n{source_name} bounded source body\n",
            encoding="utf-8",
        )


def _write_fixture(root: Path) -> None:
    root.mkdir(parents=True)
    _write_required_sources(root)
    (root / "LORE.md").write_text("# Lore\n\nstatus:: active\n", encoding="utf-8")

    (root / "scenes").mkdir()
    (root / "scenes" / "development_review.md").write_text(
        "# Development review\n\nstatus:: active\n\nPRIVATE_SCENE_BODY\n",
        encoding="utf-8",
    )
    (root / "scenes" / "_inbox").mkdir()
    (root / "scenes" / "_inbox" / "draft.md").write_text(
        "# Draft scene\n\nstatus:: draft\n\nPRIVATE_INBOX_SCENE_BODY\n",
        encoding="utf-8",
    )

    (root / "relationships").mkdir()
    (root / "relationships" / "user.md").write_text(
        "# User\n\nstatus:: active\n\nPRIVATE_RELATIONSHIP_BODY\n",
        encoding="utf-8",
    )
    (root / "relationships" / "_inbox").mkdir()
    (root / "relationships" / "_inbox" / "candidate.md").write_text(
        "# Candidate\n\nPRIVATE_RELATIONSHIP_INBOX_BODY\n",
        encoding="utf-8",
    )

    (root / "memory").mkdir()
    (root / "memory" / "core.md").write_text(
        "# Core memory\n\n"
        "## Target user direction ^mem-relaylm-target-user\n\n"
        "status:: active\n"
        "importance:: high\n\n"
        "PRIVATE_MEMORY_BODY\n\n"
        "## Duplicate anchored note ^mem-relaylm-target-user\n\n"
        "status:: active\n"
        "importance:: high\n\n"
        "PRIVATE_MEMORY_BODY_DUPLICATE_ANCHOR\n",
        encoding="utf-8",
    )
    (root / "memory" / "inbox").mkdir()
    (root / "memory" / "inbox" / "candidate.md").write_text(
        "# Candidate memory\n\nstatus:: draft\n\nPRIVATE_MEMORY_INBOX_BODY\n",
        encoding="utf-8",
    )
    (root / "memory" / "forgotten").mkdir()
    (root / "memory" / "forgotten" / "old.md").write_text(
        "# Forgotten memory\n\nstatus:: forgotten\n\nPRIVATE_FORGOTTEN_MEMORY_BODY\n",
        encoding="utf-8",
    )


def _artifact_json(result: object, name: str) -> dict[str, object]:
    return json.loads(result.artifact_map()[name].text())


def _artifact_jsonl(result: object, name: str) -> list[dict[str, object]]:
    text = result.artifact_map()[name].text()
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert_no_abs_paths(result: object, root: Path) -> None:
    serialized = _serialized([artifact.text() for artifact in result.artifacts])
    forbidden = (str(root), str(root.resolve()), str(root.parent), tempfile.gettempdir())
    for token in forbidden:
        if token:
            assert token not in serialized, token


def _assert_no_timestamps_or_uuids(result: object) -> None:
    serialized = _serialized([artifact.text() for artifact in result.artifacts])
    assert "generated_at" not in serialized
    assert "created_at" not in serialized
    assert "updated_at" not in serialized
    uuid_re = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", re.I)
    assert not uuid_re.search(serialized), serialized


def _assert_public_projection_content_free(projection: dict[str, object]) -> None:
    serialized = _serialized(projection)
    assert projection["content_free"] is True
    for token in (
        "PRIVATE_MEMORY_BODY",
        "PRIVATE_RELATIONSHIP_BODY",
        "PRIVATE_SCENE_BODY",
        "PRIVATE_FORGOTTEN_MEMORY_BODY",
        "runtime-private-payload",
        "queue-record-123",
    ):
        assert token not in serialized, token


def _list_files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def _memory_unit_ids(result: object) -> set[str]:
    rows = _artifact_jsonl(result, "memory_units.jsonl")
    return {str(row["unit_id"]) for row in rows}


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "characters" / "koyomi"
        _write_fixture(root)

        dry = compile_character_workspace(root)
        assert dry.is_valid is True
        assert tuple(artifact.name for artifact in dry.artifacts) == EXPECTED_ARTIFACTS
        assert not (root / ".relaylm" / "build").exists(), "dry-run wrote build artifacts"

        for artifact in dry.artifacts:
            assert artifact.text().endswith("\n")
            if artifact.name.endswith(".json"):
                json.loads(artifact.text())
            else:
                _artifact_jsonl(dry, artifact.name)

        _assert_no_abs_paths(dry, root)
        _assert_no_timestamps_or_uuids(dry)

        before_files = _list_files(root)
        written = compile_character_workspace(root, write=True)
        assert written.is_valid is True
        after_files = _list_files(root)
        created_files = after_files - before_files
        assert created_files == {f".relaylm/build/{name}" for name in EXPECTED_ARTIFACTS}, created_files

        repeated = compile_character_workspace(root)
        assert {artifact.name: artifact.content for artifact in written.artifacts} == {
            artifact.name: artifact.content for artifact in repeated.artifacts
        }

        manifest = _artifact_json(written, "character_manifest.json")
        assert manifest["required_source_presence"]["SOUL.md"] is True
        assert manifest["optional_lore_presence"] is True
        assert manifest["lowercase_wiki_domain_presence"]["memory"] is True
        assert manifest["validation_status"] == "valid"
        assert "tier1" in manifest["tier_summary"]

        memory_rows = _artifact_jsonl(written, "memory_units.jsonl")
        forgotten = [row for row in memory_rows if row["source_path"].startswith("memory/forgotten/")]
        assert forgotten
        assert all(row["prompt_candidate"] is False and row["tier"] == "excluded" for row in forgotten)

        memory_inbox = [row for row in memory_rows if row["source_path"].startswith("memory/inbox/")]
        assert memory_inbox
        assert all(row["prompt_candidate"] is False and row["candidate_only"] is True for row in memory_inbox)

        duplicate_anchor_units = [
            row for row in memory_rows
            if row["source_path"] == "memory/core.md" and "mem-relaylm-target-user" in row["unit_id"]
        ]
        duplicate_anchor_ids = [row["unit_id"] for row in duplicate_anchor_units]
        assert len(duplicate_anchor_ids) == 2
        assert len(set(duplicate_anchor_ids)) == 2, duplicate_anchor_ids
        assert all("memory-core.md" in unit_id for unit_id in duplicate_anchor_ids)

        scene_rows = _artifact_jsonl(written, "scene_units.jsonl")
        scene_inbox = [row for row in scene_rows if row["source_path"].startswith("scenes/_inbox/")]
        assert scene_inbox
        assert all(row["prompt_candidate"] is False and row["candidate_only"] is True for row in scene_inbox)

        rel_projection = _artifact_json(written, "relationship_projection.json")
        rel_inbox = [
            row for row in rel_projection["target_relationship_units"]
            if row["source_path"].startswith("relationships/_inbox/")
        ]
        assert rel_inbox
        assert all(row["prompt_candidate"] is False for row in rel_inbox)

        context = _artifact_json(written, "context_projection.json")
        assert context["tier_order"] == ["tier0", "tier1", "tier2", "tier3"]
        assert context["dynamic_suffix_contract"]["belongs_last"] is True
        assert context["dynamic_suffix_contract"]["runtime_injection_out_of_scope"] is True

        projection = build_character_workspace_compiler_projection(root)
        _assert_public_projection_content_free(projection)

        original_memory_ids = _memory_unit_ids(written)
        original_style_hash = written.artifact_map()["style_projection.json"].content_hash
        original_context_hash = written.artifact_map()["context_projection.json"].content_hash
        root.joinpath("STYLE.md").write_text(
            "# STYLE\n\nstatus:: active\n\nchanged bounded style source\n",
            encoding="utf-8",
        )
        style_changed = compile_character_workspace(root)
        assert style_changed.artifact_map()["style_projection.json"].content_hash != original_style_hash
        assert style_changed.artifact_map()["context_projection.json"].content_hash != original_context_hash
        assert _memory_unit_ids(style_changed) == original_memory_ids

        stable_hashes_after_style = _artifact_json(style_changed, "character_manifest.json")["source_file_hashes"]
        memory_hash_before = style_changed.artifact_map()["memory_units.jsonl"].content_hash
        context_hash_before_memory = style_changed.artifact_map()["context_projection.json"].content_hash
        (root / "memory" / "core.md").write_text(
            "# Core memory\n\n"
            "## Target user direction ^mem-relaylm-target-user\n\n"
            "status:: active\n"
            "importance:: high\n\n"
            "PRIVATE_MEMORY_BODY_CHANGED\n",
            encoding="utf-8",
        )
        memory_changed = compile_character_workspace(root)
        assert memory_changed.artifact_map()["memory_units.jsonl"].content_hash != memory_hash_before
        assert memory_changed.artifact_map()["context_projection.json"].content_hash != context_hash_before_memory
        stable_hashes_after_memory = _artifact_json(memory_changed, "character_manifest.json")["source_file_hashes"]
        assert stable_hashes_after_memory == stable_hashes_after_style

        assert _memory_unit_ids(memory_changed) == _memory_unit_ids(style_changed) - {duplicate_anchor_ids[1]}

        state_root = root / ".relaylm" / "state"
        assert not state_root.exists(), ".relaylm/state was unexpectedly written"

        missing_root = Path(tmp) / "characters" / "missing"
        missing_root.mkdir()
        for filename in REQUIRED_SOURCE_FILENAMES:
            if filename != "SOUL.md":
                missing_root.joinpath(filename).write_text("# Source\n", encoding="utf-8")
        missing = compile_character_workspace(missing_root)
        assert missing.is_valid is False
        assert "missing_required_source" in missing.blocking_reason_ids

        traversal = compile_character_workspace(root / ".." / "koyomi")
        assert traversal.is_valid is False
        assert "path_traversal_rejected" in traversal.blocking_reason_ids

        outside = Path(tmp) / "outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        symlink_root = Path(tmp) / "characters" / "symlink"
        _write_fixture(symlink_root)
        try:
            (symlink_root / "memory" / "escape.md").symlink_to(outside)
        except (OSError, NotImplementedError):
            pass
        else:
            symlink_result = compile_character_workspace(symlink_root)
            assert symlink_result.is_valid is False
            assert "symlink_escape_rejected" in symlink_result.blocking_reason_ids

        artifact_symlink_root = Path(tmp) / "characters" / "artifact-symlink"
        _write_fixture(artifact_symlink_root)
        artifact_build_root = artifact_symlink_root / ".relaylm" / "build"
        artifact_build_root.mkdir(parents=True)
        original_style = (artifact_symlink_root / "STYLE.md").read_text(encoding="utf-8")
        try:
            (artifact_build_root / "style_projection.json").symlink_to("../../STYLE.md")
        except (OSError, NotImplementedError):
            pass
        else:
            try:
                compile_character_workspace(artifact_symlink_root, write=True)
            except ValueError as exc:
                assert "symlink" in str(exc)
            else:
                raise AssertionError("artifact symlink write was not rejected")
            assert (artifact_symlink_root / "STYLE.md").read_text(encoding="utf-8") == original_style

    print("CW-A2 workspace compiler projection smoke passed")


if __name__ == "__main__":
    main()
