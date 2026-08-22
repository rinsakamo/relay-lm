from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import relaylm.actual_model_targets as targets


REPO_ROOT = Path(__file__).resolve().parents[2]
VLLM_TARGET = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)
GOOGLE_VLLM_TARGET = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-google-vllm-v1.json"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot_api():
    assert hasattr(targets, "ActualModelSnapshotFile")
    assert hasattr(targets, "ActualModelRepositorySnapshotTarget")
    assert hasattr(targets, "load_actual_model_repository_snapshot_target")
    assert hasattr(targets, "verify_actual_model_repository_snapshot")
    return (
        targets.ActualModelSnapshotFile,
        targets.ActualModelRepositorySnapshotTarget,
        targets.load_actual_model_repository_snapshot_target,
        targets.verify_actual_model_repository_snapshot,
    )


def _mapping(*, files: list[dict[str, object]]) -> dict[str, object]:
    return {
        "format_version": 2,
        "target_kind": "repository_snapshot",
        "target_id": "fixture-snapshot",
        "model_family": "example/model",
        "artifact_repository": "example/model-snapshot",
        "artifact_repository_revision": "0" * 40,
        "quantization": "W4A16 compressed-tensors",
        "files": files,
        "serving_tokenizer_files": ["tokenizer.json", "tokenizer_config.json"],
        "chat_template_file": "chat_template.jinja",
    }


def _file_entry(path: str, data: bytes) -> dict[str, object]:
    return {
        "path": path,
        "size_bytes": len(data),
        "sha256": _sha256(data),
    }


def _write_target(path: Path, mapping: dict[str, object]) -> None:
    path.write_text(json.dumps(mapping), encoding="utf-8")


def test_snapshot_target_loads_strictly_and_revision_is_manifest_order_independent(
    tmp_path: Path,
) -> None:
    _, _, load_snapshot, _ = _snapshot_api()
    payloads = {
        "config.json": b"config\n",
        "tokenizer.json": b"tokenizer\n",
        "tokenizer_config.json": b"tokenizer-config\n",
        "chat_template.jinja": b"template\n",
    }
    entries = [_file_entry(path, data) for path, data in payloads.items()]

    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    _write_target(first_path, _mapping(files=entries))
    _write_target(second_path, _mapping(files=list(reversed(entries))))

    first = load_snapshot(first_path)
    second = load_snapshot(second_path)

    assert first.format_version == 2
    assert first.target_kind == "repository_snapshot"
    assert [item.path for item in first.files] == sorted(payloads)
    assert first.revision == second.revision
    assert first.model_artifact_identity == second.model_artifact_identity


