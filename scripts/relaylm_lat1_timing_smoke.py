"""LAT-1 timing smoke: RelayRUN node timing and timing_summary are wired.

Verifies (measurement-only, no behavior assertions):
1. Direct artifact build: every timed node's duration_ms is a non-negative
   int; every untimed node's started_at/completed_at/duration_ms are all
   null; nodes_timed_count + nodes_untimed_count == total node count.
2. Full request through a fake backend: the response is unaffected and the
   persisted (content-free-projected) trace record's relayrun_artifact
   carries a numeric timing_summary.
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.app import create_app
from relaylm.config import RelayLMConfig, load_config
from relaylm.managed_chat_runtime import _finalize_timing, _start_timing
from relaylm.relayrun_runtime_artifact import _build_relayrun_runtime_artifact
from relaylm.routing import resolve_route


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


_TIMED_NODES = (
    "request_received",
    "relayrel",
    "relayscn",
    "relayint",
    "relaymem_retrieval",
    "relaymem_runtime_ctx",
    "relayctx_short_term_injection",
    "token_budget_truncation",
    "backend_forward",
)


def _real_node_timings() -> dict[str, dict[str, Any]]:
    timings: dict[str, dict[str, Any]] = {}
    for node_name in _TIMED_NODES:
        started_at, start_monotonic = _start_timing()
        time.sleep(0.001)
        timings[node_name] = _finalize_timing(started_at, start_monotonic)
    return timings


def check_direct_artifact_timing() -> None:
    config = RelayLMConfig.model_validate(load_config(str(REPO_ROOT / "config.example.yaml")).model_dump())
    route = resolve_route(config, "relaylm-default")
    node_timings = _real_node_timings()

    artifact = _build_relayrun_runtime_artifact(
        config=config,
        request_id="lat1-timing-smoke-req",
        run_id="lat1-timing-smoke-run",
        route=route,
        stream_enabled=False,
        relayrel_relationship_projection={"schema_version": "relayrel.relationship_projection.v0"},
        relayscn_scene_policy_artifact={"scene_state": {"scene_type": "design_talk"}, "scene_policy": {}},
        relayemo_artifact=None,
        relayint_intent_artifact={"mode": "normal", "unresolved_reference_detected": False, "mode_reasons": []},
        relaymem_retrieval_artifact={"apply_decision": "not_eligible", "snippet_apply_decision": "not_eligible"},
        runtime_ctx_injection_result={"applied": False, "blocked_reasons": []},
        runtime_snippet_injection_result={"applied": False, "blocked_reasons": []},
        relayctx_short_term_runtime_injection_apply_result=None,
        token_budget_truncation=None,
        backend_forward_status="completed",
        node_timings=node_timings,
        stream_started=False,
        first_token_sent=False,
    )

    node_statuses = artifact["node_statuses"]
    require(len(node_statuses) == 10, node_statuses)

    timed_count = 0
    untimed_count = 0
    for node in node_statuses:
        node_name = node["node_name"]
        duration = node.get("duration_ms")
        started_at = node.get("started_at")
        completed_at = node.get("completed_at")
        if node_name in _TIMED_NODES:
            require(isinstance(duration, int) and not isinstance(duration, bool) and duration >= 0, node)
            require(isinstance(started_at, str) and isinstance(completed_at, str), node)
            timed_count += 1
        else:
            require(duration is None, node)
            require(started_at is None and completed_at is None, node)
            untimed_count += 1

    timing_summary = artifact["timing_summary"]
    require(timing_summary["schema_version"] == "relayrun.timing_summary.v0", timing_summary)
    require(timing_summary["nodes_timed_count"] == timed_count, timing_summary)
    require(timing_summary["nodes_untimed_count"] == untimed_count, timing_summary)
    require(
        timing_summary["nodes_timed_count"] + timing_summary["nodes_untimed_count"] == len(node_statuses),
        timing_summary,
    )
    require(isinstance(timing_summary["pipeline_overhead_ms"], int) and timing_summary["pipeline_overhead_ms"] >= 0, timing_summary)
    require(isinstance(timing_summary["backend_forward_ms"], int) and timing_summary["backend_forward_ms"] >= 0, timing_summary)
    require(isinstance(timing_summary["retrieval_ms"], int) and timing_summary["retrieval_ms"] >= 0, timing_summary)
    require(timing_summary["time_to_first_token_ms"] is None, timing_summary)
    print("ok direct artifact build: timed nodes have non-negative int duration_ms, untimed nodes stay null")
    print("ok timing_summary node counts match node_statuses partition")


class _BackendHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        self.rfile.read(length)
        body = json.dumps(
            {
                "id": "chatcmpl-lat1-timing-smoke",
                "object": "chat.completion",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
                ],
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def check_full_request_timing_summary() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as td:
            root = Path(td)
            cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
            cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
            trace_path = root / "trace.jsonl"
            cfg["trace"] = {"enabled": True, "path": str(trace_path)}
            cfg_path = root / "config.yaml"
            cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

            with TestClient(create_app(str(cfg_path))) as client:
                response = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "relaylm-default",
                        "messages": [{"role": "user", "content": "hello"}],
                        "stream": False,
                    },
                )
            require(response.status_code == 200, response.text)

            record = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
            relayrun_artifact = record["metadata"]["relayrun_artifact"]
            timing_summary = relayrun_artifact.get("timing_summary")
            require(isinstance(timing_summary, dict), relayrun_artifact)
            for key in (
                "pipeline_overhead_ms",
                "nodes_timed_count",
                "nodes_untimed_count",
            ):
                value = timing_summary.get(key)
                require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, timing_summary)
            for key in ("backend_forward_ms", "time_to_first_token_ms", "retrieval_ms"):
                value = timing_summary.get(key)
                require(value is None or (isinstance(value, int) and not isinstance(value, bool)), timing_summary)
            print("ok fake-backend request produces numeric timing_summary via projected trace record")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main() -> int:
    check_direct_artifact_timing()
    check_full_request_timing_summary()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
