"""Console entry point for E1-R2 character-store bootstrap."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Sequence

from .character_store_bootstrap import (
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    CharacterStoreBootstrapRequest,
    CharacterStoreBootstrapResult,
    execute_character_store_bootstrap,
    exit_code_for_character_store_bootstrap,
)
from .config import RelayLMConfig, load_config


class _CLIInputError(Exception):
    pass


class _ContentFreeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _CLIInputError("invalid_cli_input")


@dataclass(frozen=True)
class _CLIArgs:
    config: str
    character_id: str
    apply: bool


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
        config = load_config(args.config)
        result = execute_character_store_bootstrap(
            CharacterStoreBootstrapRequest(
                schema_version=REQUEST_SCHEMA,
                runtime_private=True,
                content_included=False,
                config=config,
                character_id=args.character_id,
                apply=args.apply,
            )
        )
    except (SystemExit, KeyboardInterrupt):
        raise
    except _CLIInputError:
        result = _invalid_result("character_store_bootstrap_cli_input_invalid", apply_requested=False)
    except Exception:
        result = _invalid_result("character_store_bootstrap_config_invalid", apply_requested=False)
    _emit(result)
    return exit_code_for_character_store_bootstrap(result)


def _parse_args(argv: Sequence[str] | None) -> _CLIArgs:
    parser = _ContentFreeArgumentParser(
        add_help=True,
        prog="relaylm-character-store-bootstrap",
        description="Prepare a character-scoped Primary MEM store layout by explicit operator invocation.",
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--character-id", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only. This is the default.")
    mode.add_argument("--apply", action="store_true", help="Create only missing safe layout components.")
    namespace = parser.parse_args(list(argv) if argv is not None else None)
    return _CLIArgs(
        config=namespace.config,
        character_id=namespace.character_id,
        apply=bool(namespace.apply),
    )


def _invalid_result(reason: str, *, apply_requested: bool) -> CharacterStoreBootstrapResult:
    return CharacterStoreBootstrapResult(
        schema_version=RESULT_SCHEMA,
        status="invalid_input",
        runtime_private=True,
        content_included=False,
        dry_run=not apply_requested,
        apply_requested=apply_requested,
        ready=False,
        mutated=False,
        character_scope_resolved=False,
        config_scope_valid=False,
        existing_directory_count=0,
        missing_directory_count=0,
        created_directory_count=0,
        existing_control_file_count=0,
        missing_control_file_count=0,
        created_control_file_count=0,
        actions_required=False,
        reason_ids=(reason,),
    )


def _emit(result: CharacterStoreBootstrapResult) -> None:
    sys.stdout.write(
        json.dumps(
            result.to_public_dict(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
