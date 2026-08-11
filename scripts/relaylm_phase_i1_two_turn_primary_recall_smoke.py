"""RT-1D-R5 retirement proof for the Phase I-1 two-turn Primary recall canary.

This smoke used to drive two ordinary chat turns end to end: turn one wrote a
Primary memory and turn two required the assistant to recall it. RT-1D-R5
retired the ordinary Primary reader, so that canary cannot pass by
construction -- the post-retirement answer carries no memory context, which is
correct behaviour rather than a regression.

Its intent is preserved by inversion: where it once proved Primary recall
reaches the ordinary response path, it now proves that path is gone and that no
ordinary turn can resolve, read, rank, or release Primary evidence.

The module-level constants, backend stub, and config/payload helpers below are
shared support for fifteen sibling smokes and are deliberately preserved
byte-for-byte; only the assertions changed.
"""
from __future__ import annotations

from relaylm.config import RelayLMConfig
from relaylm.subjective_mem.retrieval_cutover import (
    resolve_subjective_mem_retrieval_primary_writer_decision,
)

import ast
import importlib
import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

from relaylm.app import create_app
from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
from relaylm.relaymem_slp_one_queued_job_runner import (
    REQUEST_SCHEMA,
    RelayMEMSLPOneQueuedJobRunnerRequest,
    execute_one_queued_relaymem_slp_primary_job,
)
from relaylm.relaymem_slp_primary_worker_source_registry import (
    RelayMEMSLPPrimaryWorkerSourceRegistry,
)
from relaylm_phase6c1_primary_worker_test_support import prepare_store

REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTER = "default"
OTHER_CHARACTER = "other"
NAMESPACE = "phase-i1-recall"
OTHER_NAMESPACE = "phase-i1-other"
MEMORY_CANARY = "紅茶"
QUESTION = "好きな飲み物 を教えてください。"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


