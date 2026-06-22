#!/usr/bin/env python3
"""Validate that active docs describe current bounded runtime behavior."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *anchors: str) -> None:
    body = text(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def forbid(path: str, *anchors: str) -> None:
    body = text(path)
    found = [anchor for anchor in anchors if anchor in body]
    assert not found, f"{path}: superseded anchors remain: {found!r}"


def main() -> None:
    require(
        "README.md",
        "implemented v0 path",
        "the v1 path supports",
        "client_instruction_source.v1",
    )
    require(
        "README_ja.md",
        "実装済みv0",
        "v1は正確な",
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
    require(
        "docs/architecture/current_target_migration_guide.md",
        "v1 explicit-provenance instruction-bearing apply",
        "C4b content-free RelaySCN-facing diagnostics projection",
        "runtime-private one-shot typed-parse source consumption",
        "B2 request-runtime internal-sentinel suppression",
        "C4 runtime transport-envelope wiring",
    )
    require(
        "docs/architecture/client_instruction_authority_contract.md",
        "client_history_exclusion_apply.v1",
        "Phase 5-C4b content-free RelaySCN-facing cache-hit diagnostics projection",
        "one-shot trusted runtime-private typed-parse source consumption",
        "Current Phase 5.5-B2 through C4 provides gated",
    )
    require(
        "docs/architecture/runtime_architecture.md",
        "## Mode contract",
        "## Routing modes",
        "## Runtime ownership non-goals",
    )
    require(
        "docs/config_schema.md",
        "relayctx_stream_unpack_dry_run_enabled",
        "relayctx_stream_unpack_max_buffer_chars",
        "relayctx_tts_adapter_handoff_runtime_enabled",
        "relayctx_tts_adapter_handoff_min_segment_chars",
    )
    require(
        "docs/smoke/client_history_exclusion_manual_smoke.md",
        "Actual v1 instruction-bearing apply",
        "Missing or invalid v1 provenance",
    )

    obsolete = (
        "instruction-bearing managed apply " + "is not implemented",
        "output-side Stream Unpack and TTS-safe segmentation " + "are not implemented",
    )
    active_docs = (
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
    )
    for path in active_docs:
        forbid(path, *obsolete)

    print("RelayLM documentation current-boundary smoke passed.")


if __name__ == "__main__":
    main()
