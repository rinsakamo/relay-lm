#!/usr/bin/env python3
"""Validate that active docs retain the current bounded-runtime milestones."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *anchors: str) -> None:
    body = read_text(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing current-boundary anchors: {missing!r}"


def forbid(path: str, *anchors: str) -> None:
    body = read_text(path)
    present = [anchor for anchor in anchors if anchor in body]
    assert not present, f"{path}: superseded boundary remains: {present!r}"


def main() -> None:
    require("README.md", "client_instruction_source.v1", "implemented v0 path")
    require("README_ja.md", "client_instruction_source.v1", "実装済みv0")

    require(
        "docs/PROJECT_STATUS.md",
        "Phase 5.5-C0 through C4",
        "UI-A0 through UI-A7",
        "GET /lab/api/settings",
        "GET /lab/api/characters",
        "C1-0 through C1-5 complete",
        "C2 one-job claim/rehydrate/execute adapter: complete",
        "next-turn recall and scope isolation",
        "durably enqueued jobs",
    )
    forbid(
        "docs/PROJECT_STATUS.md",
        "Status baseline `main` commit:",
        "C1-2 one-already-claimed-job worker execution is not yet on `main`",
        "one-job claim/rehydrate/execute adapter     next integration boundary",
    )

    require(
        "docs/architecture/pipeline_implementation_plan.md",
        "UI-A0 through UI-A7: complete",
        "latest-run and memory-outcome reads: pending",
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter: complete",
        "next-turn recall and scope isolation: next",
    )

    require(
        "docs/architecture/relaymem_slp_current_target.md",
        "C1-5 durable claim-independent protected source and restart rehydration",
        "C2 one-job claim/rehydrate/execute adapter",
        "next-turn recall and scope isolation",
        "pre-enqueue background-finalizer crash window",
    )

    require(
        "docs/architecture/current_target_migration_guide.md",
        "v1 explicit-provenance instruction-bearing apply",
        "C4b content-free RelaySCN-facing diagnostics projection",
        "B2 request-runtime internal-sentinel suppression",
        "C4 runtime transport-envelope wiring",
    )

    require(
        "docs/architecture/client_instruction_authority_contract.md",
        "client_history_exclusion_apply.v1",
        "Phase 5-C4b content-free RelaySCN-facing projection diagnostics",
        "Current Phase 5.5-B2 through C4",
        "## Target cache entry contract",
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

    forbid(
        "docs/smoke/openwebui_lmstudio_manual_smoke.md",
        "instruction-bearing managed apply is not implemented",
    )
    forbid(
        "docs/smoke/openwebui_lmstudio_troubleshooting.md",
        "output-side Stream Unpack and TTS-safe segmentation are not implemented",
    )
    forbid(
        "docs/architecture/current_target_migration_guide.md",
        "Phase 5-C4b may add",
    )

    print("RelayLM documentation current-boundary smoke passed.")


if __name__ == "__main__":
    main()
