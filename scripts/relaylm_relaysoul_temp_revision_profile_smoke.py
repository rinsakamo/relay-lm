from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.profile import build_profile_blocks
from scripts.relaylm_relaysoul_temp_revision_compile_dry_run import (
    _build_profile_files_for_dir,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _block_ids(profile_dir: Path) -> list[str]:
    files = _build_profile_files_for_dir(profile_dir)
    return [block.block_id for block in build_profile_blocks(files)]


def main() -> int:
    profile_dir = REPO_ROOT / "examples" / "profiles" / "default"
    require(not (profile_dir / "ROOM_ANCHOR.md").exists(), profile_dir)

    files = _build_profile_files_for_dir(profile_dir)
    require(files.room_anchor is None, files)
    require(
        _block_ids(profile_dir)
        == [
            "common_runtime_policy",
            "character_soul_anchor",
            "character_output_policy",
            "scene_state",
        ],
        _block_ids(profile_dir),
    )
    print("ok RelaySOUL dry-run uses current four-block standard profile")

    with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
        compatibility_dir = Path(temp_dir) / "profile"
        shutil.copytree(profile_dir, compatibility_dir)
        (compatibility_dir / "ROOM_ANCHOR.md").write_text(
            "Fixed compatibility room constraint.",
            encoding="utf-8",
        )

        compatibility_files = _build_profile_files_for_dir(compatibility_dir)
        require(compatibility_files.room_anchor is not None, compatibility_files)
        require("room_anchor" in _block_ids(compatibility_dir), _block_ids(compatibility_dir))
    print("ok RelaySOUL dry-run preserves optional room-anchor compatibility")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
