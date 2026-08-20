from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from relaylm.actual_model_targets import ActualModelArtifactTarget
from relaylm.cognition_execution import (
    CognitionExecutionCapabilities,
    CognitionPassRequest,
    CognitionPassResolution,
    normalize_cognition_execution_capabilities,
    resolve_pass_request,
)
from relaylm.providers.openai_compatible_cognition import (
    OpenAICompatibleCognitionCapabilityFacts,
)
from relaylm.providers.openai_compatible_identity import OpenAICompatibleProviderIdentity

ACTUAL_MODEL_COGNITION_CAPABILITY_FORMAT_VERSION = 1
ACTUAL_MODEL_COGNITION_CAPABILITY_ID_PREFIX = "cogp-capability-"


class ActualModelCognitionCapabilityArtifactError(RuntimeError):
    """Unsupported-condition capability evidence is malformed or conflicting."""


@dataclass(frozen=True, slots=True)
class ActualModelUnsupportedCognitionConditionEvidence:
    """Content-free evidence that an explicit cognition condition cannot execute.

    This is capability evidence, not a model run. It contains no response, raw
    proposals, run_id, or model-quality judgment because semantic generation did
    not occur.
    """

    evidence_id: str
    relaylm_commit: str
    condition_id: str
    target: ActualModelArtifactTarget
    provider_identity: OpenAICompatibleProviderIdentity
    provider_cognition_facts: OpenAICompatibleCognitionCapabilityFacts
    normalized_capabilities: CognitionExecutionCapabilities
    pass_name: str
    request: CognitionPassRequest
    resolution: CognitionPassResolution
    format_version: int = ACTUAL_MODEL_COGNITION_CAPABILITY_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != ACTUAL_MODEL_COGNITION_CAPABILITY_FORMAT_VERSION:
            raise ValueError(
                "unsupported actual-model cognition capability format_version: "
                f"{self.format_version}"
            )
        _validate_relaylm_commit(self.relaylm_commit)
        if not isinstance(self.condition_id, str) or not self.condition_id.strip():
            raise ValueError("condition_id must be a non-empty string")
        if not isinstance(self.pass_name, str) or not self.pass_name.strip():
            raise ValueError("pass_name must be a non-empty string")
        if not isinstance(self.target, ActualModelArtifactTarget):
            raise TypeError("target must be ActualModelArtifactTarget")
        if not isinstance(self.provider_identity, OpenAICompatibleProviderIdentity):
            raise TypeError("provider_identity must be OpenAICompatibleProviderIdentity")
        if not isinstance(
            self.provider_cognition_facts,
            OpenAICompatibleCognitionCapabilityFacts,
        ):
            raise TypeError(
                "provider_cognition_facts must be OpenAICompatibleCognitionCapabilityFacts"
            )
        if not isinstance(self.normalized_capabilities, CognitionExecutionCapabilities):
            raise TypeError(
                "normalized_capabilities must be CognitionExecutionCapabilities"
            )
        if not isinstance(self.request, CognitionPassRequest):
            raise TypeError("request must be CognitionPassRequest")
        if not isinstance(self.resolution, CognitionPassResolution):
            raise TypeError("resolution must be CognitionPassResolution")
        if not self.resolution.unsupported_fields:
            raise ValueError(
                "unsupported cognition condition evidence requires at least one unsupported field"
            )
        expected_prefix = ACTUAL_MODEL_COGNITION_CAPABILITY_ID_PREFIX
        digest = self.evidence_id.removeprefix(expected_prefix)
        if (
            not self.evidence_id.startswith(expected_prefix)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise ValueError("evidence_id must be a content-addressed cognition capability id")

    def identity_mapping(self) -> dict[str, object]:
        """Return the stable content-addressed identity excluding evidence_id."""

        return {
            "format_version": self.format_version,
            "relaylm_commit": self.relaylm_commit,
            "condition_id": self.condition_id,
            "target": _target_identity_mapping(self.target),
            "provider_identity": self.provider_identity.to_mapping(),
            "provider_cognition_facts": self.provider_cognition_facts.to_mapping(),
            "normalized_cognition_capabilities": _capabilities_mapping(
                self.normalized_capabilities
            ),
            "pass": self.pass_name,
            "request": _request_mapping(self.request),
            "resolution": self.resolution.to_mapping(),
            "unsupported_fields": list(self.resolution.unsupported_fields),
            "condition_status": "unsupported",
            "generation_executed": False,
        }

    def to_mapping(self) -> dict[str, object]:
        mapping = self.identity_mapping()
        return {
            "format_version": mapping.pop("format_version"),
            "evidence_id": self.evidence_id,
            **mapping,
            "model_quality": None,
            "score": None,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        )


def build_unsupported_cognition_condition_evidence(
    *,
    relaylm_commit: str,
    condition_id: str,
    target: ActualModelArtifactTarget,
    provider_identity: OpenAICompatibleProviderIdentity,
    provider_cognition_facts: OpenAICompatibleCognitionCapabilityFacts,
    pass_name: str,
    request: CognitionPassRequest,
) -> ActualModelUnsupportedCognitionConditionEvidence:
    """Resolve one explicit request and construct evidence only if it is unsupported."""

    _validate_relaylm_commit(relaylm_commit)
    if not isinstance(condition_id, str) or not condition_id.strip():
        raise ValueError("condition_id must be a non-empty string")
    if not isinstance(pass_name, str) or not pass_name.strip():
        raise ValueError("pass_name must be a non-empty string")
    if not isinstance(target, ActualModelArtifactTarget):
        raise TypeError("target must be ActualModelArtifactTarget")
    if not isinstance(provider_identity, OpenAICompatibleProviderIdentity):
        raise TypeError("provider_identity must be OpenAICompatibleProviderIdentity")
    if not isinstance(
        provider_cognition_facts,
        OpenAICompatibleCognitionCapabilityFacts,
    ):
        raise TypeError(
            "provider_cognition_facts must be OpenAICompatibleCognitionCapabilityFacts"
        )
    if not isinstance(request, CognitionPassRequest):
        raise TypeError("request must be CognitionPassRequest")

    capabilities = normalize_cognition_execution_capabilities(
        structured_output=provider_cognition_facts.structured_output,
        streaming=provider_cognition_facts.streaming,
        reasoning_modes=provider_cognition_facts.reasoning_modes,
        bounded_reasoning_budget=provider_cognition_facts.bounded_reasoning_budget,
        decoding_controls=provider_cognition_facts.per_pass_decoding_controls,
    )
    resolution = resolve_pass_request(
        request=request,
        capabilities=capabilities,
    )
    if not resolution.unsupported_fields:
        raise ValueError(
            "unsupported cognition condition evidence cannot be created for a fully supported request"
        )

    identity = {
        "format_version": ACTUAL_MODEL_COGNITION_CAPABILITY_FORMAT_VERSION,
        "relaylm_commit": relaylm_commit,
        "condition_id": condition_id,
        "target": _target_identity_mapping(target),
        "provider_identity": provider_identity.to_mapping(),
        "provider_cognition_facts": provider_cognition_facts.to_mapping(),
        "normalized_cognition_capabilities": _capabilities_mapping(capabilities),
        "pass": pass_name,
        "request": _request_mapping(request),
        "resolution": resolution.to_mapping(),
        "unsupported_fields": list(resolution.unsupported_fields),
        "condition_status": "unsupported",
        "generation_executed": False,
    }
    evidence_id = ACTUAL_MODEL_COGNITION_CAPABILITY_ID_PREFIX + _stable_digest(identity)
    return ActualModelUnsupportedCognitionConditionEvidence(
        evidence_id=evidence_id,
        relaylm_commit=relaylm_commit,
        condition_id=condition_id,
        target=target,
        provider_identity=provider_identity,
        provider_cognition_facts=provider_cognition_facts,
        normalized_capabilities=capabilities,
        pass_name=pass_name,
        request=request,
        resolution=resolution,
    )


def write_unsupported_cognition_condition_evidence(
    *,
    evidence: ActualModelUnsupportedCognitionConditionEvidence,
    artifact_root: str | Path,
) -> Path:
    """Persist one immutable non-generation capability-evidence artifact."""

    if not isinstance(evidence, ActualModelUnsupportedCognitionConditionEvidence):
        raise TypeError(
            "evidence must be ActualModelUnsupportedCognitionConditionEvidence"
        )
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{evidence.evidence_id}.cognition-capability.json"
    payload = evidence.to_json() + "\n"
    if path.exists():
        return _resolve_existing(path=path, payload=payload)

    temporary = root / f".{evidence.evidence_id}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return _resolve_existing(path=path, payload=payload)
    except OSError as exc:
        raise ActualModelCognitionCapabilityArtifactError(
            f"cannot persist cognition capability evidence: {exc}"
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return path


def _target_identity_mapping(target: ActualModelArtifactTarget) -> dict[str, object]:
    return {
        "target_id": target.target_id,
        "target_revision": target.revision,
        "model_artifact": target.model_artifact_identity,
    }


def _capabilities_mapping(
    capabilities: CognitionExecutionCapabilities,
) -> dict[str, object]:
    return {
        "structured_output": capabilities.structured_output,
        "streaming": capabilities.streaming,
        "reasoning_modes": sorted(mode.value for mode in capabilities.reasoning_modes),
        "bounded_reasoning_budget": capabilities.bounded_reasoning_budget,
        "decoding_controls": sorted(
            control.value for control in capabilities.decoding_controls
        ),
    }


def _request_mapping(request: CognitionPassRequest) -> dict[str, object]:
    return {
        "reasoning_mode": (
            request.reasoning_mode.value if request.reasoning_mode is not None else None
        ),
        "reasoning_budget": request.reasoning_budget,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "max_output_tokens": request.max_output_tokens,
    }


def _stable_digest(mapping: dict[str, object]) -> str:
    payload = json.dumps(
        mapping,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_relaylm_commit(value: object) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(
            "relaylm_commit must be an exact lowercase 40-character Git SHA"
        )


def _resolve_existing(*, path: Path, payload: str) -> Path:
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ActualModelCognitionCapabilityArtifactError(
            f"cannot read existing cognition capability evidence: {exc}"
        ) from exc
    if existing != payload:
        raise ActualModelCognitionCapabilityArtifactError(
            "cognition capability evidence conflict: same evidence id has different bytes"
        )
    return path
