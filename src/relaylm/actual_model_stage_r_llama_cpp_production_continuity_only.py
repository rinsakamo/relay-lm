"""llama.cpp strategy for the #2624 production-context Continuity-only discriminator."""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Sequence
from typing import Any

from relaylm.actual_model_production_continuity_only_diagnostic import (
    CONDITION_ID,
    DIAGNOSTIC_NAME,
    SCHEMA_VERSION,
    build_continuity_only_extraction_request_body,
    parse_continuity_only_completion,
)
from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    PRIMARY_SCENARIO_ID,
    PRIMARY_TURN_INDEX,
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
from relaylm.providers.openai_compatible_reasoning import (
    OpenAICompatibleReasoningRequest,
)


SPEC = TwoTurnDiagnosticSpec(
    diagnostic_name=DIAGNOSTIC_NAME,
    condition_id=CONDITION_ID,
    schema_version=SCHEMA_VERSION,
    summary_filename="production-continuity-only-t2-summary.json",
    diagnostic_artifact_dirname="production-continuity-only",
    diagnostic_count_key="t2_continuity_only_pass2_generation_count",
    description=(
        "Run fresh production T1 and T2 Pass 1, replacing only T2 Pass 2 new-State "
        "proposal responsibility with the canonical Continuity-only diagnostic."
    ),
    scenario_id=PRIMARY_SCENARIO_ID,
    retained_turn_index=PRIMARY_TURN_INDEX,
)
SUMMARY_FILENAME = SPEC.summary_filename


class ProductionContinuityOnlyLlamaProvider(TwoTurnDiagnosticLlamaProvider):
    """Production-exact T1 plus one canonical Continuity-only retained T2 Pass 2."""

    async def _generate_t2_diagnostic(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None,
        reasoning_request: OpenAICompatibleReasoningRequest | None,
    ) -> CognitionExtractionOutput:
        prepared = build_continuity_only_extraction_request_body(
            provider=self,
            extraction_input=extraction_input,
            pass_request=pass_request,
            binding=self.retained_binding,
            reasoning_request=reasoning_request,
        )
        sequence = self.begin_diagnostic_generation()
        production_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-production-baseline-request.json"
        )
        production_overlay_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-production-retained-overlay-request.json"
        )
        continuity_only_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-continuity-only-baseline-request.json"
        )
        continuity_only_overlay_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-continuity-only-retained-overlay-request.json"
        )
        receipt_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-continuity-only-diff-receipt.json"
        )

        _write_json_create_once(production_path, prepared.production_body)
        _write_json_create_once(
            production_overlay_path,
            prepared.production_overlay_body,
        )
        _write_json_create_once(continuity_only_path, prepared.continuity_only_body)
        _write_json_create_once(
            continuity_only_overlay_path,
            prepared.continuity_only_overlay_body,
        )
        _write_json_create_once(receipt_path, prepared.diff_receipt)
        self.diagnostic_request_artifacts.extend(
            (
                production_path,
                production_overlay_path,
                continuity_only_path,
                continuity_only_overlay_path,
            )
        )
        self.diagnostic_receipt_artifacts.append(receipt_path)

        binding_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-continuity-only-binding.json"
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
                "production_request_artifact": str(production_path),
                "production_request_file_sha256": _sha256_file(production_path),
                "production_request_sha256": prepared.diff_receipt[
                    "production_request_sha256"
                ],
                "production_overlay_request_artifact": str(production_overlay_path),
                "production_overlay_request_file_sha256": _sha256_file(
                    production_overlay_path
                ),
                "production_overlay_request_sha256": prepared.diff_receipt[
                    "production_overlay_request_sha256"
                ],
                "continuity_only_request_artifact": str(continuity_only_path),
                "continuity_only_request_file_sha256": _sha256_file(
                    continuity_only_path
                ),
                "continuity_only_request_sha256": prepared.diff_receipt[
                    "continuity_only_request_sha256"
                ],
                "continuity_only_overlay_request_artifact": str(
                    continuity_only_overlay_path
                ),
                "continuity_only_overlay_request_file_sha256": _sha256_file(
                    continuity_only_overlay_path
                ),
                "continuity_only_overlay_request_sha256": prepared.diff_receipt[
                    "continuity_only_overlay_request_sha256"
                ],
                "diff_receipt_artifact": str(receipt_path),
                "diff_receipt_file_sha256": _sha256_file(receipt_path),
                "removed_model_facing_responsibility": prepared.diff_receipt[
                    "removed_model_facing_responsibility"
                ],
            },
        )
        self.diagnostic_binding_artifacts.append(binding_path)

        envelope = await self._post_two_pass(
            body=prepared.continuity_only_overlay_body,
            boundary="extraction-continuity-only",
        )
        raw_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-continuity-only-raw.json"
        )
        _write_json_create_once(raw_path, envelope)
        self.diagnostic_raw_artifacts.append(raw_path)
        return parse_continuity_only_completion(
            envelope,
            cognitive_input=extraction_input.cognitive_input,
        )

    def diagnostic_result_fields(self) -> dict[str, Any]:
        fields = super().diagnostic_result_fields()
        fields.update(
            {
                "continuity_only_request_artifacts": [
                    str(path) for path in self.diagnostic_request_artifacts
                ],
                "continuity_only_binding_artifacts": [
                    str(path) for path in self.diagnostic_binding_artifacts
                ],
                "continuity_only_receipt_artifacts": [
                    str(path) for path in self.diagnostic_receipt_artifacts
                ],
                "continuity_only_raw_artifacts": [
                    str(path) for path in self.diagnostic_raw_artifacts
                ],
            }
        )
        return fields


def main(argv: Sequence[str] | None = None) -> int:
    return run_two_turn_diagnostic_host(
        argv,
        spec=SPEC,
        provider_type=ProductionContinuityOnlyLlamaProvider,
        retained_loader=load_retained_formation_binding,
    )


def _sha256_file(path: Any) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _zero_counts() -> dict[str, int]:
    return zero_counts(SPEC)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
