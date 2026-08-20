from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

ACTUAL_MODEL_TARGET_FORMAT_VERSION = 1
ACTUAL_MODEL_REPOSITORY_SNAPSHOT_FORMAT_VERSION = 2
ACTUAL_MODEL_REPOSITORY_SNAPSHOT_KIND = "repository_snapshot"


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


@dataclass(frozen=True, slots=True)
class ActualModelSnapshotFile:
    """One exact execution-relevant file in a repository-snapshot target."""

    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _require_snapshot_relative_path(self.path, name="snapshot file path")
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
            raise ActualModelTargetError("snapshot file size_bytes must be an integer")
        if self.size_bytes <= 0:
            raise ActualModelTargetError("snapshot file size_bytes must be positive")
        _require_hex_digest(self.sha256, length=64, name="snapshot file sha256")

    def to_mapping(self) -> dict[str, object]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class ActualModelRepositorySnapshotTarget:
    """Immutable multi-file repository snapshot selected for actual-model evidence."""

    target_id: str
    model_family: str
    artifact_repository: str
    artifact_repository_revision: str
    quantization: str
    files: tuple[ActualModelSnapshotFile, ...]
    serving_tokenizer_files: tuple[str, ...]
    chat_template_file: str
    format_version: int = ACTUAL_MODEL_REPOSITORY_SNAPSHOT_FORMAT_VERSION
    target_kind: str = ACTUAL_MODEL_REPOSITORY_SNAPSHOT_KIND

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_REPOSITORY_SNAPSHOT_FORMAT_VERSION:
            raise ActualModelTargetError(
                "unsupported repository-snapshot target format_version: "
                f"{self.format_version}"
            )
        if self.target_kind != ACTUAL_MODEL_REPOSITORY_SNAPSHOT_KIND:
            raise ActualModelTargetError(
                "repository-snapshot target_kind must be "
                f"{ACTUAL_MODEL_REPOSITORY_SNAPSHOT_KIND!r}"
            )
        for name in (
            "target_id",
            "model_family",
            "artifact_repository",
            "artifact_repository_revision",
            "quantization",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ActualModelTargetError(f"{name} must be a non-empty string")
        _require_hex_digest(
            self.artifact_repository_revision,
            length=40,
            name="artifact_repository_revision",
        )

        if not isinstance(self.files, tuple) or not self.files:
            raise ActualModelTargetError("repository snapshot files must be a non-empty tuple")
        if any(not isinstance(item, ActualModelSnapshotFile) for item in self.files):
            raise ActualModelTargetError(
                "repository snapshot files must contain ActualModelSnapshotFile values"
            )
        normalized_files = tuple(sorted(self.files, key=lambda item: item.path))
        paths = tuple(item.path for item in normalized_files)
        if len(set(paths)) != len(paths):
            raise ActualModelTargetError("duplicate snapshot file path")
        object.__setattr__(self, "files", normalized_files)

        if not isinstance(self.serving_tokenizer_files, tuple) or not self.serving_tokenizer_files:
            raise ActualModelTargetError(
                "serving_tokenizer_files must be a non-empty tuple"
            )
        for path in self.serving_tokenizer_files:
            _require_snapshot_relative_path(path, name="serving_tokenizer_files entry")
        normalized_tokenizer_files = tuple(sorted(self.serving_tokenizer_files))
        if len(set(normalized_tokenizer_files)) != len(normalized_tokenizer_files):
            raise ActualModelTargetError("serving_tokenizer_files contains duplicates")
        missing_tokenizer_files = sorted(set(normalized_tokenizer_files) - set(paths))
        if missing_tokenizer_files:
            raise ActualModelTargetError(
                "serving_tokenizer_files must refer to frozen snapshot files: "
                + ", ".join(missing_tokenizer_files)
            )
        object.__setattr__(self, "serving_tokenizer_files", normalized_tokenizer_files)

        _require_snapshot_relative_path(
            self.chat_template_file,
            name="chat_template_file",
        )
        if self.chat_template_file not in set(paths):
            raise ActualModelTargetError(
                "chat_template_file must refer to a frozen snapshot file"
            )

    @property
    def revision(self) -> str:
        encoded = _canonical_json_bytes(self.to_mapping())
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    @property
    def model_artifact_identity(self) -> str:
        return (
            f"hf://{self.artifact_repository}@{self.artifact_repository_revision}"
            f"#snapshot={self.revision}"
        )

    @property
    def tokenizer_identity(self) -> str:
        files_by_path = {item.path: item for item in self.files}
        role_manifest = [
            files_by_path[path].to_mapping() for path in self.serving_tokenizer_files
        ]
        digest = hashlib.sha256(_canonical_json_bytes(role_manifest)).hexdigest()
        return f"hf-snapshot-tokenizer:sha256:{digest}"

    @property
    def chat_template_identity(self) -> str:
        files_by_path = {item.path: item for item in self.files}
        digest = files_by_path[self.chat_template_file].sha256
        return f"hf-snapshot-chat-template:sha256:{digest}"

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "model_family": self.model_family,
            "artifact_repository": self.artifact_repository,
            "artifact_repository_revision": self.artifact_repository_revision,
            "quantization": self.quantization,
            "files": [item.to_mapping() for item in self.files],
            "serving_tokenizer_files": list(self.serving_tokenizer_files),
            "chat_template_file": self.chat_template_file,
        }


