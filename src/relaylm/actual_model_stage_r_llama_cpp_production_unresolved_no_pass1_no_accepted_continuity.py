"""llama.cpp strategy for the #2715 no-accepted-Continuity discriminator."""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Sequence
from typing import Any

from relaylm.actual_model_production_continuity_overlay_diagnostic import (
    PRIMARY_SCENARIO_ID,
    PRIMARY_TURN_INDEX,
    load_retained_formation_binding,
)
from relaylm.actual_model_production_unresolved_no_pass1_no_accepted_continuity_diagnostic import (
    CONDITION_ID,
    DIAGNOSTIC_NAME,
    SCHEMA_VERSION,
    build_unresolved_no_pass1_no_accepted_continuity_request_body,
    parse_unresolved_no_pass1_no_accepted_continuity_completion,
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
    summary_filename=(
        "production-unresolved-no-pass1-no-accepted-continuity-t2-summary.json"
    ),
    diagnostic_artifact_dirname=(
        "production-unresolved-no-pass1-no-accepted-continuity"
    ),
    diagnostic_count_key=(
        "t2_unresolved_no_pass1_no_accepted_continuity_pass2_generation_count"
    ),
    description=(
        "Run fresh production T1 and T2 Pass 1, then exactly one retained-formation "
        "unresolved-only/no-Pass1 T2 Pass 2 that removes only the already-compiled "
        "accepted Continuity context prefix."
    ),
    scenario_id=PRIMARY_SCENARIO_ID,
    retained_turn_index=PRIMARY_TURN_INDEX,
)
SUMMARY_FILENAME = SPEC.summary_filename


