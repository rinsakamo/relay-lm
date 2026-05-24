from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig
from relaylm.memory_adapter import build_memory_adapter_conflict_diagnostics
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _compile(cfg: dict, payload: dict) -> object:
    config = RelayLMConfig.model_validate(cfg)
    route = resolve_route(config, "relaylm-default")
    return compile_chat_payload_if_enabled(config=config, route=route, payload=payload)


def main() -> int:
    base_cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }

    cfg = copy.deepcopy(base_cfg)
    cfg["model_routes"]["relaylm-default"]["mode"] = "memory_light"
    before = copy.deepcopy(payload)
    compiled = _compile(cfg, payload)
    require(payload == before, payload)
    dry = compiled.memory_adapter_dry_run
    readiness = compiled.memory_adapter_readiness
    conflicts = compiled.memory_adapter_conflicts
    require(isinstance(dry, dict), dry)
    require(isinstance(readiness, dict), readiness)
    require(isinstance(conflicts, dict), conflicts)
    require(dry.get("adapter_name") == "local_seed", dry)
    require(dry.get("adapter_kind") == "seed_file", dry)
    require(dry.get("status") == "ok", dry)
    require(isinstance(dry.get("candidate_count"), int) and dry["candidate_count"] > 0, dry)
    require(isinstance(dry.get("candidate_ids"), list) and dry["candidate_ids"], dry)
    require(isinstance(dry.get("selected_candidate_ids"), list), dry)
    summary = compiled.memory_selection_summary
    require(summary is not None, compiled)
    require(dry.get("candidate_count") == summary.total_candidates, (dry, summary))
    require(dry.get("selected_candidate_ids") == summary.selected_memory_ids, (dry, summary))
    scope = dry.get("scope")
    require(isinstance(scope, dict), scope)
    require(scope.get("user_id") is None, scope)
    require(scope.get("user_type") is None, scope)
    require(scope.get("room_id") is None, scope)
    require(scope.get("scene_id") is None, scope)
    require(scope.get("session_id") is None, scope)
    require(dry.get("scope_isolation_status") == "partial_scope", dry)
    missing_default = dry.get("missing_scope_fields")
    require(isinstance(missing_default, list), missing_default)
    for field in ("user_id", "room_id", "scene_id", "session_id"):
        require(field in missing_default, missing_default)
    require(dry.get("scope_warning_count") == len(missing_default), dry)
    require(readiness.get("ready_for_adapter_evaluation") is True, readiness)
    require(readiness.get("ready_for_future_enforcement") is False, readiness)
    require(readiness.get("blocked_reason") == "partial_scope", readiness)
    require(readiness.get("non_enforcing") is True, readiness)
    require(readiness.get("adapter_status") == "ok", readiness)
    require(readiness.get("scope_isolation_status") == "partial_scope", readiness)
    require(readiness.get("missing_scope_fields") == missing_default, (readiness, missing_default))
    require(conflicts.get("conflict_status") == "warning", conflicts)
    require(conflicts.get("conflict_count") == 1, conflicts)
    require(conflicts.get("conflict_reasons") == ["partial_scope"], conflicts)
    require(conflicts.get("duplicate_candidate_ids") == [], conflicts)
    require(conflicts.get("duplicate_selected_ids") == [], conflicts)
    require(conflicts.get("selected_not_in_candidates") == [], conflicts)
    require(conflicts.get("scope_conflict_reasons") == ["partial_scope"], conflicts)
    expected_ids = [*summary.selected_memory_ids, *summary.excluded_disabled_ids, *summary.excluded_character_ids]
    require(dry.get("candidate_ids") == expected_ids, (dry, summary))
    print("ok memory adapter dry-run emits local seed contract")

    cfg_no_seed = copy.deepcopy(cfg)
    cfg_no_seed["characters"]["default"]["memory_seed_path"] = None
    compiled_no_seed = _compile(cfg_no_seed, payload)
    dry_no_seed = compiled_no_seed.memory_adapter_dry_run
    readiness_no_seed = compiled_no_seed.memory_adapter_readiness
    conflicts_no_seed = compiled_no_seed.memory_adapter_conflicts
    require(isinstance(dry_no_seed, dict), dry_no_seed)
    require(isinstance(readiness_no_seed, dict), readiness_no_seed)
    require(isinstance(conflicts_no_seed, dict), conflicts_no_seed)
    require(dry_no_seed.get("status") == "not_configured", dry_no_seed)
    require(readiness_no_seed.get("ready_for_adapter_evaluation") is False, readiness_no_seed)
    require(readiness_no_seed.get("blocked_reason") == "not_configured", readiness_no_seed)
    require(readiness_no_seed.get("non_enforcing") is True, readiness_no_seed)
    require("partial_scope" in conflicts_no_seed.get("conflict_reasons", []), conflicts_no_seed)
    print("ok memory adapter dry-run not_configured when seed path missing")

    cfg_scope = copy.deepcopy(cfg)
    cfg_scope["model_routes"]["relaylm-default"]["user_id"] = "user-001"
    cfg_scope["model_routes"]["relaylm-default"]["user_type"] = "member"
    cfg_scope["model_routes"]["relaylm-default"]["room_id"] = "room-abc"
    cfg_scope["model_routes"]["relaylm-default"]["scene_id"] = "scene-x"
    cfg_scope["model_routes"]["relaylm-default"]["session_id"] = "sess-42"
    compiled_scope = _compile(cfg_scope, payload)
    dry_scope = compiled_scope.memory_adapter_dry_run
    readiness_scope = compiled_scope.memory_adapter_readiness
    conflicts_scope = compiled_scope.memory_adapter_conflicts
    require(isinstance(dry_scope, dict), dry_scope)
    require(isinstance(readiness_scope, dict), readiness_scope)
    require(isinstance(conflicts_scope, dict), conflicts_scope)
    scope_with_identity = dry_scope.get("scope")
    require(isinstance(scope_with_identity, dict), scope_with_identity)
    require(scope_with_identity.get("user_id") == "user-001", scope_with_identity)
    require(scope_with_identity.get("user_type") == "member", scope_with_identity)
    require(scope_with_identity.get("room_id") == "room-abc", scope_with_identity)
    require(scope_with_identity.get("scene_id") == "scene-x", scope_with_identity)
    require(scope_with_identity.get("session_id") == "sess-42", scope_with_identity)
    require(dry_scope.get("scope_isolation_status") == "ok", dry_scope)
    require(dry_scope.get("missing_scope_fields") == [], dry_scope)
    require(dry_scope.get("scope_warning_count") == 0, dry_scope)
    require(compiled_scope.memory_selection_summary == compiled.memory_selection_summary, (compiled_scope, compiled))
    require(compiled_scope.stable_prefix_hash == compiled.stable_prefix_hash, (compiled_scope, compiled))
    require(readiness_scope.get("ready_for_adapter_evaluation") is True, readiness_scope)
    require(readiness_scope.get("ready_for_future_enforcement") is False, readiness_scope)
    require(readiness_scope.get("blocked_reason") is None, readiness_scope)
    require(readiness_scope.get("non_enforcing") is True, readiness_scope)
    require(readiness_scope.get("adapter_status") == "ok", readiness_scope)
    require(readiness_scope.get("scope_isolation_status") == "ok", readiness_scope)
    require(readiness_scope.get("missing_scope_fields") == [], readiness_scope)
    require(conflicts_scope.get("conflict_status") == "ok", conflicts_scope)
    require(conflicts_scope.get("conflict_count") == 0, conflicts_scope)
    require(conflicts_scope.get("conflict_reasons") == [], conflicts_scope)
    print("ok memory adapter dry-run includes optional scope identity without changing memory selection")

    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_err = copy.deepcopy(cfg)
        cfg_err["characters"]["default"]["memory_seed_path"] = str(Path(tmpdir) / "missing.yaml")
        compiled_err = _compile(cfg_err, payload)
        dry_err = compiled_err.memory_adapter_dry_run
        readiness_err = compiled_err.memory_adapter_readiness
        conflicts_err = compiled_err.memory_adapter_conflicts
        require(isinstance(dry_err, dict), dry_err)
        require(isinstance(readiness_err, dict), readiness_err)
        require(isinstance(conflicts_err, dict), conflicts_err)
        require(dry_err.get("status") == "load_error", dry_err)
        require(isinstance(dry_err.get("fallback_reason"), str), dry_err)
        require(dry_err.get("fallback_reason") == compiled_err.memory_fallback_reason, (dry_err, compiled_err))
        require(compiled_err.memory_fallback_reason is not None, compiled_err)
        require(dry_err.get("scope_isolation_status") == "partial_scope", dry_err)
        require(isinstance(dry_err.get("missing_scope_fields"), list), dry_err)
        require(dry_err.get("scope_warning_count") == len(dry_err.get("missing_scope_fields")), dry_err)
        require(readiness_err.get("ready_for_adapter_evaluation") is False, readiness_err)
        require(readiness_err.get("ready_for_future_enforcement") is False, readiness_err)
        require(readiness_err.get("blocked_reason") == "load_error", readiness_err)
        require(readiness_err.get("non_enforcing") is True, readiness_err)
        require(readiness_err.get("adapter_status") == "load_error", readiness_err)
        require("partial_scope" in conflicts_err.get("conflict_reasons", []), conflicts_err)
        print("ok memory adapter dry-run load_error preserves compile fallback behavior")

    # Stable prefix hash should not depend on adapter dry-run state.
    h_ok = compiled.stable_prefix_hash
    h_no_seed = compiled_no_seed.stable_prefix_hash
    require(h_ok == h_no_seed, (h_ok, h_no_seed))
    print("ok stable prefix hash unchanged by memory adapter dry-run state")

    pass_cfg = copy.deepcopy(base_cfg)
    pass_cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    compiled_pass = _compile(pass_cfg, payload)
    require(compiled_pass.memory_adapter_dry_run is None, compiled_pass)
    require(compiled_pass.memory_adapter_readiness is None, compiled_pass)
    require(compiled_pass.memory_adapter_conflicts is None, compiled_pass)
    print("ok pass-through keeps memory adapter dry-run unset")

    synthetic_dup_candidate = build_memory_adapter_conflict_diagnostics(
        {
            "candidate_ids": ["m1", "m1", "m2"],
            "selected_candidate_ids": ["m1"],
            "scope_isolation_status": "ok",
        }
    ).to_log_dict()
    require("duplicate_candidate_ids" in synthetic_dup_candidate.get("conflict_reasons", []), synthetic_dup_candidate)
    require(synthetic_dup_candidate.get("duplicate_candidate_ids") == ["m1"], synthetic_dup_candidate)
    print("ok memory adapter conflict detects duplicate candidate ids")

    synthetic_dup_selected = build_memory_adapter_conflict_diagnostics(
        {
            "candidate_ids": ["m1", "m2"],
            "selected_candidate_ids": ["m1", "m1"],
            "scope_isolation_status": "ok",
        }
    ).to_log_dict()
    require("duplicate_selected_ids" in synthetic_dup_selected.get("conflict_reasons", []), synthetic_dup_selected)
    require(synthetic_dup_selected.get("duplicate_selected_ids") == ["m1"], synthetic_dup_selected)
    print("ok memory adapter conflict detects duplicate selected ids")

    synthetic_missing = build_memory_adapter_conflict_diagnostics(
        {
            "candidate_ids": ["m1"],
            "selected_candidate_ids": ["m2"],
            "scope_isolation_status": "ok",
        }
    ).to_log_dict()
    require("selected_not_in_candidates" in synthetic_missing.get("conflict_reasons", []), synthetic_missing)
    require(synthetic_missing.get("selected_not_in_candidates") == ["m2"], synthetic_missing)
    print("ok memory adapter conflict detects selected ids missing in candidates")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
