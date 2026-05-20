from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.diagnostics import RequestDiagnostics


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    diagnostics = RequestDiagnostics(
        request_id="request-001",
        route_model="relaylm-default",
        backend_model="local-model",
        backend_name="local_backend",
        character_id="default",
        mode_requested="pass_through",
        mode_applied="pass_through",
        stream_enabled=False,
        compiler_used=False,
    )

    headers = diagnostics.to_headers()
    require(headers["x-relaylm-request-id"] == "request-001", f"bad request id header: {headers}")
    require(headers["x-relaylm-mode"] == "pass_through", f"bad mode header: {headers}")
    require("x-relaylm-fallback-reason" not in headers, f"unexpected fallback header: {headers}")
    print("ok diagnostics headers")

    payload = diagnostics.to_log_dict()
    require(payload["request_id"] == "request-001", f"bad request_id: {payload}")
    require(payload["route_model"] == "relaylm-default", f"bad route_model: {payload}")
    require(payload["backend_model"] == "local-model", f"bad backend_model: {payload}")
    require(payload["backend_name"] == "local_backend", f"bad backend_name: {payload}")
    require(payload["character_id"] == "default", f"bad character_id: {payload}")
    require(payload["mode_applied"] == "pass_through", f"bad mode_applied: {payload}")
    require(payload["stream_enabled"] is False, f"bad stream_enabled: {payload}")
    require(payload["compiler_used"] is False, f"bad compiler_used: {payload}")
    print("ok diagnostics log payload")

    fallback = RequestDiagnostics(
        request_id="request-002",
        mode_applied="pass_through",
        fallback_reason="route_not_found",
    )
    fallback_headers = fallback.to_headers()
    require(
        fallback_headers["x-relaylm-fallback-reason"] == "route_not_found",
        f"bad fallback header: {fallback_headers}",
    )
    print("ok fallback header")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