class ProductionUnresolvedNoPass1NoAcceptedContinuityLlamaProvider(
    TwoTurnDiagnosticLlamaProvider
):
    """#2700 baseline plus one object-level accepted-Continuity context removal."""

    async def _generate_t2_diagnostic(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None,
        reasoning_request: OpenAICompatibleReasoningRequest | None,
    ) -> CognitionExtractionOutput:
        prepared = (
            build_unresolved_no_pass1_no_accepted_continuity_request_body(
                provider=self,
                extraction_input=extraction_input,
                pass_request=pass_request,
                binding=self.retained_binding,
                reasoning_request=reasoning_request,
            )
        )
        sequence = self.begin_diagnostic_generation()
        request_specs = (
            (
                "no-pass1-baseline",
                prepared.baseline.no_pass1_body,
                "baseline_no_pass1_request_sha256",
            ),
            (
                "no-pass1-retained-overlay",
                prepared.baseline.no_pass1_overlay_body,
                "baseline_no_pass1_overlay_request_sha256",
            ),
            (
                "no-pass1-no-accepted-continuity",
                prepared.treatment_body,
                "treatment_request_sha256",
            ),
            (
                "no-pass1-no-accepted-continuity-retained-overlay",
                prepared.treatment_overlay_body,
                "treatment_overlay_request_sha256",
            ),
        )
        retained_requests: list[tuple[str, Any, str]] = []
        for label, body, receipt_key in request_specs:
            path = (
                self.diagnostic_artifact_root
                / f"{sequence:04d}-t2-{label}-request.json"
            )
            _write_json_create_once(path, body)
            retained_requests.append((label, path, receipt_key))
            self.diagnostic_request_artifacts.append(path)

        baseline_input_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-baseline-cognitive-input.json"
        )
        treatment_input_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-treatment-cognitive-input.json"
        )
        removed_context_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-removed-accepted-continuity-context.json"
        )
        _write_json_create_once(
            baseline_input_path,
            prepared.baseline_cognitive_input,
        )
        _write_json_create_once(
            treatment_input_path,
            prepared.treatment_cognitive_input_serialized,
        )
        _write_json_create_once(
            removed_context_path,
            {"items": list(prepared.removed_context_items)},
        )
        self.diagnostic_request_artifacts.extend(
            (baseline_input_path, treatment_input_path, removed_context_path)
        )

        receipt_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-no-accepted-continuity-diff-receipt.json"
        )
        _write_json_create_once(receipt_path, prepared.diff_receipt)
        self.diagnostic_receipt_artifacts.append(receipt_path)

        binding_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-no-accepted-continuity-binding.json"
        )
        binding_payload: dict[str, Any] = {
            "format_version": HOST_FORMAT_VERSION,
            "diagnostic": DIAGNOSTIC_NAME,
            "retained_artifact": self.retained_binding.artifact_path,
            "retained_artifact_sha256": self.retained_binding.sha256,
            "retained_source_event_id": (
                prepared.baseline.baseline.retained_source_event_id
            ),
            "run_local_source_event_id": (
                prepared.baseline.baseline.run_local_source_event_id
            ),
            "provenance_rebound": True,
            "scenario_set_revision": self.retained_binding.scenario_set_revision,
            "subject_span": (
                prepared.baseline.baseline.model_overlay[0]["subject_span"]
            ),
            "unknown_evidence_span": (
                prepared.baseline.baseline.model_overlay[0][
                    "unknown_evidence_span"
                ]
            ),
            "model_overlay": list(
                prepared.baseline.baseline.model_overlay
            ),
            "continuity_expectation_supplied": False,
            "pass1_response_component_supplied": False,
            "accepted_continuity_context_supplied_to_treatment": False,
            "removed_accepted_continuity_context_count": (
                prepared.diff_receipt[
                    "removed_accepted_continuity_context_count"
                ]
            ),
            "baseline_cognitive_input_artifact": str(baseline_input_path),
            "baseline_cognitive_input_file_sha256": _sha256_file(
                baseline_input_path
            ),
            "treatment_cognitive_input_artifact": str(treatment_input_path),
            "treatment_cognitive_input_file_sha256": _sha256_file(
                treatment_input_path
            ),
            "removed_accepted_continuity_context_artifact": str(
                removed_context_path
            ),
            "removed_accepted_continuity_context_file_sha256": _sha256_file(
                removed_context_path
            ),
            "diff_receipt_artifact": str(receipt_path),
            "diff_receipt_file_sha256": _sha256_file(receipt_path),
            "removed_model_facing_responsibility": prepared.diff_receipt[
                "removed_model_facing_responsibility"
            ],
        }
        artifact_keys = {
            "no-pass1-baseline": "baseline_no_pass1",
            "no-pass1-retained-overlay": "baseline_no_pass1_overlay",
            "no-pass1-no-accepted-continuity": "treatment",
            "no-pass1-no-accepted-continuity-retained-overlay": (
                "treatment_overlay"
            ),
        }
        for label, path, receipt_key in retained_requests:
            artifact_key = artifact_keys[label]
            binding_payload[f"{artifact_key}_request_artifact"] = str(path)
            binding_payload[f"{artifact_key}_request_file_sha256"] = (
                _sha256_file(path)
            )
            binding_payload[f"{artifact_key}_request_sha256"] = (
                prepared.diff_receipt[receipt_key]
            )
        _write_json_create_once(binding_path, binding_payload)
        self.diagnostic_binding_artifacts.append(binding_path)

        envelope = await self._post_two_pass(
            body=prepared.treatment_overlay_body,
            boundary="extraction-unresolved-no-pass1-no-accepted-continuity",
        )
        raw_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-no-accepted-continuity-raw.json"
        )
        _write_json_create_once(raw_path, envelope)
        self.diagnostic_raw_artifacts.append(raw_path)
        return parse_unresolved_no_pass1_no_accepted_continuity_completion(
            envelope,
            cognitive_input=prepared.treatment_cognitive_input,
        )

    def diagnostic_result_fields(self) -> dict[str, Any]:
        fields = super().diagnostic_result_fields()
        fields.update(
            {
                "unresolved_no_pass1_no_accepted_continuity_request_artifacts": [
                    str(path) for path in self.diagnostic_request_artifacts
                ],
                "unresolved_no_pass1_no_accepted_continuity_binding_artifacts": [
                    str(path) for path in self.diagnostic_binding_artifacts
                ],
                "unresolved_no_pass1_no_accepted_continuity_receipt_artifacts": [
                    str(path) for path in self.diagnostic_receipt_artifacts
                ],
                "unresolved_no_pass1_no_accepted_continuity_raw_artifacts": [
                    str(path) for path in self.diagnostic_raw_artifacts
                ],
            }
        )
        return fields


def main(argv: Sequence[str] | None = None) -> int:
    return run_two_turn_diagnostic_host(
        argv,
        spec=SPEC,
        provider_type=ProductionUnresolvedNoPass1NoAcceptedContinuityLlamaProvider,
        retained_loader=load_retained_formation_binding,
    )


def _sha256_file(path: Any) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _zero_counts() -> dict[str, int]:
    return zero_counts(SPEC)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
