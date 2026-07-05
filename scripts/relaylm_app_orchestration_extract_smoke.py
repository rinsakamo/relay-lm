"""Regression smoke for the app.py managed runtime orchestration extraction.

relaylm/app.py's managed `/v1/chat/completions` handler had five near-identical
`_build_relayrun_runtime_artifact(...)` call sites and two copies of the
backend-request-error handling block. This smoke proves the extracted helpers
(`_validate_and_resolve_managed_chat_request`,
`_ManagedRuntimeArtifactContext` / `_build_relayrun_runtime_artifact_for_context`,
`_build_backend_request_error_response`) did not change:
  - request validation status codes / fallback_reason values
  - route registration
  - stream vs non-stream path selection
  - RelayRUN artifact contents (byte-identical to the un-refactored builder)
  - content-free public diagnostics
  - import-time side effects
"""
from __future__ import annotations

import asyncio
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

from relaylm.app import (
    _build_backend_request_error_response,
    _build_relayrun_runtime_artifact,
    _build_relayrun_runtime_artifact_for_context,
    _ManagedRuntimeArtifactContext,
    _validate_and_resolve_managed_chat_request,
    create_app,
)
from relaylm.adapter import BackendRequestError
from relaylm.config import ModelRoute, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.routing import resolve_route

USER_CANARY = "CANARY_APP_ORCHESTRATION_EXTRACT_USER_PRIVATE"
ASSISTANT_CANARY = "CANARY_APP_ORCHESTRATION_EXTRACT_ASSISTANT_PRIVATE"
NON_STREAM_BODY = {
    "id": "chatcmpl-orchestration-extract",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": ASSISTANT_CANARY},
            "finish_reason": "stop",
        }
    ],
}
STREAM_BODY = (
    'data: {"id":"chatcmpl-orchestration-extract","object":"chat.completion.chunk",'
    '"choices":[{"index":0,"delta":{"content":"' + ASSISTANT_CANARY + '"}}]}\n\n'
    "data: [DONE]\n\n"
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


class _FakeRequest:
    """Minimal stand-in for starlette.Request exposing only what validation needs."""

    def __init__(self, body: Any, *, raise_decode_error: bool = False) -> None:
        self._body = body
        self._raise_decode_error = raise_decode_error

    async def json(self) -> Any:
        if self._raise_decode_error:
            raise json.JSONDecodeError("bad json", "", 0)
        return self._body


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def check_validation_helper_error_branches() -> None:
    config = load_config(REPO_ROOT / "config.example.yaml")

    invalid_json = _run(
        _validate_and_resolve_managed_chat_request(
            _FakeRequest(None, raise_decode_error=True),
            request_id="req-invalid-json",
            config=config,
        )
    )
    require(invalid_json.error_response is not None, invalid_json)
    require(invalid_json.error_response.status_code == 400, invalid_json.error_response)
    require(
        invalid_json.error_response.headers.get("x-relaylm-fallback-reason") == "invalid_json",
        invalid_json.error_response.headers,
    )

    invalid_json_type = _run(
        _validate_and_resolve_managed_chat_request(
            _FakeRequest([1, 2, 3]),
            request_id="req-invalid-json-type",
            config=config,
        )
    )
    require(invalid_json_type.error_response is not None, invalid_json_type)
    require(invalid_json_type.error_response.status_code == 400, invalid_json_type.error_response)
    require(
        invalid_json_type.error_response.headers.get("x-relaylm-fallback-reason")
        == "invalid_json_type",
        invalid_json_type.error_response.headers,
    )

    missing_model = _run(
        _validate_and_resolve_managed_chat_request(
            _FakeRequest({"messages": []}),
            request_id="req-missing-model",
            config=config,
        )
    )
    require(missing_model.error_response is not None, missing_model)
    require(missing_model.error_response.status_code == 400, missing_model.error_response)
    require(
        missing_model.error_response.headers.get("x-relaylm-fallback-reason") == "missing_model",
        missing_model.error_response.headers,
    )

    invalid_stream_type = _run(
        _validate_and_resolve_managed_chat_request(
            _FakeRequest({"model": "relaylm-default", "stream": "yes"}),
            request_id="req-invalid-stream-type",
            config=config,
        )
    )
    require(invalid_stream_type.error_response is not None, invalid_stream_type)
    require(
        invalid_stream_type.error_response.status_code == 400, invalid_stream_type.error_response
    )
    require(
        invalid_stream_type.error_response.headers.get("x-relaylm-fallback-reason")
        == "invalid_stream_type",
        invalid_stream_type.error_response.headers,
    )

    route_not_found = _run(
        _validate_and_resolve_managed_chat_request(
            _FakeRequest({"model": "does-not-exist-model"}),
            request_id="req-route-not-found",
            config=config,
        )
    )
    require(route_not_found.error_response is not None, route_not_found)
    require(route_not_found.error_response.status_code == 400, route_not_found.error_response)
    require(
        route_not_found.error_response.headers.get("x-relaylm-fallback-reason")
        == "route_not_found",
        route_not_found.error_response.headers,
    )

    broken_route_config = config.model_copy(
        update={
            "model_routes": {
                **config.model_routes,
                "ghost-route": ModelRoute(backend="ghost-backend-not-configured"),
            }
        }
    )
    route_configuration_error = _run(
        _validate_and_resolve_managed_chat_request(
            _FakeRequest({"model": "ghost-route"}),
            request_id="req-route-configuration-error",
            config=broken_route_config,
        )
    )
    require(route_configuration_error.error_response is not None, route_configuration_error)
    require(
        route_configuration_error.error_response.status_code == 500,
        route_configuration_error.error_response,
    )
    require(
        route_configuration_error.error_response.headers.get("x-relaylm-fallback-reason")
        == "route_configuration_error",
        route_configuration_error.error_response.headers,
    )

    print("ok validation helper preserves status codes and fallback_reason values")


def check_validation_helper_success_path() -> None:
    config = load_config(REPO_ROOT / "config.example.yaml")
    payload = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": True,
    }
    result = _run(
        _validate_and_resolve_managed_chat_request(
            _FakeRequest(payload),
            request_id="req-success",
            config=config,
        )
    )
    require(result.error_response is None, result)
    require(result.payload == payload, result.payload)
    require(result.stream_enabled is True, result.stream_enabled)
    require(result.route is not None and result.route.route_model == "relaylm-default", result.route)
    print("ok validation helper returns payload/stream/route on success")


