from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from relaylm.lab_environment import (
    LabEnvironmentError,
    LabEnvironmentManifest,
    capture_cache_reference,
    load_lab_environment,
)


def _digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _identity(name: str, *, cache_id: str | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "identity": f"{name}-identity",
        "revision": f"{name}-revision-v1",
        "digest": _digest(name),
        "attributes": {"version": f"{name}-version"},
    }
    if cache_id is not None:
        value["cache_id"] = cache_id
    return value


def _cache_file(root: Path, name: str, content: bytes) -> dict[str, object]:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "path": name,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _inputs(tmp_path: Path) -> tuple[dict[str, object], dict[str, Path]]:
    model_root = tmp_path / "model-cache"
    runtime_root = tmp_path / "runtime-cache"
    dependency_root = tmp_path / "dependency-cache"
    model = _identity("model", cache_id="model-cache")
    runtime = _identity("runtime", cache_id="runtime-cache")
    tokenizer = _identity("tokenizer")
    chat_template = _identity("chat-template")
    quantization = _identity("quantization")
    dependencies = _identity("dependencies", cache_id="dependency-cache")
    caches = [
        {
            "id": "model-cache",
            "kind": "model",
            "identity": model["identity"],
            "revision": model["revision"],
            "digest": model["digest"],
            "files": [_cache_file(model_root, "weights.safetensors", b"model-bytes")],
        },
        {
            "id": "runtime-cache",
            "kind": "runtime",
            "identity": runtime["identity"],
            "revision": runtime["revision"],
            "digest": runtime["digest"],
            "files": [_cache_file(runtime_root, "runtime.lock", b"runtime-lock")],
        },
        {
            "id": "dependency-cache",
            "kind": "dependencies",
            "identity": dependencies["identity"],
            "revision": dependencies["revision"],
            "digest": dependencies["digest"],
            "files": [_cache_file(dependency_root, "lock.txt", b"dependency-lock")],
        },
    ]
    return (
        {
            "model": model,
            "runtime": runtime,
            "tokenizer": tokenizer,
            "chat_template": chat_template,
            "quantization": quantization,
            "dependencies": dependencies,
            "cache_references": caches,
            "host_requirements": {
                "platform": "linux",
                "native_linux_ipc": True,
                "compute_capability": "8.6",
            },
            "launcher": _identity("launcher"),
        },
        {
            "model-cache": model_root,
            "runtime-cache": runtime_root,
            "dependency-cache": dependency_root,
        },
    )


def _manifest(tmp_path: Path) -> tuple[LabEnvironmentManifest, dict[str, Path]]:
    inputs, locations = _inputs(tmp_path)
    return LabEnvironmentManifest.capture(**inputs), locations


def test_same_stable_identity_has_the_same_fingerprint(tmp_path: Path) -> None:
    inputs, _ = _inputs(tmp_path)
    first = LabEnvironmentManifest.capture(**inputs)
    second = LabEnvironmentManifest.capture(
        **{
            **inputs,
            "cache_references": list(reversed(inputs["cache_references"])),
        }  # type: ignore[arg-type]
    )

    assert first.fingerprint == second.fingerprint


def test_a_stable_identity_change_changes_the_fingerprint(tmp_path: Path) -> None:
    inputs, _ = _inputs(tmp_path)
    first = LabEnvironmentManifest.capture(**inputs)
    changed_quantization = dict(inputs["quantization"])
    changed_quantization["revision"] = "quantization-revision-v2"

    second = LabEnvironmentManifest.capture(
        **{**inputs, "quantization": changed_quantization}  # type: ignore[arg-type]
    )

    assert first.fingerprint != second.fingerprint


def test_save_and_load_are_atomic_and_preserve_the_canonical_identity(tmp_path: Path) -> None:
    manifest, locations = _manifest(tmp_path)
    path = tmp_path / "lab-environment" / "manifest.json"

    manifest.save(path)
    loaded = load_lab_environment(path)

    assert loaded.fingerprint == manifest.fingerprint
    assert loaded.to_mapping() == manifest.to_mapping()
    assert not list(path.parent.glob(".*.tmp"))
    verification = loaded.restore(
        observed_identities=loaded.identity_mapping(),
        cache_locations=locations,
    )
    assert verification.reused is True
    assert verification.fingerprint == manifest.fingerprint
    assert "gpu_free_bytes" not in json.dumps(verification.to_mapping())


@pytest.mark.parametrize("section", ("model", "runtime", "tokenizer", "quantization"))
def test_missing_required_identity_fails_closed(tmp_path: Path, section: str) -> None:
    inputs, _ = _inputs(tmp_path)
    missing = dict(inputs)
    missing.pop(section)

    with pytest.raises(LabEnvironmentError, match=section):
        LabEnvironmentManifest.capture(**missing)


