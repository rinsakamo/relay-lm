from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from tools.external_qualification import (
    ExternalQualificationError,
    validate_case,
    validate_manifest,
)

READINESS_FORMAT_VERSION = 1
READINESS_PHASES = {"pre_rc_readiness", "execution_freeze"}
RETRY_POLICY = "no_semantic_retry_or_fallback"
RESUME_POLICY = "exact_infrastructure_resume_only"


class ExternalQualificationReadinessError(ExternalQualificationError):
    """A bounded external-qualification launch plan is not ready."""


def validate_launch_readiness(raw: Mapping[str, object]) -> dict[str, object]:
    """Validate one zero-generation or execution-freeze benchmark launch plan."""

    _keys(
        raw,
        {
            "format_version",
            "phase",
            "axes",
            "comparator",
            "physical_carriage",
            "release_cases",
            "retry_policy",
            "resume_policy",
        },
        "launch readiness",
    )
    if raw["format_version"] != READINESS_FORMAT_VERSION:
        raise ExternalQualificationReadinessError(
            f"unsupported readiness format_version: {raw['format_version']}"
        )
    phase = _text(raw["phase"], "readiness phase")
    if phase not in READINESS_PHASES:
        raise ExternalQualificationReadinessError(
            f"unsupported readiness phase: {phase}"
        )

    axes = _axes(raw["axes"])
    comparator = _comparator(raw["comparator"])
    carriage = _physical_carriage(raw["physical_carriage"])
    retry_policy = _text(raw["retry_policy"], "retry_policy")
    resume_policy = _text(raw["resume_policy"], "resume_policy")
    if retry_policy != RETRY_POLICY:
        raise ExternalQualificationReadinessError(
            f"retry_policy must be {RETRY_POLICY}"
        )
    if resume_policy != RESUME_POLICY:
        raise ExternalQualificationReadinessError(
            f"resume_policy must be {RESUME_POLICY}"
        )

    release_cases = raw["release_cases"]
    if not isinstance(release_cases, list):
        raise ExternalQualificationReadinessError("release_cases must be a list")

    if phase == "pre_rc_readiness":
        if release_cases:
            raise ExternalQualificationReadinessError(
                "pre-RC readiness must not carry citable release cases"
            )
        normalized = {
            "format_version": READINESS_FORMAT_VERSION,
            "phase": phase,
            "status": "READY_EXCEPT_EXACT_RC",
            "axes": axes,
            "comparator": comparator,
            "physical_carriage": carriage,
            "release_cases": [],
            "relaylm_release": None,
            "retry_policy": retry_policy,
            "resume_policy": resume_policy,
        }
        return _with_fingerprint(normalized)

    if not carriage["registered"]:
        raise ExternalQualificationReadinessError(
            "execution freeze requires registered physical carriage"
        )
    for field in ("source_revision", "version", "license"):
        if comparator[field] is None:
            raise ExternalQualificationReadinessError(
                f"execution freeze requires exact comparator {field}"
            )
    if len(release_cases) != len(axes):
        raise ExternalQualificationReadinessError(
            "execution freeze requires exactly one release case per planned axis"
        )

    planned_by_id = {item["axis_id"]: item for item in axes}
    normalized_cases: list[dict[str, object]] = []
    release_identity: dict[str, object] | None = None
    seen_axis_ids: set[str] = set()

    for index, item in enumerate(release_cases):
        entry = _mapping(item, f"release case {index}")
        _keys(entry, {"axis_id", "case", "manifest"}, f"release case {index}")
        axis_id = _text(entry["axis_id"], f"release case {index} axis_id")
        if axis_id in seen_axis_ids:
            raise ExternalQualificationReadinessError(
                f"duplicate release case axis_id: {axis_id}"
            )
        planned = planned_by_id.get(axis_id)
        if planned is None:
            raise ExternalQualificationReadinessError(
                f"release case axis_id is not planned: {axis_id}"
            )

        case = validate_case(_mapping(entry["case"], f"release case {axis_id} case"))
        manifest = validate_manifest(
            _mapping(entry["manifest"], f"release case {axis_id} manifest")
        )
        if manifest["purpose"] != "release_qualification" or not manifest["citable"]:
            raise ExternalQualificationReadinessError(
                "execution freeze requires citable release_qualification manifests"
            )
        if case["axis"] != planned["axis_family"]:
            raise ExternalQualificationReadinessError(
                f"release case {axis_id} axis does not match planned axis family"
            )
        benchmark = _mapping(case["benchmark"], "validated benchmark")
        if benchmark["id"] != planned["benchmark_id"]:
            raise ExternalQualificationReadinessError(
                f"release case {axis_id} benchmark does not match plan"
            )
        adapter = _mapping(manifest["adapter"], "validated manifest adapter")
        if adapter["identity"] != planned["adapter_id"]:
            raise ExternalQualificationReadinessError(
                f"release case {axis_id} adapter does not match plan"
            )

        participants = {
            _text(participant["slot"], "participant slot"): participant
            for participant in manifest["participants"]
            if isinstance(participant, Mapping)
        }
        comparator_plan = _mapping(
            participants["serious_comparator"], "serious comparator participant"
        )
        comparator_identity = _mapping(
            comparator_plan["identity"], "serious comparator identity"
        )
        for field in ("implementation", "source_revision", "version", "license"):
            if comparator_identity[field] != comparator[field]:
                raise ExternalQualificationReadinessError(
                    f"release case {axis_id} comparator {field} does not match plan"
                )

        current_release = _mapping(
            manifest["relaylm_release"], "validated relaylm_release"
        )
        if release_identity is None:
            release_identity = dict(current_release)
        elif _canonical_json(current_release) != _canonical_json(release_identity):
            raise ExternalQualificationReadinessError(
                "all execution-freeze cases must bind the same exact RelayLM release"
            )

        seen_axis_ids.add(axis_id)
        normalized_cases.append(
            {
                "axis_id": axis_id,
                "case": case,
                "manifest": manifest,
            }
        )

    if seen_axis_ids != set(planned_by_id):
        raise ExternalQualificationReadinessError(
            "execution freeze does not cover every planned axis exactly once"
        )
    assert release_identity is not None
    normalized = {
        "format_version": READINESS_FORMAT_VERSION,
        "phase": phase,
        "status": "EXECUTION_FROZEN",
        "axes": axes,
        "comparator": comparator,
        "physical_carriage": carriage,
        "release_cases": normalized_cases,
        "relaylm_release": release_identity,
        "retry_policy": retry_policy,
        "resume_policy": resume_policy,
    }
    return _with_fingerprint(normalized)


