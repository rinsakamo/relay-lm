"""Repository discovery helpers: deterministic file listing and commit metadata.

Everything in this module is read-only. Nothing here writes, deletes, moves,
or renames repository content.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]

EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "generated",
        ".venv",
        "venv",
        "egg-info",
    }
)


def _is_excluded_name(name: str) -> bool:
    return name in EXCLUDED_DIR_NAMES or name.endswith(".egg-info")


def _is_excluded(relative_path: Path) -> bool:
    return any(_is_excluded_name(part) for part in relative_path.parts)


def iter_repo_files(
    root: Path = ROOT,
    suffixes: Sequence[str] | None = None,
) -> list[Path]:
    """Return a deterministically sorted list of files under root.

    Excluded directories are pruned before traversal. When suffixes is given
    (lowercase, including the leading dot), only matching files are kept.
    """
    suffix_set = (
        {suffix.lower() for suffix in suffixes}
        if suffixes is not None
        else None
    )
    matches: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not _is_excluded_name(name)
        )
        directory = Path(dirpath)
        for filename in sorted(filenames):
            path = directory / filename
            if (
                suffix_set is not None
                and path.suffix.lower() not in suffix_set
            ):
                continue
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue
            rel = path.relative_to(root)
            if _is_excluded(rel):
                continue
            matches.append(path)
    return sorted(
        matches,
        key=lambda path: path.relative_to(root).as_posix(),
    )


def relative(path: Path, root: Path = ROOT) -> str:
    return path.relative_to(root).as_posix()


def commit_sha(root: Path = ROOT) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    sha = result.stdout.strip()
    return sha or "unknown"


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