def check_runtime_artifact_context_equivalence() -> None:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")

    shared_kwargs = dict(
        config=config,
        request_id="req-context-equivalence",
        run_id="run-context-equivalence",
        route=route,
        stream_enabled=False,
        relayrel_relationship_projection={
            "schema_version": "relayrel.relationship_projection.v0",
            "content_free": True,
        },
        relayscn_scene_policy_artifact={
            "scene_state": {"scene_type": "design_talk"},
            "scene_policy": {},
        },
        relayemo_artifact=None,
        relayint_intent_artifact={"unresolved_reference_detected": False, "mode_reasons": []},
        relaymem_retrieval_artifact={
            "apply_decision": "not_eligible",
            "snippet_apply_decision": "not_eligible",
        },
        runtime_ctx_injection_result={"applied": False, "blocked_reasons": []},
        runtime_snippet_injection_result={"applied": False, "blocked_reasons": []},
        relayctx_short_term_runtime_injection_apply_result=None,
        token_budget_truncation=None,
    )

    context = _ManagedRuntimeArtifactContext(
        config=shared_kwargs["config"],
        request_id=shared_kwargs["request_id"],
        run_id=shared_kwargs["run_id"],
        route=shared_kwargs["route"],
        stream_enabled=shared_kwargs["stream_enabled"],
        relayrel_relationship_projection=shared_kwargs["relayrel_relationship_projection"],
        relayscn_scene_policy_artifact=shared_kwargs["relayscn_scene_policy_artifact"],
        relayemo_artifact=shared_kwargs["relayemo_artifact"],
        relayint_intent_artifact=shared_kwargs["relayint_intent_artifact"],
        relaymem_retrieval_artifact=shared_kwargs["relaymem_retrieval_artifact"],
        runtime_ctx_injection_result=shared_kwargs["runtime_ctx_injection_result"],
        runtime_snippet_injection_result=shared_kwargs["runtime_snippet_injection_result"],
        relayctx_short_term_runtime_injection_apply_result=(
            shared_kwargs["relayctx_short_term_runtime_injection_apply_result"]
        ),
        token_budget_truncation=shared_kwargs["token_budget_truncation"],
    )

    for variant_kwargs in (
        {"backend_forward_status": "pending", "stream_started": False, "first_token_sent": False},
        {
            "backend_forward_status": "failed",
            "backend_forward_blocked_reasons": ["BackendRequestError"],
            "stream_started": False,
            "first_token_sent": False,
        },
        {"backend_forward_status": "completed", "stream_started": True, "first_token_sent": False},
        {"backend_forward_status": "completed", "stream_started": False, "first_token_sent": False},
    ):
        direct = _build_relayrun_runtime_artifact(**shared_kwargs, **variant_kwargs)
        via_context = _build_relayrun_runtime_artifact_for_context(context, **variant_kwargs)
        require(
            direct == via_context,
            (variant_kwargs, direct, via_context),
        )

    print("ok context-based artifact builder is byte-identical to the direct builder")


