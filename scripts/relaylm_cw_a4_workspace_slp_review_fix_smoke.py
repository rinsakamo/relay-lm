"""Targeted smoke for CW-A4 review fixes."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from relaylm.character_workspace import REQUIRED_SOURCE_FILENAMES, plan_character_workspace_slp_candidates

ASSISTANT_SECRET = "ASSISTANT_ONLY_PASSWORD_SCENE_RELATIONSHIP_TOKEN"


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
            assert not queue_target.exists(), "write followed dangling symlink into .relaylm/queue"

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

    print("CW-A4 review fix smoke passed")


if __name__ == "__main__":
    main()
