"""CLI entrypoints for CW-A5 character creation and template validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from relaylm.character_creation import (
    commit_character_from_template,
    stage_quick_character,
    validate_template_path,
)


def main_create() -> None:
    parser = argparse.ArgumentParser(description="Create or dry-run a RelayLM Character Workspace from a bundled template")
    parser.add_argument("--template", required=True, help="Bundled template id")
    parser.add_argument("--name", required=True, help="Character display name / slug source")
    parser.add_argument("--tone", default="friendly", help="Tone option")
    parser.add_argument("--intended-use", default="casual chat", help="Intended use option")
    parser.add_argument("--characters-root", default="characters", help="Local characters/ root")
    parser.add_argument("--showcase-mode", choices=("starter", "as_is"), default="starter")
    parser.add_argument("--dry-run", action="store_true", help="Stage and validate without writing")
    parser.add_argument("--write", action="store_true", help="Write only after explicit approval")
    args = parser.parse_args()

    if args.dry_run == args.write:
        parser.error("choose exactly one of --dry-run or --write")

    if args.dry_run:
        payload: dict[str, Any] = stage_quick_character(
            template_id=args.template,
            name=args.name,
            tone=args.tone,
            intended_use=args.intended_use,
            showcase_mode=args.showcase_mode,
        ).to_public_dict()
    else:
        payload = commit_character_from_template(
            characters_root=Path(args.characters_root),
            template_id=args.template,
            name=args.name,
            tone=args.tone,
            intended_use=args.intended_use,
            approval=True,
            showcase_mode=args.showcase_mode,
        ).to_public_dict()

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main_validate() -> None:
    parser = argparse.ArgumentParser(description="Validate a RelayLM character template folder or zip")
    parser.add_argument("path", help="Local template folder or zip")
    args = parser.parse_args()
    payload = validate_template_path(Path(args.path)).to_public_dict()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main_create()
