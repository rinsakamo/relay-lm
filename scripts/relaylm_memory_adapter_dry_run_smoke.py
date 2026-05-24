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
    require(isinstance(dry, dict), dry)
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
    expected_ids = [*summary.selected_memory_ids, *summary.excluded_disabled_ids, *summary.excluded_character_ids]
    require(dry.get("candidate_ids") == expected_ids, (dry, summary))
    print("ok memory adapter dry-run emits local seed contract")

    cfg_no_seed = copy.deepcopy(cfg)
    cfg_no_seed["characters"]["default"]["memory_seed_path"] = None
    compiled_no_seed = _compile(cfg_no_seed, payload)
    dry_no_seed = compiled_no_seed.memory_adapter_dry_run
    require(isinstance(dry_no_seed, dict), dry_no_seed)
    require(dry_no_seed.get("status") == "not_configured", dry_no_seed)
    print("ok memory adapter dry-run not_configured when seed path missing")

    cfg_scope = copy.deepcopy(cfg)
    cfg_scope["model_routes"]["relaylm-default"]["user_id"] = "user-001"
    cfg_scope["model_routes"]["relaylm-default"]["user_type"] = "member"
    cfg_scope["model_routes"]["relaylm-default"]["room_id"] = "room-abc"
    cfg_scope["model_routes"]["relaylm-default"]["scene_id"] = "scene-x"
    cfg_scope["model_routes"]["relaylm-default"]["session_id"] = "sess-42"
    compiled_scope = _compile(cfg_scope, payload)
    dry_scope = compiled_scope.memory_adapter_dry_run
    require(isinstance(dry_scope, dict), dry_scope)
    scope_with_identity = dry_scope.get("scope")
    require(isinstance(scope_with_identity, dict), scope_with_identity)
    require(scope_with_identity.get("user_id") == "user-001", scope_with_identity)
    require(scope_with_identity.get("user_type") == "member", scope_with_identity)
    require(scope_with_identity.get("room_id") == "room-abc", scope_with_identity)
    require(scope_with_identity.get("scene_id") == "scene-x", scope_with_identity)
    require(scope_with_identity.get("session_id") == "sess-42", scope_with_identity)
    require(compiled_scope.memory_selection_summary == compiled.memory_selection_summary, (compiled_scope, compiled))
    require(compiled_scope.stable_prefix_hash == compiled.stable_prefix_hash, (compiled_scope, compiled))
    print("ok memory adapter dry-run includes optional scope identity without changing memory selection")

    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_err = copy.deepcopy(cfg)
        cfg_err["characters"]["default"]["memory_seed_path"] = str(Path(tmpdir) / "missing.yaml")
        compiled_err = _compile(cfg_err, payload)
        dry_err = compiled_err.memory_adapter_dry_run
        require(isinstance(dry_err, dict), dry_err)
        require(dry_err.get("status") == "load_error", dry_err)
        require(isinstance(dry_err.get("fallback_reason"), str), dry_err)
        require(dry_err.get("fallback_reason") == compiled_err.memory_fallback_reason, (dry_err, compiled_err))
        require(compiled_err.memory_fallback_reason is not None, compiled_err)
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
    print("ok pass-through keeps memory adapter dry-run unset")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
