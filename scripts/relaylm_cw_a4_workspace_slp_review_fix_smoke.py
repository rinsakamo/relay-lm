"""Targeted smoke for CW-A4 review fixes."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from relaylm.character_workspace import REQUIRED_SOURCE_FILENAMES, plan_character_workspace_slp_candidates

ASSISTANT_SECRET = "ASSISTANT_ONLY_PASSWORD_SCENE_RELATIONSHIP_TOKEN"
DUPLICATE_USER_FACT = "User says the public relationship trust note should be reviewed."


def _write_required_sources(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_SOURCE_FILENAMES:
        source_name = filename.removesuffix(".md")
        root.joinpath(filename).write_text(
            f"# {source_name}\n\nstatus:: active\n\n{source_name} policy.\n",
            encoding="utf-8",
        )
    (root / "memory" / "inbox").mkdir(parents=True, exist_ok=True)
    (root / "scenes" / "_inbox").mkdir(parents=True, exist_ok=True)
    (root / "relationships" / "_inbox").mkdir(parents=True, exist_ok=True)


def _write_source(root: Path, payload: object, filename: str = "turn.json") -> None:
    source_dir = root / ".relaylm" / "sources" / "conversations"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _serialized(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _assert_public_projection_safe(run: object, root: Path) -> None:
    projection = run.to_public_dict()
    serialized = _serialized(projection)
    assert projection["content_free"] is True
    assert ASSISTANT_SECRET not in serialized
    assert str(root) not in serialized
    assert str(root.resolve()) not in serialized
    assert projection["raw_source_body_included"] is False
    assert projection["queue_mutated"] is False


def _assert_no_proposals_written(root: Path) -> None:
    proposal_root = root / "proposals"
    if proposal_root.exists():
        assert not list(proposal_root.rglob("*.json")), "orphaned proposal written after blocked candidate write"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "characters" / "koyomi"
        _write_required_sources(root)
        _write_source(root, {
            "governed_messages": [
                {"role": "user", "content": "ok"},
                {
                    "role": "assistant",
                    "content": (
                        f"Speculative assistant-only password, Home scene, trust, "
                        f"most_important_person note. {ASSISTANT_SECRET}"
                    ),
                },
            ]
        })

        mixed = plan_character_workspace_slp_candidates(root)
        _assert_public_projection_safe(mixed, root)
        assert all(candidate.target_domain != "scene" for candidate in mixed.candidates), mixed.candidates
        assert all(candidate.target_domain != "relationship" for candidate in mixed.candidates), mixed.candidates
        assert not any("sensitive_memory_candidate" in candidate.reason_ids for candidate in mixed.candidates), mixed.candidates

        # P1: dangling symlink targets are false for exists() but true for is_symlink().
        candidate_path = next(candidate.target_path for candidate in mixed.candidates if candidate.target_path.startswith("memory/inbox/"))
        target = root / candidate_path
        target.parent.mkdir(parents=True, exist_ok=True)
        queue_target = root / ".relaylm" / "queue" / "new.md"
        queue_target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.symlink_to("../../.relaylm/queue/new.md")
        except (OSError, NotImplementedError):
            pass
        else:
            assert target.is_symlink()
            assert not target.exists()
            write = plan_character_workspace_slp_candidates(root, write_candidates=True)
            assert write.status == "write_blocked"
            assert "write_path_symlink_rejected" in write.blocked_reason_ids
            assert "proposal_write_skipped_after_candidate_write_failure" in write.blocked_reason_ids
            assert not queue_target.exists(), "write followed dangling symlink into .relaylm/queue"
            _assert_no_proposals_written(root)

        assistant_only_root = Path(tmp) / "characters" / "assistant-only"
        _write_required_sources(assistant_only_root)
        _write_source(assistant_only_root, {
            "governed_messages": [
                {"role": "assistant", "content": f"Speculation only. {ASSISTANT_SECRET}"}
            ]
        })
        assistant_only = plan_character_workspace_slp_candidates(assistant_only_root)
        _assert_public_projection_safe(assistant_only, assistant_only_root)
        assert any("assistant_only_speculation" in candidate.reason_ids for candidate in assistant_only.candidates)
        assert "assistant_only_speculation_blocked" in assistant_only.reason_ids

        duplicate_root = Path(tmp) / "characters" / "duplicates"
        _write_required_sources(duplicate_root)
        _write_source(duplicate_root, {"messages": [{"role": "user", "content": DUPLICATE_USER_FACT}]}, "a.json")
        _write_source(duplicate_root, {"messages": [{"role": "user", "content": DUPLICATE_USER_FACT}]}, "b.json")
        duplicate_run = plan_character_workspace_slp_candidates(duplicate_root, write_candidates=True)
        assert duplicate_run.status == "planned"
        assert "candidate_artifact_conflict" not in duplicate_run.blocked_reason_ids
        memory_paths = [candidate.target_path for candidate in duplicate_run.candidates if candidate.target_domain == "memory"]
        assert len(memory_paths) == len(set(memory_paths)) == 2, memory_paths
        assert all((duplicate_root / path).exists() for path in memory_paths)

        conflict_root = Path(tmp) / "characters" / "conflict"
        _write_required_sources(conflict_root)
        _write_source(conflict_root, {"messages": [{"role": "user", "content": "User says a memory note should be reviewed."}]})
        conflict_plan = plan_character_workspace_slp_candidates(conflict_root)
        conflict_path = next(candidate.target_path for candidate in conflict_plan.candidates if candidate.target_domain == "memory")
        (conflict_root / conflict_path).parent.mkdir(parents=True, exist_ok=True)
        (conflict_root / conflict_path).write_text("conflicting existing candidate\n", encoding="utf-8")
        conflict_write = plan_character_workspace_slp_candidates(conflict_root, write_candidates=True)
        assert conflict_write.status == "write_blocked"
        assert "candidate_artifact_conflict" in conflict_write.blocked_reason_ids
        assert "proposal_write_skipped_after_candidate_write_failure" in conflict_write.blocked_reason_ids
        _assert_no_proposals_written(conflict_root)

        partial_root = Path(tmp) / "characters" / "partial-conflict"
        _write_required_sources(partial_root)
        _write_source(partial_root, {"messages": [{"role": "user", "content": "User says this memory and scene should be reviewed."}]})
        partial_plan = plan_character_workspace_slp_candidates(partial_root)
        partial_memory_path = next(candidate.target_path for candidate in partial_plan.candidates if candidate.target_domain == "memory")
        partial_scene_path = next(candidate.target_path for candidate in partial_plan.candidates if candidate.target_domain == "scene")
        (partial_root / partial_scene_path).parent.mkdir(parents=True, exist_ok=True)
        (partial_root / partial_scene_path).write_text("conflicting existing scene candidate\n", encoding="utf-8")
        partial_write = plan_character_workspace_slp_candidates(partial_root, write_candidates=True)
        assert partial_write.status == "write_blocked"
        assert "candidate_artifact_conflict" in partial_write.blocked_reason_ids
        assert not (partial_root / partial_memory_path).exists(), "candidate batch was partially written before conflict"
        _assert_no_proposals_written(partial_root)

        cap_root = Path(tmp) / "characters" / "source-cap"
        _write_required_sources(cap_root)
        for index in range(5):
            _write_source(cap_root, {"messages": [{"role": "user", "content": f"bounded source {index}"}]}, f"{index}.json")
        cap_run = plan_character_workspace_slp_candidates(cap_root, max_source_files=2)
        assert cap_run.source_evidence_count == 2, cap_run.source_evidence_count
        assert "source_file_limit_reached" in cap_run.reason_ids

        oversized_root = Path(tmp) / "characters" / "oversized"
        _write_required_sources(oversized_root)
        source_dir = oversized_root / ".relaylm" / "sources" / "conversations"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "large.json").write_text("x" * 128, encoding="utf-8")
        oversized_run = plan_character_workspace_slp_candidates(oversized_root, max_read_bytes=16)
        assert oversized_run.source_evidence_count == 0
        assert "source_read_limit_reached" in oversized_run.reason_ids
        assert not oversized_run.candidates

        source_root_symlink = Path(tmp) / "characters" / "source-root-symlink"
        _write_required_sources(source_root_symlink)
        source_parent = source_root_symlink / ".relaylm" / "sources"
        source_parent.mkdir(parents=True, exist_ok=True)
        external_source = Path(tmp) / "external-source"
        external_source.mkdir(parents=True, exist_ok=True)
        try:
            (source_parent / "conversations").symlink_to(external_source, target_is_directory=True)
        except (OSError, NotImplementedError):
            pass
        else:
            symlink_run = plan_character_workspace_slp_candidates(source_root_symlink)
            assert symlink_run.status == "path_escape_rejected"
            assert "symlink_escape_rejected" in symlink_run.blocked_reason_ids

    print("CW-A4 review fix smoke passed")


if __name__ == "__main__":
    main()
