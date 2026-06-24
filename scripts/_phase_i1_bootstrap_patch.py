#!/usr/bin/env python3
"""One-shot branch patcher used because the execution environment has no git clone."""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    body = target.read_text(encoding="utf-8")
    if new in body:
        return
    if body.count(old) != 1:
        raise RuntimeError(f"{path}: expected one patch anchor, got {body.count(old)}")
    target.write_text(body.replace(old, new), encoding="utf-8")


def append_once(path: str, marker: str, section: str) -> None:
    target = ROOT / path
    body = target.read_text(encoding="utf-8")
    if marker in body:
        return
    target.write_text(body.rstrip() + "\n\n" + section.strip() + "\n", encoding="utf-8")


replace_once(
    "relaylm/app.py",
    "from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact\n",
    "from relaylm.relaymem_retrieval import build_relaymem_retrieval_dry_run_artifact\n"
    "from relaylm.relaymem_primary_recall import (\n"
    "    apply_relaymem_primary_recall_scope,\n"
    "    resolve_relaymem_character_store_root,\n"
    ")\n",
)

old_runtime = '''        relaymem_store_diagnostics = build_relaymem_store_diagnostics(
            root_path=config.memory.root_path,
            store_enabled=config.memory.store_enabled,
            retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
        )
        relaymem_retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayref_artifact=relayref_artifact,
            messages=_extract_trace_messages(payload),
            token_budget=_resolve_relaymem_retrieval_token_budget(config),
            store_diagnostics=relaymem_store_diagnostics,
            max_candidates=config.memory.candidate_limit,
            ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
            snippet_extraction_enabled=config.memory.snippet_extraction_enabled,
            snippet_dry_run_only=config.memory.snippet_dry_run_only,
            snippet_apply_enabled=config.memory.snippet_apply_enabled,
            snippet_budget=config.memory.snippet_budget,
            max_snippet_chars=config.memory.max_snippet_chars,
            max_snippet_candidates=config.memory.max_snippet_candidates,
        )
'''
new_runtime = '''        relaymem_scoped_store_root = resolve_relaymem_character_store_root(
            config.memory.root_path,
            route.character_id,
        )
        relaymem_store_diagnostics = build_relaymem_store_diagnostics(
            root_path=relaymem_scoped_store_root,
            store_enabled=config.memory.store_enabled,
            retrieval_dry_run_only=config.memory.retrieval_dry_run_only,
        )
        relaymem_retrieval_artifact = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact=relayscn_scene_policy_artifact,
            relayref_artifact=relayref_artifact,
            messages=_extract_trace_messages(payload),
            token_budget=_resolve_relaymem_retrieval_token_budget(config),
            store_diagnostics=relaymem_store_diagnostics,
            max_candidates=config.memory.candidate_limit,
            ctx_block_apply_enabled=config.memory.ctx_block_apply_enabled,
            snippet_extraction_enabled=config.memory.snippet_extraction_enabled,
            snippet_dry_run_only=config.memory.snippet_dry_run_only,
            snippet_apply_enabled=config.memory.snippet_apply_enabled,
            snippet_budget=config.memory.snippet_budget,
            max_snippet_chars=config.memory.max_snippet_chars,
            max_snippet_candidates=config.memory.max_snippet_candidates,
        )
        relaymem_retrieval_artifact = apply_relaymem_primary_recall_scope(
            relaymem_retrieval_artifact,
            scoped_store_root=relaymem_scoped_store_root,
            expected_namespace=route.memory_namespace,
            max_snippet_chars=config.memory.max_snippet_chars,
            max_snippet_candidates=config.memory.max_snippet_candidates,
            snippet_budget=config.memory.snippet_budget,
            chars_per_token=config.memory.chars_per_token,
        )
'''
replace_once("relaylm/app.py", old_runtime, new_runtime)

