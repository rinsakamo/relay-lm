#!/usr/bin/env python3
"""Smoke checks for client history exclusion preflight."""
from __future__ import annotations

import copy, json, sys, tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_history_exclusion_preflight import build_client_history_exclusion_preflight_node_result
import relaylm.client_history_exclusion_preflight as preflight
from relaylm.client_instruction_identity_runtime import client_instruction_identity_dependency_enabled
from relaylm.config import load_config
from relaylm.pipeline_context import PipelineContext, consume_active_pipeline_context
from relaylm.routing import resolve_route
from relaylm.trace_runtime import trace_runtime_event
from relaylm.diagnostics import RequestDiagnostics

SENTS = ("prior history sentinel", "current user text sentinel", "image/audio URL sentinel", "raw system instruction", "raw developer instruction", "normalized instruction", "SCENE_ROLE_SENTINEL_PRIVATE", "tool_call_secret", "tool args secret", "tool result secret", "exception sentinel")

def require(c: bool, m: Any) -> None:
    if not c: raise AssertionError(m)

def cfg(path: Path, *, enabled=True, canon=False, lookup=False, mode="memory_full", cache_root=None) -> None:
    c = yaml.safe_load((REPO_ROOT/"config.example.yaml").read_text())
    c["backends"]["local_backend"]["base_url"] = "http://127.0.0.1:9/v1"
    c["trace"] = {"enabled": True, "path": str(path.with_suffix('.jsonl'))}
    c["client_message_canonicalization_dry_run_enabled"] = canon
    c["client_history_exclusion_preflight_enabled"] = enabled
    c["client_instruction_extraction_dry_run_enabled"] = lookup
    c["client_instruction_cache_lookup_enabled"] = lookup
    c["client_instruction_cache_root"] = str(cache_root) if cache_root else None
    c["model_routes"]["relaylm-default"]["mode"] = mode
    path.write_text(yaml.safe_dump(c), encoding="utf-8")

def ctx(cp: Path, payload: dict[str, Any]) -> PipelineContext:
    c=load_config(str(cp)); r=resolve_route(c, payload.get("model", "relaylm-default"))
    return PipelineContext(request_id="r", run_id="u", original_payload=payload, forwarded_payload=copy.deepcopy(payload), route=r, stream_enabled=False)

def nodes(cp: Path, c: PipelineContext) -> list[dict[str, Any]]:
    conf=load_config(str(cp))
    d=RequestDiagnostics(request_id="r", character_id="default", route_model="relaylm-default", mode_applied=c.route.mode_applied, compiler_used=False)
    trace_runtime_event(config=conf, diagnostics=d, messages=[], response_text="ok")
    rec=json.loads(Path(conf.trace.path).read_text().strip().splitlines()[-1])
    return rec["metadata"].get("pipeline_node_results", [])

def no_leak(v: Any, extra=()) -> None:
    s=(json.dumps(v, ensure_ascii=False, sort_keys=True, default=str) if not isinstance(v, str) else v)+repr(v)
    for x in SENTS+tuple(extra):
        require(x not in s, x)

def user_payload(msgs): return {"model":"relaylm-default","messages":msgs,"stream":False}