def assess_launch_readiness(raw: Mapping[str, object]) -> dict[str, object]:
    """Return a bounded BLOCKED record instead of raising on readiness failure."""

    try:
        return validate_launch_readiness(raw)
    except ExternalQualificationError as exc:
        return {
            "format_version": READINESS_FORMAT_VERSION,
            "status": "BLOCKED",
            "reason": str(exc),
        }


def _axes(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list) or len(raw) < 2:
        raise ExternalQualificationReadinessError(
            "launch readiness requires at least two planned axes"
        )
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(raw):
        axis = _mapping(item, f"axis {index}")
        _keys(
            axis,
            {"axis_id", "axis_family", "benchmark_id", "adapter_id"},
            f"axis {index}",
        )
        normalized.append(
            {
                "axis_id": _text(axis["axis_id"], f"axis {index} axis_id"),
                "axis_family": _text(
                    axis["axis_family"], f"axis {index} axis_family"
                ),
                "benchmark_id": _text(
                    axis["benchmark_id"], f"axis {index} benchmark_id"
                ),
                "adapter_id": _text(
                    axis["adapter_id"], f"axis {index} adapter_id"
                ),
            }
        )
    for field in ("axis_id", "axis_family"):
        values = [item[field] for item in normalized]
        if len(set(values)) != len(values):
            raise ExternalQualificationReadinessError(
                f"planned axes must have distinct {field} values"
            )
    return normalized


def _comparator(raw: object) -> dict[str, str | None]:
    value = _mapping(raw, "comparator")
    _keys(
        value,
        {
            "implementation",
            "repository",
            "source_revision",
            "version",
            "license",
        },
        "comparator",
    )
    return {
        "implementation": _text(value["implementation"], "comparator implementation"),
        "repository": _text(value["repository"], "comparator repository"),
        "source_revision": _optional_text(
            value["source_revision"], "comparator source_revision"
        ),
        "version": _optional_text(value["version"], "comparator version"),
        "license": _optional_text(value["license"], "comparator license"),
    }


def _physical_carriage(raw: object) -> dict[str, object]:
    value = _mapping(raw, "physical_carriage")
    _keys(
        value,
        {"target", "backend", "resource_key", "registered"},
        "physical_carriage",
    )
    registered = value["registered"]
    if not isinstance(registered, bool):
        raise ExternalQualificationReadinessError(
            "physical_carriage registered must be boolean"
        )
    return {
        "target": _text(value["target"], "physical target"),
        "backend": _text(value["backend"], "physical backend"),
        "resource_key": _text(value["resource_key"], "physical resource_key"),
        "registered": registered,
    }


def _with_fingerprint(value: Mapping[str, object]) -> dict[str, object]:
    normalized = dict(value)
    encoded = _canonical_json(normalized).encode("utf-8")
    normalized["fingerprint"] = f"sha256:{hashlib.sha256(encoded).hexdigest()}"
    return normalized


def _keys(raw: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(raw) != expected:
        raise ExternalQualificationReadinessError(
            f"{label} keys must be exactly {sorted(expected)}"
        )


def _mapping(raw: object, label: str) -> Mapping[str, object]:
    if not isinstance(raw, Mapping):
        raise ExternalQualificationReadinessError(f"{label} must be an object")
    return raw


def _text(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ExternalQualificationReadinessError(f"{label} must be non-empty")
    return raw.strip()


def _optional_text(raw: object, label: str) -> str | None:
    if raw is None:
        return None
    return _text(raw, label)


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ExternalQualificationReadinessError(
            "launch readiness must be JSON-serializable"
        ) from exc