# Current-boundary smoke: pin completed capabilities, not obsolete next wording.
replace_once(
    "scripts/relaylm_documentation_current_boundary_smoke.py",
    '"""Validate current Phase 6-C2 status without pinning obsolete future wording."""',
    '"""Validate completed Phase I-1 status without pinning later product wording."""',
)
replace_once(
    "scripts/relaylm_documentation_current_boundary_smoke.py",
    '        "next-turn recall and scope isolation: next",',
    '        "I1 next-turn Primary MEM recall: complete",\n'
    '        "character and namespace isolation: complete",',
)
replace_once(
    "scripts/relaylm_documentation_current_boundary_smoke.py",
    '        "next-turn recall and scope isolation: next",',
    '        "I1 next-turn Primary MEM recall: complete",\n'
    '        "character and namespace isolation: complete",',
)
replace_once(
    "scripts/relaylm_documentation_current_boundary_smoke.py",
    '        "Next-turn recall and scope isolation: next",',
    '        "I1 next-turn Primary MEM recall: complete",\n'
    '        "Character and namespace isolation: complete",',
)
replace_once(
    "scripts/relaylm_documentation_current_boundary_smoke.py",
    '        "next-turn recall and scope isolation",',
    '        "next-turn recall and scope isolation",\n'
    '        "Phase I-1 is complete",',
)

status_section = '''
## Phase I-1 completion boundary (2026-06-24)

- I1-B producer: complete
- B3 lifecycle: complete
- C1-0 through C1-5 complete
- C2 one-job claim/rehydrate/execute adapter: complete
- I1 next-turn Primary MEM recall: complete
- character and namespace isolation: complete
- SOUL Lab real observation: next
- auditable Correct operation: later

The ordinary second-turn path now resolves an opaque character partition below
the configured RelayMEM root, uses existing M2 discovery, validates the exact
Primary page plus canonical index/log and namespace, and hands only bounded
request-local summary evidence to the existing RelayCTX snippet injection path.
Queue scanning/scheduling, daemon lifecycle, the pre-enqueue background-finalizer
crash window, Secondary MEM consolidation, SOUL mutation, and TTS/Live2D remain
outside this completion claim.
'''
append_once("docs/PROJECT_STATUS.md", "## Phase I-1 completion boundary (2026-06-24)", status_section)

plan_section = '''
## Phase I-1 Primary MEM next-turn recall — complete

Phase 6-C1-0 through C1-5 are complete. Phase 6-C2 one-job
claim/rehydrate/execute adapter: complete. I1 next-turn Primary MEM recall:
complete. character and namespace isolation: complete.

Turn 2 uses the configured root's opaque character partition, existing M2
selection, strict Primary page/index/log/namespace verification, and existing
RelayCTX bounded snippet injection. It does not introduce a parallel retriever
or synchronously wait for the Turn 1 worker. SOUL Lab real observation is next;
auditable Correct operation is later.
'''
append_once(
    "docs/architecture/pipeline_implementation_plan.md",
    "## Phase I-1 Primary MEM next-turn recall — complete",
    plan_section,
)

slp_section = '''
## Phase I-1 recall handoff

I1 next-turn Primary MEM recall: complete. Character and namespace isolation:
complete. C2 remains an explicit one-record integration seam; it is not a queue
scanner or daemon. The C2 caller and ordinary request retrieval share the
character-partition resolver. Existing M2 selection is narrowed by canonical
page/index/log/namespace validation before bounded RelayCTX injection.

The pre-enqueue background-finalizer crash window remains unresolved. SOUL Lab
real observation is next and auditable Correct operation is later.
'''
append_once(
    "docs/architecture/relaymem_slp_current_target.md",
    "## Phase I-1 recall handoff",
    slp_section,
)

c2_section = '''
## Phase I-1 downstream completion

Phase I-1 is complete. The C2 `store_root` supplied by a production caller is
resolved with the same opaque character-partition function used by ordinary
Turn 2 retrieval. C2 itself remains unchanged: exact queued B3 record,
canonical B3 claim, C1-5 protected-source lookup / rehydrate, and unchanged
C1-2 one-claimed worker. Queue scanning/scheduling and pre-enqueue
background-finalizer crash recovery remain out of scope.
'''
append_once(
    "docs/architecture/phase6c2_one_queued_primary_worker_integration.md",
    "## Phase I-1 downstream completion",
    c2_section,
)

