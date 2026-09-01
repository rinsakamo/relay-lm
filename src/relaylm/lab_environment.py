"""Stable, reusable Lab Environment identity for RelayLM v1.

This module deliberately models a prepared environment, not a live launch.
The manifest contains immutable identities and references to existing cache
locations.  It never captures ambient process, GPU, qualification, GitHub, or
semantic state.  ``restore`` verifies those references and caller-supplied
stable identities; it does not install, download, launch, or attest a runtime.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


LAB_ENVIRONMENT_FORMAT_VERSION = 1
LAB_ENVIRONMENT_KIND = "relaylm_lab_environment"
LAB_ENVIRONMENT_FINGERPRINT_PREFIX = b"relaylm-lab-environment-v1\0"

REQUIRED_IDENTITY_SECTIONS = (
    "model",
    "runtime",
    "tokenizer",
    "chat_template",
    "quantization",
    "dependencies",
)
_IDENTITY_FIELDS = {"identity", "revision", "digest", "cache_id", "attributes"}
_REQUIRED_IDENTITY_FIELDS = {"identity", "revision", "digest"}
_ENVIRONMENT_IDENTITY_FIELDS = {
    *REQUIRED_IDENTITY_SECTIONS,
    "cache_references",
    "host_requirements",
    "launcher",
}
_CACHE_REFERENCE_FIELDS = {"id", "kind", "identity", "revision", "digest", "files"}
_CACHE_FILE_FIELDS = {"path", "size_bytes", "sha256"}
_OBSERVED_IDENTITY_FIELDS = {*REQUIRED_IDENTITY_SECTIONS, "host_requirements", "launcher"}
_CACHE_KINDS = {
    "model",
    "runtime",
    "dependencies",
    "tokenizer",
    "chat_template",
    "quantization",
    "compiled",
    "environment",
    "other",
}
_CACHE_LINK_KINDS = {
    "model": "model",
    "runtime": "runtime",
    "dependencies": "dependencies",
    "tokenizer": "tokenizer",
    "chat_template": "chat_template",
    "quantization": "quantization",
}

# These names are rejected at every nested mapping level.  In particular,
# putting a volatile value under ``attributes`` must not bypass the boundary.
_FORBIDDEN_FIELDS = {
    # transient GPU/admission/capacity facts
    "gpu_free_bytes",
    "gpu_total_bytes",
    "free_gpu_bytes",
    "total_gpu_bytes",
    "free_bytes",
    "total_bytes",
    "gpu_memory_utilization",
    "memory_admission",
    "admission",
    "admission_result",
    "kv_cache",
    "kv_cache_bytes",
    "kv_capacity",
    "capacity",
    "capacity_evidence",
    "context_capacity",
    "max_model_len",
    "max_context",
    "context_window",
    # process/listener/nonce facts
    "pid",
    "ppid",
    "pgid",
    "session",
    "session_id",
    "start_time",
    "start_time_ticks",
    "listener",
    "listener_owner",
    "listener_ownership",
    "readiness",
    "runtime_nonce",
    "nonce",
    "run_id",
    "runtime_run_id",
    "transaction_id",
    # qualification/repository authority
    "execution_frozen",
    "semantic_request_count",
    "evidence_root",
    "evidence_path",
    "checkpoint",
    "checkpoint_path",
    "current_authority",
    "authority_status",
    "repository_head",
    "open_pull_requests",
    "open_writers",
    "ci_check_state",
    "issue_state",
    "issue_comments",
    "github_authority",
    # secrets and semantic payloads
    "secret",
    "secret_ref",
    "api_key",
    "access_token",
    "authorization",
    "cookie",
    "password",
    "credential",
    "credentials",
    "private_key",
    "prompt",
    "messages",
    "conversation",
    "question",
    "answer",
    "semantic",
    "semantic_payload",
    "event",
    "events",
    "memory",
    "state",
    "cognitive_package",
    "cognitive_package_state",
    "content",
    "body",
    "raw",
    "result",
    "results",
}
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bbearer\s+\S+", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|password)=\S+", re.IGNORECASE),
    re.compile(r"\b(?:sk|ghp|github_pat|hf)_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class LabEnvironmentError(ValueError):
    """A Lab Environment manifest or restore operation is not admissible."""


# Explicit aliases keep callers from mistaking validation failure for a live
# qualification failure while offering useful names at the integration edge.
LabEnvironmentValidationError = LabEnvironmentError
LabEnvironmentVerificationError = LabEnvironmentError


class LabCacheFile:
    """One immutable file record under an externally owned cache location."""

    __slots__ = ("path", "size_bytes", "sha256")

    def __init__(self, path: str, size_bytes: int, sha256: str) -> None:
        self.path = _require_relative_posix_path(path, "cache file path")
        _reject_cache_path(self.path)
        self.size_bytes = _require_positive_int(size_bytes, "cache file size_bytes")
        self.sha256 = _normalize_sha256(sha256, "cache file sha256", allow_bare=True)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "LabCacheFile":
        if not isinstance(raw, Mapping):
            raise LabEnvironmentError("cache file must be an object")
        _reject_forbidden_tree(raw, "cache file")
        _require_exact_fields(raw, _CACHE_FILE_FIELDS, "cache file")
        try:
            return cls(
                path=raw["path"],  # type: ignore[arg-type]
                size_bytes=raw["size_bytes"],  # type: ignore[arg-type]
                sha256=raw["sha256"],  # type: ignore[arg-type]
            )
        except TypeError as exc:
            raise LabEnvironmentError(f"invalid cache file fields: {exc}") from exc

    def to_mapping(self) -> dict[str, object]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


class LabCacheReference:
    """A content-addressed reference to an existing prepared cache."""

    __slots__ = ("id", "kind", "identity", "revision", "digest", "files")

    def __init__(
        self,
        *,
        id: str,
        kind: str,
        identity: str,
        revision: str,
        digest: str,
        files: Sequence[LabCacheFile],
    ) -> None:
        self.id = _require_safe_id(id, "cache id")
        self.kind = _require_cache_kind(kind)
        self.identity = _require_text(identity, "cache identity")
        self.revision = _require_text(revision, "cache revision")
        self.digest = _normalize_sha256(digest, "cache digest", allow_bare=False)
        if not isinstance(files, tuple):
            files = tuple(files)
        if not files:
            raise LabEnvironmentError(f"cache {self.id} must contain at least one file")
        if any(not isinstance(item, LabCacheFile) for item in files):
            raise LabEnvironmentError(f"cache {self.id} files must be LabCacheFile values")
        normalized = tuple(sorted(files, key=lambda item: item.path))
        if len({item.path for item in normalized}) != len(normalized):
            raise LabEnvironmentError(f"cache {self.id} contains duplicate file paths")
        self.files = normalized

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "LabCacheReference":
        if not isinstance(raw, Mapping):
            raise LabEnvironmentError("cache reference must be an object")
        _reject_forbidden_tree(raw, "cache reference")
        _require_exact_fields(raw, _CACHE_REFERENCE_FIELDS, "cache reference")
        raw_files = raw["files"]
        if not isinstance(raw_files, list):
            raise LabEnvironmentError("cache reference files must be a list")
        try:
            return cls(
                id=raw["id"],  # type: ignore[arg-type]
                kind=raw["kind"],  # type: ignore[arg-type]
                identity=raw["identity"],  # type: ignore[arg-type]
                revision=raw["revision"],  # type: ignore[arg-type]
                digest=raw["digest"],  # type: ignore[arg-type]
                files=tuple(LabCacheFile.from_mapping(item) for item in raw_files),  # type: ignore[arg-type]
            )
        except TypeError as exc:
            raise LabEnvironmentError(f"invalid cache reference fields: {exc}") from exc

    @classmethod
    def from_directory(
        cls,
        root: str | Path,
        *,
        id: str,
        kind: str,
        identity: str,
        revision: str,
        digest: str,
    ) -> "LabCacheReference":
        """Capture file digests without copying the directory contents."""

        return cls(
            id=id,
            kind=kind,
            identity=identity,
            revision=revision,
            digest=digest,
            files=_capture_cache_files(root),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "identity": self.identity,
            "revision": self.revision,
            "digest": self.digest,
            "files": [item.to_mapping() for item in self.files],
        }


class LabEnvironmentVerification:
    """Content-free result of verifying a reusable Lab Environment."""

    __slots__ = ("fingerprint", "verified_cache_ids", "observed_identity_sections", "reused")

    def __init__(
        self,
        *,
        fingerprint: str,
        verified_cache_ids: Sequence[str],
        observed_identity_sections: Sequence[str],
        reused: bool = True,
    ) -> None:
        self.fingerprint = _require_text(fingerprint, "verification fingerprint")
        self.verified_cache_ids = tuple(verified_cache_ids)
        self.observed_identity_sections = tuple(observed_identity_sections)
        if not isinstance(reused, bool):
            raise LabEnvironmentError("verification reused must be boolean")
        self.reused = reused

    def to_mapping(self) -> dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "verified_cache_ids": list(self.verified_cache_ids),
            "observed_identity_sections": list(self.observed_identity_sections),
            "reused": self.reused,
        }


class LabEnvironmentManifest:
    """Canonical stable identity for one prepared physical research environment."""

    __slots__ = ("_identity_json", "_fingerprint")

    def __init__(self, identity: Mapping[str, object]) -> None:
        normalized = _normalize_environment_identity(identity)
        self._identity_json = _canonical_json(normalized)
        self._fingerprint = _fingerprint(normalized)

    @classmethod
    def capture(
        cls,
        *,
        model: Mapping[str, object] | None = None,
        runtime: Mapping[str, object] | None = None,
        tokenizer: Mapping[str, object] | None = None,
        chat_template: Mapping[str, object] | None = None,
        quantization: Mapping[str, object] | None = None,
        dependencies: Mapping[str, object] | None = None,
        cache_references: Sequence[Mapping[str, object] | LabCacheReference] | None = None,
        host_requirements: Mapping[str, object] | None = None,
        launcher: Mapping[str, object] | None = None,
    ) -> "LabEnvironmentManifest":
        """Construct a manifest from explicit stable inputs only.

        No ambient environment, process table, GPU query, semantic fixture, or
        secret source is read by this method.
        """

        values = {
            "model": model,
            "runtime": runtime,
            "tokenizer": tokenizer,
            "chat_template": chat_template,
            "quantization": quantization,
            "dependencies": dependencies,
        }
        identity: dict[str, object] = {}
        for section, value in values.items():
            if value is None:
                raise LabEnvironmentError(f"{section} identity is required")
            identity[section] = _normalize_identity_record(
                value,
                section,
                require_cache_id=section in {"model", "runtime", "dependencies"},
            )

        if cache_references is None:
            raise LabEnvironmentError("cache_references are required")
        identity["cache_references"] = [
            item.to_mapping() if isinstance(item, LabCacheReference) else item
            for item in cache_references
        ]
        identity["host_requirements"] = (
            {} if host_requirements is None else host_requirements
        )
        identity["launcher"] = {} if launcher is None else launcher
        return cls(identity)

    from_inputs = capture

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "LabEnvironmentManifest":
        """Load and validate a complete manifest mapping, including its hash."""

        if not isinstance(raw, Mapping):
            raise LabEnvironmentError("Lab Environment manifest must be an object")
        _reject_forbidden_tree(raw, "Lab Environment manifest")
        _require_exact_fields(
            raw,
            {"format_version", "kind", "identity", "fingerprint"},
            "Lab Environment manifest",
        )
        if isinstance(raw["format_version"], bool) or raw["format_version"] != LAB_ENVIRONMENT_FORMAT_VERSION:
            raise LabEnvironmentError(
                f"unsupported Lab Environment format_version: {raw['format_version']}"
            )
        if raw["kind"] != LAB_ENVIRONMENT_KIND:
            raise LabEnvironmentError("manifest kind is not a Lab Environment")
        identity = raw["identity"]
        if not isinstance(identity, Mapping):
            raise LabEnvironmentError("Lab Environment identity must be an object")
        manifest = cls(identity)
        fingerprint = raw["fingerprint"]
        if not isinstance(fingerprint, str) or fingerprint != manifest.fingerprint:
            raise LabEnvironmentError(
                "Lab Environment fingerprint does not match canonical identity"
            )
        return manifest

    @classmethod
    def load(cls, path: str | Path) -> "LabEnvironmentManifest":
        source = Path(path)
        try:
            raw = json.loads(
                source.read_text(encoding="utf-8"),
                object_pairs_hook=_object_no_duplicates,
            )
        except LabEnvironmentError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LabEnvironmentError(f"cannot load Lab Environment manifest: {exc}") from exc
        if not isinstance(raw, dict):
            raise LabEnvironmentError("Lab Environment manifest must be an object")
        return cls.from_mapping(raw)

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def identity_mapping(self) -> dict[str, object]:
        """Return stable identity sections suitable for a fresh caller observation."""

        identity = self._identity_mapping()
        identity.pop("cache_references", None)
        return identity

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": LAB_ENVIRONMENT_FORMAT_VERSION,
            "kind": LAB_ENVIRONMENT_KIND,
            "identity": self._identity_mapping(),
            "fingerprint": self.fingerprint,
        }

    def _identity_mapping(self) -> dict[str, object]:
        try:
            value = json.loads(self._identity_json)
        except json.JSONDecodeError as exc:  # pragma: no cover - internal invariant
            raise LabEnvironmentError("stored Lab Environment identity is invalid") from exc
        if not isinstance(value, dict):  # pragma: no cover - internal invariant
            raise LabEnvironmentError("stored Lab Environment identity is not an object")
        return value

    def save(self, path: str | Path) -> Path:
        """Persist the canonical manifest with same-directory atomic replacement."""

        target = Path(path)
        payload = _canonical_json(self.to_mapping()) + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = -1
        temporary: Path | None = None
        try:
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.",
                suffix=".tmp",
                dir=target.parent,
            )
            temporary = Path(temporary_name)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                fd = -1
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temporary = None
            _fsync_directory(target.parent)
        except OSError as exc:
            raise LabEnvironmentError(f"cannot atomically save Lab Environment: {exc}") from exc
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        return target

    def verify(
        self,
        *,
        observed_identities: Mapping[str, object] | None = None,
        cache_locations: Mapping[str, str | Path] | None = None,
    ) -> LabEnvironmentVerification:
        """Verify current stable identities and referenced cache bytes.

        The caller must provide current observations and logical cache roots.
        This method intentionally has no path that can restore GPU/admission,
        process/listener, nonce, freeze, evidence, or semantic state.
        """

        if observed_identities is None:
            raise LabEnvironmentError(
                "observed_identities are required; saved identity is not current authority"
            )
        normalized_observed = _normalize_observed_identities(
            observed_identities,
            expected=self._identity_mapping(),
        )
        if cache_locations is None:
            raise LabEnvironmentError(
                "cache_locations are required; cache references cannot be restored by name alone"
            )
        verified = _verify_cache_references(
            self._identity_mapping()["cache_references"],
            cache_locations,
        )
        return LabEnvironmentVerification(
            fingerprint=self.fingerprint,
            verified_cache_ids=verified,
            observed_identity_sections=normalized_observed,
        )

    def restore(
        self,
        *,
        observed_identities: Mapping[str, object] | None = None,
        cache_locations: Mapping[str, str | Path] | None = None,
    ) -> LabEnvironmentVerification:
        """Validate reuse; never reinstall, redownload, launch, or restore live facts."""

        return self.verify(
            observed_identities=observed_identities,
            cache_locations=cache_locations,
        )


def capture_cache_reference(
    root: str | Path,
    *,
    id: str,
    kind: str,
    identity: str,
    revision: str,
    digest: str,
) -> LabCacheReference:
    """Create a digest-only reference for an existing cache directory."""

    return LabCacheReference.from_directory(
        root,
        id=id,
        kind=kind,
        identity=identity,
        revision=revision,
        digest=digest,
    )


def capture_lab_environment(**kwargs: object) -> LabEnvironmentManifest:
    return LabEnvironmentManifest.capture(**kwargs)  # type: ignore[arg-type]


def load_lab_environment(path: str | Path) -> LabEnvironmentManifest:
    return LabEnvironmentManifest.load(path)


def save_lab_environment(
    manifest: LabEnvironmentManifest,
    path: str | Path,
) -> Path:
    if not isinstance(manifest, LabEnvironmentManifest):
        raise TypeError("manifest must be a LabEnvironmentManifest")
    return manifest.save(path)


def restore_lab_environment(
    path: str | Path,
    *,
    observed_identities: Mapping[str, object],
    cache_locations: Mapping[str, str | Path],
) -> LabEnvironmentVerification:
    return load_lab_environment(path).restore(
        observed_identities=observed_identities,
        cache_locations=cache_locations,
    )


def _normalize_environment_identity(raw: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        raise LabEnvironmentError("Lab Environment identity must be an object")
    _reject_forbidden_tree(raw, "Lab Environment identity")
    _require_exact_fields(raw, _ENVIRONMENT_IDENTITY_FIELDS, "Lab Environment identity")
    normalized: dict[str, object] = {}
    for section in REQUIRED_IDENTITY_SECTIONS:
        normalized[section] = _normalize_identity_record(
            raw[section],
            section,
            require_cache_id=section in {"model", "runtime", "dependencies"},
        )

    raw_caches = raw["cache_references"]
    if not isinstance(raw_caches, list):
        raise LabEnvironmentError("cache_references must be a list")
    caches = [
        item if isinstance(item, LabCacheReference) else LabCacheReference.from_mapping(item)
        for item in raw_caches
    ]
    if not caches:
        raise LabEnvironmentError("cache_references must contain at least one cache")
    caches = sorted(caches, key=lambda item: item.id)
    if len({item.id for item in caches}) != len(caches):
        raise LabEnvironmentError("cache_references contain duplicate ids")
    normalized["cache_references"] = [item.to_mapping() for item in caches]

    host = raw["host_requirements"]
    if not isinstance(host, Mapping):
        raise LabEnvironmentError("host_requirements must be an object")
    _reject_forbidden_tree(host, "host_requirements")
    normalized["host_requirements"] = _json_value_copy(host, "host_requirements")

    launcher = raw["launcher"]
    if not isinstance(launcher, Mapping):
        raise LabEnvironmentError("launcher must be an object")
    if launcher:
        normalized["launcher"] = _normalize_identity_record(
            launcher,
            "launcher",
            require_cache_id=False,
        )
    else:
        normalized["launcher"] = {}

    _validate_cache_links(normalized)
    return normalized


def _normalize_identity_record(
    raw: object,
    section: str,
    *,
    require_cache_id: bool,
) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        raise LabEnvironmentError(f"{section} identity must be an object")
    _reject_forbidden_tree(raw, f"{section} identity")
    _require_exact_fields(raw, _IDENTITY_FIELDS, f"{section} identity", required=_REQUIRED_IDENTITY_FIELDS)
    normalized: dict[str, object] = {
        "identity": _require_text(raw["identity"], f"{section}.identity"),
        "revision": _require_text(raw["revision"], f"{section}.revision"),
        "digest": _normalize_sha256(raw["digest"], f"{section}.digest", allow_bare=False),
        "attributes": {},
    }
    if "attributes" in raw:
        attributes = raw["attributes"]
        if not isinstance(attributes, Mapping):
            raise LabEnvironmentError(f"{section}.attributes must be an object")
        _reject_forbidden_tree(attributes, f"{section}.attributes")
        normalized["attributes"] = _json_value_copy(attributes, f"{section}.attributes")
    if "cache_id" in raw:
        normalized["cache_id"] = _require_safe_id(raw["cache_id"], f"{section}.cache_id")
    elif require_cache_id:
        raise LabEnvironmentError(f"{section} identity requires cache_id")
    return normalized


def _validate_cache_links(identity: Mapping[str, object]) -> None:
    caches = {
        item["id"]: item
        for item in identity["cache_references"]  # type: ignore[index]
    }
    for section, required_kind in _CACHE_LINK_KINDS.items():
        record = identity[section]
        cache_id = record.get("cache_id")  # type: ignore[union-attr]
        if cache_id is None:
            if section in {"model", "runtime", "dependencies"}:
                raise LabEnvironmentError(f"{section} identity requires a cache reference")
            continue
        reference = caches.get(cache_id)
        if reference is None:
            raise LabEnvironmentError(f"{section} cache_id {cache_id!r} is missing")
        if reference["kind"] != required_kind:
            raise LabEnvironmentError(
                f"{section} cache_id {cache_id!r} has kind {reference['kind']!r},"
                f" expected {required_kind!r}"
            )
        for field in ("identity", "revision", "digest"):
            if reference[field] != record[field]:
                raise LabEnvironmentError(
                    f"{section} and cache {cache_id!r} {field} identity does not match"
                )


def _normalize_observed_identities(
    raw: Mapping[str, object],
    *,
    expected: Mapping[str, object],
) -> tuple[str, ...]:
    if not isinstance(raw, Mapping):
        raise LabEnvironmentError("observed_identities must be an object")
    _reject_forbidden_tree(raw, "observed_identities")
    unknown = sorted(set(raw) - _OBSERVED_IDENTITY_FIELDS)
    if unknown:
        raise LabEnvironmentError(
            "observed_identities has unknown fields: " + ", ".join(unknown)
        )
    normalized_sections: list[str] = []
    for section in REQUIRED_IDENTITY_SECTIONS:
        if section not in raw:
            raise LabEnvironmentError(f"observed identity is missing {section}")
        expected_record = expected[section]
        normalized = _normalize_identity_record(
            raw[section],
            section,
            require_cache_id="cache_id" in expected_record,  # type: ignore[operator]
        )
        if _canonical_json(normalized) != _canonical_json(expected_record):
            raise LabEnvironmentError(f"observed {section} identity does not match manifest")
        normalized_sections.append(section)

    for section in ("host_requirements", "launcher"):
        expected_value = expected[section]
        if not expected_value:
            continue
        if section not in raw:
            raise LabEnvironmentError(f"observed identity is missing {section}")
        if section == "launcher":
            normalized = _normalize_identity_record(
                raw[section],
                section,
                require_cache_id=False,
            )
        else:
            if not isinstance(raw[section], Mapping):
                raise LabEnvironmentError("observed host_requirements must be an object")
            _reject_forbidden_tree(raw[section], "observed host_requirements")
            normalized = _json_value_copy(raw[section], "observed host_requirements")
        if _canonical_json(normalized) != _canonical_json(expected_value):
            raise LabEnvironmentError(f"observed {section} identity does not match manifest")
        normalized_sections.append(section)
    return tuple(normalized_sections)


def _verify_cache_references(
    raw_references: object,
    locations: Mapping[str, str | Path],
) -> tuple[str, ...]:
    if not isinstance(locations, Mapping):
        raise LabEnvironmentError("cache_locations must be a mapping")
    if not isinstance(raw_references, list):  # pragma: no cover - internal invariant
        raise LabEnvironmentError("manifest cache references are invalid")
    verified: list[str] = []
    for raw_reference in raw_references:
        reference = LabCacheReference.from_mapping(raw_reference)  # type: ignore[arg-type]
        if reference.id not in locations:
            raise LabEnvironmentError(f"cache location is missing {reference.id}")
        location = locations[reference.id]
        if not isinstance(location, (str, Path)):
            raise LabEnvironmentError(f"cache location {reference.id} must be a path")
        root = Path(location)
        if not root.is_dir():
            raise LabEnvironmentError(f"cache location {reference.id} is not a directory")
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as exc:
            raise LabEnvironmentError(
                f"cannot resolve cache location {reference.id}: {exc}"
            ) from exc
        for item in reference.files:
            candidate = root.joinpath(*PurePosixPath(item.path).parts)
            try:
                resolved_candidate = candidate.resolve(strict=True)
            except OSError as exc:
                raise LabEnvironmentError(
                    f"cache {reference.id} file is missing: {item.path}"
                ) from exc
            if not resolved_candidate.is_relative_to(resolved_root):
                raise LabEnvironmentError(
                    f"cache {reference.id} file escapes its root: {item.path}"
                )
            if not resolved_candidate.is_file():
                raise LabEnvironmentError(
                    f"cache {reference.id} path is not a file: {item.path}"
                )
            try:
                observed_size = resolved_candidate.stat().st_size
            except OSError as exc:
                raise LabEnvironmentError(
                    f"cannot stat cache {reference.id} file: {item.path}"
                ) from exc
            if observed_size != item.size_bytes:
                raise LabEnvironmentError(
                    f"cache {reference.id} file size does not match: {item.path}"
                )
            if _sha256_file(resolved_candidate) != item.sha256:
                raise LabEnvironmentError(
                    f"cache {reference.id} file digest does not match: {item.path}"
                )
        verified.append(reference.id)
    return tuple(verified)


def _capture_cache_files(root: str | Path) -> tuple[LabCacheFile, ...]:
    source = Path(root)
    if not source.is_dir():
        raise LabEnvironmentError("cache root must be an existing directory")
    try:
        resolved_root = source.resolve(strict=True)
    except OSError as exc:
        raise LabEnvironmentError(f"cannot resolve cache root: {exc}") from exc
    files: list[LabCacheFile] = []
    for candidate in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        if candidate.is_symlink():
            raise LabEnvironmentError(
                f"cache root contains a symlink and cannot be captured: {candidate}"
            )
        if not candidate.is_file():
            continue
        try:
            resolved_candidate = candidate.resolve(strict=True)
        except OSError as exc:
            raise LabEnvironmentError(f"cannot resolve cache file: {candidate}") from exc
        if not resolved_candidate.is_relative_to(resolved_root):
            raise LabEnvironmentError(f"cache file escapes its root: {candidate}")
        relative = candidate.relative_to(source).as_posix()
        _reject_cache_path(relative)
        try:
            size = candidate.stat().st_size
        except OSError as exc:
            raise LabEnvironmentError(f"cannot stat cache file: {relative}") from exc
        files.append(
            LabCacheFile(
                path=relative,
                size_bytes=size,
                sha256=_sha256_file(candidate),
            )
        )
    if not files:
        raise LabEnvironmentError("cache root must contain at least one regular file")
    return tuple(files)


def _reject_cache_path(value: str) -> None:
    blocked = {
        ".env",
        "credentials",
        "credential",
        "secrets",
        "secret",
        "private_key",
        "events",
        "memory",
        "state",
        "prompts",
        "prompt",
        "messages",
        "conversation",
        "answers",
        "results",
    }
    for part in PurePosixPath(value).parts:
        if _key_token(part) in blocked:
            raise LabEnvironmentError(
                f"cache path {value!r} may contain secret or semantic payload"
            )


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LabEnvironmentError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_fields(
    raw: Mapping[str, object],
    allowed: set[str],
    label: str,
    *,
    required: set[str] | None = None,
) -> None:
    required_fields = allowed if required is None else required
    missing = sorted(required_fields - set(raw))
    unknown = sorted(set(raw) - allowed)
    if missing:
        raise LabEnvironmentError(f"{label} is missing fields: {', '.join(missing)}")
    if unknown:
        raise LabEnvironmentError(f"{label} has unknown fields: {', '.join(unknown)}")


def _normalize_sha256(value: object, label: str, *, allow_bare: bool) -> str:
    if not isinstance(value, str):
        raise LabEnvironmentError(f"{label} must be a SHA-256 digest")
    candidate = value[7:] if value.startswith("sha256:") else value
    if not allow_bare and not value.startswith("sha256:"):
        raise LabEnvironmentError(f"{label} must use the sha256:<digest> form")
    if not _SHA256_RE.fullmatch(candidate):
        raise LabEnvironmentError(f"{label} must be an exact lowercase SHA-256 digest")
    return candidate if allow_bare else f"sha256:{candidate}"


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LabEnvironmentError(f"{label} must be a non-empty string")
    normalized = value.strip()
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise LabEnvironmentError(f"{label} contains control characters")
    return normalized


def _require_safe_id(value: object, label: str) -> str:
    normalized = _require_text(value, label)
    if not _SAFE_ID_RE.fullmatch(normalized):
        raise LabEnvironmentError(f"{label} contains unsafe identifier characters")
    return normalized


def _require_cache_kind(value: object) -> str:
    normalized = _require_safe_id(value, "cache kind").lower()
    if normalized not in _CACHE_KINDS:
        raise LabEnvironmentError(f"unsupported cache kind: {normalized}")
    return normalized


def _require_positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise LabEnvironmentError(f"{label} must be a positive integer")
    return value


def _require_relative_posix_path(value: object, label: str) -> str:
    normalized = _require_text(value, label)
    if "\\" in normalized:
        raise LabEnvironmentError(f"{label} must be a relative POSIX path")
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or normalized in {".", ".."}
        or any(part in {"", ".", ".."} for part in path.parts)
        or str(path) != normalized
    ):
        raise LabEnvironmentError(f"{label} must be a relative POSIX path")
    return normalized


def _key_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _reject_forbidden_tree(value: object, label: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise LabEnvironmentError(f"{label} mapping keys must be strings")
            token = _key_token(key)
            if token in _FORBIDDEN_FIELDS:
                raise LabEnvironmentError(
                    f"{label}.{key} is forbidden: volatile, secret, or semantic state"
                )
            _reject_forbidden_tree(child, f"{label}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_forbidden_tree(child, f"{label}[{index}]")
    elif isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                raise LabEnvironmentError(f"{label} contains secret-like material")


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise LabEnvironmentError("Lab Environment identity must be JSON-serializable") from exc


def _json_value_copy(value: object, label: str) -> object:
    try:
        return json.loads(_canonical_json(value))
    except LabEnvironmentError as exc:
        raise LabEnvironmentError(f"{label} must be JSON-serializable") from exc


def _json_copy(value: object, label: str) -> dict[str, object]:
    copied = _json_value_copy(value, label)
    if not isinstance(copied, dict):
        raise LabEnvironmentError(f"{label} must be an object")
    return copied


def _fingerprint(identity: Mapping[str, object]) -> str:
    canonical = _canonical_json(
        {
            "format_version": LAB_ENVIRONMENT_FORMAT_VERSION,
            "kind": LAB_ENVIRONMENT_KIND,
            "identity": identity,
        }
    ).encode("utf-8")
    digest = hashlib.sha256()
    digest.update(LAB_ENVIRONMENT_FINGERPRINT_PREFIX)
    digest.update(len(canonical).to_bytes(8, "big"))
    digest.update(canonical)
    return f"sha256:{digest.hexdigest()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise LabEnvironmentError(f"cannot read cache file {path}: {exc}") from exc
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    try:
        directory_fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        try:
            os.fsync(directory_fd)
        except OSError:
            pass
    finally:
        os.close(directory_fd)


__all__ = [
    "LAB_ENVIRONMENT_FORMAT_VERSION",
    "LAB_ENVIRONMENT_KIND",
    "LabCacheFile",
    "LabCacheReference",
    "LabEnvironmentError",
    "LabEnvironmentManifest",
    "LabEnvironmentValidationError",
    "LabEnvironmentVerification",
    "LabEnvironmentVerificationError",
    "capture_cache_reference",
    "capture_lab_environment",
    "load_lab_environment",
    "restore_lab_environment",
    "save_lab_environment",
]
