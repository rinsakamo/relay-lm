"""CLI for CW-A4 RelaySLP Character Workspace candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relaylm.character_workspace import plan_character_workspace_slp_candidates


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan CW-A4 SLP workspace candidates and proposals.")
    parser.add_argument("--workspace-root", required=True, help="Character workspace root, e.g. runtime/characters/koyomi")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only; write nothing. This is the default.")
    mode.add_argument("--write-candidates", action="store_true", help="Write only allowlisted candidate/proposal artifacts.")
    parser.add_argument("--json-out", help="Optional path for the content-free public projection JSON.")
    parser.add_argument("--max-source-files", type=int, default=32)
    parser.add_argument("--max-candidates", type=int, default=64)
    parser.add_argument("--max-read-bytes", type=int, default=64 * 1024)
    return parser


def main() -> None:
    args = _parser().parse_args()
    run = plan_character_workspace_slp_candidates(
        Path(args.workspace_root),
        write_candidates=bool(args.write_candidates),
        max_source_files=args.max_source_files,
        max_candidates=args.max_candidates,
        max_read_bytes=args.max_read_bytes,
    )
    projection = run.to_public_dict()
    text = json.dumps(projection, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
