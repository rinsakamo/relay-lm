from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from relaylm.actual_model_vllm_profiler import VLLMTokenCapacityReference


VLLM_TOKEN_CAPACITY_REFERENCE_EVIDENCE_FORMAT_VERSION = 1
VLLM_TOKEN_CAPACITY_REFERENCE_EVIDENCE_PREFIX = "amkvref"
VLLM_TOKEN_CAPACITY_MODEL_RUNNERS = ("v1", "v2")


class VLLMTokenCapacityReferenceEvidenceError(ValueError):
    """A citable vLLM token-capacity reference artifact is invalid/incompatible."""


@dataclass(frozen=True, slots=True)
class VLLMTokenCapacityLaunchClass:
    """Stable compatibility identity for reusable pinned-vLLM memory geometry."""

    target_id: str
    target_revision: str
    backend_version: str
    backend_source_revision: str
    model_runner: str
    gpu_compute_capability_major: int
    gpu_compute_capability_minor: int
    gpu_total_memory_bytes: int

    def __post_init__(self) -> None:
        _require_non_empty_string(self.target_id, "target_id")
        _require_sha256_identity(self.target_revision, "target_revision")
        _require_non_empty_string(self.backend_version, "backend_version")
        _require_hex_revision(
            self.backend_source_revision,
            "backend_source_revision",
            length=40,
        )
        if self.model_runner not in VLLM_TOKEN_CAPACITY_MODEL_RUNNERS:
            raise ValueError(
                "model_runner must be one of: "
                + ", ".join(VLLM_TOKEN_CAPACITY_MODEL_RUNNERS)
            )
        _require_non_negative_int(
            self.gpu_compute_capability_major,
            "gpu_compute_capability_major",
        )
        _require_non_negative_int(
            self.gpu_compute_capability_minor,
            "gpu_compute_capability_minor",
        )
        if self.gpu_compute_capability_major == 0:
            raise ValueError("gpu_compute_capability_major must be positive")
        _require_positive_int(
            self.gpu_total_memory_bytes,
            "gpu_total_memory_bytes",
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "target_revision": self.target_revision,
            "backend_version": self.backend_version,
            "backend_source_revision": self.backend_source_revision,
            "model_runner": self.model_runner,
            "gpu_compute_capability_major": self.gpu_compute_capability_major,
            "gpu_compute_capability_minor": self.gpu_compute_capability_minor,
            "gpu_total_memory_bytes": self.gpu_total_memory_bytes,
        }

    @classmethod
    def from_mapping(cls, value: object) -> VLLMTokenCapacityLaunchClass:
        mapping = _require_mapping(value, "launch_class")
        _require_exact_keys(
            mapping,
            {
                "target_id",
                "target_revision",
                "backend_version",
                "backend_source_revision",
                "model_runner",
                "gpu_compute_capability_major",
                "gpu_compute_capability_minor",
                "gpu_total_memory_bytes",
            },
            "launch_class",
        )
        try:
            return cls(
                target_id=_require_non_empty_string(
                    mapping["target_id"],
                    "target_id",
                ),
                target_revision=_require_sha256_identity(
                    mapping["target_revision"],
                    "target_revision",
                ),
                backend_version=_require_non_empty_string(
                    mapping["backend_version"],
                    "backend_version",
                ),
                backend_source_revision=_require_hex_revision(
                    mapping["backend_source_revision"],
                    "backend_source_revision",
                    length=40,
                ),
                model_runner=_require_non_empty_string(
                    mapping["model_runner"],
                    "model_runner",
                ),
                gpu_compute_capability_major=_require_non_negative_int(
                    mapping["gpu_compute_capability_major"],
                    "gpu_compute_capability_major",
                ),
                gpu_compute_capability_minor=_require_non_negative_int(
                    mapping["gpu_compute_capability_minor"],
                    "gpu_compute_capability_minor",
                ),
                gpu_total_memory_bytes=_require_positive_int(
                    mapping["gpu_total_memory_bytes"],
                    "gpu_total_memory_bytes",
                ),
            )
        except (TypeError, ValueError) as exc:
            raise VLLMTokenCapacityReferenceEvidenceError(
                f"invalid launch class: {exc}"
            ) from exc


