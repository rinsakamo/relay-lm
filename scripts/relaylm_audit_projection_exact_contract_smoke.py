from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.audit_projection import project_audit_metadata

UUID = "a1234567-89ab-4def-8123-abcdefabcdef"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def compile_artifact(state: str) -> dict[str, object]:
    return {
        "schema_version": "relaylm.compile_decision_dry_run.v0",
        "decision_id": f"{UUID}:compile-decision-dry-run",
        "plan_id": f"{UUID}:compile-plan",
        "result_id": f"{UUID}:compile-result",
        "decision_state": state,
        "selected_route": "relaylm-default",
        "selected_mode": "memory_light",
        "backend": "local_backend",
        "character_id": "default",
        "compiled_message_count": 2,
        "blocking_reasons": [],
        "omitted_block_ids": [],
        "token_budget_status": "within_budget",
        "apply_compiled_messages": state == "COMPILE_APPLY",
        "diagnostics_only": state == "COMPILE_DRY_RUN",
        "content_free": True,
    }


def main() -> int:
    for state in ("COMPILE_DRY_RUN", "COMPILE_APPLY"):
        projected = project_audit_metadata(
            {"compile_decision_dry_run": compile_artifact(state)}
        ).metadata["compile_decision_dry_run"]
        require(projected["decision_state"] == state, projected)
        require(projected["decision_id"] == f"{UUID}:compile-decision-dry-run", projected)
        require(projected["plan_id"] == f"{UUID}:compile-plan", projected)
        require(projected["result_id"] == f"{UUID}:compile-result", projected)
    print("ok compile apply and dry-run states retain scoped UUID identifiers")

    invalid_compile = compile_artifact("COMPILE_APPLY")
    invalid_compile["decision_id"] = "https://example.invalid/private"
    invalid_compile["plan_id"] = f"{UUID}:compile-result"
    invalid = project_audit_metadata(
        {"compile_decision_dry_run": invalid_compile}
    ).metadata["compile_decision_dry_run"]
    require("decision_id" not in invalid, invalid)
    require("plan_id" not in invalid, invalid)
    require(invalid["result_id"] == f"{UUID}:compile-result", invalid)
    print("ok compile identifiers require exact UUID scope and suffix")

    nodes = project_audit_metadata(
        {
            "pipeline_node_results": [
                {
                    "node_name": "relayint_reference_repair",
                    "status": "diagnostic_only",
                    "decision": "context_repair",
                    "diagnostics": {
                        "diagnostics_only": True,
                        "content_free": True,
                        "source_node_alias": "relayint_reference_repair",
                        "compatibility_source_node": "relayref",
                        "artifact_present": True,
                        "unresolved_reference_detected": True,
                        "apply_allowed": False,
                    },
                },
                {
                    "node_name": "relayint_reference_repair",
                    "status": "diagnostic_only",
                    "decision": "future_unregistered_mode",
                    "diagnostics": {
                        "diagnostics_only": True,
                        "content_free": True,
                        "source_node_alias": "relayint_reference_repair",
                        "compatibility_source_node": "relayref",
                        "artifact_present": True,
                        "unresolved_reference_detected": False,
                        "apply_allowed": False,
                    },
                },
            ]
        }
    ).metadata["pipeline_node_results"]
    require(nodes[0]["decision"] == "context_repair", nodes)
    require("decision" not in nodes[1], nodes)
    print("ok reference repair decisions use an exact enum")

    artifacts = project_audit_metadata(
        {
            "pipeline_node_results": [
                {
                    "node_name": "client_message_canonicalization",
                    "status": "diagnostic_only",
                    "decision": "current_request_evidence_identified",
                    "artifacts": [
                        {
                            "artifact_name": "client_message_canonicalization_dry_run",
                            "schema_version": "client_message_canonicalization_dry_run.v0",
                            "present": True,
                            "diagnostics_only": True,
                            "content_free": True,
                            "applied": False,
                            "runtime_private_source": True,
                            "read_only": True,
                        }
                    ],
                },
                {
                    "node_name": "client_instruction_identity",
                    "status": "diagnostic_only",
                    "decision": "instruction_identity_ready",
                    "artifacts": [
                        {
                            "artifact_name": "client_instruction_identity_runtime_summary",
                            "schema_version": "client_instruction_identity.v0",
                            "present": True,
                            "diagnostics_only": True,
                            "content_free": True,
                            "runtime_private_source": True,
                            "read_only": True,
                            "applied": False,
                        }
                    ],
                },
                {
                    "node_name": "relayctx_unpack",
                    "status": "diagnostic_only",
                    "decision": "plain_text_no_change",
                    "artifacts": [
                        {
                            "artifact_name": "relayctx_unpack_runtime_result",
                            "schema_version": "relayctx_unpack_runtime.v0",
                            "present": True,
                            "content_free": True,
                            "applied_to_response": False,
                            "candidate_present": False,
                            "persistence_allowed": False,
                            "diagnostics_only": True,
                        }
                    ],
                },
            ]
        }
    ).metadata["pipeline_node_results"]

    canonical = artifacts[0]["artifacts"][0]
    require("runtime_private_source" not in canonical, canonical)
    require("read_only" not in canonical, canonical)
    identity = artifacts[1]["artifacts"][0]
    require(identity["runtime_private_source"] is True, identity)
    require("read_only" not in identity, identity)
    unpack = artifacts[2]["artifacts"][0]
    require(unpack["candidate_present"] is False, unpack)
    require("diagnostics_only" not in unpack, unpack)
    print("ok artifact summaries enforce artifact-specific fields")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
