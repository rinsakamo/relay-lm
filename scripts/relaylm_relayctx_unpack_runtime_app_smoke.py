from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import create_app
from relaylm.relayctx_unpack import RELAYCTX_UPDATE_CLOSE, RELAYCTX_UPDATE_OPEN


class _Capture:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.payloads: list[dict[str, Any]] = []

    def append(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)

    def count(self) -> int:
        with self._lock:
            return len(self.payloads)


class _BackendHandler(BaseHTTPRequestHandler):
    capture = _Capture()
    response_content = "ok"

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        self.capture.append(payload)
        body = {
            "id": "chatcmpl-relayctx-unpack",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self.response_content,
                    },
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

    def log_message(self, format: str, *args: object) -> None:
        return


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _structured_content(secret: str) -> str:
    envelope = {
        "schema_version": "relayctx_working_update.v0",
        "ctx_working_update": {
            "current_topic": secret,
            "next_expected_action": "remain request-local only",
        },
    }
    return (
        f"Visible runtime answer.\n{RELAYCTX_UPDATE_OPEN}\n"
        f"{json.dumps(envelope, ensure_ascii=False)}\n"
        f"{RELAYCTX_UPDATE_CLOSE}"
    )


def _write_config(
    path: Path,
    *,
    port: int,
    trace_path: Path,
    enabled: bool,
    apply_enabled: bool,
    dry_run_only: bool,
) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    cfg["relayctx_unpack_enabled"] = enabled
    cfg["relayctx_unpack_apply_enabled"] = apply_enabled
    cfg["relayctx_unpack_dry_run_only"] = dry_run_only
    cfg["relayctx_unpack_max_update_chars"] = 4096
    cfg["relayemo_enabled"] = False
    cfg["model_routes"]["relaylm-default"]["mode"] = "pass_through"
    cfg["memory"].update(
        {
            "store_enabled": False,
            "retrieval_dry_run_only": True,
            "ctx_block_apply_enabled": False,
            "snippet_extraction_enabled": False,
            "snippet_apply_enabled": False,
            "snippet_runtime_injection_enabled": False,
            "token_budget_truncation_enabled": False,
        }
    )
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def _request_payload() -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }


def _run_case(
    root: Path,
    *,
    name: str,
    port: int,
    content: str,
    enabled: bool,
    apply_enabled: bool,
    dry_run_only: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    trace_path = root / f"{name}.jsonl"
    cfg_path = root / f"{name}.yaml"
    _write_config(
        cfg_path,
        port=port,
        trace_path=trace_path,
        enabled=enabled,
        apply_enabled=apply_enabled,
        dry_run_only=dry_run_only,
    )
    _BackendHandler.response_content = content
    before = _BackendHandler.capture.count()
    with TestClient(create_app(str(cfg_path))) as client:
        response = client.post("/v1/chat/completions", json=_request_payload())
    require(response.status_code == 200, response.text)
    require(_BackendHandler.capture.count() == before + 1, _BackendHandler.capture.count())
    trace_record = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    return response.json(), trace_record


def _pipeline_results(trace_record: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = trace_record.get("metadata")
    require(isinstance(metadata, dict), trace_record)
    results = metadata.get("pipeline_node_results")
    require(isinstance(results, list), metadata)
    return results


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    secret = "request local candidate secret"
    structured = _structured_content(secret)
    malformed = (
        f"Safe malformed answer.\n{RELAYCTX_UPDATE_OPEN}\n"
        '{"schema_version":"relayctx_working_update.v0",bad}\n'
        f"{RELAYCTX_UPDATE_CLOSE}"
    )

    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
            root = Path(td)

            body, trace = _run_case(
                root,
                name="default_off",
                port=port,
                content=structured,
                enabled=False,
                apply_enabled=False,
                dry_run_only=True,
            )
            require(body["choices"][0]["message"]["content"] == structured, body)
            results = _pipeline_results(trace)
            require(
                [result.get("node_name") for result in results]
                == [
                    "relayint_reference_repair",
                    "relayint_quick_clarification",
                    "relayctx_repack",
                ],
                results,
            )
            print("ok RelayCTX Unpack runtime is default-off and response-neutral")

            body, trace = _run_case(
                root,
                name="dry_run",
                port=port,
                content=structured,
                enabled=True,
                apply_enabled=False,
                dry_run_only=True,
            )
            require(body["choices"][0]["message"]["content"] == structured, body)
            results = _pipeline_results(trace)
            require(
                [result.get("node_name") for result in results]
                == [
                    "relayint_reference_repair",
                    "relayint_quick_clarification",
                    "relayctx_repack",
                    "relayctx_unpack",
                ],
                results,
            )
            unpack = results[-1]
            require(unpack.get("status") == "diagnostic_only", unpack)
            require(unpack.get("decision") == "structured_update_dry_run", unpack)
            require(unpack.get("diagnostics", {}).get("candidate_present") is True, unpack)
            require(
                unpack.get("diagnostics", {}).get("candidate_persistence_allowed") is False,
                unpack,
            )
            require(secret not in json.dumps(unpack, ensure_ascii=False), unpack)
            print("ok RelayCTX Unpack runtime dry-run records content-free candidate metadata")

            body, trace = _run_case(
                root,
                name="apply",
                port=port,
                content=structured,
                enabled=True,
                apply_enabled=True,
                dry_run_only=False,
            )
            require(
                body["choices"][0]["message"]["content"] == "Visible runtime answer.",
                body,
            )
            results = _pipeline_results(trace)
            unpack = results[-1]
            require(unpack.get("status") == "applied", unpack)
            require(unpack.get("decision") == "visible_text_applied", unpack)
            require(unpack.get("diagnostics", {}).get("applied_to_response") is True, unpack)
            require(secret not in json.dumps(unpack, ensure_ascii=False), unpack)
            print("ok RelayCTX Unpack runtime apply replaces assistant content only")

            body, trace = _run_case(
                root,
                name="blocked_apply",
                port=port,
                content=malformed,
                enabled=True,
                apply_enabled=True,
                dry_run_only=False,
            )
            require(
                body["choices"][0]["message"]["content"] == "Safe malformed answer.",
                body,
            )
            unpack = _pipeline_results(trace)[-1]
            require(unpack.get("status") == "blocked", unpack)
            require(
                unpack.get("decision") == "blocked_update_visible_text_applied",
                unpack,
            )
            require("update_json_invalid" in unpack.get("blocked_reasons", []), unpack)
            require(unpack.get("diagnostics", {}).get("candidate_present") is False, unpack)
            print("ok RelayCTX Unpack runtime blocks update and preserves safe visible text")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
