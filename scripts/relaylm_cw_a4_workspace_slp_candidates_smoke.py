"""CW-A4 RelaySLP workspace candidate/proposal smoke."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from relaylm.character_workspace import (
    REQUIRED_SOURCE_FILENAMES,
    build_character_workspace_slp_projection,
    compile_character_workspace,
    plan_character_workspace_slp_candidates,
)

PRIVATE_MEMORY_BODY = "PRIVATE_MEMORY_BODY_SHOULD_NOT_LEAK"
PRIVATE_SCENE_BODY = "PRIVATE_SCENE_BODY_SHOULD_NOT_LEAK"
PRIVATE_RELATIONSHIP_BODY = "PRIVATE_RELATIONSHIP_BODY_SHOULD_NOT_LEAK"
PRIVATE_ASSISTANT_SPECULATION = "PRIVATE_ASSISTANT_SPECULATION_SHOULD_NOT_LEAK"


def _write_required_sources(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_SOURCE_FILENAMES:
        name = filename.removesuffix(".md")
        (root / filename).write_text(f"# {name}\n\nstatus:: active\n\n{name} policy.\n", encoding="utf-8")
    for directory in (
        "memory/inbox",
        "memory/forgotten",
        "scenes/_inbox",
        "relationships/_inbox",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "memory" / "forgotten" / "old.md").write_text(
        "# Forgotten\n\nstatus:: forgotten\n\nPRIVATE_FORGOTTEN_MEMORY_BODY\n",
        encoding="utf-8",
    )


def _write_user_source(root: Path, name: str = "turn-001.json") -> None:
    source_dir = root / ".relaylm" / "sources" / "conversations"
    source_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "relaymem.slp_finalized_turn_source.v0",
        "runtime_private": True,
        "content_included": True,
        "governed_messages": [
            {
                "role": "user",
                "content": (
                    f"Remember a low risk project note. {PRIVATE_MEMORY_BODY}. "
                    f"This also describes a Home scene pattern. {PRIVATE_SCENE_BODY}. "
                    f"The relationship trust and most_important_person parameter need review. {PRIVATE_RELATIONSHIP_BODY}."
                ),
            },
            {"role": "assistant", "content": "Acknowledged without adding extra facts."},
        ],
    }
    (source_dir / name).write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _write_sensitive_source(root: Path) -> None:
    source_dir = root / ".relaylm" / "sources" / "corrections"
    source_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "governed_messages": [
            {"role": "user", "content": "The user mentioned a password-like secret; keep this approval-gated."}
        ]
    }
    (source_dir / "sensitive.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _write_assistant_only_source(root: Path) -> None:
    source_dir = root / ".relaylm" / "sources" / "conversations"
    source_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "governed_messages": [
            {"role": "assistant", "content": f"I speculate that this is true. {PRIVATE_ASSISTANT_SPECULATION}"}
        ]
    }
    (source_dir / "assistant-only.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert_content_free_projection(projection: dict[str, object], root: Path) -> None:
    serialized = _serialized(projection)
    assert projection["content_free"] is True
    for token in (
        PRIVATE_MEMORY_BODY,
        PRIVATE_SCENE_BODY,
        PRIVATE_RELATIONSHIP_BODY,
        PRIVATE_ASSISTANT_SPECULATION,
        "PRIVATE_FORGOTTEN_MEMORY_BODY",
    ):
        assert token not in serialized, token
    for token in (str(root), str(root.resolve()), tempfile.gettempdir()):
        assert token not in serialized, token
    assert projection["raw_source_body_included"] is False
    assert projection["raw_memory_body_included"] is False
    assert projection["raw_scene_body_included"] is False
    assert projection["raw_relationship_body_included"] is False
    assert projection["absolute_paths_included"] is False
    assert projection["queue_payload_included"] is False


def _assert_no_forbidden_writes(root: Path, before: dict[str, str]) -> None:
    for rel, text in before.items():
        assert (root / rel).read_text(encoding="utf-8") == text, rel


def _forbidden_sentinels(root: Path) -> dict[str, str]:
    sentinels = {
        "SOUL.md": (root / "SOUL.md").read_text(encoding="utf-8"),
        ".relaylm/build/sentinel.txt": "BUILD_SENTINEL",
        ".relaylm/state/sentinel.txt": "STATE_SENTINEL",
        ".relaylm/queue/sentinel.txt": "QUEUE_SENTINEL",
    }
    for rel, text in sentinels.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return sentinels


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "characters" / "koyomi"
        _write_required_sources(root)
        _write_user_source(root)
        _write_sensitive_source(root)
        sentinels = _forbidden_sentinels(root)

        before = _files(root)
        dry = plan_character_workspace_slp_candidates(root)
        assert dry.status == "planned"
        assert dry.dry_run is True
        assert dry.write_candidates is False
        assert dry.to_public_dict()["memory_inbox_additions_count"] >= 1
        assert any(candidate.target_path.startswith("scenes/_inbox/") for candidate in dry.candidates)
        assert any(candidate.target_path.startswith("relationships/_inbox/") for candidate in dry.candidates)
        assert any(candidate.risk_level == "high" and candidate.approval_required for candidate in dry.candidates)
        assert not any(candidate.auto_apply_eligible for candidate in dry.candidates)
        assert _files(root) == before, "dry-run wrote files"
        _assert_content_free_projection(dry.to_public_dict(), root)
        _assert_no_forbidden_writes(root, sentinels)
        assert not any(candidate.target_path.startswith("memory/forgotten/") for candidate in dry.candidates)

        write = plan_character_workspace_slp_candidates(root, write_candidates=True)
        assert write.status == "planned", write.blocked_reason_ids
        created = _files(root) - before
        assert created == set(write.written_paths), created
        assert created
        assert all(
            rel.startswith((
                "memory/inbox/",
                "scenes/_inbox/",
                "relationships/_inbox/",
                "proposals/memory/",
                "proposals/scene/",
                "proposals/relationship/",
            ))
            for rel in created
        ), created
        _assert_no_forbidden_writes(root, sentinels)

        repeat = plan_character_workspace_slp_candidates(root, write_candidates=True)
        assert repeat.status == "planned"
        assert set(repeat.written_paths) == set(write.written_paths)

        conflict_path = next(path for path in write.written_paths if path.startswith("memory/inbox/"))
        (root / conflict_path).write_text("# conflicting candidate body\n", encoding="utf-8")
        conflict = plan_character_workspace_slp_candidates(root, write_candidates=True)
        assert conflict.status == "write_blocked"
        assert "candidate_artifact_conflict" in conflict.blocked_reason_ids
        assert (root / conflict_path).read_text(encoding="utf-8") == "# conflicting candidate body\n"

        projection = build_character_workspace_slp_projection(root)
        _assert_content_free_projection(projection, root)

        capped = plan_character_workspace_slp_candidates(root, max_source_files=1, max_candidates=1)
        assert capped.to_public_dict()["candidate_count"] == 1
        assert "source_file_limit_reached" in capped.reason_ids
        assert "candidate_limit_reached" in capped.reason_ids

        compiled = compile_character_workspace(root)
        assert compiled.is_valid is True
        assert not (root / ".relaylm" / "build" / "character_manifest.json").exists(), "CW-A4 invoked build write"

        assistant_root = Path(tmp) / "characters" / "assistant-only"
        _write_required_sources(assistant_root)
        _write_assistant_only_source(assistant_root)
        assistant = plan_character_workspace_slp_candidates(assistant_root)
        assert assistant.candidates
        assert any("assistant_only_speculation" in candidate.reason_ids for candidate in assistant.candidates)
        assert "assistant_only_speculation_blocked" in assistant.reason_ids
        _assert_content_free_projection(assistant.to_public_dict(), assistant_root)

        malformed_root = Path(tmp) / "characters" / "malformed"
        _write_required_sources(malformed_root)
        malformed_source = malformed_root / ".relaylm" / "sources" / "conversations" / "bad.json"
        malformed_source.parent.mkdir(parents=True, exist_ok=True)
        malformed_source.write_bytes(b"\xff\xfe")
        malformed = plan_character_workspace_slp_candidates(malformed_root)
        assert malformed.status == "malformed_source_evidence"
        assert malformed.candidates == ()

        traversal = plan_character_workspace_slp_candidates(root / ".." / "koyomi")
        assert traversal.status == "invalid_workspace"
        assert "path_traversal_rejected" in traversal.blocked_reason_ids

        outside = Path(tmp) / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        symlink_root = Path(tmp) / "characters" / "symlink"
        _write_required_sources(symlink_root)
        source_dir = symlink_root / ".relaylm" / "sources" / "conversations"
        source_dir.mkdir(parents=True, exist_ok=True)
        try:
            (source_dir / "escape.json").symlink_to(outside)
        except (OSError, NotImplementedError):
            pass
        else:
            symlinked = plan_character_workspace_slp_candidates(symlink_root)
            assert symlinked.status == "path_escape_rejected"
            assert "symlink_escape_rejected" in symlinked.blocked_reason_ids

    print("CW-A4 workspace SLP candidate/proposal smoke passed")


if __name__ == "__main__":
    main()