shared_sections = {
    "docs/README.md": '''
## Integration I1: next-turn Primary MEM recall

The two-turn ordinary managed path is complete: Turn 1 can publish and execute
one durable Primary MEM job through C2, and Turn 2 can select the resulting
memory through existing M2, validate character partition and namespace, and
inject bounded evidence through RelayCTX. See
[Integration I1 Primary MEM Two-Turn Recall](architecture/integration_i1_primary_mem_two_turn_recall.md).
''',
    "docs/architecture/README.md": '''
## Integration I1

- [Primary MEM two-turn recall](integration_i1_primary_mem_two_turn_recall.md):
  ordinary Turn 1 durable formation, ordinary Turn 2 scoped M2 selection,
  canonical page/index/log validation, and bounded RelayCTX injection.
''',
    "docs/architecture/relaymem_mvp_implementation_plan.md": '''
## Phase I-1 integration status

Primary MEM next-turn recall and character/namespace isolation are complete.
The implementation keeps M2 as discovery owner, validates durable M3 page,
index, and log state, deduplicates write identity, and injects only bounded
summary evidence. Secondary MEM consolidation and Lab correction remain later.
''',
    "docs/architecture/memory_lifecycle_design.md": '''
## Primary MEM next-turn use

A successfully reconciled Primary MEM may participate in a later ordinary
request only through its opaque character store partition, exact namespace,
canonical page/index/log linkage, and current RelaySCN retrieval gates. Run and
session are not added as new long-term restrictions. Held, blocked, failed,
malformed, conflicting, or unreconciled candidates are not injected.
''',
    "docs/architecture/context_packing_design.md": '''
## I1 bounded Primary MEM injection

RelayCTX receives a request-local selected-memory artifact after existing M2
selection and exact scope/integrity validation. Only bounded Primary summary
evidence is inserted before the latest user message. SOUL, OUTPUT_POLICY,
RELATIONSHIP_ANCHOR, Secondary MEM, and RelaySCN remain higher authority; path,
identity, lineage, retry, and control-file metadata are excluded from the
backend prompt and public diagnostics.
''',
    "docs/architecture/phase6_async_relayslp_bounded_slice.md": '''
## Phase I-1 downstream integration

The asynchronous slice now has a proven downstream consumer: an explicitly run
C2 job can durably form Primary MEM without delaying the visible Turn 1
response, and a later ordinary request can retrieve it through scoped M2 and
bounded RelayCTX injection. This does not add queue scanning, scheduling,
daemon lifecycle, or pre-enqueue crash recovery.
''',
}
for doc_path, section in shared_sections.items():
    marker = section.strip().splitlines()[0]
    append_once(doc_path, marker, section)

