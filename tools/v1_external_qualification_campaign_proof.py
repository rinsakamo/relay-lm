"""Static preparation and zero-semantic rehearsal verification for RelayLM v1.

This helper is qualification-only. It never invokes the public physical target and
never authorizes scientific execution. It turns preserved campaign source material
into a fresh-owner descriptor through the repository-owned preparation path and
verifies a completed public ``--rehearsal`` receipt/output bundle.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import socket
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tools.external_qualification import (
    ExternalQualificationError,
    LiveLaunchAdmissionAttestation,
    validate_case,
)
from tools.repository_authority import load_declarations, qualification_fingerprint
from tools.v1_external_qualification_campaign_prepare import (
    prepare_scientific_owner_descriptor,
)
from tools.v1_external_qualification_history_material import (
    materialize_bounded_history_axes,
)
from tools.v1_external_qualification_llama_cpp_campaign import (
    CAMPAIGN_TARGET,
    HINDSIGHT_CONSOLIDATION_LLM_REASONING_EFFORT,
    HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS,
    HINDSIGHT_LLM_SUPPORTS_STRING_PATTERN,
    HINDSIGHT_RETAIN_LLM_REASONING_EFFORT,
    HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS,
    CampaignCarriageError,
    CampaignDescriptor,
    CampaignQuestion,
    _fingerprint,
    _hindsight_owner_deployment_id,
)


_PRESERVED_2964_SOURCE_SHA256 = (
    "2d18932c0e94962a27d4d9431a06bb9a10a14e8e1ff9c7f0f67cad8dbb81df64"
)


class CampaignProofError(CampaignCarriageError):
    """Raised when static or zero-semantic proof evidence fails closed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CampaignProofError(f"cannot hash proof file {path}: {exc}") from exc
    return digest.hexdigest()


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignProofError(f"cannot read {label}: {exc}") from exc
    if not isinstance(raw, dict):
        raise CampaignProofError(f"{label} must be a JSON object")
    return raw


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _valid_fingerprint(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _apply_preserved_2964_case_compatibility(
    raw: dict[str, Any],
    *,
    source_sha256: str,
) -> dict[str, object]:
    """Canonicalize only known dependent duplicate drift in exact #2964 source.

    Generic fresh-owner preparation remains strict.  This compatibility is
    available only for the exact preserved #2964 descriptor bytes.  Case
    identity may differ only by the opaque adapter_case_ref.  Benchmark
    material must identify exactly the same path and bytes; only the dependent
    case/question fingerprints may be re-derived.
    """

    if source_sha256 != _PRESERVED_2964_SOURCE_SHA256:
        return {"status": "NOT_APPLICABLE", "axes": []}

    axes = raw.get("axes")
    freeze = raw.get("execution_freeze")
    if not isinstance(axes, list) or not isinstance(freeze, dict):
        raise CampaignProofError("preserved #2964 source is missing axes/execution_freeze")
    release_cases = freeze.get("release_cases")
    if not isinstance(release_cases, list):
        raise CampaignProofError(
            "preserved #2964 execution_freeze release_cases must be a list"
        )

    axis_by_id: dict[str, dict[str, Any]] = {}
    for axis in axes:
        if not isinstance(axis, dict):
            raise CampaignProofError("preserved #2964 axis must be an object")
        axis_id = axis.get("axis_id")
        if not isinstance(axis_id, str) or not axis_id:
            raise CampaignProofError("preserved #2964 axis requires axis_id")
        if axis_id in axis_by_id:
            raise CampaignProofError("preserved #2964 axes contain duplicate axis_id")
        axis_by_id[axis_id] = axis

    release_by_id: dict[str, dict[str, Any]] = {}
    for release_case in release_cases:
        if not isinstance(release_case, dict):
            raise CampaignProofError("preserved #2964 release case must be an object")
        axis_id = release_case.get("axis_id")
        if not isinstance(axis_id, str) or not axis_id:
            raise CampaignProofError("preserved #2964 release case requires axis_id")
        if axis_id in release_by_id:
            raise CampaignProofError(
                "preserved #2964 release cases contain duplicate axis_id"
            )
        release_by_id[axis_id] = release_case

    if set(axis_by_id) != set(release_by_id):
        raise CampaignProofError(
            "preserved #2964 axes/release cases do not cover the same axis ids"
        )

    material_keys = {"path", "sha256", "case_fingerprint", "question_fingerprints"}
    applied: list[dict[str, object]] = []
    for axis_id, axis in axis_by_id.items():
        release_case = release_by_id[axis_id]

        if _canonical_json(axis.get("manifest")) != _canonical_json(
            release_case.get("manifest")
        ):
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} manifest differs from execution freeze"
            )

        axis_case = axis.get("case")
        frozen_case = release_case.get("case")
        if not isinstance(axis_case, Mapping) or not isinstance(frozen_case, Mapping):
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} cases must be objects"
            )
        try:
            normalized_axis = validate_case(axis_case)
            normalized_frozen = validate_case(frozen_case)
        except ExternalQualificationError as exc:
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} case is invalid: {exc}"
            ) from exc

        substantive_fields = ("case_id", "axis", "benchmark", "dataset")
        differing = [
            field
            for field in substantive_fields
            if _canonical_json(normalized_axis[field])
            != _canonical_json(normalized_frozen[field])
        ]
        if differing:
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} substantive case fields differ "
                f"from execution freeze: {', '.join(differing)}"
            )

        case_differs = _canonical_json(axis_case) != _canonical_json(frozen_case)
        if (
            case_differs
            and normalized_axis["adapter_case_ref"]
            == normalized_frozen["adapter_case_ref"]
        ):
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} case mismatch is not "
                "an adapter_case_ref-only difference"
            )

        questions = axis.get("questions")
        if not isinstance(questions, list) or not questions:
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} questions must be a non-empty list"
            )
        parsed_questions: list[CampaignQuestion] = []
        for question in questions:
            if not isinstance(question, Mapping):
                raise CampaignProofError(
                    f"preserved #2964 axis {axis_id!r} question must be an object"
                )
            parsed_questions.append(CampaignQuestion.from_mapping(question))

        axis_material = axis.get("benchmark_material")
        frozen_material = release_case.get("benchmark_material")
        if not isinstance(axis_material, dict) or not isinstance(frozen_material, dict):
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} benchmark_material must be an object"
            )
        if set(axis_material) != material_keys or set(frozen_material) != material_keys:
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} benchmark_material keys drifted"
            )

        if axis_material["path"] != frozen_material["path"]:
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} benchmark material path differs "
                "from execution freeze"
            )
        if axis_material["sha256"] != frozen_material["sha256"]:
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} benchmark material SHA256 differs "
                "from execution freeze"
            )

        material_path_value = axis_material["path"]
        if not isinstance(material_path_value, str) or not material_path_value:
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} benchmark material path is invalid"
            )
        material_path = Path(material_path_value)
        if not material_path.is_absolute() or not material_path.is_file():
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} benchmark material path is not an "
                "existing absolute file"
            )
        material_sha = axis_material["sha256"]
        if not _valid_sha256(material_sha):
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} benchmark material SHA256 is invalid"
            )
        if _sha256_file(material_path) != material_sha:
            raise CampaignProofError(
                f"preserved #2964 axis {axis_id!r} benchmark material bytes drifted"
            )

        for label, material in (
            ("source axis", axis_material),
            ("execution freeze", frozen_material),
        ):
            if not _valid_fingerprint(material["case_fingerprint"]):
                raise CampaignProofError(
                    f"preserved #2964 axis {axis_id!r} {label} material "
                    "case_fingerprint is invalid"
                )
            question_fingerprints = material["question_fingerprints"]
            if (
                not isinstance(question_fingerprints, list)
                or len(question_fingerprints) != len(parsed_questions)
                or not all(_valid_fingerprint(item) for item in question_fingerprints)
            ):
                raise CampaignProofError(
                    f"preserved #2964 axis {axis_id!r} {label} material "
                    "question_fingerprints are invalid"
                )

        canonical_material = {
            "path": material_path_value,
            "sha256": material_sha,
            "case_fingerprint": _fingerprint(normalized_frozen),
            "question_fingerprints": [
                question.content_fingerprint for question in parsed_questions
            ],
        }
        dependent_fields = ("case_fingerprint", "question_fingerprints")
        material_differences = sorted(
            field
            for field in dependent_fields
            if _canonical_json(axis_material[field])
            != _canonical_json(frozen_material[field])
            or _canonical_json(axis_material[field])
            != _canonical_json(canonical_material[field])
            or _canonical_json(frozen_material[field])
            != _canonical_json(canonical_material[field])
        )

        if case_differs:
            axis["case"] = copy.deepcopy(dict(frozen_case))
        if material_differences:
            axis["benchmark_material"] = copy.deepcopy(canonical_material)
            release_case["benchmark_material"] = copy.deepcopy(canonical_material)

        if case_differs or material_differences:
            item: dict[str, object] = {
                "axis_id": axis_id,
                "material_derived_fields": material_differences,
            }
            if case_differs:
                item["source_adapter_case_ref"] = str(
                    normalized_axis["adapter_case_ref"]
                )
                item["execution_freeze_adapter_case_ref"] = str(
                    normalized_frozen["adapter_case_ref"]
                )
            applied.append(item)

    return {
        "status": "APPLIED" if applied else "NOT_NEEDED",
        "axes": applied,
    }


