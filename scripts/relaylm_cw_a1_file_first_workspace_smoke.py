"""CW-A1 file-first Character Workspace contract smoke."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from relaylm.character_workspace import (
    OPTIONAL_SOURCE_FILENAMES,
    REQUIRED_SOURCE_FILENAMES,
    CharacterWorkspacePathKind,
    CharacterWorkspaceValidationStatus,
    build_character_workspace_manifest,
    character_workspace_layout,
    classify_character_workspace_path,
    parse_character_source_file,
    parse_markdown_blocks,
    validate_character_workspace,
)


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert_content_free(value: object) -> None:
    serialized = _serialized(value)
    forbidden = (
        "SECRET_MARKDOWN_BODY",
        "SECRET_PRIVATE_PATH",
        "queue-record-123",
        "runtime-private-payload",
        "^mem-relaylm-target-user",
        "mem-relaylm-target-user",
    )
    for token in forbidden:
        assert token not in serialized, serialized


def _write_required_sources(root: Path) -> None:
    for filename in REQUIRED_SOURCE_FILENAMES:
        root.joinpath(filename).write_text(
            f"# {filename.removesuffix('.md')}\n\nstatus:: active\n\nbounded source\n",
            encoding="utf-8",
        )


def main() -> None:
    layout = character_workspace_layout()
    assert layout.required_source_filenames == REQUIRED_SOURCE_FILENAMES
    assert layout.optional_source_filenames == OPTIONAL_SOURCE_FILENAMES
    assert "SOUL.md" in layout.required_source_filenames
    assert "LORE.md" in layout.optional_source_filenames
    assert "scenes/_inbox" in layout.expected_directories
    assert ".relaylm/state" in layout.internal_directories

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "characters" / "koyomi"
        root.mkdir(parents=True)
        _write_required_sources(root)

        (root / "LORE.md").write_text("# Lore\n\noptional:: yes\n", encoding="utf-8")
        (root / "relationships").mkdir()
        (root / "relationships" / "user.md").write_text("# User\n", encoding="utf-8")
        (root / "relationships" / "_inbox").mkdir()
        (root / "relationships" / "_inbox" / "candidate.md").write_text("# Candidate\n", encoding="utf-8")
        (root / "scenes").mkdir()
        (root / "scenes" / "development_review.md").write_text("# Development review\n", encoding="utf-8")
        (root / "scenes" / "_inbox").mkdir()
        (root / "scenes" / "_inbox" / "draft.md").write_text("# Draft scene\n", encoding="utf-8")
        (root / "memory").mkdir()
        (root / "memory" / "core.md").write_text(
            "# Core memory\n\n"
            "## Target user direction ^mem-relaylm-target-user\n\n"
            "status:: active\n"
            "importance:: high\n"
            "tags:: #relaylm\n\n"
            "SECRET_MARKDOWN_BODY\n",
            encoding="utf-8",
        )
        (root / "memory" / "people").mkdir()
        (root / "memory" / "people" / "user.md").write_text("# User page\n", encoding="utf-8")
        (root / "proposals" / "scene").mkdir(parents=True)
        (root / "proposals" / "scene" / "draft.md").write_text("# Proposal\n", encoding="utf-8")
        (root / ".relaylm" / "sources" / "conversations").mkdir(parents=True)
        (root / ".relaylm" / "sources" / "conversations" / "queue-record-123.json").write_text(
            '{"payload":"runtime-private-payload"}',
            encoding="utf-8",
        )
        (root / ".relaylm" / "state").mkdir(exist_ok=True)
        (root / ".relaylm" / "state" / "scene_state.json").write_text("{}", encoding="utf-8")
        (root / ".relaylm" / "build").mkdir(exist_ok=True)
        (root / ".relaylm" / "build" / "context_projection.json").write_text("{}", encoding="utf-8")

        valid = validate_character_workspace(root, character_id="koyomi")
        assert valid.status == CharacterWorkspaceValidationStatus.VALID
        assert valid.is_valid is True
        assert valid.missing_required_sources == ()
        assert len(valid.source_results) == len(REQUIRED_SOURCE_FILENAMES) + 1

        public_valid = validate_character_workspace(root, character_id="koyomi", public=True)
        assert public_valid["status"] == "valid"
        assert public_valid["content_free"] is True
        _assert_content_free(public_valid)

        manifest = build_character_workspace_manifest(root)
        assert manifest.is_valid is True
        assert ("source", len(REQUIRED_SOURCE_FILENAMES) + 1) in manifest.domain_counts
        assert any(kind == "internal_source_evidence" for kind, _count in manifest.path_kind_counts)

        public_manifest = build_character_workspace_manifest(root, public=True)
        assert public_manifest["status"] == "valid"
        _assert_content_free(public_manifest)

        missing_root = Path(tmp) / "characters" / "missing-soul"
        missing_root.mkdir()
        for filename in REQUIRED_SOURCE_FILENAMES:
            if filename != "SOUL.md":
                missing_root.joinpath(filename).write_text("# Source\n", encoding="utf-8")
        missing = validate_character_workspace(missing_root, character_id="missing-soul")
        assert missing.status == CharacterWorkspaceValidationStatus.MISSING_REQUIRED_SOURCE
        assert missing.is_valid is False
        assert missing.missing_required_sources == ("SOUL.md",)
        assert "missing_required_source" in missing.reason_ids

        no_lore_root = Path(tmp) / "characters" / "no-lore"
        no_lore_root.mkdir()
        _write_required_sources(no_lore_root)
        no_lore = validate_character_workspace(no_lore_root, character_id="no-lore")
        assert no_lore.status == CharacterWorkspaceValidationStatus.VALID

        bad_character = validate_character_workspace(root, character_id="../escape")
        assert bad_character.status == CharacterWorkspaceValidationStatus.INVALID_CHARACTER_ID
        assert bad_character.is_valid is False

        missing_default = Path(tmp) / "characters" / "default"
        assert not missing_default.exists()
        missing_default_result = validate_character_workspace(missing_default, character_id="default")
        assert missing_default_result.status == CharacterWorkspaceValidationStatus.INVALID_ROOT
        assert not missing_default.exists()

    source_required = classify_character_workspace_path("SOUL.md")
    assert source_required.kind == CharacterWorkspacePathKind.REQUIRED_SOURCE
    assert source_required.source_kind == "soul"
    assert classify_character_workspace_path("LORE.md").kind == CharacterWorkspacePathKind.OPTIONAL_SOURCE
    assert classify_character_workspace_path(".relaylm/build/context_projection.json").kind == CharacterWorkspacePathKind.INTERNAL_GENERATED
    assert classify_character_workspace_path(".relaylm/state/emotion_state.json").kind == CharacterWorkspacePathKind.INTERNAL_STATE
    assert classify_character_workspace_path(".relaylm/sources/corrections/1.json").kind == CharacterWorkspacePathKind.INTERNAL_SOURCE_EVIDENCE
    assert classify_character_workspace_path("scenes/default.md").kind == CharacterWorkspacePathKind.SCENE_PAGE
    assert classify_character_workspace_path("scenes/_inbox/draft.md").kind == CharacterWorkspacePathKind.SCENE_PAGE
    assert classify_character_workspace_path("memory/projects/relaylm.md").kind == CharacterWorkspacePathKind.MEMORY_PAGE
    assert classify_character_workspace_path("relationships/user.md").kind == CharacterWorkspacePathKind.RELATIONSHIP_PAGE
    assert classify_character_workspace_path("proposals/memory/draft.md").kind == CharacterWorkspacePathKind.PROPOSAL
    assert classify_character_workspace_path("/absolute/path.md").reason_ids == ("path_escape_rejected",)
    assert classify_character_workspace_path("../escape.md").reason_ids == ("path_escape_rejected",)
    assert classify_character_workspace_path("memory/../SOUL.md").reason_ids == ("path_escape_rejected",)

    markdown = (
        "# Memory policy\n\n"
        "status:: active\n\n"
        "## Target user direction ^mem-relaylm-target-user\n\n"
        "status:: active\n"
        "importance:: high\n"
        "tags:: #relaylm\n\n"
        "The page is a human editing unit, not one file per memory.\n"
    )
    blocks = parse_markdown_blocks(markdown, source_path="SECRET_PRIVATE_PATH")
    assert len(blocks) == 2
    target_block = blocks[1]
    assert target_block.heading == "Target user direction"
    assert target_block.anchor == "^mem-relaylm-target-user"
    assert target_block.metadata_dict()["status"] == "active"
    assert target_block.metadata_dict()["importance"] == "high"
    assert target_block.content_hash == parse_markdown_blocks(markdown)[1].content_hash
    assert target_block.to_public_dict()["has_anchor"] is True
    _assert_content_free(target_block.to_public_dict())

    with tempfile.TemporaryDirectory() as tmp:
        source_file = Path(tmp) / "MEMORY.md"
        source_file.write_text(markdown, encoding="utf-8")
        parsed = parse_character_source_file(source_file, "memory")
        assert parsed.is_valid is True
        assert parsed.block_count == 2
        assert parsed.content_hash == parse_character_source_file(source_file, "memory").content_hash
        parsed_public = parse_character_source_file(source_file, "memory", public=True)
        assert parsed_public["filename"] == "MEMORY.md"
        assert parsed_public["status"] == "valid"
        _assert_content_free(parsed_public)

    print("CW-A1 file-first Character Workspace smoke passed")


if __name__ == "__main__":
    main()