# Deterministic ordinary two-turn integration smoke.
(ROOT / "scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py").write_text(
    textwrap.dedent(r'''
    """Ordinary two-turn Primary MEM recall and restart smoke for Phase I-1."""
    from __future__ import annotations

    import json
    import tempfile
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from pathlib import Path
    from typing import Any

    import yaml
    from fastapi.testclient import TestClient

    from relaylm.app import create_app
    from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root
    from relaylm.relaymem_slp_one_queued_job_runner import (
        REQUEST_SCHEMA,
        RelayMEMSLPOneQueuedJobRunnerRequest,
        execute_one_queued_relaymem_slp_primary_job,
    )
    from relaylm.relaymem_slp_primary_worker_source_registry import (
        RelayMEMSLPPrimaryWorkerSourceRegistry,
    )
    from relaylm_phase6c1_primary_worker_test_support import prepare_store

    REPO_ROOT = Path(__file__).resolve().parents[1]
    CHARACTER = "default"
    OTHER_CHARACTER = "other"
    NAMESPACE = "phase-i1-recall"
    OTHER_NAMESPACE = "phase-i1-other"
    MEMORY_CANARY = "紅茶"


    def require(condition: bool, detail: object) -> None:
        if not condition:
            raise AssertionError(detail)


    class Backend(BaseHTTPRequestHandler):
        payloads: list[dict[str, Any]] = []
        lock = threading.Lock()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            with type(self).lock:
                type(self).payloads.append(payload)
            messages = payload.get("messages", [])
            latest_user = next(
                (
                    str(item.get("content", ""))
                    for item in reversed(messages)
                    if isinstance(item, dict) and item.get("role") == "user"
                ),
                "",
            )
            serialized = json.dumps(messages, ensure_ascii=False)
            if "覚えて" in latest_user:
                answer = "覚えました。"
            elif "[RelayMEM Snippet Context]" in serialized and MEMORY_CANARY in serialized:
                answer = f"好きな飲み物は{MEMORY_CANARY}です。"
            else:
                answer = "記憶からは確認できません。"
            body = {
                "id": "chatcmpl-phase-i1",
                "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
            }
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)


    def write_config(path: Path, *, port: int, queue: Path, protected: Path, store: Path) -> None:
        cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
        cfg["trace"] = {"enabled": False, "path": None}
        cfg["backends"]["local_backend"]["base_url"] = f"http://127.0.0.1:{port}/v1"
        base_route = cfg["model_routes"]["relaylm-default"]
        base_route.update(
            {
                "mode": "memory_light",
                "character_id": CHARACTER,
                "memory_namespace": NAMESPACE,
                "session_id": "phase-i1-session",
            }
        )
        cfg["characters"][OTHER_CHARACTER] = dict(cfg["characters"][CHARACTER])
        cfg["model_routes"]["relaylm-other-character"] = {
            **base_route,
            "character_id": OTHER_CHARACTER,
            "memory_namespace": NAMESPACE,
        }
        cfg["model_routes"]["relaylm-other-namespace"] = {
            **base_route,
            "character_id": CHARACTER,
            "memory_namespace": OTHER_NAMESPACE,
        }
        cfg["relayemo_enabled"] = False
        cfg["relaymem_slp_runtime_enqueue_enabled"] = True
        cfg["relaymem_slp_runtime_enqueue_dry_run_only"] = False
        cfg["relaymem_slp_runtime_enqueue_apply_enabled"] = True
        cfg["relaymem_slp_queue_root"] = str(queue.resolve())
        cfg["relaymem_slp_protected_source_root"] = str(protected.resolve())
        cfg["memory"].update(
            {
                "root_path": str(store.resolve()),
                "store_enabled": True,
                "retrieval_dry_run_only": False,
                "ctx_block_apply_enabled": True,
                "snippet_extraction_enabled": True,
                "snippet_dry_run_only": False,
                "snippet_apply_enabled": True,
                "snippet_runtime_injection_enabled": True,
                "snippet_runtime_dry_run_only": False,
                "candidate_limit": 8,
                "max_snippet_candidates": 3,
                "max_snippet_chars": 512,
                "snippet_budget": 512,
                "token_budget_truncation_enabled": False,
            }
        )
        path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


    def payload(model: str, text: str) -> dict[str, Any]:
        return {
            "model": model,
            "messages": [{"role": "user", "content": text}],
            "stream": False,
            "metadata": {
                "scene_state": {
                    "schema_version": "relayscn.scene_state.v0",
                    "scene_type": "design_talk",
                    "confidence": 0.99,
                    "stability": 0.99,
                    "signals": [],
                }
            },
        }


    def read_queued(queue: Path) -> dict[str, object]:
        files = list(queue.glob("slp-dispatch-v0-*.json"))
        require(len(files) == 1, files)
        value = json.loads(files[0].read_text(encoding="utf-8"))
        require(type(value) is dict and value.get("state") == "queued", value)
        return value


    def main() -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
                root = Path(directory)
                queue = root / "queue"
                protected = root / "protected"
                store = root / "store"
                queue.mkdir()
                protected.mkdir()
                store.mkdir()
                scoped_value = resolve_relaymem_character_store_root(str(store), CHARACTER)
                require(scoped_value is not None, "character scope")
                scoped = Path(scoped_value)
                prepare_store(scoped)
                config = root / "config.yaml"
                write_config(
                    config,
                    port=int(server.server_address[1]),
                    queue=queue,
                    protected=protected,
                    store=store,
                )

                producer_app = create_app(str(config))
                with TestClient(producer_app) as client:
                    first = client.post(
                        "/v1/chat/completions",
                        json=payload(
                            "relaylm-default",
                            f"私の 好きな飲み物 は {MEMORY_CANARY} です。覚えてください。",
                        ),
                    )
                require(first.status_code == 200, first.text)
                queued = read_queued(queue)

                # Simulate producer/process restart: C2 receives no hot registry state.
                result = execute_one_queued_relaymem_slp_primary_job(
                    RelayMEMSLPOneQueuedJobRunnerRequest(
                        schema_version=REQUEST_SCHEMA,
                        runtime_private=True,
                        content_included=False,
                        queued_record=dict(queued),
                        source_registry=RelayMEMSLPPrimaryWorkerSourceRegistry(),
                        character_id=CHARACTER,
                        queue_root=str(queue),
                        protected_source_root=str(protected),
                        store_root=str(scoped),
                        claim_owner="phase-i1-worker",
                        enabled=True,
                        dry_run_only=False,
                        apply_enabled=True,
                        lease_duration_seconds=300,
                    )
                )
                require(result.status == "worker_completed", result.to_log_dict())
                require(result.worker_status == "terminal_succeeded", result.to_log_dict())
                require(result.restart_rehydrated, result.to_log_dict())

                # A fresh request runtime reads only the durable store.
                recall_app = create_app(str(config))
                with TestClient(recall_app) as client:
                    second = client.post(
                        "/v1/chat/completions",
                        json=payload("relaylm-default", "好きな飲み物 を教えてください。"),
                    )
                    wrong_character = client.post(
                        "/v1/chat/completions",
                        json=payload("relaylm-other-character", "好きな飲み物 を教えてください。"),
                    )
                    wrong_namespace = client.post(
                        "/v1/chat/completions",
                        json=payload("relaylm-other-namespace", "好きな飲み物 を教えてください。"),
                    )
                require(second.status_code == 200, second.text)
                require(MEMORY_CANARY in second.json()["choices"][0]["message"]["content"], second.json())
                require(
                    wrong_character.json()["choices"][0]["message"]["content"] == "記憶からは確認できません。",
                    wrong_character.json(),
                )
                require(
                    wrong_namespace.json()["choices"][0]["message"]["content"] == "記憶からは確認できません。",
                    wrong_namespace.json(),
                )
                payloads = Backend.payloads[-3:]
                correct_serialized = json.dumps(payloads[0].get("messages"), ensure_ascii=False)
                wrong_char_serialized = json.dumps(payloads[1].get("messages"), ensure_ascii=False)
                wrong_ns_serialized = json.dumps(payloads[2].get("messages"), ensure_ascii=False)
                require("[RelayMEM Snippet Context]" in correct_serialized, "missing injected context")
                require(MEMORY_CANARY in correct_serialized, "missing memory evidence")
                require("[RelayMEM Snippet Context]" not in wrong_char_serialized, "wrong-character leak")
                require("[RelayMEM Snippet Context]" not in wrong_ns_serialized, "wrong-namespace leak")
                require("slp-dispatch-v0:" not in correct_serialized, "dispatch metadata leaked")
                require("lineage_fingerprint" not in correct_serialized, "lineage metadata leaked")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        print("Phase I-1 two-turn Primary MEM recall smoke passed")


    if __name__ == "__main__":
        main()
    ''').lstrip(),
    encoding="utf-8",
)

