#!/usr/bin/env python3
"""O1D1 accepted scheduler configuration smoke."""
from __future__ import annotations

from itertools import product
from pathlib import Path
import sys

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from _relaylm_o1d1_support import config_data, make_config  # noqa: E402
from relaylm.config import RelayLMConfig  # noqa: E402
from relaylm.relaymem_slp_scheduler_round import (  # noqa: E402
    build_relaymem_slp_scheduler_gates,
)

FIELDS = (
    "relaymem_local_scheduler_enabled",
    "relaymem_local_scheduler_dry_run_only",
    "relaymem_local_scheduler_apply_enabled",
    "relaymem_local_scheduler_replay_lane_enabled",
    "relaymem_local_scheduler_queue_lane_enabled",
)
VALID_TRIPLES = {
    (False, True, False): "disabled",
    (True, True, False): "dry_run",
    (True, False, True): "apply",
}


def rejected(data: dict[str, object]) -> bool:
    try:
        RelayLMConfig.model_validate(data)
    except ValidationError:
        return True
    return False


def main() -> None:
    defaults = make_config()
    assert defaults.relaymem_local_scheduler_enabled is False
    assert defaults.relaymem_local_scheduler_dry_run_only is True
    assert defaults.relaymem_local_scheduler_apply_enabled is False
    assert defaults.relaymem_local_scheduler_replay_lane_enabled is True
    assert defaults.relaymem_local_scheduler_queue_lane_enabled is True
    assert build_relaymem_slp_scheduler_gates(defaults).mode == "disabled"

    for triple, mode in VALID_TRIPLES.items():
        enabled, dry_run_only, apply_enabled = triple
        config = make_config(
            relaymem_local_scheduler_enabled=enabled,
            relaymem_local_scheduler_dry_run_only=dry_run_only,
            relaymem_local_scheduler_apply_enabled=apply_enabled,
        )
        assert build_relaymem_slp_scheduler_gates(config).mode == mode
        for field in FIELDS:
            assert type(getattr(config, field)) is bool

    for field in FIELDS:
        for invalid in (0, 1, "false", "true", "0", "1", None):
            assert rejected(config_data(**{field: invalid})), (field, invalid)

    for triple in product((False, True), repeat=3):
        data = config_data(
            relaymem_local_scheduler_enabled=triple[0],
            relaymem_local_scheduler_dry_run_only=triple[1],
            relaymem_local_scheduler_apply_enabled=triple[2],
        )
        if triple in VALID_TRIPLES:
            RelayLMConfig.model_validate(data)
        else:
            assert rejected(data), triple

    assert rejected(
        config_data(
            relaymem_local_scheduler_enabled=True,
            relaymem_local_scheduler_dry_run_only=True,
            relaymem_local_scheduler_apply_enabled=False,
            relaymem_local_scheduler_replay_lane_enabled=False,
            relaymem_local_scheduler_queue_lane_enabled=False,
        )
    )
    disabled_no_lanes = RelayLMConfig.model_validate(
        config_data(
            relaymem_local_scheduler_enabled=False,
            relaymem_local_scheduler_dry_run_only=True,
            relaymem_local_scheduler_apply_enabled=False,
            relaymem_local_scheduler_replay_lane_enabled=False,
            relaymem_local_scheduler_queue_lane_enabled=False,
        )
    )
    assert build_relaymem_slp_scheduler_gates(disabled_no_lanes).mode == "disabled"

    # Scheduler apply does not rewrite or elevate either lower authority.
    lower_dry_run = make_config(
        relaymem_local_scheduler_enabled=True,
        relaymem_local_scheduler_dry_run_only=False,
        relaymem_local_scheduler_apply_enabled=True,
        relaymem_local_worker_enabled=True,
        relaymem_local_worker_dry_run_only=True,
        relaymem_local_worker_apply_enabled=False,
        relaymem_slp_durable_finalization_enabled=True,
        relaymem_slp_durable_finalization_dry_run_only=True,
        relaymem_slp_durable_finalization_apply_enabled=False,
    )
    assert build_relaymem_slp_scheduler_gates(lower_dry_run).mode == "apply"
    assert lower_dry_run.relaymem_local_worker_dry_run_only is True
    assert lower_dry_run.relaymem_local_worker_apply_enabled is False
    assert lower_dry_run.relaymem_slp_durable_finalization_dry_run_only is True
    assert lower_dry_run.relaymem_slp_durable_finalization_apply_enabled is False
    print("O1D1 config smoke passed")


if __name__ == "__main__":
    main()
