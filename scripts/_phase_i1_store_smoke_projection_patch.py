#!/usr/bin/env python3
from pathlib import Path

PATH = Path("scripts/relaylm_relaymem_store_dry_run_smoke.py")
body = PATH.read_text(encoding="utf-8")


def replace(old: str, new: str) -> None:
    global body
    if old not in body:
        raise SystemExit(f"missing patch anchor: {old!r}")
    body = body.replace(old, new, 1)


replace(
    '''    def last(self) -> dict[str, Any]:
        with self._lock:
            if not self.payloads:
                raise AssertionError("no backend payload captured")
            return self.payloads[-1]
''',
    '''    def last_chat_payload(self) -> dict[str, Any]:
        with self._lock:
            for payload in reversed(self.payloads):
                if isinstance(payload.get("messages"), list):
                    return payload
        raise AssertionError("no backend chat payload captured")
''',
)
replace(
    '''def _last_retrieval_artifact(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    record = json.loads(lines[-1])
    artifact = record.get("metadata", {}).get("relaymem_retrieval_artifact")
    require(isinstance(artifact, dict), record)
    return artifact
''',
    '''def _last_backend_response_metadata(trace_path: Path) -> dict[str, Any]:
    lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
    require(bool(lines), "trace is empty")
    for line in reversed(lines):
        record = json.loads(line)
        metadata = record.get("metadata") if isinstance(record, dict) else None
        if isinstance(metadata, dict) and metadata.get("event") == "backend_response":
            return metadata
    raise AssertionError("backend_response trace record is missing")


def _content_free_projection(metadata: dict[str, Any]) -> dict[str, Any]:
    require("relaymem_retrieval_artifact" not in metadata, "full retrieval artifact leaked")
    projection = metadata.get("relaymem_primary_recall_projection")
    require(isinstance(projection, dict), "primary recall projection missing")
    require(projection.get("content_free") is True, projection)
    require(projection.get("content_included") is False, projection)
    require(projection.get("memory_text_included") is False, projection)
    require(projection.get("path_values_included") is False, projection)
    require(projection.get("digest_values_included") is False, projection)
    require(projection.get("lineage_values_included") is False, projection)
    require(projection.get("idempotency_values_included") is False, projection)
    return projection
''',
)
replace(
    '''        "relaymem_store_diagnostics",
        "store_diagnostics",
        "ctx_block",
''',
    '''        "relaymem_store_diagnostics",
        "relaymem_primary_recall_projection",
        "store_diagnostics",
        "ctx_block",
''',
)
replace(
    '''                    artifact = _last_retrieval_artifact(trace_path)
                    store_diag = artifact.get("store_diagnostics")
                    require(isinstance(store_diag, dict), artifact)
                    require(store_diag["store_enabled"] is False, store_diag)
                    require(
                        store_diag["fallback_reason"] == "memory_store_disabled",
                        store_diag,
                    )
                    print("ok runtime artifact emits disabled store diagnostics")
''',
    '''                    metadata = _last_backend_response_metadata(trace_path)
                    projection = _content_free_projection(metadata)
                    require(projection["selected_count"] == 0, projection)
                    require(
                        projection["fallback_reason"] == "memory_store_disabled",
                        projection,
                    )
                    require(projection["injection_performed"] is False, projection)
                    print("ok runtime emits content-free disabled-store projection")
''',
)
replace(
    '''                    artifact = _last_retrieval_artifact(trace_path)
                    store_diag = artifact.get("store_diagnostics")
                    require(isinstance(store_diag, dict), artifact)
                    require(store_diag["store_enabled"] is True, store_diag)
                    require(store_diag["index_present"] is True, store_diag)
                    require(store_diag["pages_discovered"] > 0, store_diag)
                    require(store_diag["validation"]["full_tree_materialized"] is False, store_diag)
                    require(store_diag["validation"]["full_file_reads"] is False, store_diag)
                    require(artifact["selected"] == [], artifact)
                    require(artifact["ctx_block"] is None, artifact)
                    _assert_no_backend_artifact(capture.last())
                    require(
                        capture.last().get("metadata") == payload["metadata"],
                        capture.last(),
                    )
                    print("ok runtime artifact includes store diagnostics without mutation")
''',
    '''                    metadata = _last_backend_response_metadata(trace_path)
                    projection = _content_free_projection(metadata)
                    require(projection["selected_count"] == 0, projection)
                    require(projection["memory_used"] is False, projection)
                    require(projection["injection_performed"] is False, projection)
                    backend_payload = capture.last_chat_payload()
                    _assert_no_backend_artifact(backend_payload)
                    require(
                        backend_payload.get("metadata") == payload["metadata"],
                        "backend metadata changed",
                    )
                    print("ok runtime store status is content-free and non-mutating")
''',
)
PATH.write_text(body, encoding="utf-8")