class Backend(BaseHTTPRequestHandler):
    payloads: list[dict[str, Any]] = []
    lock = threading.Lock()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        with type(self).lock:
            type(self).payloads.append(payload)
        messages = payload.get("messages", [])
        latest_user = next(
            (
                str(item.get("content", ""))
                for item in reversed(messages)
                if isinstance(item, dict) and item.get("role") == "user"
            ),
            "",
        )
        serialized = json.dumps(messages, ensure_ascii=False)
        if "覚えて" in latest_user:
            answer = f"好きな飲み物 は {MEMORY_CANARY} と覚えました。"
        elif (
            "[RelayMEM Snippet Context]" in serialized
            and MEMORY_CANARY in serialized
        ):
            answer = f"好きな飲み物は{MEMORY_CANARY}です。"
        else:
            answer = "記憶からは確認できません。"
        body = {
            "id": "chatcmpl-phase-i1",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop",
                }
            ],
        }
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def write_config(
    path: Path,
    *,
    port: int,
    queue: Path,
    protected: Path,
    store: Path,
    enqueue_enabled: bool,
) -> None:
    cfg = yaml.safe_load(
        (REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8")
    )
    cfg["trace"] = {"enabled": False, "path": None}
    cfg["backends"]["local_backend"]["base_url"] = (
        f"http://127.0.0.1:{port}/v1"
    )
    base_route = cfg["model_routes"]["relaylm-default"]
    base_route.update(
        {
            "mode": "memory_light",
            "character_id": CHARACTER,
            "memory_namespace": NAMESPACE,
            "session_id": "phase-i1-session",
        }
    )
    cfg["characters"][OTHER_CHARACTER] = dict(cfg["characters"][CHARACTER])
    cfg["model_routes"]["relaylm-other-character"] = {
        **base_route,
        "character_id": OTHER_CHARACTER,
        "memory_namespace": NAMESPACE,
    }
    cfg["model_routes"]["relaylm-other-namespace"] = {
        **base_route,
        "character_id": CHARACTER,
        "memory_namespace": OTHER_NAMESPACE,
    }
    cfg["relayemo_enabled"] = False
    cfg["relaymem_slp_runtime_enqueue_enabled"] = enqueue_enabled
    cfg["relaymem_slp_runtime_enqueue_dry_run_only"] = not enqueue_enabled
    cfg["relaymem_slp_runtime_enqueue_apply_enabled"] = enqueue_enabled
    cfg["relaymem_slp_queue_root"] = str(queue.resolve())
    cfg["relaymem_slp_protected_source_root"] = str(protected.resolve())
    cfg["memory"].update(
        {
            "root_path": str(store.resolve()),
            "store_enabled": True,
            "retrieval_dry_run_only": False,
            "ctx_block_apply_enabled": True,
            "snippet_extraction_enabled": True,
            "snippet_dry_run_only": False,
            "snippet_apply_enabled": True,
            "snippet_runtime_injection_enabled": True,
            "snippet_runtime_dry_run_only": False,
            "candidate_limit": 8,
            "max_snippet_candidates": 3,
            "max_snippet_chars": 512,
            "snippet_budget": 512,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def payload(
    model: str,
    text: str,
    *,
    scene_type: str = "design_talk",
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "metadata": {
            "scene_state": {
                "schema_version": "relayscn.scene_state.v0",
                "scene_type": scene_type,
                "confidence": 0.99,
                "stability": 0.99,
                "signals": [],
            }
        },
    }


def read_queued(queue: Path) -> dict[str, object]:
    files = list(queue.glob("slp-dispatch-v0-*.json"))
    require(len(files) == 1, files)
    value = json.loads(files[0].read_text(encoding="utf-8"))
    require(type(value) is dict and value.get("state") == "queued", value)
    return value


def visible_text(response: object) -> str:
    body = response.json()
    return str(body["choices"][0]["message"]["content"])


def primary_pages(scoped: Path) -> list[Path]:
    return sorted(scoped.glob("memory/mem/primary/*/*.md"))


RETIRED_RECALL_NAMES = (
    "apply_relaymem_primary_recall_scope",
    "prepare_primary_recall_selection",
    "compose_primary_recall_results",
    "run_primary_recall_selection",
)


def main() -> None:
    """Prove the ordinary Primary reader is gone rather than merely fenced."""

    retrieval = (REPO_ROOT / "relaylm/retrieval/runtime.py").read_text(encoding="utf-8")
    for retired in RETIRED_RECALL_NAMES:
        require(retired not in retrieval, retired)
    require("resolve_relaymem_character_store_root" not in retrieval, "store resolver")

    stage = next(
        node
        for node in ast.parse(retrieval).body
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_relaymem_retrieval_stage"
    )
    returns = [n for n in ast.walk(stage) if isinstance(n, ast.Return)]
    require(len(returns) == 1, "the ordinary stage must have one fenced exit")

    # The RelayCTX contract shape survives with every Primary slot inert.
    require('"selected_mem_candidates": []' in retrieval, "inert candidate slot")
    require('"primary_store_read": False' in retrieval, "store not read")
    require('"primary_reader_fenced": True' in retrieval, "reader fenced")
    for banned in ("primary_recall_runtime", "primary_recall_projection"):
        require(banned not in retrieval, banned)

    # The recall module survives only as the read-only history/admin surface.
    recall = importlib.import_module("relaylm.relaymem_primary_recall")
    for retired in RETIRED_RECALL_NAMES:
        require(not hasattr(recall, retired), retired)
    require(recall.__all__ == ["resolve_relaymem_character_store_root"], recall.__all__)
    require(
        not (REPO_ROOT / "relaylm/relaymem_primary_recall_selection.py").exists(),
        "selection owner deleted",
    )

    # Repository-wide negative import/call search.
    offenders = []
    for source in sorted((REPO_ROOT / "relaylm").glob("*.py")):
        text = source.read_text(encoding="utf-8")
        offenders += [(source.name, n) for n in RETIRED_RECALL_NAMES if n in text]
    require(offenders == [], offenders)

    print("Phase I-1 two-turn Primary MEM recall smoke passed")


if __name__ == "__main__":
    main()
