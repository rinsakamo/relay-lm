"""Fresh scientific-owner campaign descriptor preparation for RelayLM v1.

This module is qualification-only.  It deliberately does not accept a prior
campaign descriptor as input.  Owner-local roots and Hindsight operational
identity are derived from a fresh owner root/id.  Campaign axes are the
canonical launch-intent inputs; duplicated execution-freeze release cases are
derived from those axes.  The existing campaign parser remains the final
admission authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.external_qualification import validate_case
from tools.v1_external_qualification_llama_cpp_campaign import (
    CAMPAIGN_FORMAT_VERSION,
    CAMPAIGN_TARGET,
    CampaignAxis,
    CampaignCarriageError,
    CampaignQuestion,
    CampaignDescriptor,
    HindsightLifecycleSpec,
    RelayLMExactRCSpec,
    _campaign_contract,
    _fingerprint,
    _hindsight_operational_fingerprint,
    _hindsight_owner_deployment_id,
)

_HINDSIGHT_TEMPLATE_IMPLEMENTATIONS = frozenset({"hindsight", "Hindsight"})
_RELAYLM_TEMPLATE_IMPLEMENTATIONS = frozenset({"relaylm", "relaylm_exact_rc"})


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


def _canonicalize_hindsight_template_identity(
    identity: dict[str, Any],
    *,
    label: str,
) -> None:
    implementation = identity.get("implementation")
    if implementation not in _HINDSIGHT_TEMPLATE_IMPLEMENTATIONS:
        raise CampaignCarriageError(f"{label} must be Hindsight")
    identity["implementation"] = "hindsight"


def _canonicalize_relaylm_template_identity(
    identity: dict[str, Any],
    *,
    label: str,
) -> None:
    implementation = identity.get("implementation")
    if implementation not in _RELAYLM_TEMPLATE_IMPLEMENTATIONS:
        raise CampaignCarriageError(f"{label} must be RelayLM")
    identity["implementation"] = "relaylm"


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
            if not isinstance(identity, dict):
                raise CampaignCarriageError("serious comparator must be Hindsight")
            _canonicalize_hindsight_template_identity(
                identity,
                label="serious comparator",
            )
            identity["source_revision"] = lifecycle.source_revision
            identity["version"] = lifecycle.runtime_version
            identity["deployment"] = operational_fingerprint
        elif slot == "relaylm_exact_rc":
            rc_count += 1
            if not isinstance(identity, dict):
                raise CampaignCarriageError("relaylm_exact_rc participant must be RelayLM")
            _canonicalize_relaylm_template_identity(
                identity,
                label="relaylm_exact_rc participant",
            )
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


def _canonicalize_benchmark_material_template(raw: dict[str, Any]) -> None:
    if "benchmark_material" not in raw:
        return
    material = raw.get("benchmark_material")
    case = raw.get("case")
    questions = raw.get("questions")
    if not isinstance(material, dict):
        raise CampaignCarriageError("campaign axis benchmark_material must be an object")
    if not isinstance(case, Mapping):
        raise CampaignCarriageError("campaign axis case must be an object")
    if not isinstance(questions, list) or not questions:
        raise CampaignCarriageError("campaign axis questions must be a non-empty list")

    source_case_fingerprint = material.get("case_fingerprint")
    if (
        not isinstance(source_case_fingerprint, str)
        or not source_case_fingerprint.startswith("sha256:")
        or len(source_case_fingerprint) != 71
    ):
        raise CampaignCarriageError(
            "campaign axis source benchmark material case fingerprint is invalid"
        )
    source_question_fingerprints = material.get("question_fingerprints")
    if not isinstance(source_question_fingerprints, list) or not all(
        isinstance(item, str) and item.startswith("sha256:") and len(item) == 71
        for item in source_question_fingerprints
    ):
        raise CampaignCarriageError(
            "campaign axis source benchmark material question fingerprints are invalid"
        )

    normalized_case = validate_case(case)
    parsed_questions: list[CampaignQuestion] = []
    for item in questions:
        if not isinstance(item, Mapping):
            raise CampaignCarriageError("campaign axis question must be an object")
        parsed_questions.append(CampaignQuestion.from_mapping(item))
    material["case_fingerprint"] = _fingerprint(normalized_case)
    material["question_fingerprints"] = [
        question.content_fingerprint for question in parsed_questions
    ]


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
        _canonicalize_benchmark_material_template(raw)
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
    """Derive release-case duplicates from canonical prepared axes.

    The execution-freeze template contributes launch intent that is not already
    owned by an axis: planned-axis declarations, comparator family, registered
    physical carriage, and retry/resume policy.  Its historical release_cases
    are not independent authority and are replaced wholesale.
    """

    freeze = _mapping_copy(execution_freeze, label="execution freeze template")
    comparator = freeze.get("comparator")
    if not isinstance(comparator, dict):
        raise CampaignCarriageError("execution freeze comparator must be Hindsight")
    _canonicalize_hindsight_template_identity(
        comparator,
        label="execution freeze comparator",
    )
    comparator["source_revision"] = lifecycle.source_revision
    comparator["version"] = lifecycle.runtime_version

    if not isinstance(freeze.get("release_cases"), list):
        raise CampaignCarriageError("execution freeze release_cases must be a list")

    release_cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for axis in axes:
        if not isinstance(axis, Mapping):
            raise CampaignCarriageError("prepared axis must be an object")
        axis_id = axis.get("axis_id")
        if not isinstance(axis_id, str) or not axis_id or axis_id in seen:
            raise CampaignCarriageError("prepared axes must have unique axis_id values")
        seen.add(axis_id)
        release_case: dict[str, Any] = {
            "axis_id": axis_id,
            "case": _json_copy(axis["case"], label="prepared axis case"),
            "manifest": _json_copy(axis["manifest"], label="prepared axis manifest"),
        }
        if "benchmark_material" in axis:
            release_case["benchmark_material"] = _json_copy(
                axis["benchmark_material"],
                label="prepared benchmark material",
            )
        if "history_material" in axis:
            release_case["history_material"] = _json_copy(
                axis["history_material"],
                label="prepared Hindsight history material",
            )
        release_cases.append(release_case)

    freeze["release_cases"] = release_cases
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
    result.  Historical execution-freeze release-case copies are deliberately
    ignored and re-derived from the validated prepared axes.
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