def check_backend_request_error_response_shape() -> None:
    config = load_config(REPO_ROOT / "config.example.yaml")
    route = resolve_route(config, "relaylm-default")
    context = _ManagedRuntimeArtifactContext(
        config=config,
        request_id="req-backend-error",
        run_id="run-backend-error",
        route=route,
        stream_enabled=False,
        relayrel_relationship_projection={"content_free": True},
        relayscn_scene_policy_artifact={"scene_state": {"scene_type": "design_talk"}, "scene_policy": {}},
        relayemo_artifact=None,
        relayint_intent_artifact={"unresolved_reference_detected": False, "mode_reasons": []},
        relaymem_retrieval_artifact={"apply_decision": "not_eligible", "snippet_apply_decision": "not_eligible"},
        runtime_ctx_injection_result={"applied": False, "blocked_reasons": []},
        runtime_snippet_injection_result={"applied": False, "blocked_reasons": []},
        relayctx_short_term_runtime_injection_apply_result=None,
        token_budget_truncation=None,
    )
    diagnostics = RequestDiagnostics(request_id="req-backend-error", trace_enabled=False)
    response = _build_backend_request_error_response(
        config=config,
        exc=BackendRequestError("connection refused"),
        diagnostics=diagnostics,
        runtime_artifact_context=context,
        forwarded_payload={"messages": []},
    )
    require(response.status_code == 502, response)
    body = json.loads(bytes(response.body))
    require(body["error"]["type"] == "backend_connection_error", body)
    require("connection refused" in body["error"]["message"], body)
    print("ok shared backend-request-error response has the original 502 shape")


class _Capture:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.payloads: list[dict[str, Any]] = []

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)


class _BackendHandler(BaseHTTPRequestHandler):
    capture: _Capture

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        type(self).capture.add(payload)
        if payload.get("stream") is True:
            encoded = STREAM_BODY.encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return
        encoded = json.dumps(NON_STREAM_BODY).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _write_config(path: Path, *, backend_port: int, trace_path: Path) -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{backend_port}/v1"
    cfg["trace"] = {"enabled": True, "path": str(trace_path)}
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


