"""Exact field contracts layered onto the typed audit projection core.

The core module owns generic validator combinators and registry traversal. This
module installs the field-specific contracts that must stay aligned with runtime
producer shapes. Installation is deterministic and runs once during package
initialization, before request handling or concurrent projection calls.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_UUID_TEXT = (
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)


def install_audit_projection_contracts(ap: Any) -> None:
    """Install exact compile, node-decision, and artifact-summary contracts."""

    if getattr(ap, "_EXACT_AUDIT_CONTRACTS_INSTALLED", False):
        return

    ap.TOP_LEVEL_PROJECTORS["compile_decision_dry_run"] = ap._mapping(
        {
            "schema_version": ap._optional(ap._bounded_token),
            "decision_id": _scoped_uuid_id(ap, "compile-decision-dry-run"),
            "plan_id": _scoped_uuid_id(ap, "compile-plan"),
            "result_id": _scoped_uuid_id(ap, "compile-result"),
            "decision_state": ap._enum("COMPILE_DRY_RUN", "COMPILE_APPLY"),
            "selected_route": ap._bounded_token,
            "selected_mode": ap._bounded_token,
            "backend": ap._bounded_token,
            "character_id": ap._optional(ap._opaque_id),
            "compiled_message_count": ap._non_negative_int,
            "blocking_reasons": ap._REASON_LIST,
            "omitted_block_ids": ap._OPAQUE_ID_LIST,
            "token_budget_status": ap._bounded_token,
            "apply_compiled_messages": ap._bool,
            "diagnostics_only": ap._bool,
            "content_free": ap._optional(ap._bool),
        }
    )

    reference = ap.PIPELINE_NODE_PROJECTORS["relayint_reference_repair"]
    ap.PIPELINE_NODE_PROJECTORS["relayint_reference_repair"] = ap.NodeProjector(
        decisions=frozenset({"none", "context_repair", "suggest_reflect"}),
        diagnostics=reference.diagnostics,
        artifact_names=reference.artifact_names,
    )

    artifact_projectors = _artifact_projectors(ap)

    def exact_artifact_list(allowed_names: frozenset[str]):
        def validate(value: Any):
            if not isinstance(value, Sequence) or isinstance(
                value, (str, bytes, bytearray)
            ):
                return ap._drop()

            output: list[object] = []
            dropped = 0
            for item in value:
                if not isinstance(item, Mapping):
                    dropped += 1
                    continue
                artifact_name = item.get("artifact_name")
                if (
                    not isinstance(artifact_name, str)
                    or artifact_name not in allowed_names
                ):
                    dropped += 1
                    continue
                projector = artifact_projectors.get(artifact_name)
                if projector is None:
                    dropped += 1
                    continue
                clean, child_dropped = projector(item)
                dropped += child_dropped
                if clean is ap._DROP or clean is ap._OMIT:
                    dropped += 1
                    continue
                output.append(clean)
            return output, dropped

        return validate

    ap._artifact_list = exact_artifact_list
    ap._EXACT_AUDIT_CONTRACTS_INSTALLED = True


def _scoped_uuid_id(ap: Any, suffix: str):
    pattern = re.compile(rf"^{_UUID_TEXT}:{re.escape(suffix)}$", re.IGNORECASE)

    def validate(value: Any):
        if isinstance(value, str) and pattern.fullmatch(value):
            return ap._ok(value)
        return ap._drop()

    return validate


def _artifact_projectors(ap: Any) -> dict[str, Any]:
    common = {
        "diagnostics_only": ap._optional(ap._bool),
        "content_free": ap._optional(ap._bool),
        "applied": ap._optional(ap._bool),
    }

    def artifact(
        name: str,
        schema_version: str | None,
        *,
        extras: Mapping[str, Any] | None = None,
    ):
        fields: dict[str, Any] = {
            "artifact_name": ap._enum(name),
            "schema_version": (
                ap._optional(ap._enum(schema_version))
                if schema_version is not None
                else ap._optional(_reject_non_none(ap))
            ),
            "present": ap._bool,
            **common,
        }
        if extras:
            fields.update(extras)
        return ap._mapping(fields)

    return {
        "client_message_canonicalization_dry_run": artifact(
            "client_message_canonicalization_dry_run",
            "client_message_canonicalization_dry_run.v0",
        ),
        "client_instruction_extraction_dry_run": artifact(
            "client_instruction_extraction_dry_run",
            "client_instruction_extraction_dry_run.v0",
        ),
        "client_instruction_fingerprint_dry_run": artifact(
            "client_instruction_fingerprint_dry_run",
            "client_instruction_fingerprint_dry_run.v0",
        ),
        "client_instruction_identity_runtime_summary": artifact(
            "client_instruction_identity_runtime_summary",
            "client_instruction_identity.v0",
            extras={"runtime_private_source": ap._optional(ap._bool)},
        ),
        "client_instruction_cache_dry_run": artifact(
            "client_instruction_cache_dry_run",
            "client_instruction_cache_dry_run.v0",
            extras={"dry_run_only": ap._optional(ap._bool)},
        ),
        "client_instruction_cache_lookup_runtime_summary": artifact(
            "client_instruction_cache_lookup_runtime_summary",
            "client_instruction_cache_lookup_runtime.v0",
            extras={
                "runtime_private_source": ap._optional(ap._bool),
                "read_only": ap._optional(ap._bool),
            },
        ),
        "client_history_exclusion_preflight_summary": artifact(
            "client_history_exclusion_preflight_summary",
            "client_history_exclusion_preflight.v0",
            extras={
                "runtime_private_source": ap._optional(ap._bool),
                "payload_mutation_applied": ap._optional(ap._bool),
            },
        ),
        "relayref_artifact": artifact(
            "relayref_artifact",
            "relayref.dry_run_artifact.v0",
        ),
        "relayint_fast_path_dry_run": artifact(
            "relayint_fast_path_dry_run",
            "relayint_fast_path_dry_run.v0",
        ),
        "relayint_quick_clarification_preflight": artifact(
            "relayint_quick_clarification_preflight",
            "relayint_quick_clarification_preflight.v0",
        ),
        "relayint_quick_clarification_apply_plan": artifact(
            "relayint_quick_clarification_apply_plan",
            "relayint_quick_clarification_apply_plan.v0",
        ),
        "runtime_ctx_injection_result": artifact(
            "runtime_ctx_injection_result",
            "relaymem.runtime_ctx_injection_result.v0",
        ),
        "runtime_snippet_injection_result": artifact(
            "runtime_snippet_injection_result",
            "relaymem.runtime_snippet_injection_result.v0",
        ),
        "token_budget_truncation": artifact(
            "token_budget_truncation",
            None,
        ),
        "relayctx_short_term_runtime_injection_apply_result": artifact(
            "relayctx_short_term_runtime_injection_apply_result",
            "relayctx_short_term_runtime_injection_apply_result.v0",
        ),
        "relayctx_unpack_runtime_result": ap._mapping(
            {
                "artifact_name": ap._enum("relayctx_unpack_runtime_result"),
                "schema_version": ap._optional(
                    ap._enum("relayctx_unpack_runtime.v0")
                ),
                "present": ap._bool,
                "content_free": ap._optional(ap._bool),
                "applied_to_response": ap._optional(ap._bool),
                "candidate_present": ap._optional(ap._bool),
                "persistence_allowed": ap._optional(ap._bool),
            }
        ),
    }


def _reject_non_none(ap: Any):
    def validate(value: Any):
        return ap._drop()

    return validate
