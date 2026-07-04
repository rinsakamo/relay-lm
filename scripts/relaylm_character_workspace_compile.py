"""Compile a file-first Character Workspace into CW-A2 build artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relaylm.character_workspace import compile_character_workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Character Workspace .relaylm/build artifacts.")
    parser.add_argument("--workspace-root", required=True, help="Path to characters/<character> workspace root.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Generate artifacts in memory only. This is the default.")
    mode.add_argument("--write", action="store_true", help="Write generated artifacts under .relaylm/build.")
    args = parser.parse_args(argv)

    result = compile_character_workspace(Path(args.workspace_root), write=bool(args.write))
    projection = result.to_public_dict()
    print(json.dumps(projection, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
