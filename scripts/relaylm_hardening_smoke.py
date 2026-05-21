from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.memory_context import MemoryConfigurationError
from relaylm.request_compiler import compile_chat_payload_if_enabled
from relaylm.routing import resolve_route
from relaylm.trace import append_trace_record, build_trace_record, read_trace_records
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        record = build_trace_record(
            trace_id="atomic-001",
            created_at="2026-05-21T00:00:00+00:00",
            character_id="default",
            route_model="relaylm-default",
            mode_applied="pass_through",
            compiler_used=False,
            messages=[{"role": "user", "content": "hello"}],
        )
        append_trace_record(trace_path, record)
        raw = trace_path.read_text(encoding="utf-8")
        require(raw.count("\n") == 1, raw)
        json.loads(raw.strip())
        require(read_trace_records(trace_path)[0].trace_id == "atomic-001", raw)
        print("ok atomic trace append line")

    config = load_config(REPO_ROOT / "config.example.yaml").model_copy(deep=True)
    config.trace.enabled = True
    config.trace.path = "/dev/null/relaylm_trace.jsonl"
    diagnostics = RequestDiagnostics(
        request_id="trace-fail-001",
        route_model="relaylm-default",
        character_id="default",
        mode_applied="pass_through",
        compiler_used=False,
        trace_enabled=True,
    )
    wrote = trace_runtime_event(
        config=config,
        diagnostics=diagnostics,
        messages=[{"role": "user", "content": "hello"}],
        metadata={"event": "backend_error"},
    )
    require(wrote is False, wrote)
    print("ok trace write failure swallowed")

    memory_config = load_config(REPO_ROOT / "config.example.yaml").model_copy(deep=True)
    memory_config.model_routes["relaylm-default"].mode = "memory_light"
    memory_config.characters["default"].memory_seed_path = "/tmp/relaylm_missing_memory_seed.yaml"
    route = resolve_route(memory_config, "relaylm-default")
    compiled = compile_chat_payload_if_enabled(
        config=memory_config,
        route=route,
        payload={
            "model": "relaylm-default",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )
    require(compiled.compiler_used is True, compiled)
    require(compiled.memory_block_used is False, compiled)
    require(compiled.memory_fallback_reason == "memory_seed_load_error:FileNotFoundError", compiled)
    require(compiled.payload["messages"][0]["role"] == "system", compiled.payload)
    require("<retrieved_memory>" not in compiled.payload["messages"][0]["content"], compiled.payload)
    print("ok memory seed failure fallback")

    bad_config = load_config(REPO_ROOT / "config.example.yaml").model_copy(deep=True)
    bad_config.model_routes["relaylm-default"].mode = "memory_light"
    bad_config.model_routes["relaylm-default"].character_id = "missing-character"
    bad_route = resolve_route(bad_config, "relaylm-default")
    try:
        compile_chat_payload_if_enabled(
            config=bad_config,
            route=bad_route,
            payload={
                "model": "relaylm-default",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
            },
        )
    except MemoryConfigurationError:
        print("ok memory configuration error preserved")
    else:
        raise AssertionError("expected MemoryConfigurationError")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
