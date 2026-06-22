#!/usr/bin/env python3
"""Fail when active documentation regresses to superseded runtime boundaries."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    text = read(path)
    for needle in needles:
        assert needle in text, f"{path}: missing current-boundary anchor: {needle!r}"


def forbid(path: str, *needles: str) -> None:
    text = read(path)
    for needle in needles:
        assert needle not in text, f"{path}: contains superseded boundary: {needle!r}"


def main() -> None:
    require(
        "README.md",
        "client_history_exclusion_apply.v0",
        "client_history_exclusion_apply.v1",
        "client_instruction_source.v1",
    )
    require(
        "README_ja.md",
        "client_history_exclusion_apply.v0",
        "client_history_exclusion_apply.v1",
        "client_instruction_source.v1",
    )

    require(
        "docs/PROJECT_STATUS.md",
        "Phase 5.5-C0 through C4",
        "C4b content-free RelaySCN-facing cache-hit diagnostics projection",
        "C5 runtime-private typed-parse validation",
        "UI-A0 through UI-A7",
        "GET /lab/api/settings",
        "GET /lab/api/characters",
    )
    forbid("docs/PROJECT_STATUS.md", "Status baseline `main` commit:")

    require(
        "docs/architecture/pipeline_implementation_plan.md",
        "UI-A7 local-only settings/characters read projections: complete",
        "latest-run and memory-outcome reads: pending",
        "Phase 6-B3",
    )
    forbid(
        "docs/architecture/pipeline_implementation_plan.md",
        "UI-A0 through UI-A6: complete as browser-local mock/presentation slices",
        "real /lab/api/* read and mutation integration: pending",
    )

    require(
        "docs/architecture/current_target_migration_guide.md",
        "v1 explicit-provenance instruction-bearing apply",
        "C4b content-free RelaySCN-facing diagnostics projection",
        "runtime-private one-shot typed-parse source consumption",
        "B2 request-runtime internal-sentinel suppression",
        "C4 runtime transport-envelope wiring",
    )
    forbid(
        "docs/architecture/current_target_migration_guide.md",
        "Phase 5-C4b may add",
        "Output-side Stream Unpack, internal-envelope suppression, safe segmentation, and TTS-aware forwarding remain target work",
    )

    require(
        "docs/architecture/client_instruction_authority_contract.md",
        "client_history_exclusion_apply.v1",
        "Phase 5-C4b content-free RelaySCN-facing cache-hit diagnostics projection",
        "one-shot runtime-private typed-parse source consumption",
        "Current Phase 5.5 provides gated stream-safety",
    )
    forbid(
        "docs/architecture/client_instruction_authority_contract.md",
        "Phase 5-C4a adds instruction-bearing managed apply",
        "cache projection applied=false until 5-C4b",
        "cache write applied=false until 5-C5",
    )

    require(
        "docs/config_schema.md",
        "relayctx_stream_unpack_dry_run_enabled",
        "relayctx_stream_unpack_dry_run_only",
        "relayctx_stream_unpack_max_buffer_chars",
        "relayctx_tts_adapter_handoff_runtime_enabled",
        "relayctx_tts_adapter_handoff_runtime_dry_run_only",
        "relayctx_tts_adapter_handoff_max_segment_chars",
        "relayctx_tts_adapter_handoff_min_segment_chars",
    )

    require(
        "docs/smoke/client_history_exclusion_manual_smoke.md",
        "Actual v1 instruction-bearing apply",
        "Missing or invalid v1 provenance",
    )
    forbid(
        "docs/smoke/client_history_exclusion_manual_smoke.md",
        "Instruction-bearing unsupported apply",
    )

    active_docs = [
        "README.md",
        "README_ja.md",
        "docs/PROJECT_STATUS.md",
        "docs/config_schema.md",
        "docs/openwebui_lmstudio_mvp.md",
        "docs/architecture/pipeline_implementation_plan.md",
        "docs/architecture/current_target_migration_guide.md",
        "docs/architecture/client_instruction_authority_contract.md",
        "docs/architecture/runtime_architecture.md",
        "docs/architecture/runtime_operational_requirements.md",
        "docs/architecture/open_llm_vtuber_current_target.md",
        "docs/architecture/open_llm_vtuber_integration.md",
        "docs/smoke/openwebui_lmstudio_manual_smoke.md",
        "docs/smoke/client_history_exclusion_manual_smoke.md",
        "docs/smoke/openwebui_lmstudio_troubleshooting.md",
    ]
    superseded_sentences = (
        "instruction-bearing managed apply is not implemented",
        "output-side Stream Unpack and TTS-safe segmentation are not implemented",
    )
    for path in active_docs:
        forbid(path, *superseded_sentences)

    print("RelayLM documentation current-boundary smoke passed.")


if __name__ == "__main__":
    main()
