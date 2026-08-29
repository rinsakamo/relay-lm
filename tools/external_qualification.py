from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path

from tools.release_identity import ReleaseIdentityError, expected_release_tag, parse_release_version

FORMAT_VERSION = 1
SLOTS = (
    "same_model_direct",
    "simple_baseline",
    "serious_comparator",
    "relaylm_exact_rc",
)
PURPOSES = {"dry_run", "prequalification_smoke", "release_qualification"}
CLASSIFICATIONS = {
    "reproducible_competitive_result",
    "specialist_deferred_capability_loss",
    "generalizable_core_defect_candidate",
    "benchmark_adapter_mismatch",
    "non_reproducible_workload",
    "resource_impracticality",
    "comparison_condition_mismatch",
}


class ExternalQualificationError(ValueError):
    """External qualification input or evidence violates the frozen contract."""


def validate_release_identity(raw: Mapping[str, object]) -> dict[str, object]:
    _keys(raw, {"schema_version", "package", "version", "release_kind", "tag", "commit", "artifacts"}, "release identity")
    if raw["schema_version"] != 1 or raw["package"] != "relaylm":
        raise ExternalQualificationError("release identity must be RelayLM schema v1")
    version = _text(raw["version"], "release version")
    try:
        parsed = parse_release_version(version)
    except ReleaseIdentityError as exc:
        raise ExternalQualificationError(str(exc)) from exc
    if parsed.kind not in {"rc", "final"}:
        raise ExternalQualificationError("citable qualification requires an rc or final identity")
    if raw["release_kind"] != parsed.kind or raw["tag"] != expected_release_tag(parsed):
        raise ExternalQualificationError("release kind/tag does not match release version")
    commit = _commit(raw["commit"], "release commit")
    artifacts = raw["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise ExternalQualificationError("release identity must contain exactly wheel and sdist")
    normalized_artifacts = []
    for item in artifacts:
        item = _mapping(item, "release artifact")
        _keys(item, {"filename", "sha256"}, "release artifact")
        normalized_artifacts.append(
            {"filename": _text(item["filename"], "artifact filename"), "sha256": _sha256(item["sha256"], "artifact sha256")}
        )
    names = {item["filename"] for item in normalized_artifacts}
    wheels = [name for name in names if name.startswith(f"relaylm-{version}-") and name.endswith(".whl")]
    if f"relaylm-{version}.tar.gz" not in names or len(wheels) != 1:
        raise ExternalQualificationError("release artifacts must be version-matching wheel and sdist")
    return {
        "package": "relaylm",
        "version": version,
        "release_kind": parsed.kind,
        "tag": raw["tag"],
        "commit": commit,
        "artifacts": sorted(normalized_artifacts, key=lambda item: item["filename"]),
    }


def validate_case(raw: Mapping[str, object]) -> dict[str, object]:
    _keys(raw, {"case_id", "axis", "benchmark", "dataset", "adapter_case_ref"}, "benchmark case")
    benchmark = _mapping(raw["benchmark"], "benchmark")
    dataset = _mapping(raw["dataset"], "dataset")
    _keys(benchmark, {"id", "repository", "revision", "license"}, "benchmark")
    _keys(dataset, {"revision", "license"}, "dataset")
    return {
        "case_id": _text(raw["case_id"], "case_id"),
        "axis": _text(raw["axis"], "axis"),
        "benchmark": {key: _text(benchmark[key], f"benchmark {key}") for key in ("id", "repository", "revision", "license")},
        "dataset": {key: _text(dataset[key], f"dataset {key}") for key in ("revision", "license")},
        "adapter_case_ref": _text(raw["adapter_case_ref"], "adapter_case_ref"),
    }


def validate_manifest(raw: Mapping[str, object]) -> dict[str, object]:
    _keys(raw, {"format_version", "purpose", "harness", "adapter", "participants", "relaylm_release", "judge", "replicate_id"}, "manifest")
    if raw["format_version"] != FORMAT_VERSION:
        raise ExternalQualificationError(f"unsupported format_version: {raw['format_version']}")
    purpose = _text(raw["purpose"], "purpose")
    if purpose not in PURPOSES:
        raise ExternalQualificationError(f"unsupported purpose: {purpose}")
    harness = _revision_identity(raw["harness"], "harness")
    adapter = _revision_identity(raw["adapter"], "adapter")
    replicate_id = _text(raw["replicate_id"], "replicate_id")
    judge = _optional_judge(raw["judge"])

    participants = raw["participants"]
    if not isinstance(participants, list) or len(participants) != len(SLOTS):
        raise ExternalQualificationError("participants must be canonical A/B/C/D slots")
    normalized_participants = [_participant(item) for item in participants]
    if tuple(item["slot"] for item in normalized_participants) != SLOTS:
        raise ExternalQualificationError("participants must be canonical A/B/C/D slots")
    plans = {item["slot"]: item for item in normalized_participants}

    release = None if raw["relaylm_release"] is None else validate_release_identity(_mapping(raw["relaylm_release"], "relaylm_release"))
    if purpose != "release_qualification":
        if release is not None:
            raise ExternalQualificationError("pre-RC dry/smoke evidence must not carry a citable #1447 release identity")
    else:
        if release is None:
            raise ExternalQualificationError("release_qualification is blocked until exact #1447 release identity is supplied")
        for slot in ("same_model_direct", "serious_comparator", "relaylm_exact_rc"):
            if plans[slot]["identity"] is None:
                raise ExternalQualificationError(f"release_qualification requires enabled {slot}")
        direct = plans["same_model_direct"]["identity"]
        relay = plans["relaylm_exact_rc"]["identity"]
        assert isinstance(direct, dict) and isinstance(relay, dict)
        if relay["version"] != release["version"] or relay["source_revision"] != release["commit"]:
            raise ExternalQualificationError("RelayLM slot must match exact release version and commit")
        if direct["physical_model"] != relay["physical_model"]:
            raise ExternalQualificationError("same_model_direct must match RelayLM physical model/tokenizer/quantization")

    return {
        "format_version": FORMAT_VERSION,
        "purpose": purpose,
        "citable": purpose == "release_qualification",
        "harness": harness,
        "adapter": adapter,
        "participants": normalized_participants,
        "relaylm_release": release,
        "judge": judge,
        "replicate_id": replicate_id,
    }


def validate_observation(raw: Mapping[str, object]) -> dict[str, object]:
    _keys(raw, {"quality", "tokens", "latency", "resources", "known_limitations", "failure"}, "observation")
    quality = _mapping(raw["quality"], "quality")
    normalized_quality: dict[str, int | float] = {}
    for key, value in quality.items():
        key = _text(key, "benchmark metric name")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not _finite(value):
            raise ExternalQualificationError("benchmark-native metric values must be finite numbers")
        normalized_quality[key] = value

    tokens = _mapping(raw["tokens"], "tokens")
    latency = _mapping(raw["latency"], "latency")
    resources = _mapping(raw["resources"], "resources")
    _keys(tokens, {"model_input_tokens", "model_output_tokens", "model_call_count"}, "tokens")
    _keys(latency, {"ttft_ms", "query_latency_ms", "end_to_end_ms"}, "latency")
    _keys(resources, {"peak_gpu_memory_bytes", "peak_cpu_memory_bytes", "persistent_storage_bytes", "notes"}, "resources")
    for name, value in tokens.items():
        _non_negative(value, f"tokens {name}")
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ExternalQualificationError(f"tokens {name} must be an integer or null")
    if tokens["model_call_count"] is None:
        raise ExternalQualificationError("model_call_count must not be null")
    for name, value in latency.items():
        _non_negative(value, f"latency {name}")
    for name in ("peak_gpu_memory_bytes", "peak_cpu_memory_bytes", "persistent_storage_bytes"):
        value = resources[name]
        _non_negative(value, f"resources {name}")
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ExternalQualificationError(f"resources {name} must be an integer or null")
    notes = _text_list(resources["notes"], "resource notes")
    limitations = _text_list(raw["known_limitations"], "known_limitations")
    failure = None if raw["failure"] is None else _text(raw["failure"], "failure")
    return {
        "quality": normalized_quality,
        "tokens": dict(tokens),
        "latency": dict(latency),
        "resources": {**{name: resources[name] for name in ("peak_gpu_memory_bytes", "peak_cpu_memory_bytes", "persistent_storage_bytes")}, "notes": notes},
        "known_limitations": limitations,
        "failure": failure,
    }


Executor = Callable[[Mapping[str, object], Mapping[str, object]], Mapping[str, object]]


def run_case(
    *,
    manifest: Mapping[str, object],
    case: Mapping[str, object],
    classification: str,
    executors: Mapping[str, Executor],
) -> dict[str, object]:
    manifest = validate_manifest(manifest)
    case = validate_case(case)
    if classification not in CLASSIFICATIONS:
        raise ExternalQualificationError(f"unsupported result classification: {classification}")
    results = []
    for plan in manifest["participants"]:
        assert isinstance(plan, dict)
        slot = plan["slot"]
        identity = plan["identity"]
        if identity is None:
            results.append({"slot": slot, "observation": None, "omission_reason": plan["omission_reason"]})
            continue
        executor = executors.get(slot)
        if executor is None:
            raise ExternalQualificationError(f"missing executor for enabled {slot}")
        observation = validate_observation(_mapping(executor(case, identity), f"{slot} observation"))
        results.append({"slot": slot, "observation": observation, "omission_reason": None})
    run_id = stable_run_id(manifest=manifest, case=case)
    return {
        "format_version": FORMAT_VERSION,
        "run_id": run_id,
        "manifest": manifest,
        "case": case,
        "classification": classification,
        "results": results,
    }


def stable_run_id(*, manifest: Mapping[str, object], case: Mapping[str, object]) -> str:
    manifest = _validated_manifest(manifest)
    case = validate_case(case)
    encoded = json.dumps({"manifest": manifest, "case": case}, sort_keys=True, separators=(",", ":")).encode()
    return f"external-qualification-{hashlib.sha256(encoded).hexdigest()}"


def write_evidence(*, evidence: Mapping[str, object], artifact_root: str | Path) -> Path:
    evidence = dict(evidence)
    _keys(evidence, {"format_version", "run_id", "manifest", "case", "classification", "results"}, "evidence")
    if evidence["format_version"] != FORMAT_VERSION:
        raise ExternalQualificationError("unsupported evidence format_version")
    manifest = _validated_manifest(_mapping(evidence["manifest"], "evidence manifest"))
    case = validate_case(_mapping(evidence["case"], "evidence case"))
    expected = stable_run_id(manifest=manifest, case=case)
    if evidence["run_id"] != expected:
        raise ExternalQualificationError("run_id does not match manifest and case")
    classification = evidence["classification"]
    if classification not in CLASSIFICATIONS:
        raise ExternalQualificationError("unsupported result classification")
    results = _evidence_results(evidence["results"])
    evidence = {
        "format_version": FORMAT_VERSION,
        "run_id": expected,
        "manifest": manifest,
        "case": case,
        "classification": classification,
        "results": results,
    }
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{expected}.json"
    payload = json.dumps(evidence, sort_keys=True, indent=2) + "\n"
    if path.exists():
        return _existing(path, payload)
    temporary = root / f".{expected}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _existing(path, payload)
    except OSError as exc:
        raise ExternalQualificationError(f"cannot persist external qualification evidence: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def _evidence_results(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list) or len(raw) != len(SLOTS):
        raise ExternalQualificationError("evidence results must contain canonical A/B/C/D slots")
    normalized = []
    for expected_slot, item in zip(SLOTS, raw, strict=True):
        item = _mapping(item, "evidence result")
        _keys(item, {"slot", "observation", "omission_reason"}, "evidence result")
        if item["slot"] != expected_slot:
            raise ExternalQualificationError("evidence results must contain canonical A/B/C/D slots")
        observation = item["observation"]
        omission = item["omission_reason"]
        if observation is None:
            omission = _text(omission, "omission_reason")
        else:
            observation = validate_observation(_mapping(observation, "evidence observation"))
            if omission is not None:
                raise ExternalQualificationError("executed evidence result must not have omission_reason")
        normalized.append({"slot": expected_slot, "observation": observation, "omission_reason": omission})
    return normalized


def _validated_manifest(raw: Mapping[str, object]) -> dict[str, object]:
    if "citable" not in raw:
        return validate_manifest(raw)
    raw = dict(raw)
    raw.pop("citable")
    return validate_manifest(raw)


def _participant(raw: object) -> dict[str, object]:
    raw = _mapping(raw, "participant")
    _keys(raw, {"slot", "identity", "omission_reason"}, "participant")
    slot = _text(raw["slot"], "participant slot")
    if slot not in SLOTS:
        raise ExternalQualificationError(f"unsupported architecture slot: {slot}")
    identity = None if raw["identity"] is None else _participant_identity(raw["identity"])
    omission = raw["omission_reason"]
    if identity is None:
        omission = _text(omission, "omission_reason")
    elif omission is not None:
        raise ExternalQualificationError("enabled participant must not have omission_reason")
    return {"slot": slot, "identity": identity, "omission_reason": omission}


def _participant_identity(raw: object) -> dict[str, object]:
    raw = _mapping(raw, "participant identity")
    keys = {
        "implementation", "source_revision", "version", "deployment", "license", "physical_model",
        "provider", "backend", "runtime", "context_capacity", "decoding", "reasoning", "hardware",
        "retry_policy", "matched_condition_differences",
    }
    _keys(raw, keys, "participant identity")
    physical = _mapping(raw["physical_model"], "physical_model")
    hardware = _mapping(raw["hardware"], "hardware")
    _keys(physical, {"artifact", "tokenizer", "quantization"}, "physical_model")
    _keys(hardware, {"gpu", "cpu", "offload"}, "hardware")
    capacity = raw["context_capacity"]
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
        raise ExternalQualificationError("context_capacity must be a positive integer")
    decoding = _string_mapping(raw["decoding"], "decoding")
    reasoning = _string_mapping(raw["reasoning"], "reasoning")
    return {
        **{name: _text(raw[name], name) for name in ("implementation", "source_revision", "version", "deployment", "license")},
        "physical_model": {name: _text(physical[name], f"physical_model {name}") for name in ("artifact", "tokenizer", "quantization")},
        **{name: _text(raw[name], name) for name in ("provider", "backend", "runtime")},
        "context_capacity": capacity,
        "decoding": decoding,
        "reasoning": reasoning,
        "hardware": {name: _text(hardware[name], f"hardware {name}") for name in ("gpu", "cpu", "offload")},
        "retry_policy": _text(raw["retry_policy"], "retry_policy"),
        "matched_condition_differences": _text_list(raw["matched_condition_differences"], "matched_condition_differences"),
    }


def _revision_identity(raw: object, name: str) -> dict[str, str]:
    raw = _mapping(raw, name)
    _keys(raw, {"identity", "revision"}, name)
    return {"identity": _text(raw["identity"], f"{name} identity"), "revision": _commit(raw["revision"], f"{name} revision")}


def _optional_judge(raw: object) -> dict[str, str] | None:
    if raw is None:
        return None
    raw = _mapping(raw, "judge")
    _keys(raw, {"identity", "policy"}, "judge")
    return {"identity": _text(raw["identity"], "judge identity"), "policy": _text(raw["policy"], "judge policy")}


def _existing(path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExternalQualificationError(f"cannot read existing evidence: {exc}") from exc
    if existing == payload:
        return path
    raise ExternalQualificationError("run ID already exists with different evidence; use a distinct replicate_id")


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ExternalQualificationError(f"{name} must be an object")
    return value


def _keys(raw: Mapping[str, object], expected: set[str], name: str) -> None:
    if set(raw) != expected:
        raise ExternalQualificationError(f"{name} fields must be exactly: {', '.join(sorted(expected))}")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExternalQualificationError(f"{name} must be a non-empty string")
    return value


def _commit(value: object, name: str) -> str:
    value = _text(value, name)
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise ExternalQualificationError(f"{name} must be a lowercase 40-hex commit SHA")
    return value


def _sha256(value: object, name: str) -> str:
    value = _text(value, name)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ExternalQualificationError(f"{name} must be a lowercase 64-hex sha256")
    return value


def _string_mapping(value: object, name: str) -> dict[str, str]:
    value = _mapping(value, name)
    return {_text(key, f"{name} key"): _text(item, f"{name} value") for key, item in value.items()}


def _text_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ExternalQualificationError(f"{name} must be a list")
    return [_text(item, name) for item in value]


def _finite(value: int | float) -> bool:
    return not isinstance(value, float) or float("-inf") < value < float("inf")


def _non_negative(value: object, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or not _finite(value):
        raise ExternalQualificationError(f"{name} must be a finite non-negative number or null")
