from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.state import CanonicalState, StateRecord
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}\n', encoding="utf-8"
    )
    return CharacterDirectory(root)


@pytest.mark.parametrize("sources", [(), ("",), ("   ",)])
def test_save_state_rejects_empty_provenance_without_replacing_authority(
    tmp_path: Path,
    sources: tuple[str, ...],
) -> None:
    character = _make_character(tmp_path)
    before = character.state_path.read_text(encoding="utf-8")
    state = CanonicalState(
        states=(
            StateRecord(
                state_id="state-1",
                state_class="user.preference",
                key="tea",
                value="likes",
                sources=sources,
            ),
        )
    )

    with pytest.raises(CharacterDataError, match="sources"):
        character.save_state(state)

    assert character.state_path.read_text(encoding="utf-8") == before
    assert not (tmp_path / "memory" / ".state.json.tmp").exists()


def test_load_state_rejects_duplicate_top_level_authority_member(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    character.state_path.write_text(
        '{"format_version":1,"states":[],"states":[]}\n',
        encoding="utf-8",
    )

    with pytest.raises(CharacterDataError, match="duplicate JSON object member: states"):
        character.load_state()


def test_load_state_rejects_duplicate_record_authority_member(tmp_path: Path) -> None:
    character = _make_character(tmp_path)
    character.state_path.write_text(
        '{"format_version":1,"states":[{'
        '"state_id":"state-1","state_class":"user.preference","key":"tea",'
        '"value":"likes","value":"dislikes","status":"active",'
        '"sources":["evt-1"]}]}\n',
        encoding="utf-8",
    )

    with pytest.raises(CharacterDataError, match="duplicate JSON object member: value"):
        character.load_state()