def _find_comparator_identity(axis: Mapping[str, object]) -> Mapping[str, object]:
    manifest = axis.get("manifest")
    if not isinstance(manifest, Mapping):
        raise CampaignProofError("prepared axis manifest must be an object")
    participants = manifest.get("participants")
    if not isinstance(participants, Sequence) or isinstance(participants, (str, bytes)):
        raise CampaignProofError("prepared axis participants must be a list")
    matches: list[Mapping[str, object]] = []
    for participant in participants:
        if not isinstance(participant, Mapping):
            continue
        if participant.get("slot") != "serious_comparator":
            continue
        identity = participant.get("identity")
        if not isinstance(identity, Mapping):
            raise CampaignProofError("serious comparator identity must be an object")
        matches.append(identity)
    if len(matches) != 1:
        raise CampaignProofError("prepared axis must contain exactly one serious comparator")
    return matches[0]


def prepare_static_proof(
    *,
    repo_root: Path,
    source_path: Path,
    source_sha256: str,
    plan_path: Path,
    owner_root: Path,
    owner_id: str,
    repository_head: str,
    repository_tree: str,
    expected_rc_sha256: str | None = None,
    expected_core_fingerprint: str | None = None,
    memconflict_source: Path | None = None,
    longmemeval_source: Path | None = None,
    history_output_root: Path | None = None,
) -> dict[str, object]:
    """Prepare and verify one fresh-owner descriptor without semantic execution."""

    if _sha256_file(source_path) != source_sha256:
        raise CampaignProofError("preserved source descriptor SHA256 mismatch")
    raw = _read_json_object(source_path, label="preserved source descriptor")
    preserved_case_compatibility = {
        "status": "NOT_REQUIRED",
        "reason": "legacy execution-freeze release-case duplicates are derived from canonical axes",
        "axes": [],
    }

    execution_freeze = raw.get("execution_freeze")
    if not isinstance(execution_freeze, Mapping):
        raise CampaignProofError("source execution_freeze must be an object")
    comparator = execution_freeze.get("comparator")
    if not isinstance(comparator, Mapping):
        raise CampaignProofError("source execution-freeze comparator must be an object")
    source_comparator_implementation = comparator.get("implementation")
    if source_comparator_implementation not in {"Hindsight", "hindsight"}:
        raise CampaignProofError("preserved source comparator is not recognized Hindsight")

    lifecycle_raw = raw.get("hindsight_lifecycle")
    if not isinstance(lifecycle_raw, Mapping):
        raise CampaignProofError("source hindsight_lifecycle must be an object")
    lifecycle_base = copy.deepcopy(dict(lifecycle_raw))
    # Runtime bounds are current repository authority, not historical descriptor
    # authority. Older preserved descriptors predate this field; newer ones may
    # carry it only as evidence and are normalized away before fresh derivation.
    lifecycle_base.pop("retain_max_completion_tokens", None)
    lifecycle_base.pop("fail_on_extraction_errors", None)
    lifecycle_base.pop("llm_supports_string_pattern", None)
    lifecycle_base.pop("retain_llm_reasoning_effort", None)
    lifecycle_base.pop("consolidation_llm_reasoning_effort", None)
    lifecycle_base.pop("llm_max_concurrent", None)
    try:
        stale_deployment = lifecycle_base.pop("deployment_id")
        stale_profile = lifecycle_base.pop("database_profile")
    except KeyError as exc:
        raise CampaignProofError(
            "preserved source lifecycle must carry owner-local deployment/profile"
        ) from exc
    if not isinstance(stale_deployment, str) or not stale_deployment:
        raise CampaignProofError("preserved source deployment_id must be non-empty")
    if not isinstance(stale_profile, str) or not stale_profile:
        raise CampaignProofError("preserved source database_profile must be non-empty")

    axes = raw.get("axes")
    llama_cpp = raw.get("llama_cpp")
    relaylm_exact_rc = raw.get("relaylm_exact_rc")
    if not isinstance(axes, Sequence) or isinstance(axes, (str, bytes)):
        raise CampaignProofError("source axes must be a list")

    history_inputs = (memconflict_source, longmemeval_source)
    if any(value is not None for value in history_inputs):
        if any(value is None for value in history_inputs):
            raise CampaignProofError(
                "MemConflict and LongMemEval sources must be supplied together"
            )
        if history_output_root is None:
            history_output_root = plan_path.parent / f"{plan_path.stem}-history"
        materialized_axes, history_receipt = materialize_bounded_history_axes(
            axes=[
                axis
                for axis in axes
                if isinstance(axis, Mapping)
            ],
            memconflict_source=memconflict_source,
            longmemeval_source=longmemeval_source,
            output_root=history_output_root,
        )
        if len(materialized_axes) != len(axes):
            raise CampaignProofError(
                "source axes contain a non-object entry"
            )
        axes = materialized_axes
    else:
        history_receipt = {
            "status": "NOT_REQUESTED",
            "semantic_generation_count": 0,
            "benchmark_question_execution_count": 0,
            "axes": [],
        }

    if not isinstance(llama_cpp, Mapping):
        raise CampaignProofError("source llama_cpp must be an object")
    if not isinstance(relaylm_exact_rc, Mapping):
        raise CampaignProofError("source relaylm_exact_rc must be an object")

    authority = {
        "status": "CURRENT_AUTHORITY_CONFIRMED",
        "branch": "v1",
        "repository_head": repository_head,
        "repository_tree": repository_tree,
    }
    prepared = prepare_scientific_owner_descriptor(
        owner_id=owner_id,
        owner_root=owner_root,
        execution_freeze=execution_freeze,
        axes=axes,
        llama_cpp=llama_cpp,
        relaylm_exact_rc=relaylm_exact_rc,
        hindsight_lifecycle_base=lifecycle_base,
        authority=authority,
    )
    plan = prepared.to_mapping()

    prepared_freeze = plan.get("execution_freeze")
    if not isinstance(prepared_freeze, Mapping):
        raise CampaignProofError("prepared execution_freeze must be an object")
    prepared_comparator = prepared_freeze.get("comparator")
    if not isinstance(prepared_comparator, Mapping):
        raise CampaignProofError("prepared comparator must be an object")
    if prepared_comparator.get("implementation") != "hindsight":
        raise CampaignProofError("prepared comparator was not canonicalized to hindsight")

    prepared_axes = plan.get("axes")
    if not isinstance(prepared_axes, list) or not prepared_axes:
        raise CampaignProofError("prepared descriptor must contain axes")
    for axis in prepared_axes:
        if not isinstance(axis, Mapping):
            raise CampaignProofError("prepared axis must be an object")
        identity = _find_comparator_identity(axis)
        if identity.get("implementation") != "hindsight":
            raise CampaignProofError(
                "prepared serious comparator was not canonicalized to hindsight"
            )

    expected_deployment = _hindsight_owner_deployment_id(owner_id)
    lifecycle = plan.get("hindsight_lifecycle")
    if not isinstance(lifecycle, Mapping):
        raise CampaignProofError("prepared hindsight_lifecycle must be an object")
    if lifecycle.get("deployment_id") != expected_deployment:
        raise CampaignProofError("fresh owner deployment_id was not derived from owner_id")
    if lifecycle.get("database_profile") != owner_id:
        raise CampaignProofError("fresh owner database_profile was not derived from owner_id")
    if lifecycle.get("retain_max_completion_tokens") != HINDSIGHT_RETAIN_MAX_COMPLETION_TOKENS:
        raise CampaignProofError("fresh owner Hindsight retain bound was not repository-derived")
    if lifecycle.get("fail_on_extraction_errors") is not HINDSIGHT_FAIL_ON_EXTRACTION_ERRORS:
        raise CampaignProofError(
            "fresh owner Hindsight extraction-loss policy was not repository-derived"
        )
    if lifecycle.get("llm_supports_string_pattern") is not HINDSIGHT_LLM_SUPPORTS_STRING_PATTERN:
        raise CampaignProofError(
            "fresh owner Hindsight string-pattern capability was not repository-derived"
        )
    if lifecycle.get("retain_llm_reasoning_effort") != HINDSIGHT_RETAIN_LLM_REASONING_EFFORT:
        raise CampaignProofError(
            "fresh owner Hindsight retain reasoning policy was not repository-derived"
        )
    if (
        lifecycle.get("consolidation_llm_reasoning_effort")
        != HINDSIGHT_CONSOLIDATION_LLM_REASONING_EFFORT
    ):
        raise CampaignProofError(
            "fresh owner Hindsight consolidation reasoning policy was not repository-derived"
        )
    if expected_deployment == stale_deployment or owner_id == stale_profile:
        raise CampaignProofError("fresh owner retained stale owner-local identity")

    if expected_rc_sha256 is not None:
        prepared_rc = plan.get("relaylm_exact_rc")
        if not isinstance(prepared_rc, Mapping):
            raise CampaignProofError("prepared relaylm_exact_rc must be an object")
        if prepared_rc.get("wheel_sha256") != expected_rc_sha256:
            raise CampaignProofError("accepted RC wheel identity drifted")

    admitted = CampaignDescriptor.from_mapping(plan)
    if admitted.fingerprint != prepared.campaign_fingerprint:
        raise CampaignProofError("prepared campaign fingerprint did not re-admit exactly")

    stale = copy.deepcopy(plan)
    stale_lifecycle = stale["hindsight_lifecycle"]
    assert isinstance(stale_lifecycle, dict)
    stale_lifecycle["deployment_id"] = stale_deployment
    stale_lifecycle["database_profile"] = stale_profile
    try:
        CampaignDescriptor.from_mapping(stale)
    except CampaignCarriageError:
        stale_lifecycle_rejected = True
    else:
        stale_lifecycle_rejected = False
    if not stale_lifecycle_rejected:
        raise CampaignProofError("stale owner-local lifecycle substitution was admitted")

    stale_mutual = copy.deepcopy(stale)
    stale_health = stale_mutual["hindsight_health"]
    assert isinstance(stale_health, dict)
    stale_health_deployment = stale_health["deployment"]
    assert isinstance(stale_health_deployment, dict)
    stale_health_deployment["deployment_id"] = stale_deployment
    try:
        CampaignDescriptor.from_mapping(stale_mutual)
    except CampaignCarriageError:
        mutually_stale_rejected = True
    else:
        mutually_stale_rejected = False
    if not mutually_stale_rejected:
        raise CampaignProofError("mutually stale Hindsight owner identity was admitted")

    core_fingerprint: str | None = None
    if expected_core_fingerprint is not None:
        spec_path = repo_root / "evaluation/actual_model/qualifications/core-semantic-v1.json"
        spec = _read_json_object(spec_path, label="Core qualification spec")
        roots = spec.get("roots")
        if not isinstance(roots, list) or not all(isinstance(item, str) for item in roots):
            raise CampaignProofError("Core qualification roots must be string paths")
        expected_from_spec = spec.get("expected_fingerprint")
        core_fingerprint = qualification_fingerprint(
            repo_root,
            load_declarations(repo_root),
            roots=tuple(roots),
        )
        if (
            core_fingerprint != expected_core_fingerprint
            or expected_from_spec != expected_core_fingerprint
        ):
            raise CampaignProofError("Core qualification fingerprint drifted")

    _write_json(plan_path, plan)
    return {
        "status": "FRESH_OWNER_STATIC_PROOF_PASS",
        "owner_id": owner_id,
        "deployment_id": expected_deployment,
        "descriptor_sha256": _sha256_file(plan_path),
        "campaign_fingerprint": prepared.campaign_fingerprint,
        "source_descriptor_sha256": source_sha256,
        "source_comparator_implementation": source_comparator_implementation,
        "prepared_comparator_implementation": "hindsight",
        "preserved_case_compatibility": preserved_case_compatibility,
        "accepted_rc_sha256": expected_rc_sha256,
        "core_fingerprint": core_fingerprint,
        "history_materialization": history_receipt,
        "stale_lifecycle_substitution": "REJECTED",
        "mutually_stale_owner_identity": "REJECTED",
        "SCIENTIFIC_SPEND": "UNSPENT",
    }


