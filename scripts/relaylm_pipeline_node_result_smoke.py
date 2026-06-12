from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.pipeline_node_result import (
    PipelineNodeResult,
    build_pipeline_node_result,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _assert_minimal_result() -> None:
    result = build_pipeline_node_result(
        node_name="relayint_reference_repair",
        status="diagnostic_only",
    )

    require(isinstance(result, PipelineNodeResult), result)
    require(result.node_name == "relayint_reference_repair", result)
    require(result.status == "diagnostic_only", result)
    require(result.decision is None, result)
    require(result.blocked_reasons == [], result)
    require(result.diagnostics == {}, result)
    require(result.artifacts == [], result)

    serialized = result.to_log_dict()
    require(
        set(serialized)
        == {
            "node_name",
            "status",
            "decision",
            "blocked_reasons",
            "diagnostics",
            "artifacts",
        },
        serialized,
    )
    print("ok PipelineNodeResult minimal diagnostics-only shape")


def _assert_builder_copies_input_containers() -> None:
    blocked_reasons = ["scene_gate_blocked"]
    diagnostics = {"preflight_applicable": False}
    artifacts = [{"schema_version": "relayint.preflight.v0"}]

    result = build_pipeline_node_result(
        node_name="relayint_quick_clarification",
        status="blocked",
        decision="keep_backend_forwarding",
        blocked_reasons=blocked_reasons,
        diagnostics=diagnostics,
        artifacts=artifacts,
    )

    blocked_reasons.append("caller_mutated")
    diagnostics["caller_mutated"] = True
    artifacts.append({"schema_version": "caller.mutated.v0"})
    artifacts[0]["caller_mutated"] = True

    require(result.blocked_reasons == ["scene_gate_blocked"], result)
    require(result.diagnostics == {"preflight_applicable": False}, result)
    require(
        result.artifacts == [{"schema_version": "relayint.preflight.v0"}],
        result,
    )
    print("ok PipelineNodeResult builder detaches caller-owned containers")


def _assert_serialization_is_detached() -> None:
    result = build_pipeline_node_result(
        node_name="relayctx_repack",
        status="applied",
        decision="payload_repacked",
        blocked_reasons=("none",),
        diagnostics={"diagnostics_only": True},
        artifacts=({"schema_version": "relayctx.repack.v0"},),
    )

    serialized = result.to_log_dict()
    serialized["blocked_reasons"].append("serialized_mutation")
    serialized["diagnostics"]["serialized_mutation"] = True
    serialized["artifacts"][0]["serialized_mutation"] = True

    require(result.blocked_reasons == ["none"], result)
    require(result.diagnostics == {"diagnostics_only": True}, result)
    require(
        result.artifacts == [{"schema_version": "relayctx.repack.v0"}],
        result,
    )
    print("ok PipelineNodeResult serialization detaches log containers")


def _assert_frozen_record() -> None:
    result = build_pipeline_node_result(
        node_name="backend_forward",
        status="skipped",
        decision="diagnostics_only_test",
    )

    try:
        result.node_name = "mutated"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("PipelineNodeResult must remain frozen")

    require(result.node_name == "backend_forward", result)
    print("ok PipelineNodeResult top-level record is frozen")


def main() -> None:
    _assert_minimal_result()
    _assert_builder_copies_input_containers()
    _assert_serialization_is_detached()
    _assert_frozen_record()


if __name__ == "__main__":
    main()