@dataclass(frozen=True, slots=True)
class VLLMTokenCapacityReferenceEvidence:
    """Immutable successful-launch evidence yielding one compatible KV reference."""

    launch_class: VLLMTokenCapacityLaunchClass
    startup_free_bytes: int
    reference: VLLMTokenCapacityReference
    format_version: int = VLLM_TOKEN_CAPACITY_REFERENCE_EVIDENCE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != VLLM_TOKEN_CAPACITY_REFERENCE_EVIDENCE_FORMAT_VERSION:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "unsupported token-capacity-reference evidence format_version"
            )
        if not isinstance(self.launch_class, VLLMTokenCapacityLaunchClass):
            raise TypeError("launch_class must be VLLMTokenCapacityLaunchClass")
        if not isinstance(self.reference, VLLMTokenCapacityReference):
            raise TypeError("reference must be VLLMTokenCapacityReference")
        _require_positive_int(self.startup_free_bytes, "startup_free_bytes")
        expected_startup = (
            self.reference.non_kv_memory_bytes + self.reference.kv_cache_memory_bytes
        )
        if self.startup_free_bytes != expected_startup:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "startup_free_bytes does not match the successful launch envelope"
            )
        if self.startup_free_bytes > self.launch_class.gpu_total_memory_bytes:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "startup_free_bytes exceeds launch-class GPU total memory"
            )

    @classmethod
    def from_successful_launch(
        cls,
        *,
        launch_class: VLLMTokenCapacityLaunchClass,
        startup_free_bytes: int,
        kv_cache_memory_bytes: int,
        kv_cache_capacity_tokens: int,
        kv_allocation_unit_bytes: int,
        kv_allocation_unit_tokens: int,
    ) -> VLLMTokenCapacityReferenceEvidence:
        if not isinstance(launch_class, VLLMTokenCapacityLaunchClass):
            raise TypeError("launch_class must be VLLMTokenCapacityLaunchClass")
        reference = VLLMTokenCapacityReference.from_successful_launch_envelope(
            startup_free_bytes=startup_free_bytes,
            kv_cache_memory_bytes=kv_cache_memory_bytes,
            kv_cache_capacity_tokens=kv_cache_capacity_tokens,
            kv_allocation_unit_bytes=kv_allocation_unit_bytes,
            kv_allocation_unit_tokens=kv_allocation_unit_tokens,
        )
        return cls(
            launch_class=launch_class,
            startup_free_bytes=startup_free_bytes,
            reference=reference,
        )

    @property
    def evidence_id(self) -> str:
        digest = hashlib.sha256(
            _canonical_json_bytes(self._payload_mapping())
        ).hexdigest()
        return f"{VLLM_TOKEN_CAPACITY_REFERENCE_EVIDENCE_PREFIX}-{digest}"

    def _payload_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "launch_class": self.launch_class.to_mapping(),
            "successful_launch": {
                "startup_free_bytes": self.startup_free_bytes,
                "non_kv_memory_bytes": self.reference.non_kv_memory_bytes,
                "kv_cache_memory_bytes": self.reference.kv_cache_memory_bytes,
                "kv_cache_capacity_tokens": self.reference.kv_cache_capacity_tokens,
                "kv_allocation_unit_bytes": self.reference.kv_allocation_unit_bytes,
                "kv_allocation_unit_tokens": self.reference.kv_allocation_unit_tokens,
            },
        }

    def to_mapping(self) -> dict[str, object]:
        return {"evidence_id": self.evidence_id, **self._payload_mapping()}

    @classmethod
    def from_mapping(cls, value: object) -> VLLMTokenCapacityReferenceEvidence:
        mapping = _require_mapping(value, "token-capacity-reference evidence")
        _require_exact_keys(
            mapping,
            {"evidence_id", "format_version", "launch_class", "successful_launch"},
            "token-capacity-reference evidence",
        )
        format_version = _require_positive_int(
            mapping["format_version"],
            "format_version",
        )
        if format_version != VLLM_TOKEN_CAPACITY_REFERENCE_EVIDENCE_FORMAT_VERSION:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "unsupported token-capacity-reference evidence format_version"
            )
        launch_class = VLLMTokenCapacityLaunchClass.from_mapping(mapping["launch_class"])
        successful = _require_mapping(mapping["successful_launch"], "successful_launch")
        _require_exact_keys(
            successful,
            {
                "startup_free_bytes",
                "non_kv_memory_bytes",
                "kv_cache_memory_bytes",
                "kv_cache_capacity_tokens",
                "kv_allocation_unit_bytes",
                "kv_allocation_unit_tokens",
            },
            "successful_launch",
        )
        try:
            evidence = cls.from_successful_launch(
                launch_class=launch_class,
                startup_free_bytes=_require_positive_int(
                    successful["startup_free_bytes"],
                    "startup_free_bytes",
                ),
                kv_cache_memory_bytes=_require_positive_int(
                    successful["kv_cache_memory_bytes"],
                    "kv_cache_memory_bytes",
                ),
                kv_cache_capacity_tokens=_require_positive_int(
                    successful["kv_cache_capacity_tokens"],
                    "kv_cache_capacity_tokens",
                ),
                kv_allocation_unit_bytes=_require_positive_int(
                    successful["kv_allocation_unit_bytes"],
                    "kv_allocation_unit_bytes",
                ),
                kv_allocation_unit_tokens=_require_positive_int(
                    successful["kv_allocation_unit_tokens"],
                    "kv_allocation_unit_tokens",
                ),
            )
        except (TypeError, ValueError) as exc:
            raise VLLMTokenCapacityReferenceEvidenceError(
                f"invalid successful launch geometry: {exc}"
            ) from exc
        if successful["non_kv_memory_bytes"] != evidence.reference.non_kv_memory_bytes:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "non_kv_memory_bytes does not match the successful launch envelope"
            )
        evidence_id = _require_non_empty_string(mapping["evidence_id"], "evidence_id")
        if evidence_id != evidence.evidence_id:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "token-capacity-reference evidence_id does not match content"
            )
        return evidence

    def require_compatible_reference(
        self,
        launch_class: VLLMTokenCapacityLaunchClass,
    ) -> VLLMTokenCapacityReference:
        if not isinstance(launch_class, VLLMTokenCapacityLaunchClass):
            raise TypeError("launch_class must be VLLMTokenCapacityLaunchClass")
        if launch_class != self.launch_class:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "token-capacity reference launch class is incompatible"
            )
        return self.reference


