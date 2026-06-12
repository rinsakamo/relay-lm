from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
for path in (REPO_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from relaylm.app import create_app
from relaylm_relayrun_runtime_checkpoint_dry_run_smoke import (  # type: ignore[import-not-found]
    _BackendHandler,
    _Capture,
    _build_store,
)

RAW_VALUES = (
    "それで",
    "hidden handoff value",
    "https://example.invalid/private.png",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _write_config(path: Path, *, port: int, trace_path: Path, store_root: Path) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["relayint_fast_path_dry_run_enabled"] = True
    cfg["relayint_quick_clarification_preflight_enabled"] = True
    cfg["relayint_quick_clarification_dry_run_only"] = True
    cfg["relayint_quick_clarification_apply_enabled"] = True
    cfg["relayint_quick_clarification_apply_dry_run_only"] = False
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["memory"].update(
        {
            "root_path": str(store_root),
            "store_enabled": False,
            "retrieval_dry_run_only": True,
            "ctx_block_apply_enabled": False,
            "snippet_extraction_enabled": False,
            "snippet_dry_run_only": True,
            "snippet_apply_enabled": False,
            "snippet_runtime_injection_enabled": False,
            "snippet_runtime_dry_run_only": True,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _payload() -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "それで"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.invalid/private.png"},
                    },
                ],
            }
        ],
        "metadata": {
            "scene_state": {
                "scene_type": "design_talk",
                "confidence": 0.95,
                "stability": 0.9,
            },
            "ctx": {
                "ctx_handoff_guess": {"summary": "hidden handoff value"},
            },
        },
        "stream": False,
    }


def _assert_no_raw_content(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False)
    for raw in RAW_VALUES:
        require(raw not in encoded, value)


def main() -> None:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
            root = Path(td)
            store_root = _build_store(root / "store")
            trace_path = root / "trace.jsonl"
            cfg_path = root / "cfg.yaml"
            _write_config(
                cfg_path,
                port=int(server.server_address[1]),
                trace_path=trace_path,
                store_root=store_root,
            )
            payload = _payload()
            original = json.loads(json.dumps(payload, ensure_ascii=False))
            before_count = capture.count()
            with TestClient(create_app(str(cfg_path))) as client:
                response = client.post("/v1/chat/completions", json=payload)

            require(response.status_code == 200, response.text)
            response_body = response.json()
            require(payload == original, payload)
            require(capture.count() == before_count + 1, capture.count())
            backend_payload = capture.get(before_count)
            require(backend_payload.get("messages") == original["messages"], backend_payload)
            require(backend_payload.get("metadata") == original["metadata"], backend_payload)
            require(
                response_body["choices"][0]["message"]["content"] == "ok",
                response_body,
            )

            record = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
            metadata = record.get("metadata")
            require(isinstance(metadata, dict), record)
            results = metadata.get("pipeline_node_results")
            require(isinstance(results, list), metadata)
            require(
                [result.get("node_name") for result in results]
                == [
                    "relayint_reference_repair",
                    "relayint_quick_clarification",
                    "relayctx_repack",
                ],
                results,
            )
            _assert_no_raw_content(results)

            reference = results[0]
            require(reference.get("status") == "diagnostic_only", reference)
            require(
                reference.get("diagnostics", {}).get("compatibility_source_node")
                == "relayref",
                reference,
            )
            require(
                reference.get("diagnostics", {}).get("source_node_alias")
                == "relayint_reference_repair",
                reference,
            )

            quick = results[1]
            require(quick.get("status") == "diagnostic_only", quick)
            require(quick.get("decision") == "apply_plan_recorded", quick)
            require("phase4_plan_only" in quick.get("blocked_reasons", []), quick)
            require(
                quick.get("diagnostics", {}).get("apply_allowed") is False,
                quick,
            )

            repack = results[2]
            require(repack.get("status") in {"diagnostic_only", "applied"}, repack)
            require(
                isinstance(repack.get("diagnostics", {}).get("phase_artifact_count"), int),
                repack,
            )
            print("ok runtime records content-free Phase 4.5 pipeline node results")
            print("ok backend forwarding and backend-owned response remain unchanged")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
