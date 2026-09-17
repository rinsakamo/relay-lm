"""Fresh scientific-owner campaign descriptor preparation for RelayLM v1.

This module is qualification-only.  It deliberately does not accept a prior
campaign descriptor as input.  Owner-local roots and Hindsight operational
identity are derived from a fresh owner root/id, while the existing campaign
parser remains the final admission authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.v1_external_qualification_llama_cpp_campaign import (
    CAMPAIGN_FORMAT_VERSION,
    CAMPAIGN_TARGET,
    CampaignAxis,
    CampaignCarriageError,
    CampaignDescriptor,
    HindsightLifecycleSpec,
    RelayLMExactRCSpec,
    _campaign_contract,
    _hindsight_operational_fingerprint,
    _hindsight_owner_deployment_id,
)


def _json_copy(value: object, *, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise CampaignCarriageError(f"{label} must be JSON serializable") from exc


def _mapping_copy(value: Mapping[str, object], *, label: str) -> dict[str, Any]:
    copied = _json_copy(dict(value), label=label)
    if not isinstance(copied, dict):
        raise CampaignCarriageError(f"{label} must be an object")
    return copied


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _descriptor_sha256(value: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_owner_root(owner_id: str, owner_root: str | Path) -> Path:
    # The deployment-id helper is the repository-owned owner-id validator.
    _hindsight_owner_deployment_id(owner_id)
    root = Path(owner_root)
    if not root.is_absolute():
        raise CampaignCarriageError("scientific owner root must be absolute")
    if root.name != owner_id:
        raise CampaignCarriageError("scientific owner root leaf must equal owner_id")
    if root.exists():
        raise CampaignCarriageError("scientific owner root must be fresh and absent")
    return root


def _derive_hindsight_lifecycle(
    *,
    owner_id: str,
    base: Mapping[str, object],
) -> HindsightLifecycleSpec:
    raw = _mapping_copy(base, label="Hindsight lifecycle base")
    forbidden = {"deployment_id", "database_profile"} & set(raw)
    if forbidden:
        raise CampaignCarriageError(
            "Hindsight lifecycle base must omit owner-local fields: "
            + ", ".join(sorted(forbidden))
        )
    raw["deployment_id"] = _hindsight_owner_deployment_id(owner_id)
    raw["database_profile"] = owner_id
    return HindsightLifecycleSpec.from_mapping(raw)


def _derive_hindsight_health(
    *,
    lifecycle: HindsightLifecycleSpec,
    license_name: str,
) -> dict[str, object]:
    if not isinstance(license_name, str) or not license_name.strip():
        raise CampaignCarriageError("Hindsight license must be a non-empty string")
    return {
        "implementation": "hindsight",
        "source_revision": lifecycle.source_revision,
        "version": lifecycle.runtime_version,
        "license": license_name,
        "deployment": {
            "deployment_id": lifecycle.deployment_id,
            "dependency_fingerprint": lifecycle.dependency_fingerprint,
            "import_status": "passed",
            "llm_connection_verification": "skipped_zero_semantic_policy",
            "process_health_status": "passed",
            "capability_status": "passed",
        },
        "semantic_operations_called": [],
        "semantic_generation_count": 0,
        "benchmark_question_count": 0,
        "answer_model_generation_count": 0,
        "judge_call_count": 0,
    }


def _rewrite_release_identity(
    manifest: dict[str, Any],
    *,
    exact_rc: RelayLMExactRCSpec,
    operational_fingerprint: str,
    lifecycle: HindsightLifecycleSpec,
) -> None:
    participants = manifest.get("participants")
    if not isinstance(participants, list):
        raise CampaignCarriageError("campaign manifest participants must be a list")
    comparator_count = 0
    rc_count = 0
    for participant in participants:
        if not isinstance(participant, dict):
            raise CampaignCarriageError("campaign participant must be an object")
        slot = participant.get("slot")
        identity = participant.get("identity")
        if slot == "serious_comparator":
            comparator_count += 1
            if not isinstance(identity, dict) or identity.get("implementation") != "hindsight":
                raise CampaignCarriageError("serious comparator must be Hindsight")
            identity["source_revision"] = lifecycle.source_revision
            identity["version"] = lifecycle.runtime_version
            identity["deployment"] = operational_fingerprint
        elif slot == "relaylm_exact_rc":
            rc_count += 1
            if not isinstance(identity, dict) or identity.get("implementation") != "relaylm":
                raise CampaignCarriageError("relaylm_exact_rc participant must be RelayLM")
            identity["source_revision"] = exact_rc.source_revision
            identity["version"] = exact_rc.version
    if comparator_count != 1 or rc_count != 1:
        raise CampaignCarriageError(
            "campaign manifest must contain exactly one serious comparator and exact RC"
        )

    release = manifest.get("relaylm_release")
    if not isinstance(release, dict):
        raise CampaignCarriageError("campaign manifest requires relaylm_release")
    release["version"] = exact_rc.version
    release["commit"] = exact_rc.source_revision
    artifacts = release.get("artifacts")
    if not isinstance(artifacts, list):
        raise CampaignCarriageError("relaylm_release artifacts must be a list")
    wheels = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and artifact.get("filename") == exact_rc.wheel_path.name
    ]
    if len(wheels) != 1:
        raise CampaignCarriageError("relaylm_release must contain the exact RC wheel once")
    wheels[0]["sha256"] = exact_rc.wheel_sha256


def _derive_axes(
    *,
    axes: Sequence[Mapping[str, object]],
    exact_rc: RelayLMExactRCSpec,
    lifecycle: HindsightLifecycleSpec,
    authority: Mapping[str, object],
    operational_fingerprint: str,
) -> list[dict[str, Any]]:
    authority_copy = _mapping_copy(authority, label="current qualification authority")
    if authority_copy.get("status") != "CURRENT_AUTHORITY_CONFIRMED":
        raise CampaignCarriageError("current qualification authority was not confirmed")
    if authority_copy.get("branch") != "v1":
        raise CampaignCarriageError("scientific owner preparation requires v1 authority")

    prepared: list[dict[str, Any]] = []
    for source_axis in axes:
        raw = _mapping_copy(source_axis, label="campaign axis template")
        manifest = raw.get("manifest")
        identity = raw.get("identity")
        if not isinstance(manifest, dict) or not isinstance(identity, dict):
            raise CampaignCarriageError("campaign axis template is incomplete")
        _rewrite_release_identity(
            manifest,
            exact_rc=exact_rc,
            operational_fingerprint=operational_fingerprint,
            lifecycle=lifecycle,
        )
        identity["authority"] = _json_copy(
            authority_copy, label="current qualification authority"
        )
        identity["candidate"] = exact_rc.source_revision
        identity.pop("campaign_contract", None)
        parsed = CampaignAxis.from_mapping(raw)
        identity["campaign_contract"] = _campaign_contract(parsed)
        # Parse again so the returned mapping is known to satisfy the typed axis schema.
        CampaignAxis.from_mapping(raw)
        prepared.append(raw)
    return prepared


def _derive_execution_freeze(
    *,
    execution_freeze: Mapping[str, object],
    axes: Sequence[Mapping[str, object]],
    lifecycle: HindsightLifecycleSpec,
) -> dict[str, Any]:
    freeze = _mapping_copy(execution_freeze, label="execution freeze template")
    comparator = freeze.get("comparator")
    if not isinstance(comparator, dict) or comparator.get("implementation") != "hindsight":
        raise CampaignCarriageError("execution freeze comparator must be Hindsight")
    comparator["source_revision"] = lifecycle.source_revision
    comparator["version"] = lifecycle.runtime_version

    release_cases = freeze.get("release_cases")
    if not isinstance(release_cases, list):
        raise CampaignCarriageError("execution freeze release_cases must be a list")
    axis_by_id = {
        str(axis.get("axis_id")): axis
        for axis in axes
        if isinstance(axis, Mapping) and axis.get("axis_id") is not None
    }
    if len(axis_by_id) != len(axes):
        raise CampaignCarriageError("prepared axes must have unique axis_id values")
    seen: set[str] = set()
    for release_case in release_cases:
        if not isinstance(release_case, dict):
            raise CampaignCarriageError("execution freeze release case must be an object")
        axis_id = str(release_case.get("axis_id"))
        axis = axis_by_id.get(axis_id)
        if axis is None or axis_id in seen:
            raise CampaignCarriageError("execution freeze release cases do not match prepared axes")
        seen.add(axis_id)
        release_case["case"] = _json_copy(axis["case"], label="prepared axis case")
        release_case["manifest"] = _json_copy(
            axis["manifest"], label="prepared axis manifest"
        )
        if "benchmark_material" in axis:
            release_case["benchmark_material"] = _json_copy(
                axis["benchmark_material"], label="prepared benchmark material"
            )
    if seen != set(axis_by_id):
        raise CampaignCarriageError("execution freeze must cover every prepared axis")
    return freeze


@dataclass(frozen=True, slots=True)
class PreparedScientificOwnerDescriptor:
    """Validated fresh descriptor plus immutable preparation fingerprints."""

    mapping: Mapping[str, object]
    descriptor_sha256: str
    campaign_fingerprint: str

    def to_mapping(self) -> dict[str, Any]:
        return _mapping_copy(self.mapping, label="prepared campaign descriptor")


def prepare_scientific_owner_descriptor(
    *,
    owner_id: str,
    owner_root: str | Path,
    execution_freeze: Mapping[str, object],
    axes: Sequence[Mapping[str, object]],
    llama_cpp: Mapping[str, object],
    relaylm_exact_rc: Mapping[str, object],
    hindsight_lifecycle_base: Mapping[str, object],
    authority: Mapping[str, object],
    hindsight_license: str = "MIT",
) -> PreparedScientificOwnerDescriptor:
    """Derive a new owner descriptor without accepting an old descriptor object.

    ``hindsight_lifecycle_base`` intentionally cannot carry ``deployment_id`` or
    ``database_profile``.  Those values, owner-local roots, expected health,
    comparator deployment identity, frozen campaign contracts, and authority
    are all derived here before the existing production parser admits the
    result.
    """

    root = _require_owner_root(owner_id, owner_root)
    exact_rc = RelayLMExactRCSpec.from_mapping(
        _mapping_copy(relaylm_exact_rc, label="exact RC identity")
    )
    lifecycle = _derive_hindsight_lifecycle(
        owner_id=owner_id,
        base=hindsight_lifecycle_base,
    )
    operational_fingerprint = _hindsight_operational_fingerprint(owner_id, lifecycle)
    prepared_axes = _derive_axes(
        axes=axes,
        exact_rc=exact_rc,
        lifecycle=lifecycle,
        authority=authority,
        operational_fingerprint=operational_fingerprint,
    )
    prepared_freeze = _derive_execution_freeze(
        execution_freeze=execution_freeze,
        axes=prepared_axes,
        lifecycle=lifecycle,
    )
    raw: dict[str, object] = {
        "format_version": CAMPAIGN_FORMAT_VERSION,
        "target": CAMPAIGN_TARGET,
        "execution_freeze": prepared_freeze,
        "artifact_root": str(root / "campaign-artifacts"),
        "llama_cpp": _mapping_copy(llama_cpp, label="llama.cpp launch identity"),
        "hindsight_health": _derive_hindsight_health(
            lifecycle=lifecycle,
            license_name=hindsight_license,
        ),
        "axes": prepared_axes,
        "owner_id": owner_id,
        "spend_ledger_path": str(root / "scientific-spend.json"),
        "relaylm_exact_rc": exact_rc.to_mapping(),
        "hindsight_lifecycle": lifecycle.to_mapping(),
    }
    admitted = CampaignDescriptor.from_mapping(raw)
    return PreparedScientificOwnerDescriptor(
        mapping=_mapping_copy(raw, label="prepared campaign descriptor"),
        descriptor_sha256=_descriptor_sha256(raw),
        campaign_fingerprint=admitted.fingerprint,
    )
