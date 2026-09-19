"""Repeatable non-citable smoke for the repaired Hindsight comparator route.

This diagnostic intentionally sits outside the scientific campaign transaction.
It uses repository-owned synthetic text only, never opens a ScientificSpendLedger,
and never writes into a scientific owner's durable roots.  Its purpose is to
exercise the live retain -> consolidation -> recall transport repaired for
#2985 before a one-shot external-qualification campaign consumes benchmark
work.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from tools.v1_external_qualification_llama_cpp_campaign import (
    CampaignCarriageError,
    HindsightDeploymentSession,
    HindsightHealthAttestation,
    HindsightHistorySession,
    HindsightLifecycleSpec,
    LlamaCppLaunchSpec,
    LiveLaunchSession,
    _hindsight_axis_bank_id,
    _hindsight_owner_deployment_id,
    _hindsight_retrieved_memories,
    _write_json_fsync,
    start_llama_cpp_session,
    verify_hindsight_health,
)


SMOKE_TARGET = "v1:hindsight-comparator-synthetic-smoke"
SMOKE_FORMAT_VERSION = 1
_SYNTHETIC_SESSION_ID = "synthetic-session-0001"
_SYNTHETIC_TIMESTAMP = "2025-01-02T00:00:00+00:00"
_SYNTHETIC_QUERY_TIMESTAMP = "2025-01-02T12:00:00+00:00"
_SYNTHETIC_QUESTION = "Where is the copper token stored?"
_SYNTHETIC_ITEMS: tuple[Mapping[str, str | None], ...] = (
    {
        "role": "user",
        "content": "The copper token is stored in drawer seven.",
        "timestamp": _SYNTHETIC_TIMESTAMP,
    },
    {
        "role": "assistant",
        "content": "Understood; the copper token is in drawer seven.",
        "timestamp": _SYNTHETIC_TIMESTAMP,
    },
)


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CampaignCarriageError(f"{label} must be an object")
    return value


def _load_source_descriptor(path: Path) -> Mapping[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CampaignCarriageError(f"cannot read source descriptor: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CampaignCarriageError("source descriptor is not valid JSON") from exc
    return _mapping(raw, label="source descriptor")


def _derive_diagnostic_bindings(
    source: Mapping[str, Any],
    *,
    diagnostic_owner_id: str,
) -> tuple[LlamaCppLaunchSpec, HindsightLifecycleSpec, HindsightHealthAttestation]:
    """Copy only operational identities and replace owner-local Hindsight state."""

    llama = LlamaCppLaunchSpec.from_mapping(
        _mapping(source.get("llama_cpp"), label="source descriptor llama_cpp")
    )

    lifecycle_raw = dict(
        _mapping(
            source.get("hindsight_lifecycle"),
            label="source descriptor hindsight_lifecycle",
        )
    )
    lifecycle_raw["deployment_id"] = _hindsight_owner_deployment_id(
        diagnostic_owner_id
    )
    lifecycle_raw["database_profile"] = diagnostic_owner_id
    lifecycle = HindsightLifecycleSpec.from_mapping(lifecycle_raw)

    source_health = _mapping(
        source.get("hindsight_health"),
        label="source descriptor hindsight_health",
    )
    license_name = source_health.get("license")
    if not isinstance(license_name, str) or not license_name.strip():
        raise CampaignCarriageError(
            "source descriptor hindsight_health.license must be non-empty"
        )
    health = HindsightHealthAttestation.from_mapping(
        {
            "implementation": "hindsight",
            "source_revision": lifecycle.source_revision,
            "version": lifecycle.runtime_version,
            "license": license_name,
            "deployment": {
                "deployment_id": lifecycle.deployment_id,
                "dependency_fingerprint": lifecycle.dependency_fingerprint,
                "import_status": "passed",
                "llm_connection_verification": "skipped_zero_semantic_policy",
                "process_health_status": "passed",
                "capability_status": "passed",
            },
            "semantic_operations_called": [],
            "semantic_generation_count": 0,
            "benchmark_question_count": 0,
            "answer_model_generation_count": 0,
            "judge_call_count": 0,
        }
    )
    return llama, lifecycle, health


def _llama_cpp_chat_smoke(spec: LlamaCppLaunchSpec) -> Mapping[str, object]:
    payload = {
        "model": spec.expected_model_alias,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Synthetic infrastructure diagnostic. "
                    "Reply briefly that the local model endpoint is reachable."
                ),
            }
        ],
        "temperature": 0,
        "stream": False,
    }
    try:
        with httpx.Client(timeout=120.0, trust_env=False) as client:
            response = client.post(
                f"http://127.0.0.1:{spec.port}/v1/chat/completions",
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic request failed"
        ) from exc
    if response.status_code != 200:
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic returned "
            f"HTTP {response.status_code}"
        )
    try:
        body = response.json()
    except ValueError as exc:
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic response was not JSON"
        ) from exc
    if not isinstance(body, Mapping):
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic response was not an object"
        )
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise CampaignCarriageError(
            "synthetic llama.cpp chat diagnostic response had no choices"
        )
    return {
        "endpoint": "/v1/chat/completions",
        "status_code": response.status_code,
        "response_keys": sorted(str(key) for key in body),
        "choice_count": len(choices),
    }


def run_synthetic_hindsight_smoke(
    *,
    source_descriptor: Mapping[str, Any],
    diagnostic_owner_id: str,
    repo_root: Path,
    artifact_root: Path,
) -> Mapping[str, Any]:
    """Run one isolated synthetic live comparator diagnostic.

    The function deliberately has no benchmark inputs and no scientific ledger
    parameter.  A new artifact root is required for every invocation so failed
    diagnostics remain inspectable without contaminating a later retry.
    """

    if not repo_root.is_absolute():
        raise CampaignCarriageError("repo_root must be absolute")
    if not artifact_root.is_absolute():
        raise CampaignCarriageError("artifact_root must be absolute")
    if artifact_root.exists():
        raise CampaignCarriageError("synthetic smoke artifact_root must be fresh")
    artifact_root.mkdir(parents=True, exist_ok=False)

    llama_spec, lifecycle_spec, expected_health = _derive_diagnostic_bindings(
        source_descriptor,
        diagnostic_owner_id=diagnostic_owner_id,
    )
    bank_id = _hindsight_axis_bank_id(
        lifecycle_spec.database_profile,
        "synthetic-smoke",
    )
    history = HindsightHistorySession(
        session_id=_SYNTHETIC_SESSION_ID,
        order=0,
        items=_SYNTHETIC_ITEMS,
    )

    lifecycle = HindsightDeploymentSession(
        lifecycle_spec,
        expected_health,
        repo_root=repo_root,
        evidence_root=artifact_root / "hindsight",
    )
    live_session: LiveLaunchSession | None = None
    lifecycle_cleanup: Mapping[str, Any] | None = None
    live_cleanup: Mapping[str, Any] | None = None
    result: dict[str, Any] | None = None
    failure: BaseException | None = None

    try:
        lifecycle.start()
        observed_health = verify_hindsight_health(expected_health, lifecycle)
        live_session = start_llama_cpp_session(
            llama_spec,
            artifact_root / "llama-cpp",
        )
        live_attestation = live_session.attest()

        pre_existing_pending = lifecycle.consolidation_pending_ids(
            bank_id=bank_id,
            allow_missing_bank=True,
        )
        retain_request = history.to_retain_request(
            bank_id=bank_id,
            context_label="MemConflict",
            exchange_index=0,
        )
        lifecycle.retain(bank_id=bank_id, items=(retain_request,))
        consolidation = lifecycle.wait_for_consolidation(
            bank_id=bank_id,
            pre_existing_pending_ids=pre_existing_pending,
        )
        recalled = lifecycle.recall(
            _SYNTHETIC_QUESTION,
            bank_id=bank_id,
            query_timestamp=_SYNTHETIC_QUERY_TIMESTAMP,
        )
        retrieved = _hindsight_retrieved_memories(recalled)
        if not retrieved:
            raise CampaignCarriageError(
                "synthetic Hindsight recall returned no mapped memories"
            )
        llama_chat = _llama_cpp_chat_smoke(llama_spec)

        result = {
            "format_version": SMOKE_FORMAT_VERSION,
            "target": SMOKE_TARGET,
            "status": "NON_CITABLE_DIAGNOSTIC_PASS",
            "citable": False,
            "scientific_spend": "NOT_OPENED",
            "benchmark_text_used": False,
            "benchmark_question_count": 0,
            "judge_call_count": 0,
            "diagnostic_owner_id": diagnostic_owner_id,
            "bank_id": bank_id,
            "hindsight_health_fingerprint": observed_health.fingerprint,
            "hindsight_semantic_operation_count": lifecycle.semantic_operation_count,
            "retrieved_memory_count": len(retrieved),
            "consolidation": dict(consolidation),
            "llama_cpp_launch_count": live_session.launch_count,
            "llama_cpp_live_attestation_fingerprint": live_attestation.fingerprint,
            "llama_cpp_chat": dict(llama_chat),
            "synthetic_contract": {
                "session_id": _SYNTHETIC_SESSION_ID,
                "question": _SYNTHETIC_QUESTION,
                "query_timestamp": _SYNTHETIC_QUERY_TIMESTAMP,
                "retain_context": "MemConflict",
            },
        }
    except BaseException as exc:
        failure = exc
    finally:
        if live_session is not None:
            try:
                live_cleanup = live_session.cleanup()
            except BaseException as exc:
                live_cleanup = {
                    "all_owned_processes_terminated": False,
                    "external_processes_touched": 0,
                    "errors": [f"llama cleanup raised {type(exc).__name__}"],
                }
                if failure is None:
                    failure = exc
        try:
            lifecycle_cleanup = lifecycle.cleanup()
        except BaseException as exc:
            lifecycle_cleanup = {
                "all_owned_processes_terminated": False,
                "external_processes_touched": 0,
                "errors": [f"Hindsight cleanup raised {type(exc).__name__}"],
            }
            if failure is None:
                failure = exc

    if result is None:
        result = {
            "format_version": SMOKE_FORMAT_VERSION,
            "target": SMOKE_TARGET,
            "status": "NON_CITABLE_DIAGNOSTIC_FAIL",
            "citable": False,
            "scientific_spend": "NOT_OPENED",
            "benchmark_text_used": False,
            "benchmark_question_count": 0,
            "judge_call_count": 0,
            "diagnostic_owner_id": diagnostic_owner_id,
            "bank_id": bank_id,
            "failure": None
            if failure is None
            else {
                "type": type(failure).__name__,
                "message": str(failure),
            },
        }

    result["cleanup"] = {
        "llama_cpp": None if live_cleanup is None else dict(live_cleanup),
        "hindsight": (
            None if lifecycle_cleanup is None else dict(lifecycle_cleanup)
        ),
    }
    _write_json_fsync(
        artifact_root / "synthetic-hindsight-smoke.json",
        result,
    )

    if failure is not None:
        raise failure
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a non-citable synthetic Hindsight comparator smoke."
    )
    parser.add_argument("--source-descriptor", type=Path, required=True)
    parser.add_argument("--diagnostic-owner-id", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    source = _load_source_descriptor(args.source_descriptor.resolve())
    result = run_synthetic_hindsight_smoke(
        source_descriptor=source,
        diagnostic_owner_id=args.diagnostic_owner_id,
        repo_root=args.repo_root.resolve(),
        artifact_root=args.artifact_root.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
