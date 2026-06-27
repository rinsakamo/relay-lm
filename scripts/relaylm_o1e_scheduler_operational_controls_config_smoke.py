from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pydantic import ValidationError

from relaylm.config import RelayLMConfig, load_config
from relaylm.relaymem_slp_scheduler_operations import validate_scheduler_operational_controls_config


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _raw(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "backends": {"local": {"base_url": "http://127.0.0.1:8000/v1"}},
        "model_routes": {"relaylm-default": {"backend": "local"}},
    }
    data.update(overrides)
    return data


def _config(**overrides: Any) -> RelayLMConfig:
    return RelayLMConfig.model_validate(_raw(**overrides))


def _rejects(**overrides: Any) -> None:
    try:
        RelayLMConfig.model_validate(_raw(**overrides))
    except ValidationError:
        return
    except ValueError:
        return
    raise AssertionError(f"config unexpectedly accepted: {overrides}")


def main() -> int:
    default = _config()
    require(validate_scheduler_operational_controls_config(default) == ("disabled", "disabled", ()), default)

    dry = _config(
        relaymem_local_scheduler_operational_controls_enabled=True,
        relaymem_local_scheduler_operational_controls_dry_run_only=True,
        relaymem_local_scheduler_operational_controls_apply_enabled=False,
    )
    require(validate_scheduler_operational_controls_config(dry) == ("dry_run", "disabled", ()), dry)

    apply = _config(
        relaymem_local_scheduler_operational_controls_enabled=True,
        relaymem_local_scheduler_operational_controls_dry_run_only=False,
        relaymem_local_scheduler_operational_controls_apply_enabled=True,
        relaymem_local_scheduler_stale_recovery_enabled=True,
        relaymem_local_scheduler_stale_recovery_dry_run_only=False,
        relaymem_local_scheduler_stale_recovery_apply_enabled=True,
    )
    require(validate_scheduler_operational_controls_config(apply) == ("apply", "apply", ()), apply)

    _rejects(
        relaymem_local_scheduler_operational_controls_enabled=True,
        relaymem_local_scheduler_operational_controls_dry_run_only=False,
        relaymem_local_scheduler_operational_controls_apply_enabled=False,
    )
    _rejects(
        relaymem_local_scheduler_stale_recovery_enabled=True,
        relaymem_local_scheduler_stale_recovery_dry_run_only=True,
        relaymem_local_scheduler_stale_recovery_apply_enabled=False,
    )
    _rejects(
        relaymem_local_scheduler_operational_controls_enabled=True,
        relaymem_local_scheduler_operational_controls_dry_run_only=True,
        relaymem_local_scheduler_operational_controls_apply_enabled=False,
        relaymem_local_scheduler_stale_recovery_enabled=True,
        relaymem_local_scheduler_stale_recovery_dry_run_only=False,
        relaymem_local_scheduler_stale_recovery_apply_enabled=True,
    )
    _rejects(
        relaymem_local_scheduler_operational_controls_enabled=True,
        relaymem_local_scheduler_operational_controls_dry_run_only=True,
        relaymem_local_scheduler_operational_controls_apply_enabled=False,
        relaymem_local_scheduler_apply_enabled=True,
    )
    _rejects(
        relaymem_local_scheduler_operational_controls_enabled=1,
        relaymem_local_scheduler_operational_controls_dry_run_only=True,
        relaymem_local_scheduler_operational_controls_apply_enabled=False,
    )
    _rejects(relaymem_local_scheduler_stale_recovery_max_scan_entries=0)
    _rejects(relaymem_local_scheduler_stale_recovery_max_scan_entries=4097)

    example = load_config(REPO_ROOT / "config.example.yaml")
    require(validate_scheduler_operational_controls_config(example) == ("disabled", "disabled", ()), example)
    print("ok O1E config gates fail closed and config.example loads")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
