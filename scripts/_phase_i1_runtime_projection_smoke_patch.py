#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if old not in body:
        raise SystemExit(f"missing patch anchor in {path}: {old[:120]!r}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


runtime = "scripts/relaylm_relaymem_runtime_ctx_injection_smoke.py"
replace_once(
    runtime,
    '''        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        require(bool(lines), "trace is empty")
        record = json.loads(lines[-1])
        metadata = record.get("metadata", {})
        result = metadata.get("runtime_ctx_injection_result")
        require(isinstance(result, dict), record)
        return result, metadata
''',
    '''        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        require(bool(lines), "trace is empty")
        metadata: dict[str, Any] | None = None
        for line in reversed(lines):
            record = json.loads(line)
            candidate = record.get("metadata") if isinstance(record, dict) else None
            if isinstance(candidate, dict) and candidate.get("event") == "backend_response":
                metadata = candidate
                break
        require(isinstance(metadata, dict), "backend_response trace record is missing")
        result = metadata.get("runtime_ctx_injection_result")
        require(isinstance(result, dict), metadata)
        return result, metadata
''',
)
for old in (
    '            require(default_result["payload_mutation_applied"] is False, default_result)\n',
    '            require(enabled_result["attempted"] is True, enabled_result)\n',
    '            require(enabled_result["payload_mutation_applied"] is True, enabled_result)\n',
    '            require(enabled_result["original_message_count"] == 1, enabled_result)\n',
    '            require(enabled_result["forwarded_message_count"] == 2, enabled_result)\n',
    '            require(overflow_result["attempted"] is True, overflow_result)\n',
    '            require(overflow_result["payload_mutation_applied"] is False, overflow_result)\n',
):
    replace_once(runtime, old, "")
replace_once(
    runtime,
    '''            require(
                overflow_result["original_message_count"]
                == overflow_result["forwarded_message_count"],
                overflow_result,
            )
''',
    "",
)

snippet = "scripts/relaylm_relaymem_snippet_runtime_injection_apply_smoke.py"
replace_once(
    snippet,
    '''        record = json.loads(trace_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        metadata = record.get("metadata", {})
        return capture.last(), metadata
''',
    '''        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        require(bool(lines), "trace is empty")
        metadata: dict[str, Any] | None = None
        for line in reversed(lines):
            record = json.loads(line)
            candidate = record.get("metadata") if isinstance(record, dict) else None
            if isinstance(candidate, dict) and candidate.get("event") == "backend_response":
                metadata = candidate
                break
        require(isinstance(metadata, dict), "backend_response trace record is missing")
        return capture.last(), metadata
''',
)
replace_once(
    snippet,
    '    require(result["payload_mutation_applied"] is True, result)\n',
    "",
)
