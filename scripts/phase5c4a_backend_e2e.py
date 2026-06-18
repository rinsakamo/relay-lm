#!/usr/bin/env python3
"""Bounded instruction-bearing backend integration smoke."""
from __future__ import annotations

import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import relaylm_client_history_exclusion_apply_forward_gate_smoke as gate
from phase5c4a_explicit_smoke_support import payload


def check(backend, request, included, excluded) -> None:
    messages = backend["messages"]
    assert len(messages) == 2
    assert messages[-1] == request["messages"][-1]
    prefix = messages[0]["content"]
    for value in included:
        assert prefix.count(value) == 1
    for value in excluded:
        assert value not in prefix
    assert "relaylm" not in backend
    for key in (
        "stream",
        "temperature",
        "top_p",
        "max_tokens",
        "tools",
        "tool_choice",
        "response_format",
        "provider_options",
    ):
        assert backend[key] == request[key]


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), gate._BackendHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as td:
            root = Path(td)
            cases = (
                (
                    payload(
                        [("system", "selected system sentinel"), ("system", "frontend summary sentinel")],
                        selected_instruction_indices=[0],
                    ),
                    ("selected system sentinel",),
                    ("frontend summary sentinel", "prior user sentinel", "prior assistant sentinel"),
                ),
                (
                    payload(
                        [
                            ("developer", "selected developer sentinel"),
                            ("system", "frontend memory note sentinel"),
                            ("system", "selected stream system sentinel"),
                        ],
                        selected_instruction_indices=[0, 2],
                        stream=True,
                    ),
                    ("selected developer sentinel", "selected stream system sentinel"),
                    ("frontend memory note sentinel", "prior user sentinel", "prior assistant sentinel"),
                ),
            )
            for index, (request, included, excluded) in enumerate(cases):
                original = gate._payload
                gate._payload = lambda **kwargs: request
                try:
                    _, backend, _ = gate._run_success_case(
                        root,
                        name=f"e2e_{index}",
                        port=int(server.server_address[1]),
                        enabled=True,
                        dry_run_only=False,
                        mode="memory_light",
                    )
                finally:
                    gate._payload = original
                check(backend, request, included, excluded)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print("phase5c4a_backend_e2e passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