def check_managed_route_http_behavior_unchanged() -> None:
    capture = _Capture()
    _BackendHandler.capture = capture
    server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    try:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            trace_path = root / "trace.jsonl"
            config_path = root / "config.yaml"
            _write_config(config_path, backend_port=port, trace_path=trace_path)

            app = create_app(str(config_path))

            installed_paths = {route.path for route in app.routes if hasattr(route, "path")}
            require(
                {"/healthz", "/v1/models", "/v1/chat/completions"} <= installed_paths,
                installed_paths,
            )

            with TestClient(app) as client:
                bad = client.post("/v1/chat/completions", content="not json")
                require(bad.status_code == 400, bad.text)
                require(
                    bad.headers.get("x-relaylm-fallback-reason") == "invalid_json", bad.headers
                )

                missing_model = client.post("/v1/chat/completions", json={"messages": []})
                require(missing_model.status_code == 400, missing_model.text)
                require(
                    missing_model.headers.get("x-relaylm-fallback-reason") == "missing_model",
                    missing_model.headers,
                )

                non_stream = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "relaylm-default",
                        "messages": [{"role": "user", "content": USER_CANARY}],
                        "stream": False,
                    },
                )
                require(non_stream.status_code == 200, non_stream.text)
                require(non_stream.json() == NON_STREAM_BODY, non_stream.json())
                require("x-relaylm-run-id" in non_stream.headers, non_stream.headers)
                non_stream_headers_text = json.dumps(dict(non_stream.headers))
                require(USER_CANARY not in non_stream_headers_text, non_stream_headers_text)

                with client.stream(
                    "POST",
                    "/v1/chat/completions",
                    json={
                        "model": "relaylm-default",
                        "messages": [{"role": "user", "content": USER_CANARY + "-stream"}],
                        "stream": True,
                    },
                ) as stream_response:
                    require(stream_response.status_code == 200, stream_response.status_code)
                    require(
                        stream_response.headers.get("content-type", "").startswith(
                            "text/event-stream"
                        ),
                        stream_response.headers,
                    )
                    streamed = "".join(stream_response.iter_text())
                require(streamed == STREAM_BODY, streamed)

            trace_records = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            require(trace_records, "expected trace records to be written")
            trace_text = json.dumps(trace_records, ensure_ascii=False)
            require(USER_CANARY not in trace_text, trace_text)
            require(ASSISTANT_CANARY not in trace_text, trace_text)
            print("ok non-stream/stream managed route behavior and content-free trace unchanged")

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory2:
            root2 = Path(directory2)
            trace_path2 = root2 / "trace.jsonl"
            config_path2 = root2 / "config.yaml"
            # Point at a closed port so the backend forward raises BackendRequestError.
            closed_server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
            closed_port = int(closed_server.server_address[1])
            closed_server.server_close()
            _write_config(config_path2, backend_port=closed_port, trace_path=trace_path2)
            failing_app = create_app(str(config_path2))
            with TestClient(failing_app) as client:
                failure = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "relaylm-default",
                        "messages": [{"role": "user", "content": "hello"}],
                        "stream": False,
                    },
                )
                require(failure.status_code == 502, failure.text)
                require(
                    failure.json()["error"]["type"] == "backend_connection_error",
                    failure.json(),
                )
            print("ok backend connection failure still returns 502 backend_connection_error")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def check_no_import_time_side_effects() -> None:
    import relaylm.app as app_module

    require(hasattr(app_module, "create_app"), "create_app missing")
    app_one = app_module.create_app(str(REPO_ROOT / "config.example.yaml"))
    app_two = app_module.create_app(str(REPO_ROOT / "config.example.yaml"))
    paths_one = {route.path for route in app_one.routes if hasattr(route, "path")}
    paths_two = {route.path for route in app_two.routes if hasattr(route, "path")}
    require(paths_one == paths_two, (paths_one, paths_two))
    print("ok repeated create_app calls are deterministic with no import-time side effects")


def main() -> None:
    check_validation_helper_error_branches()
    check_validation_helper_success_path()
    check_runtime_artifact_context_equivalence()
    check_backend_request_error_response_shape()
    check_managed_route_http_behavior_unchanged()
    check_no_import_time_side_effects()
    print("relaylm_app_orchestration_extract_smoke: PASS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
