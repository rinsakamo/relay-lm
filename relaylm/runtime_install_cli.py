"""Console entry point for explicit RelayLM runtime install/preflight."""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .config import load_config
from .runtime_install import (
    PROJECTION_SCHEMA,
    REQUEST_SCHEMA,
    RuntimeInstallRequest,
    execute_runtime_install,
    exit_code_for_runtime_install,
    invalid_runtime_install_report,
)


class _CLIInputError(Exception):
    pass


class _ContentFreeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _CLIInputError("invalid_cli_input")


@dataclass(frozen=True)
class _CLIArgs:
    config: str
    write: bool
    character_id: str | None
    json_out: str | None


def main(argv: Sequence[str] | None = None) -> int:
    args = _CLIArgs(config="", write=False, character_id=None, json_out=None)
    try:
        args = _parse_args(argv)
        config = load_config(args.config)
        result = execute_runtime_install(
            RuntimeInstallRequest(
                schema_version=REQUEST_SCHEMA,
                runtime_private=True,
                content_included=False,
                config=config,
                config_path=args.config,
                write=args.write,
                character_id=args.character_id,
            )
        )
    except (SystemExit, KeyboardInterrupt):
        raise
    except _CLIInputError:
        result = invalid_runtime_install_report("runtime_install_cli_input_invalid", write_requested=False, config_loaded=False)
    except FileNotFoundError:
        result = invalid_runtime_install_report("runtime_install_config_missing", write_requested=args.write, config_loaded=False)
    except Exception:
        result = invalid_runtime_install_report("runtime_install_config_invalid", write_requested=args.write, config_loaded=False)

    payload = result.to_public_dict()
    if args.json_out is not None:
        json_reason = _write_json_out(args.json_out, payload)
        if json_reason is not None and result.status != "invalid_input":
            result = invalid_runtime_install_report(
                json_reason,
                write_requested=args.write,
                config_loaded=payload.get("config_loaded") is True,
            )
            payload = result.to_public_dict()
    _emit_payload(payload)
    return exit_code_for_runtime_install(result)


def _parse_args(argv: Sequence[str] | None) -> _CLIArgs:
    parser = _ContentFreeArgumentParser(
        add_help=True,
        prog="relaylm-runtime-install",
        description="Explicit dry-run-first RelayLM local runtime install/preflight.",
    )
    parser.add_argument("--config", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only. This is the default.")
    mode.add_argument("--write", action="store_true", help="Create only safe missing runtime layout directories.")
    parser.add_argument("--character-id", help="Optionally run the E1-R2 character-store bootstrap authority.")
    parser.add_argument("--json-out", help="Write the content-free report to a new JSON file.")
    namespace = parser.parse_args(list(argv) if argv is not None else None)
    return _CLIArgs(
        config=namespace.config,
        write=bool(namespace.write),
        character_id=namespace.character_id,
        json_out=namespace.json_out,
    )


def _emit_payload(payload: dict[str, object]) -> None:
    assert payload.get("schema_version") == PROJECTION_SCHEMA
    sys.stdout.write(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _write_json_out(path_value: str, payload: dict[str, object]) -> str | None:
    path = Path(path_value)
    if path.exists():
        return "runtime_install_json_out_exists"
    if not path.parent.exists() or not path.parent.is_dir():
        return "runtime_install_json_out_parent_missing"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError:
        return "runtime_install_json_out_create_failed"
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.write("\n")
    except OSError:
        return "runtime_install_json_out_write_failed"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
