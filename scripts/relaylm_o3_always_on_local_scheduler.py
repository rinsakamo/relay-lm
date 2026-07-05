#!/usr/bin/env python3
"""O3 opt-in always-on local RelayMEM scheduler CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.config import load_config  # noqa: E402
from relaylm.relaymem_slp_scheduler_operations import SchedulerSignalCancellationAdapter  # noqa: E402
from relaylm.relaymem_slp_supervised_scheduler_service import (  # noqa: E402
    RelayMEMSLPSupervisedSchedulerServiceSettings,
    make_relaymem_slp_supervised_scheduler_service_projection,
    run_relaymem_slp_supervised_scheduler_service,
)


_NORMAL_STATUSES = {"disabled", "completed", "idle", "cancelled", "shutdown_requested"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the opt-in RelayMEM O3 always-on local scheduler wrapper.",
    )
    parser.add_argument("--config", help="Path to RelayLM config YAML.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--max-rounds",
        type=int,
        default=1,
        help="Run a bounded validation loop with this many O2 rounds. Must be >= 1.",
    )
    group.add_argument(
        "--always-on",
        action="store_true",
        help="Run without a max-rounds cap until idle policy, cancellation, shutdown, or failure.",
    )
    parser.add_argument(
        "--idle-sleep-ms",
        type=int,
        default=1000,
        help="Bounded idle sleep between service rounds when idle has not reached the stop limit.",
    )
    parser.add_argument(
        "--stop-after-idle-rounds",
        type=int,
        default=1,
        help="Stop after this many consecutive idle rounds.",
    )
    parser.add_argument(
        "--max-sleep-ms",
        type=int,
        default=60_000,
        help="Upper bound for any policy-recommended sleep.",
    )
    return parser


def _print_projection(projection: Mapping[str, object]) -> None:
    print(json.dumps(dict(projection), ensure_ascii=False, sort_keys=True))


def _exit_code(status: object) -> int:
    if status in _NORMAL_STATUSES:
        return 0
    if status in {"invalid_config", "invalid_input"}:
        return 2
    if status == "unsafe_state":
        return 3
    return 4


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.always_on and (type(args.max_rounds) is not int or args.max_rounds < 1):
        projection = make_relaymem_slp_supervised_scheduler_service_projection(
            status="invalid_config",
            reason_id="cli_max_rounds_invalid",
        )
        _print_projection(projection)
        return _exit_code(projection["status"])

    max_rounds = None if args.always_on else args.max_rounds

    try:
        settings = RelayMEMSLPSupervisedSchedulerServiceSettings(
            max_rounds=max_rounds,
            stop_after_idle_rounds=args.stop_after_idle_rounds,
            idle_sleep_ms=args.idle_sleep_ms,
            max_sleep_ms=args.max_sleep_ms,
            install_signal_handlers=False,
        )
    except Exception:
        projection = make_relaymem_slp_supervised_scheduler_service_projection(
            status="invalid_config",
            reason_id="cli_scheduler_settings_invalid",
        )
        _print_projection(projection)
        return _exit_code(projection["status"])

    try:
        config = load_config(args.config)
    except Exception:
        projection = make_relaymem_slp_supervised_scheduler_service_projection(
            status="invalid_config",
            reason_id="config_load_failed",
        )
        _print_projection(projection)
        return _exit_code(projection["status"])

    adapter = SchedulerSignalCancellationAdapter()
    with adapter.installed():
        result = run_relaymem_slp_supervised_scheduler_service(
            config=config,
            settings=settings,
            cancellation=adapter.token,
        )
    projection = result.projection()
    _print_projection(projection)
    return _exit_code(projection["status"])


if __name__ == "__main__":
    raise SystemExit(main())