def test_all() -> None:
  with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
    root=Path(td)
    # default off
    cp=root/"off.yaml"; cfg(cp, enabled=False)
    p=user_payload([{"role":"user","content":"current user text sentinel"}]); orig=copy.deepcopy(p)
    c=ctx(cp,p); require(c.client_history_exclusion_preflight_result is None, c); require(c.forwarded_payload==orig and c.original_payload==orig and c.last_mutating_step is None, c)
    require(build_client_history_exclusion_preflight_node_result(None) is None, "node")
    consume_active_pipeline_context(); print("ok default-off")
    # dependency activation + no instruction
    cp=root/"on.yaml"; cfg(cp, enabled=True, canon=False)
    p=user_payload([{"role":"user","content":"prior history sentinel"},{"role":"assistant","content":"prior history sentinel"},{"role":"user","content":"current user text sentinel"}]); orig=copy.deepcopy(p)
    c=ctx(cp,p); r=c.client_history_exclusion_preflight_result
    require(r and r.status=="ready" and r.instruction_resolution_mode=="none" and r.history_exclusion_apply_ready and r.excluded_message_count_candidate==2, r)
    require(r.current_user_message == p["messages"][-1] and r.current_user_message is not p["messages"][-1], r)
    p["messages"][-1]["content"]="changed"; require(r.current_user_message["content"]=="current user text sentinel", r.current_user_message)
    ns=nodes(cp,c); names=[n["node_name"] for n in ns]
    require(names[:1]==["client_message_canonicalization"] and "client_history_exclusion_preflight" in names, names)
    no_leak(ns); require(c.forwarded_payload==orig and c.last_mutating_step is None, c); print("ok dependency activation and no-instruction")
    # pass through
    cp=root/"pass.yaml"; cfg(cp, enabled=True, mode="pass_through")
    c=ctx(cp,user_payload([{"role":"user","content":"current user text sentinel"}])) ; r=c.client_history_exclusion_preflight_result
    require(r and r.status=="skipped" and r.current_user_message is None and "pass_through_route_exempt" in r.blocked_reasons, r); consume_active_pipeline_context(); print("ok pass-through")
    # cache hit/miss/blocked via monkeypatch lightweight objects
    from relaylm.client_message_canonicalization import build_client_message_canonicalization_dry_run
    art=build_client_message_canonicalization_dry_run(user_payload([{"role":"system","content":"raw system instruction"},{"role":"developer","content":"raw developer instruction"},{"role":"user","content":"current user text sentinel"}]), enabled=True, managed_route=True)
    class L: pass
    l=L(); l.status="hit"; r=preflight.build_client_history_exclusion_preflight(user_payload([{"role":"system","content":"raw system instruction"},{"role":"developer","content":"raw developer instruction"},{"role":"user","content":"current user text sentinel"}]), art, l, enabled=True, managed_route=True)
    require(r and r.status=="ready" and r.instruction_resolution_mode=="cache_hit" and r.raw_instruction_exclusion_candidate, r); no_leak(preflight.build_client_history_exclusion_preflight_node_result(r).to_log_dict()); print("ok cache hit")
    l.status="miss"; missp=user_payload([{"role":"system","content":"raw system instruction"},{"role":"user","content":"current user text sentinel"}]); missart=build_client_message_canonicalization_dry_run(missp, enabled=True, managed_route=True); r=preflight.build_client_history_exclusion_preflight(missp, missart, l, enabled=True, managed_route=True)
    require(r and r.status=="pending" and r.first_pass_evidence_required and not r.blocked_reasons, r); require(preflight.build_client_history_exclusion_preflight_node_result(r).decision=="client_instruction_first_pass_required", r); print("ok cache miss")
    l.status="blocked"; r=preflight.build_client_history_exclusion_preflight(missp, missart, l, enabled=True, managed_route=True)
    require(r and r.status=="blocked" and not r.history_exclusion_apply_ready, r); print("ok cache blocked")
    # multimodal detach/privacy
    mm=user_payload([{"role":"user","content":[{"type":"text","text":"current user text sentinel"},{"type":"image_url","image_url":{"url":"image/audio URL sentinel"}}]}]); art=build_client_message_canonicalization_dry_run(mm, enabled=True, managed_route=True); r=preflight.build_client_history_exclusion_preflight(mm, art, None, enabled=True, managed_route=True)
    require(r and r.status=="ready" and r.current_user_multimodal and r.current_user_message is not mm["messages"][0], r); r.current_user_message["content"][1]["image_url"]["url"]="mut"; require(mm["messages"][0]["content"][1]["image_url"]["url"]=="image/audio URL sentinel", mm); no_leak(preflight.build_client_history_exclusion_preflight_node_result(r).to_log_dict()); no_leak(r); print("ok multimodal detached privacy")
    # invalids
    for bad in [{"model":"relaylm-default"},{"model":"relaylm-default","messages":"x"}, user_payload([1]), user_payload([{"role":"assistant","content":"x"}]), user_payload([{"role":"user","content":"   "}]), user_payload([{"role":"user","content":[{"type":"text","text":""}]}])]:
      art=build_client_message_canonicalization_dry_run(bad, enabled=True, managed_route=True) if isinstance(bad.get("messages"), list) else None
      r=preflight.build_client_history_exclusion_preflight(bad, art, None, enabled=True, managed_route=True); require(r and r.status=="blocked", (bad,r))
    print("ok invalid sources")
    # active tool
    tp=user_payload([{"role":"user","content":"prior history sentinel"},{"role":"assistant","content":"x","tool_calls":[{"id":"tool_call_secret","function":{"arguments":"tool args secret"}}]},{"role":"tool","content":"tool result secret"},{"role":"user","content":"current user text sentinel"}])
    art=build_client_message_canonicalization_dry_run(tp, enabled=True, managed_route=True); r=preflight.build_client_history_exclusion_preflight(tp, art, None, enabled=True, managed_route=True)
    require(r and r.status=="blocked" and r.current_user_message is None and not r.history_exclusion_apply_ready, r); no_leak(preflight.build_client_history_exclusion_preflight_node_result(r).to_log_dict()); print("ok active tool transaction")
    # runtime exception
    cp=root/"ex.yaml"; cfg(cp, enabled=True)
    old=preflight.build_client_history_exclusion_preflight; preflight.build_client_history_exclusion_preflight=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("exception sentinel"))
    try:
      c=ctx(cp,user_payload([{"role":"user","content":"current user text sentinel"}])); r=c.client_history_exclusion_preflight_result
      require(r and r.status=="blocked" and r.blocked_reasons == ("history_exclusion_preflight_preparation_failed",), r); no_leak(preflight.build_client_history_exclusion_preflight_node_result(r).to_log_dict())
    finally: preflight.build_client_history_exclusion_preflight=old; consume_active_pipeline_context()
    print("ok runtime exception")
    # ordering with lookup enabled (empty instructions lookup source-blocked but preflight ready)
    cp=root/"ord.yaml"; cfg(cp, enabled=True, canon=False, lookup=True)
    c=ctx(cp,user_payload([{"role":"user","content":"current user text sentinel"}])) ; ns=nodes(cp,c); names=[n["node_name"] for n in ns]
    exp=["client_message_canonicalization","client_instruction_extraction","client_instruction_fingerprint","client_instruction_identity","client_instruction_cache","client_instruction_cache_lookup","client_history_exclusion_preflight"]
    require(names[:7]==exp, names); no_leak(ns); print("ok ordering and privacy")

if __name__ == "__main__":
    test_all(); print("client_history_exclusion_preflight_smoke passed")
