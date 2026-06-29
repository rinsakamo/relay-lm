from __future__ import annotations

import sys
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

    files = _build_profile_files_for_dir(profile_dir)
    require(files.scene_state is not None, files)
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
    print("ok RelaySOUL dry-run uses current scene-state standard profile")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