@dataclass(frozen=True, slots=True)
class ActualModelRepositorySnapshotVerification:
    """Content-free proof that required local snapshot files match frozen identity."""

    target_id: str
    target_revision: str
    verified_file_count: int

    def to_mapping(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "target_revision": self.target_revision,
            "verified_file_count": self.verified_file_count,
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


def load_actual_model_repository_snapshot_target(
    path: str | Path,
) -> ActualModelRepositorySnapshotTarget:
    """Load one strict machine-readable multi-file repository-snapshot target."""

    source = Path(path)
    try:
        raw = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_object_no_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActualModelTargetError(
            f"cannot load repository-snapshot target: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ActualModelTargetError("repository-snapshot target must be a JSON object")

    expected = {
        "format_version",
        "target_kind",
        "target_id",
        "model_family",
        "artifact_repository",
        "artifact_repository_revision",
        "quantization",
        "files",
        "serving_tokenizer_files",
        "chat_template_file",
    }
    _require_exact_fields(raw, expected=expected, subject="repository-snapshot target")

    raw_files = raw["files"]
    if not isinstance(raw_files, list) or not raw_files:
        raise ActualModelTargetError("repository snapshot files must be a non-empty list")
    snapshot_files: list[ActualModelSnapshotFile] = []
    for index, item in enumerate(raw_files):
        if not isinstance(item, dict):
            raise ActualModelTargetError(
                f"repository snapshot files[{index}] must be a JSON object"
            )
        _require_exact_fields(
            item,
            expected={"path", "size_bytes", "sha256"},
            subject=f"repository snapshot files[{index}]",
        )
        try:
            snapshot_files.append(ActualModelSnapshotFile(**item))
        except TypeError as exc:
            raise ActualModelTargetError(
                f"invalid repository snapshot files[{index}]: {exc}"
            ) from exc

    raw_tokenizer_files = raw["serving_tokenizer_files"]
    if not isinstance(raw_tokenizer_files, list) or not raw_tokenizer_files:
        raise ActualModelTargetError(
            "serving_tokenizer_files must be a non-empty list"
        )
    if any(not isinstance(item, str) for item in raw_tokenizer_files):
        raise ActualModelTargetError("serving_tokenizer_files must contain strings")

    try:
        return ActualModelRepositorySnapshotTarget(
            target_id=raw["target_id"],
            model_family=raw["model_family"],
            artifact_repository=raw["artifact_repository"],
            artifact_repository_revision=raw["artifact_repository_revision"],
            quantization=raw["quantization"],
            files=tuple(snapshot_files),
            serving_tokenizer_files=tuple(raw_tokenizer_files),
            chat_template_file=raw["chat_template_file"],
            format_version=raw["format_version"],
            target_kind=raw["target_kind"],
        )
    except TypeError as exc:
        raise ActualModelTargetError(
            f"invalid repository-snapshot target fields: {exc}"
        ) from exc


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


def verify_actual_model_repository_snapshot(
    *,
    target: ActualModelRepositorySnapshotTarget,
    snapshot_root: str | Path,
) -> ActualModelRepositorySnapshotVerification:
    """Verify every frozen execution file under one local repository snapshot."""

    if not isinstance(target, ActualModelRepositorySnapshotTarget):
        raise TypeError("target must be ActualModelRepositorySnapshotTarget")
    root = Path(snapshot_root)
    if not root.is_dir():
        raise ActualModelTargetError("repository snapshot root must be a readable directory")
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise ActualModelTargetError(f"cannot resolve repository snapshot root: {exc}") from exc

    for item in target.files:
        candidate = root.joinpath(*PurePosixPath(item.path).parts)
        if not candidate.exists():
            raise ActualModelTargetError(
                f"required repository snapshot file is missing: {item.path}"
            )
        try:
            resolved_candidate = candidate.resolve(strict=True)
        except OSError as exc:
            raise ActualModelTargetError(
                f"cannot resolve repository snapshot file {item.path}: {exc}"
            ) from exc
        if not resolved_candidate.is_relative_to(resolved_root):
            raise ActualModelTargetError(
                f"repository snapshot file escapes snapshot root: {item.path}"
            )
        if not resolved_candidate.is_file():
            raise ActualModelTargetError(
                f"required repository snapshot path is not a file: {item.path}"
            )
        size = resolved_candidate.stat().st_size
        if size != item.size_bytes:
            raise ActualModelTargetError(
                f"repository snapshot file size does not match frozen target: {item.path}"
            )
        observed_sha256 = _sha256_file(resolved_candidate)
        if observed_sha256 != item.sha256:
            raise ActualModelTargetError(
                f"repository snapshot file SHA256 does not match frozen target: {item.path}"
            )

    return ActualModelRepositorySnapshotVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        verified_file_count=len(target.files),
    )


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ActualModelTargetError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_fields(
    raw: dict[str, Any],
    *,
    expected: set[str],
    subject: str,
) -> None:
    observed = set(raw)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise ActualModelTargetError(f"{subject} is missing fields: " + ", ".join(missing))
    if unknown:
        raise ActualModelTargetError(f"{subject} has unknown fields: " + ", ".join(unknown))


def _require_snapshot_relative_path(value: str, *, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ActualModelTargetError(f"{name} must be a non-empty relative POSIX path")
    if "\\" in value:
        raise ActualModelTargetError(f"{name} must be a relative POSIX path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value in {".", ".."}
        or any(part in {"", ".", ".."} for part in path.parts)
        or str(path) != value
    ):
        raise ActualModelTargetError(f"{name} must be a relative POSIX path")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise ActualModelTargetError(f"cannot read repository snapshot file: {exc}") from exc
    return digest.hexdigest()


def _require_hex_digest(value: str, *, length: int, name: str) -> None:
    if len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise ActualModelTargetError(
            f"{name} must be an exact lowercase {length}-character hexadecimal digest"
        )
