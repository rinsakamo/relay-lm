from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from relaylm.cognition_execution import CognitionExtractionOutput


COGNITION_EXECUTION_EVIDENCE_FORMAT_VERSION = 1
BUFFERED_EXECUTION_PATH = "buffered"
STREAMING_EXECUTION_PATH = "streaming"
SINGLE_PASS_OUTPUT_CONTRACT = "relaylm_cognitive_output:v1"
CONVERSATION_OUTPUT_CONTRACT = "relaylm_conversation_output:v1"
EXTRACTION_OUTPUT_CONTRACT = "relaylm_structured_cognition_output:v1"


class ShadowExtractionStatus(StrEnum):
    """Terminal status for a non-authoritative shadow extraction observation."""

    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CognitionExecutionEvidenceIdentity:
    """Provider-neutral identity of the resolved ordinary-turn execution topology."""

    mode: str
    execution_path: str
    canonical_output_contract: str | None
    conversation_output_contract: str | None
    extraction_output_contract: str | None
    shadow_output_contract: str | None
    canonical_mutation_source: str
    format_version: int = COGNITION_EXECUTION_EVIDENCE_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != COGNITION_EXECUTION_EVIDENCE_FORMAT_VERSION:
            raise ValueError(
                f"unsupported cognition execution evidence format: {self.format_version}"
            )
        if self.mode == "auto":
            raise ValueError("auto is unresolved policy and cannot be evidence identity")
        if self.mode not in {"single_pass", "two_pass", "shadow_two_pass"}:
            raise ValueError(f"unsupported cognition execution evidence mode: {self.mode}")
        if self.execution_path not in {
            BUFFERED_EXECUTION_PATH,
            STREAMING_EXECUTION_PATH,
        }:
            raise ValueError(f"unsupported execution_path: {self.execution_path}")
        if self.canonical_mutation_source not in {"single_pass", "pass2"}:
            raise ValueError(
                "canonical_mutation_source must be single_pass or pass2"
            )
        for name in (
            "canonical_output_contract",
            "conversation_output_contract",
            "extraction_output_contract",
            "shadow_output_contract",
        ):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be a non-empty string when present")
        self._validate_mode_shape()

    @classmethod
    def single_pass(cls, *, execution_path: str) -> "CognitionExecutionEvidenceIdentity":
        return cls(
            mode="single_pass",
            execution_path=execution_path,
            canonical_output_contract=SINGLE_PASS_OUTPUT_CONTRACT,
            conversation_output_contract=None,
            extraction_output_contract=None,
            shadow_output_contract=None,
            canonical_mutation_source="single_pass",
        )

    @classmethod
    def two_pass(cls, *, execution_path: str) -> "CognitionExecutionEvidenceIdentity":
        return cls(
            mode="two_pass",
            execution_path=execution_path,
            canonical_output_contract=None,
            conversation_output_contract=CONVERSATION_OUTPUT_CONTRACT,
            extraction_output_contract=EXTRACTION_OUTPUT_CONTRACT,
            shadow_output_contract=None,
            canonical_mutation_source="pass2",
        )

    @classmethod
    def shadow_two_pass(
        cls, *, execution_path: str
    ) -> "CognitionExecutionEvidenceIdentity":
        return cls(
            mode="shadow_two_pass",
            execution_path=execution_path,
            canonical_output_contract=SINGLE_PASS_OUTPUT_CONTRACT,
            conversation_output_contract=None,
            extraction_output_contract=EXTRACTION_OUTPUT_CONTRACT,
            shadow_output_contract=EXTRACTION_OUTPUT_CONTRACT,
            canonical_mutation_source="single_pass",
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "mode": self.mode,
            "execution_path": self.execution_path,
            "canonical_output_contract": self.canonical_output_contract,
            "conversation_output_contract": self.conversation_output_contract,
            "extraction_output_contract": self.extraction_output_contract,
            "shadow_output_contract": self.shadow_output_contract,
            "canonical_mutation_source": self.canonical_mutation_source,
        }

    def _validate_mode_shape(self) -> None:
        if self.mode == "single_pass":
            valid = (
                self.canonical_output_contract == SINGLE_PASS_OUTPUT_CONTRACT
                and self.conversation_output_contract is None
                and self.extraction_output_contract is None
                and self.shadow_output_contract is None
                and self.canonical_mutation_source == "single_pass"
            )
            if not valid:
                raise ValueError("single_pass identity has an incoherent contract shape")
            return
        if self.mode == "two_pass":
            valid = (
                self.canonical_output_contract is None
                and self.conversation_output_contract == CONVERSATION_OUTPUT_CONTRACT
                and self.extraction_output_contract == EXTRACTION_OUTPUT_CONTRACT
                and self.shadow_output_contract is None
                and self.canonical_mutation_source == "pass2"
            )
            if not valid:
                raise ValueError("two_pass identity has an incoherent contract shape")
            return
        valid = (
            self.canonical_output_contract == SINGLE_PASS_OUTPUT_CONTRACT
            and self.conversation_output_contract is None
            and self.extraction_output_contract == EXTRACTION_OUTPUT_CONTRACT
            and self.shadow_output_contract == EXTRACTION_OUTPUT_CONTRACT
            and self.canonical_mutation_source == "single_pass"
        )
        if not valid:
            raise ValueError("shadow_two_pass identity has an incoherent contract shape")


@dataclass(frozen=True, slots=True)
class ShadowExtractionEvidence:
    """Raw non-authoritative shadow proposal observation bound to one User Event."""

    execution_identity: CognitionExecutionEvidenceIdentity
    originating_event_id: str
    status: ShadowExtractionStatus
    output: CognitionExtractionOutput | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.execution_identity.mode != "shadow_two_pass":
            raise ValueError("shadow extraction evidence requires shadow_two_pass identity")
        if not isinstance(self.originating_event_id, str) or not self.originating_event_id.strip():
            raise ValueError("originating_event_id must not be empty")
        if self.status is ShadowExtractionStatus.COMPLETED:
            if not isinstance(self.output, CognitionExtractionOutput):
                raise TypeError("completed shadow evidence requires CognitionExtractionOutput")
            if self.failure_reason is not None:
                raise ValueError("completed shadow evidence must not carry failure_reason")
            return
        if self.output is not None:
            raise ValueError("failed shadow evidence must not carry output")
        if self.failure_reason is None or not self.failure_reason.strip():
            raise ValueError("failed shadow evidence requires failure_reason")
