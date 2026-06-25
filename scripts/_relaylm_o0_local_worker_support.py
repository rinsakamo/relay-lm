"""Test-only support for O0 local one-job runner smokes."""
from __future__ import annotations

from pathlib import Path

import yaml

from relaylm.config import RelayLMConfig
from relaylm.local_worker_once import (
    REQUEST_SCHEMA,
    RelayLMLocalWorkerOnceRequest,
)
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)

from _relaylm_phase6c1_durable_source_support import (
    CHARACTER_ID,
    PRIVATE_TOKENS,
    apply_durable,
    artifact_path,
)
from relaylm_phase6c1_primary_worker_test_support import prepare_store, require


def queued_from(applied: object) -> dict[str, object]:
    runtime_result = getattr(applied, "runtime_result", None)
    enqueue = getattr(runtime_result, "enqueue_result", None)
    queued = getattr(enqueue, "durable_record", None)
    require(type(queued) is dict, getattr(applied, "to_log_dict", lambda: applied)())
    return dict(queued)


def build_config(
    queue_root: Path,
    protected_root: Path,
    memory_root: Path,
    namespace: str,
    *,
    mode: str = "apply",
    character_id: str = CHARACTER_ID,
    extra_character_id: str | None = None,
    discovery_max_entries: int = 256,
) -> RelayLMConfig:
    routes: dict[str, object] = {
        "relaylm-default": {
            "backend": "local_backend",
            "backend_model": "local-model",
            "character_id": character_id,
            "mode": "memory_light",
            "memory_namespace": namespace,
        }
    }
    characters: dict[str, object] = {
        character_id: {"soul": "unused", "output_policy": "unused"}
    }
    if extra_character_id is not None:
        routes["relaylm-ambiguous"] = {
            "backend": "local_backend",
            "backend_model": "local-model",
            "character_id": extra_character_id,
            "mode": "memory_light",
            "memory_namespace": namespace,
        }
        characters[extra_character_id] = {
            "soul": "unused",
            "output_policy": "unused",
        }
    gates = {
        "disabled": (False, True, False),
        "dry_run": (True, True, False),
        "apply": (True, False, True),
    }[mode]
    return RelayLMConfig.model_validate(
        {
            "mode": "pass_through",
            "backends": {
                "local_backend": {
                    "type": "openai_compatible",
                    "base_url": "http://127.0.0.1:1234/v1",
                }
            },
            "model_routes": routes,
            "characters": characters,
            "memory": {"root_path": str(memory_root)},
            "relaymem_slp_queue_root": str(queue_root),
            "relaymem_slp_protected_source_root": str(protected_root),
            "relaymem_local_worker_enabled": gates[0],
            "relaymem_local_worker_dry_run_only": gates[1],
            "relaymem_local_worker_apply_enabled": gates[2],
            "relaymem_local_worker_claim_owner": "worker-o0-smoke",
            "relaymem_local_worker_lease_duration_seconds": 300,
            "relaymem_local_worker_discovery_max_entries": discovery_max_entries,
        }
    )


def build_request(config: RelayLMConfig, *, character_id: str | None = None):
    return RelayLMLocalWorkerOnceRequest(
        schema_version=REQUEST_SCHEMA,
        runtime_private=True,
        content_included=False,
        config=config,
        character_id=character_id,
    )


def produce(queue_root: Path, protected_root: Path) -> tuple[dict[str, object], Path]:
    applied = apply_durable(
        queue_root,
        protected_root,
        RelayMEMSLPPrimaryWorkerSourceRegistry(),
    )
    require(applied.status == "enqueued", applied.to_log_dict())
    return queued_from(applied), artifact_path(protected_root)


def prepare_scoped_store(memory_root: Path, character_id: str = CHARACTER_ID) -> Path:
    resolved = resolve_relaymem_character_store_root(str(memory_root), character_id)
    require(resolved is not None, "character store resolution")
    scoped = Path(resolved)
    prepare_store(scoped)
    return scoped


def assert_content_free(value: object, *extra_tokens: str) -> None:
    text = repr(value)
    for token in (*PRIVATE_TOKENS, *extra_tokens):
        require(token not in text, ("protected leak", token))


def write_config(path: Path, config: RelayLMConfig) -> None:
    path.write_text(
        yaml.safe_dump(config.model_dump(mode="json"), sort_keys=True),
        encoding="utf-8",
    )
