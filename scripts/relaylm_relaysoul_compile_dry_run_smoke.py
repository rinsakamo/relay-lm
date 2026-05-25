from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.relaysoul_compile_dry_run import build_relaysoul_patch_compile_dry_run
from relaylm.relaysoul_patch import RelaySOULPatchCandidate, build_relaysoul_patch_candidate_dry_run
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _compiled_log(config: RelayLMConfig) -> dict[str, object]:
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    route = resolve_route(config, "relaylm-default")
    compiled = compile_chat_payload_if_enabled(config=config, route=route, payload=payload)
    return compiled.to_log_dict()


def main() -> int:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    cfg["characters"]["default"]["memory_seed_path"] = "examples/memory/default_memories.yaml"
    config = RelayLMConfig.model_validate(cfg)
    log = _compiled_log(config)

    patch_ok = build_relaysoul_patch_candidate_dry_run(
        RelaySOULPatchCandidate(
            candidate_id="cand-1",
            mode="calibration",
            target_files=["OUTPUT_POLICY.md", "SCENE_STATE.md"],
            feedback_ids=[],
            feedback_labels=[],
            freeform_notes_present=False,
        ),
        {"feedback_status": "ok", "stable_prefix_hash_present": True},
        {"budget_status": "ok", "source_budget_ratios": {}},
    ).to_log_dict()

    out = build_relaysoul_patch_compile_dry_run(patch_ok, log).to_log_dict()
    require(out["compile_dry_run_status"] == "ok", out)
    require("OUTPUT_POLICY.md" in out["stable_prefix_target_files"], out)
    require("SCENE_STATE.md" in out["dynamic_target_files"], out)
    require(out["stable_prefix_hash_present"] is True, out)
    print("ok compile dry-run integration")

    blocked = copy.deepcopy(patch_ok)
    blocked["dry_run_status"] = "blocked"
    out = build_relaysoul_patch_compile_dry_run(blocked, log).to_log_dict()
    require("patch_dry_run_blocked" in out["blocking_reasons"], out)

    out = build_relaysoul_patch_compile_dry_run(patch_ok, None).to_log_dict()
    require("missing_compiled_request_log" in out["blocking_reasons"], out)

    log_no_compiler = dict(log)
    log_no_compiler["compiler_used"] = False
    out = build_relaysoul_patch_compile_dry_run(patch_ok, log_no_compiler).to_log_dict()
    require("compiler_not_used" in out["blocking_reasons"], out)

    unsupported = copy.deepcopy(patch_ok)
    unsupported["candidate"] = dict(unsupported["candidate"])
    unsupported["candidate"]["target_files"] = ["UNKNOWN.md"]
    out = build_relaysoul_patch_compile_dry_run(unsupported, log).to_log_dict()
    require("unsupported_target_file" in out["blocking_reasons"], out)

    missing_block = copy.deepcopy(patch_ok)
    missing_block["candidate"] = dict(missing_block["candidate"])
    missing_block["candidate"]["target_files"] = ["STABLE_MEMORY_SUMMARY.md"]
    out = build_relaysoul_patch_compile_dry_run(missing_block, log).to_log_dict()
    require("target_block_missing_from_compile" in out["warning_reasons"], out)
    print("ok missing target block warning")

    empty_observed = copy.deepcopy(log)
    empty_observed["context_block_summary"] = dict(empty_observed.get("context_block_summary") or {})
    empty_observed["context_block_summary"]["block_ids"] = []
    empty_target = copy.deepcopy(patch_ok)
    empty_target["candidate"] = dict(empty_target["candidate"])
    empty_target["candidate"]["target_files"] = ["OUTPUT_POLICY.md"]
    out = build_relaysoul_patch_compile_dry_run(empty_target, empty_observed).to_log_dict()
    require("character_output_policy" in out["missing_target_block_ids"], out)
    require("target_block_missing_from_compile" in out["warning_reasons"], out)
    print("ok empty observed block_ids treated as missing")

    budget_warn_log = copy.deepcopy(log)
    budget_warn_log["persona_source_budget_diagnostics"] = {
        "budget_status": "warning",
    }
    out = build_relaysoul_patch_compile_dry_run(patch_ok, budget_warn_log).to_log_dict()
    require(out["persona_budget_warning"] is True, out)
    require("persona_source_budget_warning" in out["warning_reasons"], out)

    warn_patch = copy.deepcopy(patch_ok)
    warn_patch["dry_run_status"] = "warning"
    out = build_relaysoul_patch_compile_dry_run(warn_patch, log).to_log_dict()
    require("patch_dry_run_warning" in out["warning_reasons"], out)

    require("patch_text" not in str(out), out)
    print("ok content-free artifact")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