def test_snapshot_verification_requires_exact_required_files_and_derives_role_identities(
    tmp_path: Path,
) -> None:
    SnapshotFile, SnapshotTarget, _, verify_snapshot = _snapshot_api()
    payloads = {
        "config.json": b"config\n",
        "tokenizer.json": b"tokenizer\n",
        "tokenizer_config.json": b"tokenizer-config\n",
        "chat_template.jinja": b"template\n",
    }
    root = tmp_path / "model"
    root.mkdir()
    for relative_path, data in payloads.items():
        (root / relative_path).write_bytes(data)

    target = SnapshotTarget(
        target_id="fixture-snapshot",
        model_family="example/model",
        artifact_repository="example/model-snapshot",
        artifact_repository_revision="0" * 40,
        quantization="W4A16 compressed-tensors",
        files=tuple(
            SnapshotFile(path=path, size_bytes=len(data), sha256=_sha256(data))
            for path, data in payloads.items()
        ),
        serving_tokenizer_files=("tokenizer.json", "tokenizer_config.json"),
        chat_template_file="chat_template.jinja",
    )

    receipt = verify_snapshot(target=target, snapshot_root=root)

    assert receipt.target_id == target.target_id
    assert receipt.target_revision == target.revision
    assert receipt.verified_file_count == len(payloads)
    assert target.tokenizer_identity.startswith("hf-snapshot-tokenizer:sha256:")
    assert target.chat_template_identity == (
        "hf-snapshot-chat-template:sha256:" + _sha256(payloads["chat_template.jinja"])
    )

    changed_tokenizer = SnapshotTarget(
        target_id=target.target_id,
        model_family=target.model_family,
        artifact_repository=target.artifact_repository,
        artifact_repository_revision=target.artifact_repository_revision,
        quantization=target.quantization,
        files=tuple(
            SnapshotFile(
                path=item.path,
                size_bytes=item.size_bytes,
                sha256=("f" * 64 if item.path == "tokenizer.json" else item.sha256),
            )
            for item in target.files
        ),
        serving_tokenizer_files=target.serving_tokenizer_files,
        chat_template_file=target.chat_template_file,
    )
    assert changed_tokenizer.tokenizer_identity != target.tokenizer_identity

    changed_template = SnapshotTarget(
        target_id=target.target_id,
        model_family=target.model_family,
        artifact_repository=target.artifact_repository,
        artifact_repository_revision=target.artifact_repository_revision,
        quantization=target.quantization,
        files=tuple(
            SnapshotFile(
                path=item.path,
                size_bytes=item.size_bytes,
                sha256=("e" * 64 if item.path == "chat_template.jinja" else item.sha256),
            )
            for item in target.files
        ),
        serving_tokenizer_files=target.serving_tokenizer_files,
        chat_template_file=target.chat_template_file,
    )
    assert changed_template.chat_template_identity != target.chat_template_identity


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing", "missing"),
        ("size", "size"),
        ("sha", "SHA256"),
    ],
)
def test_snapshot_verification_fails_closed_on_required_file_mismatch(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    SnapshotFile, SnapshotTarget, _, verify_snapshot = _snapshot_api()
    original = b"tokenizer\n"
    root = tmp_path / "model"
    root.mkdir()
    file_path = root / "tokenizer.json"
    file_path.write_bytes(original)
    (root / "chat_template.jinja").write_bytes(b"template\n")

    target = SnapshotTarget(
        target_id="fixture-snapshot",
        model_family="example/model",
        artifact_repository="example/model-snapshot",
        artifact_repository_revision="0" * 40,
        quantization="W4A16 compressed-tensors",
        files=(
            SnapshotFile(
                path="tokenizer.json",
                size_bytes=len(original),
                sha256=_sha256(original),
            ),
            SnapshotFile(
                path="chat_template.jinja",
                size_bytes=len(b"template\n"),
                sha256=_sha256(b"template\n"),
            ),
        ),
        serving_tokenizer_files=("tokenizer.json",),
        chat_template_file="chat_template.jinja",
    )

    if mutation == "missing":
        file_path.unlink()
    elif mutation == "size":
        file_path.write_bytes(original + b"x")
    else:
        file_path.write_bytes(b"different\n")

    with pytest.raises(targets.ActualModelTargetError, match=message):
        verify_snapshot(target=target, snapshot_root=root)


def test_snapshot_loader_rejects_duplicate_paths_path_traversal_and_unknown_fields(
    tmp_path: Path,
) -> None:
    _, _, load_snapshot, _ = _snapshot_api()
    tokenizer = _file_entry("tokenizer.json", b"tokenizer\n")
    template = _file_entry("chat_template.jinja", b"template\n")

    duplicate_path = tmp_path / "duplicate.json"
    _write_target(duplicate_path, _mapping(files=[tokenizer, tokenizer, template]))
    with pytest.raises(targets.ActualModelTargetError, match="duplicate snapshot file path"):
        load_snapshot(duplicate_path)

    traversal_path = tmp_path / "traversal.json"
    traversal = dict(tokenizer)
    traversal["path"] = "../tokenizer.json"
    _write_target(traversal_path, _mapping(files=[traversal, template]))
    with pytest.raises(targets.ActualModelTargetError, match="relative POSIX path"):
        load_snapshot(traversal_path)

    unknown_path = tmp_path / "unknown.json"
    mapping = _mapping(files=[tokenizer, template])
    mapping["unexpected"] = True
    _write_target(unknown_path, mapping)
    with pytest.raises(targets.ActualModelTargetError, match="unknown fields"):
        load_snapshot(unknown_path)


def test_snapshot_loader_requires_declared_tokenizer_and_template_roles_to_be_frozen_files(
    tmp_path: Path,
) -> None:
    _, _, load_snapshot, _ = _snapshot_api()
    tokenizer = _file_entry("tokenizer.json", b"tokenizer\n")
    template = _file_entry("chat_template.jinja", b"template\n")

    missing_tokenizer_role = _mapping(files=[tokenizer, template])
    missing_tokenizer_role["serving_tokenizer_files"] = ["tokenizer_config.json"]
    tokenizer_path = tmp_path / "missing-tokenizer-role.json"
    _write_target(tokenizer_path, missing_tokenizer_role)
    with pytest.raises(targets.ActualModelTargetError, match="serving_tokenizer_files"):
        load_snapshot(tokenizer_path)

    missing_template_role = _mapping(files=[tokenizer, template])
    missing_template_role["serving_tokenizer_files"] = ["tokenizer.json"]
    missing_template_role["chat_template_file"] = "other-template.jinja"
    template_path = tmp_path / "missing-template-role.json"
    _write_target(template_path, missing_template_role)
    with pytest.raises(targets.ActualModelTargetError, match="chat_template_file"):
        load_snapshot(template_path)


def test_vllm_gemma_snapshot_target_freezes_exact_execution_manifest() -> None:
    target = targets.load_actual_model_repository_snapshot_target(VLLM_TARGET)

    assert target.format_version == 2
    assert target.target_kind == "repository_snapshot"
    assert target.target_id == "gemma-4-12b-it-qat-w4a16-vllm-v1"
    assert target.model_family == "google/gemma-4-12B-it"
    assert target.artifact_repository == "unsloth/gemma-4-12B-it-qat-w4a16"
    assert (
        target.artifact_repository_revision
        == "626f3b2f8a3799cb2b64ca5fc09443c90fe2cbb2"
    )
    assert target.quantization == "W4A16 compressed-tensors"
    assert target.serving_tokenizer_files == (
        "tokenizer.json",
        "tokenizer_config.json",
    )
    assert target.chat_template_file == "chat_template.jinja"

    expected_files = {
        "model.safetensors": (
            10_264_229_896,
            "60b6e3989502969d8ae04185d72ecbbc7db63978d5af747a493d53895aa6bfa3",
        ),
        "config.json": (
            6_126,
            "ba14713d084391532b285f7c252b954b7c6c0db97f427a9d8fb788edc2949168",
        ),
        "tokenizer.json": (
            32_169_626,
            "cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f",
        ),
        "tokenizer_config.json": (
            2_774,
            "ee66825f1a587ca13bcb90d7e60f59bc99e84f3b8bc0cefdc3ea595cd5abf773",
        ),
        "chat_template.jinja": (
            18_924,
            "845f1ee48e39fc942fe190da9df6a1c5db229e17a96ea08966ad1c9274e73d1b",
        ),
        "processor_config.json": (
            1_382,
            "6b938e76555b3e9946890770e1abcd442a4718f34041a58e8139dc8ad34545c9",
        ),
        "generation_config.json": (
            255,
            "c70f87dc2995fc43406c0bcfb41b69c6d31c2d0c033fa09e536ffabc091ae24c",
        ),
    }
    assert {
        item.path: (item.size_bytes, item.sha256) for item in target.files
    } == expected_files


def test_google_official_gemma_snapshot_target_freezes_exact_execution_manifest() -> None:
    target = targets.load_actual_model_repository_snapshot_target(GOOGLE_VLLM_TARGET)

    assert target.format_version == 2
    assert target.target_kind == "repository_snapshot"
    assert target.target_id == "gemma-4-12b-it-qat-w4a16-google-vllm-v1"
    assert target.model_family == "google/gemma-4-12B-it"
    assert target.artifact_repository == "google/gemma-4-12b-it-qat-w4a16-ct"
    assert (
        target.artifact_repository_revision
        == "9c79b5e652ae36f02bb07d3ca29124a9d1b009bd"
    )
    assert target.quantization == "W4A16 compressed-tensors"
    assert target.serving_tokenizer_files == (
        "tokenizer.json",
        "tokenizer_config.json",
    )
    assert target.chat_template_file == "chat_template.jinja"

    expected_files = {
        "model.safetensors": (
            10_264_229_896,
            "60b6e3989502969d8ae04185d72ecbbc7db63978d5af747a493d53895aa6bfa3",
        ),
        "config.json": (
            6_183,
            "aa3ba82096a857e8b9a157df21a50df15a67e889a84b7580a4eb4f2b86c28d78",
        ),
        "tokenizer.json": (
            32_169_626,
            "cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f",
        ),
        "tokenizer_config.json": (
            2_774,
            "ee66825f1a587ca13bcb90d7e60f59bc99e84f3b8bc0cefdc3ea595cd5abf773",
        ),
        "chat_template.jinja": (
            17_466,
            "36e3a42e5cf14cd0020e72d92e1fdd9970f59b82170e421f0cbe1bb42bead3f0",
        ),
        "processor_config.json": (
            1_382,
            "6b938e76555b3e9946890770e1abcd442a4718f34041a58e8139dc8ad34545c9",
        ),
        "generation_config.json": (
            255,
            "c70f87dc2995fc43406c0bcfb41b69c6d31c2d0c033fa09e536ffabc091ae24c",
        ),
    }
    assert {
        item.path: (item.size_bytes, item.sha256) for item in target.files
    } == expected_files
    assert target.revision == (
        "sha256:19a47b8e917bf6d0b0c6b39e2f91161805c8f0855e9ced4233a65a6f92aa4c62"
    )

    unsloth = targets.load_actual_model_repository_snapshot_target(VLLM_TARGET)
    unsloth_files = {item.path: item for item in unsloth.files}
    google_files = {item.path: item for item in target.files}
    assert google_files["model.safetensors"].sha256 == unsloth_files[
        "model.safetensors"
    ].sha256
    assert target.target_id != unsloth.target_id
    assert target.artifact_repository != unsloth.artifact_repository
    assert target.model_artifact_identity != unsloth.model_artifact_identity
    assert target.revision != unsloth.revision
