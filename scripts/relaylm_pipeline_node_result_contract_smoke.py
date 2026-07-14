#!/usr/bin/env python3
"""Pin docs/contracts/pipeline_node_result_contract.md against current code.

Recomputes the current PipelineNodeResult shape, PIPELINE_NODE_PROJECTORS
node-name set, best-effort exception boundary, and RelayREF non-dependency
directly from source (AST + regex + actual calls), rather than trusting the
contract's own prose.
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CONTRACT_PATH = REPO_ROOT / "docs/contracts/pipeline_node_result_contract.md"
RESULT_PATH = REPO_ROOT / "relaylm/pipeline_node_result.py"
CONTEXT_PATH = REPO_ROOT / "relaylm/pipeline_context.py"
ADAPTER_PATH = REPO_ROOT / "relaylm/pipeline_node_adapter.py"
TRACE_RUNTIME_PATH = REPO_ROOT / "relaylm/trace_runtime.py"
AUDIT_PROJECTION_PATH = REPO_ROOT / "relaylm/audit_projection.py"
RELAYRUN_PATH = REPO_ROOT / "relaylm/relayrun.py"

from relaylm.config import BackendConfig
from relaylm.pipeline_context import PipelineContext
from relaylm.pipeline_node_result import (
    PipelineNodeResult,
    build_pipeline_node_result,
)
from relaylm.routing import ResolvedRoute


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _module_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _module_ast(path: Path) -> ast.Module:
    return ast.parse(_module_source(path))


def _literal_status_values() -> set[str]:
    tree = _module_ast(RESULT_PATH)
    for node in ast.walk(tree):
        target = node.targets[0] if isinstance(node, ast.Assign) else getattr(node, "target", None)
        if getattr(target, "id", None) == "PipelineNodeStatus":
            subscript = node.value
            require(isinstance(subscript, ast.Subscript), "PipelineNodeStatus is not a Literal[...] subscript")
            elt = subscript.slice
            values = elt.elts if isinstance(elt, ast.Tuple) else [elt]
            return {value.value for value in values}
    raise AssertionError("PipelineNodeStatus definition not found")


def _dataclass_field_names() -> list[str]:
    tree = _module_ast(RESULT_PATH)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PipelineNodeResult":
            is_frozen_dataclass = any(
                isinstance(decorator, ast.Call)
                and getattr(decorator.func, "id", None) == "dataclass"
                and any(
                    keyword.arg == "frozen" and getattr(keyword.value, "value", None) is True
                    for keyword in decorator.keywords
                )
                for decorator in node.decorator_list
            )
            require(is_frozen_dataclass, "PipelineNodeResult is no longer @dataclass(frozen=True)")
            return [
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            ]
    raise AssertionError("PipelineNodeResult class definition not found")


def _pipeline_node_projector_names() -> list[str]:
    tree = _module_ast(AUDIT_PROJECTION_PATH)
    for node in ast.walk(tree):
        target = node.targets[0] if isinstance(node, ast.Assign) else getattr(node, "target", None)
        if getattr(target, "id", None) == "PIPELINE_NODE_PROJECTORS":
            require(isinstance(node.value, ast.Dict), "PIPELINE_NODE_PROJECTORS is not a dict literal")
            return [key.value for key in node.value.keys]
    raise AssertionError("PIPELINE_NODE_PROJECTORS definition not found")


def _record_node_result_source() -> str:
    source = _module_source(CONTEXT_PATH)
    match = re.search(
        r"def record_node_result\(self, result: PipelineNodeResult\) -> None:\n(?:.*\n)*?"
        r"(?=\n    def |\Z)",
        source,
    )
    require(match is not None, "record_node_result() not found")
    return match.group(0)


def _assert_status_enum() -> None:
    expected = {"applied", "skipped", "blocked", "failed", "diagnostic_only"}
    actual = _literal_status_values()
    require(actual == expected, f"PipelineNodeStatus drift: {sorted(actual)}")
    contract = _module_source(CONTRACT_PATH)
    for status in expected:
        require(f'"{status}"' in contract, f"contract omits status {status!r}")
    print("ok PipelineNodeStatus matches exactly: applied, skipped, blocked, failed, diagnostic_only")


def _assert_field_shape() -> None:
    expected = ["node_name", "status", "decision", "blocked_reasons", "diagnostics", "artifacts"]
    actual = _dataclass_field_names()
    require(actual == expected, f"PipelineNodeResult field order/shape drift: {actual}")
    print("ok PipelineNodeResult field shape matches exactly and dataclass is frozen (AST-verified)")


def _assert_frozen_at_runtime() -> None:
    result = build_pipeline_node_result(node_name="contract_smoke_probe", status="diagnostic_only")
    try:
        result.node_name = "mutated"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("PipelineNodeResult accepted a top-level field mutation")
    print("ok PipelineNodeResult is frozen at runtime")


def _assert_builder_detaches_top_level_containers() -> None:
    blocked_reasons = ["preflight_missing"]
    artifacts = [{"schema_version": "relayint_quick_clarification_apply_plan.v0"}]
    result = build_pipeline_node_result(
        node_name="contract_smoke_probe",
        status="blocked",
        blocked_reasons=blocked_reasons,
        artifacts=artifacts,
    )
    blocked_reasons.append("caller_mutated_after_build")
    artifacts.append({"schema_version": "caller.mutated.v0"})
    require(result.blocked_reasons == ["preflight_missing"], result.blocked_reasons)
    require(len(result.artifacts) == 1, result.artifacts)
    print("ok build_pipeline_node_result() detaches caller-owned top-level containers")


def _assert_to_log_dict_is_shallow_not_deep() -> None:
    nested = {"inner": ["still_shared"]}
    result = build_pipeline_node_result(
        node_name="contract_smoke_probe",
        status="diagnostic_only",
        diagnostics={"nested_container": nested},
    )
    logged = result.to_log_dict()

    # Top-level detachment: mutating the returned dict's own keys must not
    # reach back into the frozen record.
    logged["blocked_reasons"] = ["mutated_top_level"]
    require(result.blocked_reasons == [], result.blocked_reasons)

    # Shallow detachment: to_log_dict() copies one level only, so a nested
    # mutable value reached through the log dict is the *same* object the
    # frozen record's diagnostics dict holds -- this is deliberate current
    # behavior per the contract, not full immutability.
    logged["diagnostics"]["nested_container"]["inner"].append("mutated_via_log_dict")
    require(
        result.diagnostics["nested_container"]["inner"] == ["still_shared", "mutated_via_log_dict"],
        "to_log_dict() is unexpectedly deep-copying nested diagnostics values; "
        "update the contract if this changed intentionally",
    )
    print("ok to_log_dict() detachment is shallow (top-level only), matching the contract")


def _assert_record_node_result_has_no_local_exception_handling() -> None:
    source = _record_node_result_source()
    require("try" not in source and "except" not in source, source)
    require(source.count("\n") <= 4, f"record_node_result() grew unexpectedly: {source!r}")
    print("ok PipelineContext.record_node_result() is a bare append with no local exception handling")


def _assert_best_effort_boundary_is_in_trace_runtime() -> None:
    trace_source = _module_source(TRACE_RUNTIME_PATH)
    require(
        "def trace_runtime_event(" in trace_source,
        "trace_runtime_event() entry point missing",
    )
    require(
        "def _consume_pipeline_node_results(" in trace_source,
        "_consume_pipeline_node_results() missing",
    )
    event_slice = trace_source.split("def trace_runtime_event(", 1)[1].split("\ndef ", 1)[0]
    require("except Exception:" in event_slice, "trace_runtime_event() lost its except-Exception boundary")
    consume_slice = trace_source.split("def _consume_pipeline_node_results(", 1)[1].split("\ndef ", 1)[0]
    require(
        "except Exception:" in consume_slice,
        "_consume_pipeline_node_results() lost its except-Exception boundary",
    )
    print("ok best-effort exception handling lives in relaylm/trace_runtime.py, not in record_node_result()")


def _route() -> ResolvedRoute:
    return ResolvedRoute(
        route_model="relaylm-default",
        backend_name="local_backend",
        backend=BackendConfig(base_url="http://127.0.0.1:1234/v1"),
        backend_model="local-model",
        character_id=None,
        mode_requested="pass_through",
        mode_applied="pass_through",
        cache_namespace=None,
        memory_namespace=None,
    )


def _context() -> PipelineContext:
    payload = {"model": "relaylm-default", "messages": [], "stream": False}
    return PipelineContext(
        request_id="contract-smoke-request",
        run_id="contract-smoke-run",
        original_payload=payload,
        forwarded_payload=dict(payload),
        route=_route(),
        stream_enabled=False,
    )


def _assert_ordering() -> None:
    context = _context()
    for name in ("first_node", "second_node", "third_node"):
        context.record_node_result(build_pipeline_node_result(node_name=name, status="diagnostic_only"))
    require(
        [result.node_name for result in context.node_results] == ["first_node", "second_node", "third_node"],
        [result.node_name for result in context.node_results],
    )
    require(
        [entry["node_name"] for entry in context.node_results_to_log_dicts()]
        == ["first_node", "second_node", "third_node"],
        context.node_results_to_log_dicts(),
    )

    other_context = _context()
    require(
        other_context.node_results == [],
        "a fresh PipelineContext instance is not starting with an empty node_results list",
    )
    print("ok PipelineContext.node_results preserves append order and is request-local per instance")


def _assert_current_node_name_set() -> None:
    expected = {
        "client_message_canonicalization",
        "client_instruction_extraction",
        "client_instruction_fingerprint",
        "client_instruction_identity",
        "client_instruction_cache",
        "client_instruction_cache_lookup",
        "client_instruction_relayscn_projection",
        "client_history_exclusion_preflight",
        "relayint_reference_repair",
        "relayint_reference_intent",
        "client_history_exclusion_apply",
        "relayint_quick_clarification",
        "relayctx_repack",
        "relayctx_unpack",
        "relaymem_slp_finalized_turn_source",
        "relaymem_slp_runtime_enqueue",
    }
    actual = set(_pipeline_node_projector_names())
    require(len(expected) == 16, f"expected set itself drifted from 16: {len(expected)}")
    require(actual == expected, f"PIPELINE_NODE_PROJECTORS node-name set drift: {sorted(actual)}")

    contract = _module_source(CONTRACT_PATH)
    for name in expected:
        require(name in contract, f"contract omits current node name: {name}")
    print(f"ok PIPELINE_NODE_PROJECTORS node-name set matches exactly ({len(expected)} names, set-compared)")


def _assert_relayint_reference_repair_is_compatibility_label_only() -> None:
    adapter_source = _module_source(ADAPTER_PATH)
    require(
        '"relayint_reference_repair"' in adapter_source,
        "relayint_reference_repair node name missing from pipeline_node_adapter.py",
    )
    require(
        "relayref_artifact" not in adapter_source,
        "pipeline_node_adapter.py reintroduced a live relayref_artifact data dependency",
    )
    require(
        '"compatibility_source_node": "relayref"' in adapter_source,
        "relayint_reference_repair no longer carries its fixed relayref compatibility label",
    )

    projection_source = _module_source(AUDIT_PROJECTION_PATH)
    require(
        'frozenset({"relayref_artifact", "relayint_intent_artifact"})' in projection_source,
        "relayint_reference_repair NodeProjector artifact_names allowlist changed unexpectedly",
    )
    print(
        "ok relayint_reference_repair carries only a fixed relayref compatibility label; "
        "no live relayref_artifact data dependency exists in the adapter"
    )


def _assert_no_routing_or_relayrun_consumption() -> None:
    relayrun_source = _module_source(RELAYRUN_PATH)
    require("node_results" not in relayrun_source, "relaylm/relayrun.py now references node_results")
    require(
        "PipelineNodeResult" not in relayrun_source,
        "relaylm/relayrun.py now references PipelineNodeResult",
    )
    print("ok relaylm/relayrun.py does not consume node_results or PipelineNodeResult")


def main() -> None:
    _assert_status_enum()
    _assert_field_shape()
    _assert_frozen_at_runtime()
    _assert_builder_detaches_top_level_containers()
    _assert_to_log_dict_is_shallow_not_deep()
    _assert_record_node_result_has_no_local_exception_handling()
    _assert_best_effort_boundary_is_in_trace_runtime()
    _assert_ordering()
    _assert_current_node_name_set()
    _assert_relayint_reference_repair_is_compatibility_label_only()
    _assert_no_routing_or_relayrun_consumption()
    print("PipelineNodeResult contract smoke passed")


if __name__ == "__main__":
    main()
