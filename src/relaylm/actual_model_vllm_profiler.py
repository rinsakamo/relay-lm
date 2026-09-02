from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


_KV_CACHE_FLAG = r"--kv-cache-memory(?:-bytes)?=(?P<bytes>[1-9][0-9]*)"
_FULLY_UTILIZE_ROLE = r"to\s+fully\s+utilize(?:\s+available)?\s+gpu\s+memory"
_KV_CACHE_FULLY_UTILIZE_SUFFIX_PATTERN = re.compile(
    rf"{_KV_CACHE_FLAG}(?:(?!--kv-cache-memory)[^\r\n])*?{_FULLY_UTILIZE_ROLE}",
    re.IGNORECASE,
)
_KV_CACHE_FULLY_UTILIZE_PREFIX_PATTERN = re.compile(
    rf"{_FULLY_UTILIZE_ROLE}(?:(?!--kv-cache-memory)[^\r\n])*?{_KV_CACHE_FLAG}",
    re.IGNORECASE,
)
_MEMORY_UTILIZATION_SCALE = 1_000_000
_TOKEN_CAPACITY_REFERENCE_EVIDENCE_FORMAT_VERSION = 1
_TOKEN_CAPACITY_REFERENCE_EVIDENCE_PREFIX = "amkvref"
_VLLM_MODEL_RUNNERS = ("v1", "v2")