@pytest.mark.parametrize("section", ("model", "runtime", "tokenizer", "quantization"))
def test_wrong_current_identity_fails_closed(tmp_path: Path, section: str) -> None:
    manifest, locations = _manifest(tmp_path)
    observed = manifest.identity_mapping()
    wrong = dict(observed[section])
    wrong["revision"] = f"{wrong['revision']}-wrong"
    observed[section] = wrong

    with pytest.raises(LabEnvironmentError, match=section):
        manifest.restore(observed_identities=observed, cache_locations=locations)


def test_missing_cache_and_changed_cache_bytes_fail_closed(tmp_path: Path) -> None:
    manifest, locations = _manifest(tmp_path)
    missing = dict(locations)
    missing.pop("model-cache")
    with pytest.raises(LabEnvironmentError, match="model-cache"):
        manifest.restore(
            observed_identities=manifest.identity_mapping(),
            cache_locations=missing,
        )

    (locations["model-cache"] / "weights.safetensors").write_bytes(b"changed")
    with pytest.raises(LabEnvironmentError, match="model-cache"):
        manifest.restore(
            observed_identities=manifest.identity_mapping(),
            cache_locations=locations,
        )


@pytest.mark.parametrize(
    "field",
    (
        "gpu_free_bytes",
        "gpu_memory_utilization",
        "kv_capacity",
        "pid",
        "runtime_nonce",
        "run_id",
        "execution_frozen",
        "semantic_request_count",
        "evidence_root",
        "memory",
        "prompt",
    ),
)
def test_volatile_and_semantic_fields_cannot_be_saved(
    tmp_path: Path, field: str
) -> None:
    inputs, _ = _inputs(tmp_path)
    changed_runtime = dict(inputs["runtime"])
    attributes = dict(changed_runtime["attributes"])  # type: ignore[arg-type]
    attributes[field] = 1
    changed_runtime["attributes"] = attributes

    with pytest.raises(LabEnvironmentError, match=field):
        LabEnvironmentManifest.capture(**{**inputs, "runtime": changed_runtime})  # type: ignore[arg-type]


def test_secrets_are_rejected_and_never_serialized(tmp_path: Path) -> None:
    inputs, _ = _inputs(tmp_path)
    changed_launcher = dict(inputs["launcher"])
    changed_launcher["attributes"] = {"api_key": "not-to-be-saved"}

    with pytest.raises(LabEnvironmentError, match="api_key"):
        LabEnvironmentManifest.capture(**{**inputs, "launcher": changed_launcher})  # type: ignore[arg-type]


def test_prompt_only_changes_do_not_rebuild_the_physical_environment(tmp_path: Path) -> None:
    inputs, _ = _inputs(tmp_path)
    first = LabEnvironmentManifest.capture(**inputs)
    prompt_a = "A semantic experiment prompt"
    prompt_b = "A different semantic experiment prompt"

    assert prompt_a != prompt_b
    assert LabEnvironmentManifest.capture(**inputs).fingerprint == first.fingerprint


def test_cache_references_do_not_copy_the_large_artifact_bytes(tmp_path: Path) -> None:
    manifest, _ = _manifest(tmp_path)

    serialized = json.dumps(manifest.to_mapping(), sort_keys=True)

    assert "model-bytes" not in serialized
    assert "weights.safetensors" in serialized


def test_capture_cache_reference_records_digests_without_copying_files(
    tmp_path: Path,
) -> None:
    root = tmp_path / "prepared-cache"
    (root / "nested").mkdir(parents=True)
    (root / "nested" / "artifact.bin").write_bytes(b"large-artifact-reference")

    reference = capture_cache_reference(
        root,
        id="model-cache",
        kind="model",
        identity="model-identity",
        revision="model-revision-v1",
        digest=_digest("model"),
    )

    assert reference.to_mapping()["files"] == [
        {
            "path": "nested/artifact.bin",
            "size_bytes": len(b"large-artifact-reference"),
            "sha256": hashlib.sha256(b"large-artifact-reference").hexdigest(),
        }
    ]
    assert (root / "nested" / "artifact.bin").exists()


def test_load_rejects_a_tampered_fingerprint(tmp_path: Path) -> None:
    manifest, _ = _manifest(tmp_path)
    path = tmp_path / "manifest.json"
    manifest.save(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["fingerprint"] = _digest("tampered")
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(LabEnvironmentError, match="fingerprint"):
        load_lab_environment(path)


def test_a_handwritten_semantic_cache_path_is_rejected_on_load(tmp_path: Path) -> None:
    manifest, _ = _manifest(tmp_path)
    raw = manifest.to_mapping()
    raw["identity"]["cache_references"][0]["files"][0]["path"] = "events/answers.json"  # type: ignore[index]
    raw["fingerprint"] = manifest.fingerprint

    with pytest.raises(LabEnvironmentError, match="semantic"):
        LabEnvironmentManifest.from_mapping(raw)
