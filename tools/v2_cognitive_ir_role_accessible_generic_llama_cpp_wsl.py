from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy
from tools.physical_common_generation import (
    DEFAULT_CERTIFICATE,
    load_certificate,
    verify_checkout,
)
from tools.relay_physical_run import _load_targets


INNER_TRANSACTION_MODULE_ROLE_ACCESSIBLE_GENERIC = (
    "tools.v2_cognitive_ir_role_accessible_generic_llama_cpp_transaction"
)
WALL_TIME_SCHEMA_ROLE_ACCESSIBLE_GENERIC = (
    "relaylm2-cognitive-ir-role-accessible-generic-wsl-wall-time-v1"
)
COMMON_PHYSICAL_GENERATION_ID = "relay-common-physical-g2"
COMMON_PHYSICAL_AGGREGATE_IDENTITY = (
    "sha256:bb983011905bdd8b5393c2c3459b691289f5ced9a41561bb8dc7f642fa330b87"
)
TARGET_NAME = "v2:role-accessible-generic"
TARGET_BRANCH = "v2"
TARGET_MODULE = "tools.v2_cognitive_ir_role_accessible_generic_llama_cpp_wsl"
TARGET_REQUIRED_DISTRIBUTIONS = ("httpx",)


class RoleAccessibleGenericWslLauncherError(RuntimeError):
    """The #2904 WSL adapter cannot bind the E5-RA1 transaction."""


def verify_common_physical_binding(
    repo_root: Path | None = None,
) -> Mapping[str, str]:
    root = (
        repo_root.resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[1]
    )
    certificate = load_certificate(root / DEFAULT_CERTIFICATE)
    identity = verify_checkout(
        root,
        certificate,
        expected_generation_id=COMMON_PHYSICAL_GENERATION_ID,
        expected_aggregate_identity=COMMON_PHYSICAL_AGGREGATE_IDENTITY,
    )
    targets = _load_targets(root)
    target = targets.get(TARGET_NAME)
    if target is None:
        raise RoleAccessibleGenericWslLauncherError(
            f"common target registry is missing {TARGET_NAME}"
        )
    if (
        target.branch != TARGET_BRANCH
        or target.module != TARGET_MODULE
        or target.required_distributions != TARGET_REQUIRED_DISTRIBUTIONS
    ):
        raise RoleAccessibleGenericWslLauncherError(
            "E5-RA1 common target registry binding drifted"
        )
    return identity


def main(argv: Sequence[str] | None = None) -> int:
    verify_common_physical_binding()
    expected = "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    if legacy.INNER_TRANSACTION_MODULE != expected:
        raise RoleAccessibleGenericWslLauncherError(
            "legacy shared-floor WSL transaction module binding drifted"
        )
    old_module = legacy.INNER_TRANSACTION_MODULE
    old_schema = legacy.WALL_TIME_SCHEMA
    legacy.INNER_TRANSACTION_MODULE = INNER_TRANSACTION_MODULE_ROLE_ACCESSIBLE_GENERIC
    legacy.WALL_TIME_SCHEMA = WALL_TIME_SCHEMA_ROLE_ACCESSIBLE_GENERIC
    try:
        return legacy.main(argv)
    finally:
        legacy.INNER_TRANSACTION_MODULE = old_module
        legacy.WALL_TIME_SCHEMA = old_schema


if __name__ == "__main__":
    raise SystemExit(main())