def write_vllm_token_capacity_reference_evidence(
    *,
    evidence: VLLMTokenCapacityReferenceEvidence,
    artifact_root: str | Path,
) -> Path:
    """Atomically persist one immutable citable token-capacity reference."""

    if not isinstance(evidence, VLLMTokenCapacityReferenceEvidence):
        raise TypeError("evidence must be VLLMTokenCapacityReferenceEvidence")
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{evidence.evidence_id}.json"
    encoded = _canonical_json_bytes(evidence.to_mapping()) + b"\n"
    if path.exists():
        if path.read_bytes() != encoded:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "existing token-capacity-reference artifact conflicts with evidence_id"
            )
        return path

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=root,
            prefix=f".{evidence.evidence_id}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def load_vllm_token_capacity_reference_evidence(
    path: str | Path,
) -> VLLMTokenCapacityReferenceEvidence:
    """Strictly reload one citable token-capacity-reference artifact."""

    artifact = Path(path)
    try:
        value = json.loads(artifact.read_text(encoding="utf-8"))
        evidence = VLLMTokenCapacityReferenceEvidence.from_mapping(value)
    except VLLMTokenCapacityReferenceEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise VLLMTokenCapacityReferenceEvidenceError(
            f"cannot load token-capacity-reference evidence: {exc}"
        ) from exc
    expected_name = f"{evidence.evidence_id}.json"
    if artifact.name != expected_name:
        raise VLLMTokenCapacityReferenceEvidenceError(
            "token-capacity-reference artifact filename does not match evidence_id"
        )
    return evidence


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VLLMTokenCapacityReferenceEvidenceError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise VLLMTokenCapacityReferenceEvidenceError(
            f"{label} keys must be strings"
        )
    return value


def _require_exact_keys(
    mapping: Mapping[str, object],
    expected: set[str],
    label: str,
) -> None:
    actual = set(mapping)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise VLLMTokenCapacityReferenceEvidenceError(
            f"{label} keys mismatch: missing={missing}, extra={extra}"
        )


def _require_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _require_non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _require_sha256_identity(value: object, label: str) -> str:
    text = _require_non_empty_string(value, label)
    if not text.startswith("sha256:"):
        raise ValueError(f"{label} must be a sha256 identity")
    digest = text.removeprefix("sha256:")
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{label} must be a lowercase sha256 identity")
    return text


def _require_hex_revision(value: object, label: str, *, length: int) -> str:
    text = _require_non_empty_string(value, label)
    if len(text) != length or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise ValueError(
            f"{label} must be a {length}-character lowercase hex revision"
        )
    return text