def _read_public_result(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CampaignProofError(f"cannot read public target stdout: {exc}") from exc
    for line in reversed(lines):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(item, dict)
            and item.get("target") == CAMPAIGN_TARGET
            and "status" in item
        ):
            return item
    raise CampaignProofError("public target stdout contains no campaign result object")


def _require_clean_cleanup(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CampaignProofError(f"{label} must be an object")
    if value.get("all_owned_processes_terminated") is not True:
        raise CampaignProofError(f"{label} did not terminate all owned processes")
    if value.get("external_processes_touched") != 0:
        raise CampaignProofError(f"{label} touched an external process")
    if value.get("errors") != []:
        raise CampaignProofError(f"{label} reported cleanup errors")
    return value


def _assert_runtime_identity(
    *,
    runtime_identity: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    owner_id: str,
) -> None:
    runtime_version = lifecycle.get("runtime_version")
    expected_version = (
        runtime_version.lstrip("v") if isinstance(runtime_version, str) else None
    )
    expected_equal = {
        "deployment_id": lifecycle.get("deployment_id"),
        "database_profile": owner_id,
        "version": expected_version,
        "source_revision": lifecycle.get("source_revision"),
        "source_tree": lifecycle.get("source_tree"),
        "dependency_fingerprint": lifecycle.get("dependency_fingerprint"),
        "llm_model": lifecycle.get("llm_model"),
        "llm_base_url": lifecycle.get("llm_base_url"),
        "retain_max_completion_tokens": lifecycle.get("retain_max_completion_tokens"),
        "fail_on_extraction_errors": lifecycle.get("fail_on_extraction_errors"),
        "llm_supports_string_pattern": lifecycle.get("llm_supports_string_pattern"),
        "retain_llm_reasoning_effort": lifecycle.get("retain_llm_reasoning_effort"),
        "consolidation_llm_reasoning_effort": lifecycle.get(
            "consolidation_llm_reasoning_effort"
        ),
        "embeddings_provider": lifecycle.get("embeddings_provider"),
        "reranker_provider": lifecycle.get("reranker_provider"),
        "embeddings_onnx_model_sha256": lifecycle.get("embeddings_onnx_model_sha256"),
        "embeddings_onnx_tokenizer_tree_sha256": lifecycle.get(
            "embeddings_onnx_tokenizer_tree_sha256"
        ),
        "package_wheel_sha256": lifecycle.get("package_wheel_sha256"),
        "embeddings_onnx_model_path": lifecycle.get("embeddings_onnx_model_path"),
        "embeddings_onnx_tokenizer_path": lifecycle.get(
            "embeddings_onnx_tokenizer_path"
        ),
    }
    for key, expected in expected_equal.items():
        if runtime_identity.get(key) != expected:
            raise CampaignProofError(f"Hindsight runtime identity drifted at {key}")


def _assert_ports_free(plan: Mapping[str, Any]) -> None:
    sections = ("llama_cpp", "relaylm_exact_rc", "hindsight_lifecycle")
    for section in sections:
        raw = plan.get(section)
        if not isinstance(raw, Mapping):
            raise CampaignProofError(f"plan {section} must be an object")
        port = raw.get("port")
        if isinstance(port, bool) or not isinstance(port, int):
            raise CampaignProofError(f"plan {section}.port must be an integer")
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise CampaignProofError(f"owned port {port} is not bind-free") from exc
        finally:
            probe.close()


def verify_zero_semantic_rehearsal(
    *,
    plan_path: Path,
    queue_path: Path,
    stdout_path: Path,
    owner_id: str,
    source_path: Path | None = None,
    source_sha256: str | None = None,
    check_ports: bool = True,
) -> dict[str, object]:
    """Verify a completed public ``--rehearsal`` without performing new work."""

    plan = _read_json_object(plan_path, label="fresh campaign descriptor")
    CampaignDescriptor.from_mapping(plan)
    if plan.get("owner_id") != owner_id:
        raise CampaignProofError("plan owner_id does not match proof owner")

    queue = _read_json_object(queue_path, label="physical queue receipt")
    if queue.get("state") != "CHILD_EXITED":
        raise CampaignProofError("physical queue did not reach CHILD_EXITED")
    if queue.get("child_exit_code") != 0:
        raise CampaignProofError("physical queue child did not exit zero")
    if queue.get("lease_state") != "RELEASED":
        raise CampaignProofError("physical queue lease was not released")

    result = _read_public_result(stdout_path)
    if result.get("status") != "PRE_CALL_BARRIER_REACHED":
        raise CampaignProofError("rehearsal did not reach PRE_CALL_BARRIER_REACHED")
    if result.get("pre_call_barrier_reached") is not True:
        raise CampaignProofError("pre-call barrier flag was not true")
    if result.get("SCIENTIFIC_SPEND") != "UNSPENT":
        raise CampaignProofError("scientific spend was not preserved as UNSPENT")
    if result.get("llama_server_launch_count") != 1:
        raise CampaignProofError("owned llama-server launch count was not exactly one")
    if result.get("exact_rc_adapter_launch_count") != 0:
        raise CampaignProofError("exact RC adapter unexpectedly launched during rehearsal")
    if result.get("exact_rc_adapter_query_count") != 0:
        raise CampaignProofError("exact RC adapter unexpectedly queried during rehearsal")

    observed_execution = result.get("observed_execution")
    if not isinstance(observed_execution, Mapping):
        raise CampaignProofError("observed execution receipt is absent")
    if observed_execution.get("authority") != "OBSERVED_EXECUTION":
        raise CampaignProofError("observed execution receipt authority is invalid")
    observed_live = observed_execution.get("live_launch_attestation")
    if not isinstance(observed_live, Mapping):
        raise CampaignProofError("observed live launch attestation is absent")
    try:
        observed_attestation = LiveLaunchAdmissionAttestation.from_mapping(observed_live)
    except ExternalQualificationError as exc:
        raise CampaignProofError(f"observed live launch attestation is invalid: {exc}") from exc
    if (
        observed_execution.get("live_launch_attestation_fingerprint")
        != observed_attestation.fingerprint
    ):
        raise CampaignProofError("observed live launch attestation fingerprint drifted")

    expected_counters = {
        "semantic_generation_count": 0,
        "benchmark_question_count": 0,
        "answer_model_generation_count": 0,
        "judge_call_count": 0,
        "scientific_durable_run_completion_count": 0,
    }
    if result.get("counters") != expected_counters:
        raise CampaignProofError("rehearsal scientific counters were not all zero")

    _require_clean_cleanup(result.get("cleanup"), label="llama cleanup")

    lifecycle = plan.get("hindsight_lifecycle")
    if not isinstance(lifecycle, Mapping):
        raise CampaignProofError("plan hindsight_lifecycle must be an object")
    expected_deployment = _hindsight_owner_deployment_id(owner_id)
    if lifecycle.get("deployment_id") != expected_deployment:
        raise CampaignProofError("plan Hindsight deployment does not match proof owner")
    if lifecycle.get("database_profile") != owner_id:
        raise CampaignProofError("plan Hindsight database profile does not match proof owner")

    hindsight_cleanup = _require_clean_cleanup(
        result.get("hindsight_cleanup"),
        label="Hindsight cleanup",
    )
    for key, expected in (
        ("started", True),
        ("start_count", 1),
        ("health_count", 1),
        ("semantic_operation_count", 0),
        ("cleanup_count", 1),
        ("deployment_id", expected_deployment),
    ):
        if hindsight_cleanup.get(key) != expected:
            raise CampaignProofError(f"Hindsight cleanup {key} mismatch")

    runtime_identity_path_value = hindsight_cleanup.get("runtime_identity_path")
    if not isinstance(runtime_identity_path_value, str) or not runtime_identity_path_value:
        raise CampaignProofError("Hindsight runtime identity path is absent")
    if observed_execution.get("hindsight_runtime_identity_path") != runtime_identity_path_value:
        raise CampaignProofError("observed Hindsight runtime identity path drifted")
    runtime_identity_path = Path(runtime_identity_path_value)
    runtime_identity = _read_json_object(
        runtime_identity_path,
        label="Hindsight runtime identity",
    )
    _assert_runtime_identity(
        runtime_identity=runtime_identity,
        lifecycle=lifecycle,
        owner_id=owner_id,
    )

    exact_cleanup = result.get("exact_rc_cleanup")
    if not isinstance(exact_cleanup, Mapping):
        raise CampaignProofError("exact RC cleanup receipt is absent")
    if exact_cleanup.get("removed") is not True or exact_cleanup.get("errors") != []:
        raise CampaignProofError("exact RC installation cleanup failed")
    if exact_cleanup.get("adapter") is not None:
        raise CampaignProofError("exact RC adapter cleanup exists despite zero launch")

    if source_path is not None or source_sha256 is not None:
        if source_path is None or source_sha256 is None:
            raise CampaignProofError("source path and SHA256 must be supplied together")
        if _sha256_file(source_path) != source_sha256:
            raise CampaignProofError("preserved source descriptor changed after rehearsal")

    if check_ports:
        _assert_ports_free(plan)

    return {
        "status": "ZERO_SEMANTIC_PHYSICAL_PROOF_PASS",
        "owner_id": owner_id,
        "deployment_id": expected_deployment,
        "campaign_fingerprint": result.get("campaign_fingerprint"),
        "scientific_spend": "UNSPENT",
        "queue_state": "CHILD_EXITED",
        "lease_state": "RELEASED",
        "descriptor_sha256": _sha256_file(plan_path),
        "queue_sha256": _sha256_file(queue_path),
        "stdout_sha256": _sha256_file(stdout_path),
        "runtime_identity_path": str(runtime_identity_path),
        "runtime_identity_sha256": _sha256_file(runtime_identity_path),
        "observed_live_launch_fingerprint": observed_attestation.fingerprint,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare or verify the RelayLM v1 zero-semantic campaign proof."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--repo-root", type=Path, required=True)
    prepare.add_argument("--source", type=Path, required=True)
    prepare.add_argument("--source-sha256", required=True)
    prepare.add_argument("--plan", type=Path, required=True)
    prepare.add_argument("--owner-root", type=Path, required=True)
    prepare.add_argument("--owner-id", required=True)
    prepare.add_argument("--repository-head", required=True)
    prepare.add_argument("--repository-tree", required=True)
    prepare.add_argument("--expected-rc-sha256")
    prepare.add_argument("--expected-core-fingerprint")
    prepare.add_argument("--memconflict-source", type=Path)
    prepare.add_argument("--longmemeval-source", type=Path)
    prepare.add_argument("--history-output-root", type=Path)

    verify = sub.add_parser("verify")
    verify.add_argument("--plan", type=Path, required=True)
    verify.add_argument("--queue", type=Path, required=True)
    verify.add_argument("--stdout", type=Path, required=True)
    verify.add_argument("--owner-id", required=True)
    verify.add_argument("--source", type=Path)
    verify.add_argument("--source-sha256")
    verify.add_argument("--skip-port-check", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            receipt = prepare_static_proof(
                repo_root=args.repo_root.resolve(),
                source_path=args.source.resolve(),
                source_sha256=args.source_sha256,
                plan_path=args.plan.resolve(),
                owner_root=args.owner_root.resolve(),
                owner_id=args.owner_id,
                repository_head=args.repository_head,
                repository_tree=args.repository_tree,
                expected_rc_sha256=args.expected_rc_sha256,
                expected_core_fingerprint=args.expected_core_fingerprint,
                memconflict_source=(
                    None
                    if args.memconflict_source is None
                    else args.memconflict_source.resolve()
                ),
                longmemeval_source=(
                    None
                    if args.longmemeval_source is None
                    else args.longmemeval_source.resolve()
                ),
                history_output_root=(
                    None
                    if args.history_output_root is None
                    else args.history_output_root.resolve()
                ),
            )
        else:
            receipt = verify_zero_semantic_rehearsal(
                plan_path=args.plan.resolve(),
                queue_path=args.queue.resolve(),
                stdout_path=args.stdout.resolve(),
                owner_id=args.owner_id,
                source_path=None if args.source is None else args.source.resolve(),
                source_sha256=args.source_sha256,
                check_ports=not args.skip_port_check,
            )
    except CampaignCarriageError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