@dataclass(frozen=True, slots=True)
class VLLMTokenCapacityReference:
    """Stable same-launch-class memory geometry for one attested vLLM runtime."""

    non_kv_memory_bytes: int
    kv_cache_memory_bytes: int
    kv_cache_capacity_tokens: int
    kv_allocation_unit_bytes: int
    kv_allocation_unit_tokens: int

    def __post_init__(self) -> None:
        for name in (
            "non_kv_memory_bytes",
            "kv_cache_memory_bytes",
            "kv_cache_capacity_tokens",
            "kv_allocation_unit_bytes",
            "kv_allocation_unit_tokens",
        ):
            _require_int(getattr(self, name), name)
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")

        allocation_capacity_tokens = (
            self.kv_cache_memory_bytes // self.kv_allocation_unit_bytes
        ) * self.kv_allocation_unit_tokens
        if allocation_capacity_tokens < self.kv_cache_capacity_tokens:
            raise ValueError(
                "KV allocation geometry cannot carry the attested KV token capacity"
            )

    @classmethod
    def from_successful_launch_envelope(
        cls,
        *,
        startup_free_bytes: int,
        kv_cache_memory_bytes: int,
        kv_cache_capacity_tokens: int,
        kv_allocation_unit_bytes: int,
        kv_allocation_unit_tokens: int,
    ) -> VLLMTokenCapacityReference:
        """Build a conservative non-KV envelope from one successful launch."""

        for name, value in (
            ("startup_free_bytes", startup_free_bytes),
            ("kv_cache_memory_bytes", kv_cache_memory_bytes),
            ("kv_cache_capacity_tokens", kv_cache_capacity_tokens),
            ("kv_allocation_unit_bytes", kv_allocation_unit_bytes),
            ("kv_allocation_unit_tokens", kv_allocation_unit_tokens),
        ):
            _require_int(value, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if kv_cache_memory_bytes >= startup_free_bytes:
            raise ValueError(
                "successful launch evidence must leave positive non-KV memory"
            )
        return cls(
            non_kv_memory_bytes=startup_free_bytes - kv_cache_memory_bytes,
            kv_cache_memory_bytes=kv_cache_memory_bytes,
            kv_cache_capacity_tokens=kv_cache_capacity_tokens,
            kv_allocation_unit_bytes=kv_allocation_unit_bytes,
            kv_allocation_unit_tokens=kv_allocation_unit_tokens,
        )

    @property
    def kv_bytes_per_token_upper_bound(self) -> int:
        """Conservative byte/token slope derived from the attested KV capacity."""

        return _ceil_div(self.kv_cache_memory_bytes, self.kv_cache_capacity_tokens)

    def required_kv_cache_memory_bytes(self, *, target_model_len: int) -> int:
        """Convert a selected token window into page-conservative explicit KV bytes."""

        _require_int(target_model_len, "target_model_len")
        if target_model_len <= 0:
            raise ValueError("target_model_len must be positive")
        if target_model_len > self.kv_cache_capacity_tokens:
            raise ValueError(
                "target_model_len exceeds the attested KV token capacity; "
                "fresh launch-capability evidence is required"
            )

        continuous_requirement = (
            self.kv_bytes_per_token_upper_bound * target_model_len
        )
        allocation_requirement = (
            _ceil_div(target_model_len, self.kv_allocation_unit_tokens)
            * self.kv_allocation_unit_bytes
        )
        return max(continuous_requirement, allocation_requirement)

    def required_total_memory_bytes(self, *, target_model_len: int) -> int:
        return self.non_kv_memory_bytes + self.required_kv_cache_memory_bytes(
            target_model_len=target_model_len
        )


class VLLMTokenCapacityReferenceEvidenceError(ValueError):
    """A citable vLLM token-capacity reference artifact is invalid/incompatible."""


@dataclass(frozen=True, slots=True)
class VLLMTokenCapacityLaunchClass:
    """Stable compatibility identity for one reusable vLLM memory-geometry class."""

    target_id: str
    target_revision: str
    backend_version: str
    backend_source_revision: str
    model_runner: str
    host_capability_class: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.target_id, "target_id")
        _require_sha256_identity(self.target_revision, "target_revision")
        _require_non_empty_string(self.backend_version, "backend_version")
        _require_hex_revision(
            self.backend_source_revision,
            "backend_source_revision",
            length=40,
        )
        if self.model_runner not in _VLLM_MODEL_RUNNERS:
            raise ValueError(
                "model_runner must be one of: " + ", ".join(_VLLM_MODEL_RUNNERS)
            )
        _require_non_empty_string(
            self.host_capability_class,
            "host_capability_class",
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "target_revision": self.target_revision,
            "backend_version": self.backend_version,
            "backend_source_revision": self.backend_source_revision,
            "model_runner": self.model_runner,
            "host_capability_class": self.host_capability_class,
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
                "host_capability_class",
            },
            "launch_class",
        )
        return cls(
            target_id=mapping["target_id"],  # type: ignore[arg-type]
            target_revision=mapping["target_revision"],  # type: ignore[arg-type]
            backend_version=mapping["backend_version"],  # type: ignore[arg-type]
            backend_source_revision=mapping["backend_source_revision"],  # type: ignore[arg-type]
            model_runner=mapping["model_runner"],  # type: ignore[arg-type]
            host_capability_class=mapping["host_capability_class"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class VLLMTokenCapacityReferenceEvidence:
    """Immutable successful-launch evidence yielding one compatible KV reference."""

    launch_class: VLLMTokenCapacityLaunchClass
    startup_free_bytes: int
    reference: VLLMTokenCapacityReference
    format_version: int = _TOKEN_CAPACITY_REFERENCE_EVIDENCE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != _TOKEN_CAPACITY_REFERENCE_EVIDENCE_FORMAT_VERSION:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "unsupported token-capacity-reference evidence format_version"
            )
        if not isinstance(self.launch_class, VLLMTokenCapacityLaunchClass):
            raise TypeError("launch_class must be VLLMTokenCapacityLaunchClass")
        if not isinstance(self.reference, VLLMTokenCapacityReference):
            raise TypeError("reference must be VLLMTokenCapacityReference")
        _require_int(self.startup_free_bytes, "startup_free_bytes")
        if self.startup_free_bytes <= 0:
            raise ValueError("startup_free_bytes must be positive")
        expected_startup = (
            self.reference.non_kv_memory_bytes + self.reference.kv_cache_memory_bytes
        )
        if self.startup_free_bytes != expected_startup:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "startup_free_bytes does not match the successful launch envelope"
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
        digest = hashlib.sha256(_canonical_json_bytes(self._payload_mapping())).hexdigest()
        return f"{_TOKEN_CAPACITY_REFERENCE_EVIDENCE_PREFIX}-{digest}"

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
        return {
            "evidence_id": self.evidence_id,
            **self._payload_mapping(),
        }

    @classmethod
    def from_mapping(cls, value: object) -> VLLMTokenCapacityReferenceEvidence:
        mapping = _require_mapping(value, "token-capacity-reference evidence")
        _require_exact_keys(
            mapping,
            {"evidence_id", "format_version", "launch_class", "successful_launch"},
            "token-capacity-reference evidence",
        )
        format_version = mapping["format_version"]
        _require_int(format_version, "format_version")  # type: ignore[arg-type]
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
                startup_free_bytes=successful["startup_free_bytes"],  # type: ignore[arg-type]
                kv_cache_memory_bytes=successful["kv_cache_memory_bytes"],  # type: ignore[arg-type]
                kv_cache_capacity_tokens=successful["kv_cache_capacity_tokens"],  # type: ignore[arg-type]
                kv_allocation_unit_bytes=successful["kv_allocation_unit_bytes"],  # type: ignore[arg-type]
                kv_allocation_unit_tokens=successful["kv_allocation_unit_tokens"],  # type: ignore[arg-type]
            )
        except (TypeError, ValueError) as exc:
            raise VLLMTokenCapacityReferenceEvidenceError(
                f"invalid successful launch geometry: {exc}"
            ) from exc
        if evidence.format_version != format_version:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "unsupported token-capacity-reference evidence format_version"
            )
        if successful["non_kv_memory_bytes"] != evidence.reference.non_kv_memory_bytes:
            raise VLLMTokenCapacityReferenceEvidenceError(
                "non_kv_memory_bytes does not match the successful launch envelope"
            )
        evidence_id = mapping["evidence_id"]
        _require_non_empty_string(evidence_id, "evidence_id")  # type: ignore[arg-type]
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


