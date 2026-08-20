from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import relaylm.actual_model_targets as targets


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
    missing_template_role["chat_template_file"] = "other-template.jinja"
    template_path = tmp_path / "missing-template-role.json"
    _write_target(template_path, missing_template_role)
    with pytest.raises(targets.ActualModelTargetError, match="chat_template_file"):
        load_snapshot(template_path)
