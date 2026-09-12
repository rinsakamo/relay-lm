"""llama.cpp strategy for the #2593 production-overlay discriminator."""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Sequence
from typing import Any

from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    CONDITION_ID,
    DIAGNOSTIC_NAME,
    PRIMARY_SCENARIO_ID,
    PRIMARY_TURN_INDEX,
    SCHEMA_VERSION,
    assert_production_schema_unchanged,
    build_overlay_extraction_request_body,
    load_retained_formation_binding,
)
from relaylm.actual_model_stage_r_llama_cpp import _write_json_create_once
from relaylm.actual_model_stage_r_llama_cpp_two_turn_diagnostic import (
    HOST_FORMAT_VERSION,
    TwoTurnDiagnosticLlamaProvider,
    TwoTurnDiagnosticSpec,
    run_two_turn_diagnostic_host,
    zero_counts,
)
from relaylm.cognition_execution import (
    CognitionExtractionInput,
    CognitionExtractionOutput,
    CognitionPassRequest,
)
from relaylm.providers.openai_compatible import (
    _require_candidate_sources_in_cognitive_input,
)
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)
from relaylm.providers.openai_compatible_two_pass import _parse_extraction_completion


SPEC = TwoTurnDiagnosticSpec(
    diagnostic_name=DIAGNOSTIC_NAME,
    condition_id=CONDITION_ID,
    schema_version=SCHEMA_VERSION,
    summary_filename="production-continuity-overlay-t2-summary.json",
    diagnostic_artifact_dirname="production-continuity-overlay",
    diagnostic_count_key="t2_overlay_pass2_generation_count",
    description=(
        "Run fresh production T1 and T2 Pass 1, adding only the retained "
        "formation overlay to production T2 Pass 2."
    ),
    scenario_id=PRIMARY_SCENARIO_ID,
    retained_turn_index=PRIMARY_TURN_INDEX,
)
SUMMARY_FILENAME = SPEC.summary_filename


class ProductionContinuityOverlayLlamaProvider(TwoTurnDiagnosticLlamaProvider):
    """Production-exact T1 extraction and one overlaid production T2 extraction."""

    async def _generate_t2_diagnostic(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None,
        reasoning_request: OpenAICompatibleReasoningRequest | None,
    ) -> CognitionExtractionOutput:
        prepared = build_overlay_extraction_request_body(
            provider=self,
            extraction_input=extraction_input,
            pass_request=pass_request,
            binding=self.retained_binding,
            reasoning_request=reasoning_request,
        )
        assert_production_schema_unchanged(prepared)
        sequence = self.begin_diagnostic_generation()
        baseline_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-production-baseline-request.json"
        )
        request_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-retained-overlay-request.json"
        )
        _write_json_create_once(baseline_path, prepared.baseline_body)
        _write_json_create_once(request_path, prepared.body)
        self.diagnostic_request_artifacts.extend((baseline_path, request_path))

        binding_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-retained-overlay-binding.json"
        )
        _write_json_create_once(
            binding_path,
            {
                "format_version": HOST_FORMAT_VERSION,
                "diagnostic": DIAGNOSTIC_NAME,
                "retained_artifact": self.retained_binding.artifact_path,
                "retained_artifact_sha256": self.retained_binding.sha256,
                "retained_source_event_id": prepared.retained_source_event_id,
                "run_local_source_event_id": prepared.run_local_source_event_id,
                "provenance_rebound": True,
                "scenario_set_revision": self.retained_binding.scenario_set_revision,
                "subject_span": prepared.model_overlay[0]["subject_span"],
                "unknown_evidence_span": prepared.model_overlay[0][
                    "unknown_evidence_span"
                ],
                "model_overlay": list(prepared.model_overlay),
                "continuity_expectation_supplied": False,
                "baseline_request_artifact": str(baseline_path),
                "baseline_request_sha256": _sha256_file(baseline_path),
                "overlay_request_artifact": str(request_path),
                "overlay_request_sha256": _sha256_file(request_path),
            },
        )
        self.diagnostic_binding_artifacts.append(binding_path)

        envelope = await self._post_two_pass(
            body=prepared.body,
            boundary="extraction-overlay",
        )
        raw_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-retained-overlay-raw.json"
        )
        _write_json_create_once(raw_path, envelope)
        self.diagnostic_raw_artifacts.append(raw_path)
        output = _parse_extraction_completion(envelope)
        _require_candidate_sources_in_cognitive_input(
            output,
            extraction_input.cognitive_input,
        )
        return output

    @property
    def overlay_generation_count(self) -> int:
        return self.diagnostic_generation_count

    @property
    def overlay_request_artifacts(self) -> list[Any]:
        return self.diagnostic_request_artifacts

    @property
    def overlay_binding_artifacts(self) -> list[Any]:
        return self.diagnostic_binding_artifacts

    @property
    def overlay_raw_artifacts(self) -> list[Any]:
        return self.diagnostic_raw_artifacts

    def diagnostic_result_fields(self) -> dict[str, Any]:
        fields = super().diagnostic_result_fields()
        fields.update(
            {
                "overlay_request_artifacts": [
                    str(path) for path in self.diagnostic_request_artifacts
                ],
                "overlay_binding_artifacts": [
                    str(path) for path in self.diagnostic_binding_artifacts
                ],
                "overlay_raw_artifacts": [
                    str(path) for path in self.diagnostic_raw_artifacts
                ],
            }
        )
        return fields


def main(argv: Sequence[str] | None = None) -> int:
    return run_two_turn_diagnostic_host(
        argv,
        spec=SPEC,
        provider_type=ProductionContinuityOverlayLlamaProvider,
        retained_loader=load_retained_formation_binding,
    )


def _sha256_file(path: Any) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _zero_counts() -> dict[str, int]:
    """Compatibility surface for the existing evaluation-carriage regression."""

    return zero_counts(SPEC)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
