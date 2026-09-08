from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json

from tools.external_qualification import (
    FROZEN_EXPERIMENT_IDENTITY_FIELDS,
    LIVE_LAUNCH_ADMISSION_FIELDS,
)


PREFLIGHT_VERSION = "relaylm2-host-owned-physical-preflight-v1"
CONTROLLER_MAX_ESTABLISHMENT_CYCLES = 3


class PhysicalControllerPreflightError(ValueError):
    """The read-only controller setup does not satisfy the canonical contract."""


@dataclass(frozen=True, slots=True)
class ControllerPreflightResult:
    version: str
    identity_snapshot: Mapping[str, object]
    material_binding: Mapping[str, object]


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise PhysicalControllerPreflightError(
            "physical controller preflight values must be canonical JSON"
        ) from exc


def _snapshot(value: Mapping[str, object], label: str) -> dict[str, object]:
    copied = json.loads(_canonical_json(dict(value)))
    if not isinstance(copied, dict):
        raise PhysicalControllerPreflightError(f"{label} must be an object")
    return copied


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PhysicalControllerPreflightError(f"{label} must be an object")
    return value


def _equal(left: object, right: object) -> bool:
    return _canonical_json(left) == _canonical_json(right)


def validate_frozen_identity_controller_setup(
    *,
    identity: Mapping[str, object],
    material_binding_fields: Sequence[str],
    observed_binding_a: Mapping[str, object],
    observed_binding_b: Mapping[str, object],
) -> ControllerPreflightResult:
    """Validate the controller-owned read-only portion of physical preflight.

    This function deliberately does not freeze an experiment identity, create a
    durable run, authorize a scientific transaction, or call a provider. Those
    responsibilities stay inside the experiment host.
    """

    identity_snapshot = _snapshot(identity, "raw experiment identity")
    if set(identity_snapshot) != set(FROZEN_EXPERIMENT_IDENTITY_FIELDS):
        missing = sorted(set(FROZEN_EXPERIMENT_IDENTITY_FIELDS) - set(identity_snapshot))
        extra = sorted(set(identity_snapshot) - set(FROZEN_EXPERIMENT_IDENTITY_FIELDS))
        raise PhysicalControllerPreflightError(
            f"raw experiment identity field set mismatch; missing={missing!r} extra={extra!r}"
        )

    launch = _mapping(identity_snapshot.get("launch_admission"), "launch admission")
    if set(launch) != set(LIVE_LAUNCH_ADMISSION_FIELDS):
        missing = sorted(set(LIVE_LAUNCH_ADMISSION_FIELDS) - set(launch))
        extra = sorted(set(launch) - set(LIVE_LAUNCH_ADMISSION_FIELDS))
        raise PhysicalControllerPreflightError(
            f"launch admission field set mismatch; missing={missing!r} extra={extra!r}"
        )

    for identity_name, launch_name in (
        ("backend", "backend"),
        ("runtime", "runtime"),
        ("context_capacity", "admitted_context"),
        ("capacity_evidence", "capacity_evidence"),
    ):
        if not _equal(identity_snapshot[identity_name], launch[launch_name]):
            raise PhysicalControllerPreflightError(
                f"controller identity {identity_name} does not mirror launch_admission.{launch_name}"
            )

    fields = tuple(material_binding_fields)
    if not fields or len(set(fields)) != len(fields):
        raise PhysicalControllerPreflightError(
            "material binding fields must be a non-empty unique sequence"
        )
    missing_binding = [name for name in fields if name not in identity_snapshot]
    if missing_binding:
        raise PhysicalControllerPreflightError(
            "raw experiment identity is missing material binding fields: "
            + ", ".join(missing_binding)
        )

    expected_binding = _snapshot(
        {name: identity_snapshot[name] for name in fields},
        "material binding",
    )
    for label, observed in (
        ("binding A", observed_binding_a),
        ("binding B", observed_binding_b),
    ):
        observed_snapshot = _snapshot(observed, label)
        if set(observed_snapshot) != set(fields):
            raise PhysicalControllerPreflightError(
                f"{label} field set does not match the host material binding"
            )
        if not _equal(observed_snapshot, expected_binding):
            raise PhysicalControllerPreflightError(
                f"{label} does not match the proposed host material binding"
            )

    if not _equal(observed_binding_a, observed_binding_b):
        raise PhysicalControllerPreflightError(
            "fresh controller binding A/B observations disagree"
        )

    return ControllerPreflightResult(
        version=PREFLIGHT_VERSION,
        identity_snapshot=identity_snapshot,
        material_binding=expected_binding,
    )
