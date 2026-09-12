"""llama.cpp strategy for the #2676 unresolved-only discriminator."""

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
from relaylm.actual_model_production_unresolved_only_diagnostic import (
    CONDITION_ID,
    DIAGNOSTIC_NAME,
    SCHEMA_VERSION,
    build_unresolved_only_extraction_request_body,
    parse_unresolved_only_completion,
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
    summary_filename="production-unresolved-only-t2-summary.json",
    diagnostic_artifact_dirname="production-unresolved-only",
    diagnostic_count_key="t2_unresolved_only_pass2_generation_count",
    description=(
        "Run fresh production T1 and T2 Pass 1, replacing only T2 Pass 2 "
        "multi-kind Continuity projection responsibility with the canonical "
        "unresolved-only diagnostic."
    ),
    scenario_id=PRIMARY_SCENARIO_ID,
    retained_turn_index=PRIMARY_TURN_INDEX,
)
SUMMARY_FILENAME = SPEC.summary_filename


class ProductionUnresolvedOnlyLlamaProvider(TwoTurnDiagnosticLlamaProvider):
    """Production-exact T1 plus one canonical unresolved-only retained T2 Pass 2."""

    async def _generate_t2_diagnostic(
        self,
        extraction_input: CognitionExtractionInput,
        *,
        pass_request: CognitionPassRequest | None,
        reasoning_request: OpenAICompatibleReasoningRequest | None,
    ) -> CognitionExtractionOutput:
        prepared = build_unresolved_only_extraction_request_body(
            provider=self,
            extraction_input=extraction_input,
            pass_request=pass_request,
            binding=self.retained_binding,
            reasoning_request=reasoning_request,
        )
        sequence = self.begin_diagnostic_generation()
        request_specs = (
            (
                "production-baseline",
                prepared.production_body,
                "production_request_sha256",
            ),
            (
                "production-retained-overlay",
                prepared.production_overlay_body,
                "production_overlay_request_sha256",
            ),
            (
                "continuity-only-baseline",
                prepared.continuity_only_body,
                "continuity_only_request_sha256",
            ),
            (
                "continuity-only-retained-overlay",
                prepared.continuity_only_overlay_body,
                "continuity_only_overlay_request_sha256",
            ),
            (
                "unresolved-only-baseline",
                prepared.unresolved_only_body,
                "unresolved_only_request_sha256",
            ),
            (
                "unresolved-only-retained-overlay",
                prepared.unresolved_only_overlay_body,
                "unresolved_only_overlay_request_sha256",
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

        receipt_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-unresolved-only-diff-receipt.json"
        )
        _write_json_create_once(receipt_path, prepared.diff_receipt)
        self.diagnostic_receipt_artifacts.append(receipt_path)

        binding_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-unresolved-only-binding.json"
        )
        binding_payload: dict[str, Any] = {
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
            "diff_receipt_artifact": str(receipt_path),
            "diff_receipt_file_sha256": _sha256_file(receipt_path),
            "removed_model_facing_responsibility": prepared.diff_receipt[
                "removed_model_facing_responsibility"
            ],
        }
        for label, path, receipt_key in retained_requests:
            artifact_key = {
                "production-baseline": "production",
                "production-retained-overlay": "production_overlay",
                "continuity-only-baseline": "continuity_only",
                "continuity-only-retained-overlay": "continuity_only_overlay",
                "unresolved-only-baseline": "unresolved_only",
                "unresolved-only-retained-overlay": "unresolved_only_overlay",
            }[label]
            binding_payload[f"{artifact_key}_request_artifact"] = str(path)
            binding_payload[f"{artifact_key}_request_file_sha256"] = _sha256_file(path)
            binding_payload[f"{artifact_key}_request_sha256"] = prepared.diff_receipt[
                receipt_key
            ]
        _write_json_create_once(binding_path, binding_payload)
        self.diagnostic_binding_artifacts.append(binding_path)

        envelope = await self._post_two_pass(
            body=prepared.unresolved_only_overlay_body,
            boundary="extraction-unresolved-only",
        )
        raw_path = (
            self.diagnostic_artifact_root
            / f"{sequence:04d}-t2-unresolved-only-raw.json"
        )
        _write_json_create_once(raw_path, envelope)
        self.diagnostic_raw_artifacts.append(raw_path)
        return parse_unresolved_only_completion(
            envelope,
            cognitive_input=extraction_input.cognitive_input,
        )

    def diagnostic_result_fields(self) -> dict[str, Any]:
        fields = super().diagnostic_result_fields()
        fields.update(
            {
                "unresolved_only_request_artifacts": [
                    str(path) for path in self.diagnostic_request_artifacts
                ],
                "unresolved_only_binding_artifacts": [
                    str(path) for path in self.diagnostic_binding_artifacts
                ],
                "unresolved_only_receipt_artifacts": [
                    str(path) for path in self.diagnostic_receipt_artifacts
                ],
                "unresolved_only_raw_artifacts": [
                    str(path) for path in self.diagnostic_raw_artifacts
                ],
            }
        )
        return fields


def main(argv: Sequence[str] | None = None) -> int:
    return run_two_turn_diagnostic_host(
        argv,
        spec=SPEC,
        provider_type=ProductionUnresolvedOnlyLlamaProvider,
        retained_loader=load_retained_formation_binding,
    )


def _sha256_file(path: Any) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _zero_counts() -> dict[str, int]:
    return zero_counts(SPEC)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