# Direct scope/security smoke for corrupt, duplicate, unrelated, and bounded cases.
(ROOT / "scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py").write_text(
    textwrap.dedent(r'''
    """Security and fail-closed smoke for Phase I-1 scoped recall."""
    from __future__ import annotations

    import json
    import os
    import tempfile
    from hashlib import sha256
    from pathlib import Path

    from relaylm._relaymem_primary_page_writer_common import stable_hash
    from relaylm.relaymem_primary_recall import (
        apply_relaymem_primary_recall_scope,
        resolve_relaymem_character_store_root,
    )
    from relaylm_phase6c1_primary_worker_test_support import prepare_store

    CHARACTER = "security-a"
    OTHER_CHARACTER = "security-b"
    NAMESPACE = "security-namespace-canary"
    SUMMARY = "好きな飲み物 は 紅茶 です。"


    def require(condition: bool, detail: object) -> None:
        if not condition:
            raise AssertionError(detail)


    def broad(path: str, *, decision: str = "eligible_but_not_applied", duplicate: bool = False) -> dict[str, object]:
        candidate = {
            "path": path,
            "source": "mem_page",
            "reason": "keyword_match",
            "estimated_chars": len(SUMMARY),
            "estimated_tokens": 8,
            "memory_layer": "primary",
            "layout_profile": "target_primary_secondary",
            "applied_to_ctx": False,
        }
        return {
            "artifact_version": "relaymem_retrieval.v0",
            "snippet_apply_decision": decision,
            "selected_mem_candidates": [candidate, dict(candidate)] if duplicate else [candidate],
        }


    def write_memory(root: Path) -> str:
        identity = sha256(b"phase-i1-security-memory").hexdigest()
        lineage = sha256(b"phase-i1-security-lineage").hexdigest()
        relative = f"memory/mem/primary/relationships/{identity}.md"
        metadata = {
            "summary": SUMMARY,
            "schema_version": "relaymem.primary_page.v0",
            "memory_layer": "primary",
            "memory_kind": "relationship_moment",
            "source_event_kind": "turn",
            "promotion_policy": "free_to_update",
            "safety_scope": "ordinary_memory",
            "namespace": NAMESPACE,
            "lineage_fingerprint": lineage,
            "idempotency_key": identity,
            "summary_origin": "trusted_in_process_summary",
            "content_role": "evidence",
            "title": "飲み物",
        }
        page = "---\n" + "\n".join(
            f"{key}: {json.dumps(str(value), ensure_ascii=False)}" for key, value in metadata.items()
        ) + f"\n---\n# Primary memory\n\n## Summary\n\n{SUMMARY}\n"
        page_path = root / relative
        page_path.write_text(page, encoding="utf-8")
        digest = sha256(page.encode("utf-8")).hexdigest()
        index_id = stable_hash(("relaymem-primary-index-entry-v0", identity, digest, relative))
        log_id = stable_hash(("relaymem-primary-log-entry-v0", identity, digest, relative))
        index_entry = {
            "schema_version": "relaymem.primary_index_entry.v0",
            "entry_id": index_id,
            "page_relative_path": relative,
            "memory_layer": "primary",
            "memory_kind": "relationship_moment",
            "target_category": "primary_relationships",
            "namespace": NAMESPACE,
            "source_event_kind": "turn",
            "promotion_policy": "free_to_update",
            "safety_scope": "ordinary_memory",
            "idempotency_key": identity,
            "page_digest": digest,
        }
        log_entry = {
            "schema_version": "relaymem.primary_log_entry.v0",
            "entry_id": log_id,
            "index_entry_id": index_id,
            "operation": "primary_page_published",
            "page_relative_path": relative,
            "memory_layer": "primary",
            "memory_kind": "relationship_moment",
            "target_category": "primary_relationships",
            "namespace": NAMESPACE,
            "source_event_kind": "turn",
            "promotion_policy": "free_to_update",
            "safety_scope": "ordinary_memory",
            "lineage_fingerprint": lineage,
            "idempotency_key": identity,
            "page_digest": digest,
        }
        (root / "memory/mem/index.md").write_text(
            "# Index\n<!-- relaymem-primary-index-entry-v0 "
            + json.dumps(index_entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + " -->\n",
            encoding="utf-8",
        )
        (root / "memory/mem/log.md").write_text(
            "# Log\n<!-- relaymem-primary-log-entry-v0 "
            + json.dumps(log_entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + " -->\n",
            encoding="utf-8",
        )
        return relative


    def apply(value: dict[str, object], root: Path, namespace: str = NAMESPACE, max_chars: int = 512) -> dict[str, object]:
        return apply_relaymem_primary_recall_scope(
            value,
            scoped_store_root=str(root),
            expected_namespace=namespace,
            max_snippet_chars=max_chars,
            max_snippet_candidates=3,
            snippet_budget=512,
            chars_per_token=4,
        )


    def main() -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first_value = resolve_relaymem_character_store_root(str(base), CHARACTER)
            other_value = resolve_relaymem_character_store_root(str(base), OTHER_CHARACTER)
            require(first_value is not None and other_value is not None, "scope resolver")
            first = Path(first_value)
            other = Path(other_value)
            prepare_store(first)
            prepare_store(other)
            relative = write_memory(first)

            valid = apply(broad(relative, duplicate=True), first)
            runtime = valid["primary_recall_runtime"]
            projection = valid["primary_recall_projection"]
            require(runtime["selected_count"] == 1, runtime)
            require(projection["selected_count"] == 1, projection)
            require(valid["snippet_runtime_injection_plan"]["preview_text"], valid)
            public_text = repr(projection)
            for forbidden in (SUMMARY, NAMESPACE, relative, "idempotency_key", "lineage_fingerprint"):
                require(forbidden not in public_text, (forbidden, public_text))

            wrong_namespace = apply(broad(relative), first, "wrong-namespace")
            require(wrong_namespace["primary_recall_projection"]["selected_count"] == 0, wrong_namespace)
            wrong_character = apply(broad(relative), other)
            require(wrong_character["primary_recall_projection"]["selected_count"] == 0, wrong_character)
            blocked_scene = apply(broad(relative, decision="blocked_scene_policy"), first)
            require(blocked_scene["primary_recall_projection"]["selected_count"] == 0, blocked_scene)
            bounded = apply(broad(relative), first, max_chars=4)
            require(bounded["primary_recall_projection"]["selected_count"] == 0, bounded)

            page = first / relative
            original = page.read_bytes()
            page.write_bytes(original + b"corrupt")
            corrupt = apply(broad(relative), first)
            require(corrupt["primary_recall_projection"]["selected_count"] == 0, corrupt)
            page.write_bytes(original)

            index = first / "memory/mem/index.md"
            original_index = index.read_text(encoding="utf-8")
            index.write_text("# Index\n", encoding="utf-8")
            mismatch = apply(broad(relative), first)
            require(mismatch["primary_recall_projection"]["selected_count"] == 0, mismatch)
            index.write_text(original_index, encoding="utf-8")

            if hasattr(os, "symlink"):
                real = page.with_suffix(".real.md")
                page.rename(real)
                try:
                    page.symlink_to(real.name)
                    linked = apply(broad(relative), first)
                    require(linked["primary_recall_projection"]["selected_count"] == 0, linked)
                finally:
                    if page.is_symlink():
                        page.unlink()
                    real.rename(page)
        print("Phase I-1 scoped recall security smoke passed")


    if __name__ == "__main__":
        main()
    ''').lstrip(),
    encoding="utf-8",
)

