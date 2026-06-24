#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if old not in body:
        raise SystemExit(f"missing patch anchor in {path}: {old[:120]!r}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


selection = "scripts/relaylm_relaymem_selection_dry_run_smoke.py"
replace_once(
    selection,
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
replace_once(
    selection,
    '''def _post_and_get_artifact(
    client: TestClient,
    trace_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
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


def _post_and_get_projection(
    client: TestClient,
    trace_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post("/v1/chat/completions", json=payload)
    require(resp.status_code == 200, resp.text)
    metadata = _last_backend_response_metadata(trace_path)
    require("relaymem_retrieval_artifact" not in metadata, "full retrieval artifact leaked")
    projection = metadata.get("relaymem_primary_recall_projection")
    require(isinstance(projection, dict), metadata)
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
replace_once(
    selection,
    '''        "relaymem_retrieval_artifact",
        "selected_mem_candidates",
        "ctx_block",
        "store_diagnostics",
''',
    '''        "relaymem_retrieval_artifact",
        "relaymem_primary_recall_projection",
        "selected_mem_candidates",
        "ctx_block",
        "store_diagnostics",
''',
)
replace_once(
    selection,
    '''        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        port = int(server.server_address[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "disabled.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    store_root=store_root,
                    store_enabled=False,
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    artifact = _post_and_get_artifact(
                        client,
                        trace_path,
                        _scene_payload("design_talk", "RelayMEM retrieval"),
                    )
                    require(artifact["selected_mem_candidates"] == [], artifact)
                    require(artifact["selected"] == [], artifact)
                    print("ok disabled store has no selected mem candidates")

            with tempfile.TemporaryDirectory() as td:
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "enabled.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    store_root=store_root,
                    store_enabled=True,
                    candidate_limit=2,
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    design_payload = _scene_payload("design_talk", "RelayMEM retrieval")
                    design = _post_and_get_artifact(client, trace_path, design_payload)
                    candidates = design["selected_mem_candidates"]
                    require(0 < len(candidates) <= 2, design)
                    require(candidates[0]["source"] == "mem_page", design)
                    require(candidates[0]["applied_to_ctx"] is False, design)
                    require(design["ctx_block"] is None, design)
                    require(design["apply_allowed"] is False, design)
                    blocked_reasons = {item["reason"] for item in design["blocked"]}
                    require("malformed_or_unreadable_file" in blocked_reasons, design)
                    _assert_no_backend_artifact(capture.last())
                    require(
                        capture.last().get("metadata") == design_payload["metadata"],
                        capture.last(),
                    )
                    print("ok design scene emits selection dry-run candidates")

                    recovery = _post_and_get_artifact(
                        client,
                        trace_path,
                        _scene_payload("recovery", "何の話だったっけ"),
                    )
                    require(recovery["retrieval_scope"] == "current_context_only", recovery)
                    require(recovery["selected_mem_candidates"] == [], recovery)
                    print("ok recovery scene suppresses mem candidate selection")

                    for scene_type in ("formal_document", "medical_or_safety"):
                        artifact = _post_and_get_artifact(
                            client,
                            trace_path,
                            _scene_payload(scene_type, "RelayMEM evidence"),
                        )
                        require(artifact["selected_mem_candidates"] == [], artifact)
                    print("ok formal and medical scenes suppress mem candidate selection")

                    latest = _post_and_get_artifact(
                        client,
                        trace_path,
                        _scene_payload("design_talk", "RelayMEM trace check"),
                    )
                    require(isinstance(latest.get("selected_mem_candidates"), list), latest)
                    print("ok trace metadata includes selected_mem_candidates")
        finally:
            server.shutdown()
            server.server_close()
''',
    '''        capture = _Capture()
        _BackendHandler.capture = capture
        server = ThreadingHTTPServer(("127.0.0.1", 0), _BackendHandler)
        port = int(server.server_address[1])
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as td:
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "disabled.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    store_root=store_root,
                    store_enabled=False,
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    projection = _post_and_get_projection(
                        client,
                        trace_path,
                        _scene_payload("design_talk", "RelayMEM retrieval"),
                    )
                    require(projection["selected_count"] == 0, projection)
                    require(projection["fallback_reason"] == "memory_store_disabled", projection)
                    require(projection["injection_performed"] is False, projection)
                    print("ok disabled store emits a content-free zero-selection projection")

            with tempfile.TemporaryDirectory() as td:
                trace_path = Path(td) / "trace.jsonl"
                cfg_path = Path(td) / "enabled.yaml"
                _write_config(
                    cfg_path,
                    port=port,
                    trace_path=trace_path,
                    store_root=store_root,
                    store_enabled=True,
                    candidate_limit=2,
                )
                app = create_app(str(cfg_path))
                with TestClient(app) as client:
                    design_payload = _scene_payload("design_talk", "RelayMEM retrieval")
                    design = _post_and_get_projection(client, trace_path, design_payload)
                    require(design["selected_count"] == 0, design)
                    require(design["character_scope_resolved"] is False, design)
                    require(design["scope_matched"] is False, design)
                    require("legacy_flat_store_compatibility" in design["blocked_reason_ids"], design)
                    backend_payload = capture.last_chat_payload()
                    _assert_no_backend_artifact(backend_payload)
                    require(
                        backend_payload.get("metadata") == design_payload["metadata"],
                        "backend metadata changed",
                    )
                    print("ok legacy-flat runtime selection remains content-free and non-mutating")

                    recovery = _post_and_get_projection(
                        client,
                        trace_path,
                        _scene_payload("recovery", "何の話だったっけ"),
                    )
                    require(recovery["retrieval_scope"] == "current_context_only", recovery)
                    require(recovery["selected_count"] == 0, recovery)
                    print("ok recovery scene suppresses runtime selection")

                    for scene_type in ("formal_document", "medical_or_safety"):
                        projection = _post_and_get_projection(
                            client,
                            trace_path,
                            _scene_payload(scene_type, "RelayMEM evidence"),
                        )
                        require(projection["selected_count"] == 0, projection)
                        require(projection["persistence_block"] is True, projection)
                    print("ok formal and medical scenes suppress runtime selection")

                    latest = _post_and_get_projection(
                        client,
                        trace_path,
                        _scene_payload("design_talk", "RelayMEM trace check"),
                    )
                    require(latest["content_free"] is True, latest)
                    require(latest["selected_layer_counts"] == {"primary": 0}, latest)
                    print("ok trace metadata exposes only the content-free selection projection")
        finally:
            server.shutdown()
            server.server_close()
''',
)

ctx_plan = "scripts/relaylm_relaymem_ctx_injection_plan_dry_run_smoke.py"
replace_once(
    ctx_plan,
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
replace_once(
    ctx_plan,
    '''def _last_trace_artifact(trace_path: Path) -> dict[str, Any]:
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
    require(isinstance(projection, dict), metadata)
    require(projection.get("content_free") is True, projection)
    require(projection.get("content_included") is False, projection)
    require(projection.get("memory_text_included") is False, projection)
    require(projection.get("path_values_included") is False, projection)
    require(projection.get("backend_prompt_included") is False, projection)
    return projection
''',
)
replace_once(
    ctx_plan,
    '''        "relaymem_retrieval_artifact",
        "ctx_block",
''',
    '''        "relaymem_retrieval_artifact",
        "relaymem_primary_recall_projection",
        "ctx_block",
''',
)
replace_once(
    ctx_plan,
    '''                    traced = _last_trace_artifact(trace_path)
                    traced_plan = _assert_plan_baseline(traced)
                    require(traced_plan["preview_text"], traced_plan)
                    _assert_no_backend_artifact(capture.last())
                    print("ok trace metadata includes ctx_injection_plan without backend mutation")
''',
    '''                    metadata = _last_backend_response_metadata(trace_path)
                    projection = _content_free_projection(metadata)
                    require(projection["selected_count"] == 0, projection)
                    require(projection["character_scope_resolved"] is False, projection)
                    require(projection["injection_performed"] is False, projection)
                    require("legacy_flat_store_compatibility" in projection["blocked_reason_ids"], projection)
                    _assert_no_backend_artifact(capture.last_chat_payload())
                    print("ok trace exposes only content-free plan status without backend mutation")
''',
)
