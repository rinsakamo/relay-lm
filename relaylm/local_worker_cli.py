"""Console entry point for the O0 local one-job runner."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Sequence

from .config import load_config
from .local_worker_once import (
    PROJECTION_SCHEMA,
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    RelayLMLocalWorkerOnceRequest,
    RelayLMLocalWorkerOnceResult,
    execute_local_worker_once,
    exit_code_for_local_worker_once,
)


class _CLIInputError(Exception):
    pass


class _ContentFreeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _CLIInputError("invalid_cli_input")


@dataclass(frozen=True)
class _CLIArgs:
    config: str
    once: bool
    character_id: str | None


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
        if not args.once:
            raise _CLIInputError("once_required")
        config = load_config(args.config)
        result = execute_local_worker_once(
            RelayLMLocalWorkerOnceRequest(
                schema_version=REQUEST_SCHEMA,
                runtime_private=True,
                content_included=False,
                config=config,
                character_id=args.character_id,
            )
        )
    except (SystemExit, KeyboardInterrupt):
        raise
    except _CLIInputError:
        result = _invalid_result("local_worker_cli_input_invalid")
    except Exception:
        result = _invalid_result("local_worker_config_invalid")
    _emit(result)
    return exit_code_for_local_worker_once(result)


def _parse_args(argv: Sequence[str] | None) -> _CLIArgs:
    parser = _ContentFreeArgumentParser(add_help=True, prog="relaylm-worker")
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--character-id")
    namespace = parser.parse_args(list(argv) if argv is not None else None)
    return _CLIArgs(
        config=namespace.config,
        once=namespace.once,
        character_id=namespace.character_id,
    )


def _invalid_result(reason: str) -> RelayLMLocalWorkerOnceResult:
    return RelayLMLocalWorkerOnceResult(
        schema_version=RESULT_SCHEMA,
        status="invalid_input",
        runtime_private=True,
        content_included=False,
        exit_category="invalid_configuration",
        selected=False,
        eligible=False,
        canonical_reread_performed=False,
        character_scope_resolved=False,
        c2_result=None,
        reason_ids=(reason,),
    )


def _emit(result: RelayLMLocalWorkerOnceResult) -> None:
    payload = result.to_log_dict()
    assert payload.get("schema_version") == PROJECTION_SCHEMA
    sys.stdout.write(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