(ROOT / "scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py").write_text(
    textwrap.dedent('''
    """CI runner for Phase I-1 two-turn Primary MEM recall."""
    from __future__ import annotations

    import subprocess
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]


    def main() -> None:
        for script in (
            "scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py",
            "scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py",
            "scripts/relaylm_documentation_current_boundary_smoke.py",
        ):
            subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=True)
        print("Phase I-1 two-turn Primary MEM recall CI runner passed")


    if __name__ == "__main__":
        main()
    ''').lstrip(),
    encoding="utf-8",
)

(ROOT / ".github/workflows/phase-i1-two-turn-primary-recall-smoke.yml").write_text(
    textwrap.dedent('''
    name: Phase I-1 two-turn Primary MEM recall smoke

    on:
      push:
        paths:
          - "relaylm/**"
          - "scripts/relaylm_phase_i1_*"
          - "scripts/relaylm_documentation_current_boundary_smoke.py"
          - "docs/**"
          - ".github/workflows/phase-i1-two-turn-primary-recall-smoke.yml"
      pull_request:
        paths:
          - "relaylm/**"
          - "scripts/relaylm_phase_i1_*"
          - "scripts/relaylm_documentation_current_boundary_smoke.py"
          - "docs/**"
          - ".github/workflows/phase-i1-two-turn-primary-recall-smoke.yml"

    permissions:
      contents: read

    jobs:
      smoke:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: "3.12"
          - run: pip install -e .
          - run: python -m compileall -q relaylm scripts
          - run: PYTHONPATH=.:scripts python scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py
          - run: PYTHONPATH=. python scripts/relaylm_docs_link_check.py
          - run: PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_contract_smoke.py
          - run: PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_primary_worker_ci_runner.py
          - run: PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_worker_integration_ci_runner.py
          - run: PYTHONPATH=.:scripts python scripts/relaylm_phase6c1_durable_protected_source_smoke.py
          - run: PYTHONPATH=.:scripts python scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py
    ''').lstrip(),
    encoding="utf-8",
)

# Bootstrap files must not remain in the feature branch.
(ROOT / ".github/workflows/_phase_i1_bootstrap.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)

subprocess.run(["python", "-m", "compileall", "-q", "relaylm", "scripts"], cwd=ROOT, check=True)
subprocess.run(
    ["python", "scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py"],
    cwd=ROOT,
    env={**__import__("os").environ, "PYTHONPATH": ".:scripts"},
    check=True,
)
subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT, check=True)
subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
subprocess.run(["git", "commit", "-m", "feat: wire I1 Primary MEM next-turn recall"], cwd=ROOT, check=True)
subprocess.run(["git", "push", "origin", "HEAD:phase-i1-primary-mem-next-turn-recall"], cwd=ROOT, check=True)
