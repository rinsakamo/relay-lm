from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ACTUAL_MODEL_TARGET_FORMAT_VERSION = 1


class ActualModelTargetError(ValueError):
    """Actual-model target metadata or local artifact does not match frozen authority."""


@dataclass(frozen=True, slots=True)
class ActualModelArtifactTarget:
    """Immutable model-artifact identity selected for citable actual-model evidence."""

    target_id: str
    model_family: str
    artifact_repository: str
    artifact_repository_revision: str
    artifact_filename: str
    quantization: str
    artifact_size_bytes: int
    artifact_sha256: str
    upstream_tokenizer_sha256: str
    format_version: int = ACTUAL_MODEL_TARGET_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_TARGET_FORMAT_VERSION:
            raise ActualModelTargetError(
                f"unsupported actual-model target format_version: {self.format_version}"
            )
        for name in (
            "target_id",
            "model_family",
            "artifact_repository",
            "artifact_repository_revision",
            "artifact_filename",
            "quantization",
            "artifact_sha256",
            "upstream_tokenizer_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ActualModelTargetError(f"{name} must be a non-empty string")
        if self.artifact_filename != Path(self.artifact_filename).name or "\\" in self.artifact_filename:
            raise ActualModelTargetError("artifact_filename must be a basename")
        _require_hex_digest(
            self.artifact_repository_revision,
            length=40,
            name="artifact_repository_revision",
        )
        _require_hex_digest(self.artifact_sha256, length=64, name="artifact_sha256")
        _require_hex_digest(
            self.upstream_tokenizer_sha256,
            length=64,
            name="upstream_tokenizer_sha256",
        )
        if isinstance(self.artifact_size_bytes, bool) or not isinstance(
            self.artifact_size_bytes, int
        ):
            raise ActualModelTargetError("artifact_size_bytes must be an integer")
        if self.artifact_size_bytes <= 0:
            raise ActualModelTargetError("artifact_size_bytes must be positive")

    @property
    def revision(self) -> str:
        encoded = json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    @property
    def model_artifact_identity(self) -> str:
        return (
            f"hf://{self.artifact_repository}@{self.artifact_repository_revision}/"
            f"{self.artifact_filename}#sha256={self.artifact_sha256}"
        )

    @property
    def tokenizer_identity(self) -> str:
        """Serving tokenizer identity: tokenizer embedded in the exact frozen GGUF bytes."""

        return f"gguf-embedded-tokenizer:sha256:{self.artifact_sha256}"

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "target_id": self.target_id,
            "model_family": self.model_family,
            "artifact_repository": self.artifact_repository,
            "artifact_repository_revision": self.artifact_repository_revision,
            "artifact_filename": self.artifact_filename,
            "quantization": self.quantization,
            "artifact_size_bytes": self.artifact_size_bytes,
            "artifact_sha256": self.artifact_sha256,
            "upstream_tokenizer_sha256": self.upstream_tokenizer_sha256,
        }


@dataclass(frozen=True, slots=True)
class ActualModelArtifactVerification:
    """Content-free proof that one local file is the exact frozen target artifact."""

    target_id: str
    target_revision: str
    artifact_size_bytes: int
    artifact_sha256: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "target_revision": self.target_revision,
            "artifact_size_bytes": self.artifact_size_bytes,
            "artifact_sha256": self.artifact_sha256,
        }


def load_actual_model_target(path: str | Path) -> ActualModelArtifactTarget:
    """Load one strict machine-readable target freeze."""

    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_object_no_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActualModelTargetError(f"cannot load actual-model target: {exc}") from exc
    if not isinstance(raw, dict):
        raise ActualModelTargetError("actual-model target must be a JSON object")

    expected = {
        "format_version",
        "target_id",
        "model_family",
        "artifact_repository",
        "artifact_repository_revision",
        "artifact_filename",
        "quantization",
        "artifact_size_bytes",
        "artifact_sha256",
        "upstream_tokenizer_sha256",
    }
    observed = set(raw)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise ActualModelTargetError(
            "actual-model target is missing fields: " + ", ".join(missing)
        )
    if unknown:
        raise ActualModelTargetError(
            "actual-model target has unknown fields: " + ", ".join(unknown)
        )

    try:
        return ActualModelArtifactTarget(**raw)
    except TypeError as exc:
        raise ActualModelTargetError(f"invalid actual-model target fields: {exc}") from exc


def verify_actual_model_artifact(
    *,
    target: ActualModelArtifactTarget,
    artifact_path: str | Path,
) -> ActualModelArtifactVerification:
    """Verify size + SHA256 before a local file may be cited under the frozen target."""

    if not isinstance(target, ActualModelArtifactTarget):
        raise TypeError("target must be ActualModelArtifactTarget")
    path = Path(artifact_path)
    if not path.is_file():
        raise ActualModelTargetError("actual-model artifact path must be a readable file")
    size = path.stat().st_size
    if size != target.artifact_size_bytes:
        raise ActualModelTargetError(
            "actual-model artifact size does not match the frozen target"
        )

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise ActualModelTargetError(f"cannot read actual-model artifact: {exc}") from exc
    observed_sha256 = digest.hexdigest()
    if observed_sha256 != target.artifact_sha256:
        raise ActualModelTargetError(
            "actual-model artifact SHA256 does not match the frozen target"
        )

    return ActualModelArtifactVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_size_bytes=size,
        artifact_sha256=observed_sha256,
    )


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ActualModelTargetError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_hex_digest(value: str, *, length: int, name: str) -> None:
    if len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise ActualModelTargetError(
            f"{name} must be an exact lowercase {length}-character hexadecimal digest"
        )