@dataclass(frozen=True, slots=True)
class VLLMLaunchMemoryAdmission:
    """Fresh feasibility check for a fixed, token-derived vLLM memory envelope."""

    free_bytes: int
    total_bytes: int
    required_memory_bytes: int
    target_model_len: int
    kv_cache_memory_bytes: int

    def __post_init__(self) -> None:
        for name in (
            "free_bytes",
            "total_bytes",
            "required_memory_bytes",
            "target_model_len",
            "kv_cache_memory_bytes",
        ):
            _require_int(getattr(self, name), name)
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.free_bytes > self.total_bytes:
            raise ValueError("free_bytes must not exceed total_bytes")
        if self.required_memory_bytes > self.total_bytes:
            raise ValueError("required_memory_bytes must not exceed total_bytes")
        if self.kv_cache_memory_bytes >= self.required_memory_bytes:
            raise ValueError(
                "required_memory_bytes must include positive non-KV memory"
            )
        if self.free_bytes < self.required_memory_bytes:
            raise ValueError(
                "fresh free GPU memory is below the token-derived required memory"
            )
        if self._utilization_units <= 0:
            raise ValueError(
                "required memory is too small to render a positive vLLM startup admission"
            )

    @classmethod
    def for_token_window(
        cls,
        *,
        free_bytes: int,
        total_bytes: int,
        target_model_len: int,
        reference: VLLMTokenCapacityReference,
    ) -> VLLMLaunchMemoryAdmission:
        if not isinstance(reference, VLLMTokenCapacityReference):
            raise TypeError("reference must be VLLMTokenCapacityReference")
        kv_cache_memory_bytes = reference.required_kv_cache_memory_bytes(
            target_model_len=target_model_len
        )
        return cls(
            free_bytes=free_bytes,
            total_bytes=total_bytes,
            required_memory_bytes=(
                reference.non_kv_memory_bytes + kv_cache_memory_bytes
            ),
            target_model_len=target_model_len,
            kv_cache_memory_bytes=kv_cache_memory_bytes,
        )

    @property
    def _utilization_units(self) -> int:
        units = (
            self.required_memory_bytes * _MEMORY_UTILIZATION_SCALE
        ) // self.total_bytes
        if units >= _MEMORY_UTILIZATION_SCALE:
            return _MEMORY_UTILIZATION_SCALE
        while units > 0 and math.ceil(
            self.total_bytes * (units / _MEMORY_UTILIZATION_SCALE)
        ) > self.required_memory_bytes:
            units -= 1
        return units

    @property
    def gpu_memory_utilization(self) -> str:
        """Pinned-vLLM startup guard derived from required bytes, never free bytes."""

        units = self._utilization_units
        whole, fractional = divmod(units, _MEMORY_UTILIZATION_SCALE)
        return f"{whole}.{fractional:06d}"

    def final_memory_args(self) -> tuple[str, ...]:
        """Render the fixed target window and explicit KV budget for final runtime."""

        return (
            "--gpu-memory-utilization",
            self.gpu_memory_utilization,
            "--kv-cache-memory-bytes",
            str(self.kv_cache_memory_bytes),
            "--max-model-len",
            str(self.target_model_len),
        )


class VLLMProfilerRecommendationError(ValueError):
    """A profiler log does not contain one unambiguous KV-cache recommendation."""


def parse_vllm_kv_cache_recommendation_bytes(log_text: str) -> int:
    """Return the pinned-vLLM fully-utilize GPU KV-cache recommendation."""

    if not isinstance(log_text, str):
        raise TypeError("log_text must be a string")

    recommendations = {
        int(match.group("bytes"))
        for pattern in (
            _KV_CACHE_FULLY_UTILIZE_SUFFIX_PATTERN,
            _KV_CACHE_FULLY_UTILIZE_PREFIX_PATTERN,
        )
        for match in pattern.finditer(log_text)
    }
    if not recommendations:
        raise VLLMProfilerRecommendationError(
            "vLLM fully-utilize KV-cache recommendation not found"
        )
    if len(recommendations) != 1:
        raise VLLMProfilerRecommendationError(
            "conflicting vLLM fully-utilize KV-cache recommendations"
        )
    return next(iter(recommendations))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract the exact pinned-vLLM fully-utilize GPU KV-cache byte "
            "recommendation for launch-capability evidence."
        )
    )
    parser.add_argument(
        "--log",
        type=Path,
        required=True,
        help="Path to the raw pinned-vLLM profiler log.",
    )
    return parser


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _ceil_div(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


def _require_int(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")


def _require_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_sha256_identity(value: object, label: str) -> str:
    text = _require_non_empty_string(value, label)
    prefix = "sha256:"
    if not text.startswith(prefix):
        raise ValueError(f"{label} must be a sha256 identity")
    digest = text[len(prefix) :]
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{label} must be a lowercase sha256 identity")
    return text


def _require_hex_revision(value: object, label: str, *, length: int) -> str:
    text = _require_non_empty_string(value, label)
    if len(text) != length or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{label} must be a {length}-character lowercase hex revision")
    return text


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


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        log_text = args.log.read_text(encoding="utf-8")
        recommendation = parse_vllm_kv_cache_recommendation_bytes(log_text)
    except (OSError, UnicodeError, VLLMProfilerRecommendationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(recommendation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())