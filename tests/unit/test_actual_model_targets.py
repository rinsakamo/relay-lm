from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from relaylm.actual_model_targets import (
    ActualModelArtifactTarget,
    ActualModelTargetError,
    load_actual_model_target,
    verify_actual_model_artifact,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PRIMARY_TARGET = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-v1.json"
)


def test_primary_gemma_target_matches_frozen_issue_authority() -> None:
    target = load_actual_model_target(PRIMARY_TARGET)

    assert target.target_id == "gemma-4-12b-it-q4-k-m-v1"
    assert target.model_family == "google/gemma-4-12B-it"
    assert target.artifact_repository == "bartowski/gemma-4-12B-it-GGUF"
    assert (
        target.artifact_repository_revision
        == "2ae7d41be21ca62de00a2d320ee9cec50daa3aa6"
    )
    assert target.artifact_filename == "gemma-4-12B-it-Q4_K_M.gguf"
    assert target.quantization == "Q4_K_M"
    assert target.artifact_size_bytes == 7_662_533_088
    assert (
        target.artifact_sha256
        == "3962624dcd25b947d889dc9ae1bf275b61db6cd4dbe694057f34fffef1671509"
    )
    assert (
        target.upstream_tokenizer_sha256
        == "cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f"
    )
    assert (
        target.revision
        == "sha256:c5a65e32e2b2478d51ba831299c454c0e2e115ccd3b602f2e57d53bd6a51131b"
    )
    assert target.model_artifact_identity.endswith(
        "gemma-4-12B-it-Q4_K_M.gguf"
        "#sha256=3962624dcd25b947d889dc9ae1bf275b61db6cd4dbe694057f34fffef1671509"
    )
    assert target.tokenizer_identity == (
        "gguf-embedded-tokenizer:sha256:"
        "3962624dcd25b947d889dc9ae1bf275b61db6cd4dbe694057f34fffef1671509"
    )


def test_target_loader_rejects_unknown_and_duplicate_fields(tmp_path: Path) -> None:
    target = load_actual_model_target(PRIMARY_TARGET)
    mapping = target.to_mapping()

    unknown_path = tmp_path / "unknown.json"
    unknown_path.write_text(
        json.dumps({**mapping, "unexpected": True}),
        encoding="utf-8",
    )
    with pytest.raises(ActualModelTargetError, match="unknown fields"):
        load_actual_model_target(unknown_path)

    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(
        '{"format_version":1,"format_version":1}',
        encoding="utf-8",
    )
    with pytest.raises(ActualModelTargetError, match="duplicate JSON key"):
        load_actual_model_target(duplicate_path)


def test_local_artifact_verification_requires_exact_size_and_sha(tmp_path: Path) -> None:
    content = b"frozen-gguf-bytes"
    artifact = tmp_path / "local-model.gguf"
    artifact.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    target = ActualModelArtifactTarget(
        target_id="fixture-target",
        model_family="example/model",
        artifact_repository="example/model-GGUF",
        artifact_repository_revision="0" * 40,
        artifact_filename="model.gguf",
        quantization="Q4_K_M",
        artifact_size_bytes=len(content),
        artifact_sha256=digest,
        upstream_tokenizer_sha256="1" * 64,
    )

    verified = verify_actual_model_artifact(target=target, artifact_path=artifact)

    assert verified.target_id == target.target_id
    assert verified.target_revision == target.revision
    assert verified.artifact_size_bytes == len(content)
    assert verified.artifact_sha256 == digest

    with pytest.raises(ActualModelTargetError, match="size"):
        verify_actual_model_artifact(
            target=replace(target, artifact_size_bytes=len(content) + 1),
            artifact_path=artifact,
        )
    with pytest.raises(ActualModelTargetError, match="SHA256"):
        verify_actual_model_artifact(
            target=replace(target, artifact_sha256="f" * 64),
            artifact_path=artifact,
        )


def test_target_revision_changes_when_artifact_identity_changes() -> None:
    target = load_actual_model_target(PRIMARY_TARGET)
    changed = replace(target, artifact_sha256="f" * 64)

    assert changed.revision != target.revision
