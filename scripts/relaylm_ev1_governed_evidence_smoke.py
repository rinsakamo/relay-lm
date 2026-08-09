#!/usr/bin/env python3
"""End-to-end EV-1 Governed Evidence runtime smoke.

Exercises the full managed-route request path (through the real FastAPI app,
with a mocked OpenAI-compatible backend) across the required feature
postures: disabled, dry-run, non-stream apply, streaming-apply fail-closed,
pass-through
exemption. Complements the focused unit/functional tests in
``tests/test_evidence_*.py``.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import httpx
import respx
import yaml
from fastapi.testclient import TestClient

from relaylm.app import create_app
from relaylm.evidence.store import EvidenceRecordStore

BACKEND_BASE_URL = "http://127.0.0.1:8000/v1"
BACKEND_CHAT_COMPLETIONS_URL = f"{BACKEND_BASE_URL}/chat/completions"

BACKEND_CHAT_RESPONSE = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1234567890,
    "model": "local-model",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello there!"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
}
STREAM_BODY = (
    b'data: {"id":"chatcmpl-i11","choices":[{"delta":{"content":"hi"}}]}\n\n'
    b"data: [DONE]\n\n"
)


def require(condition: bool, detail: Any) -> None:
    if not condition:
        raise AssertionError(detail)


def write_config(
    config_dir: Path,
    *,
    mode: str = "memory_light",
    evidence_enabled: bool = False,
    evidence_dry_run_only: bool = True,
    evidence_apply_enabled: bool = False,
    evidence_data_root: str | None = None,
) -> Path:
    config = {
        "backends": {
            "local_backend": {
                "type": "openai_compatible",
                "base_url": BACKEND_BASE_URL,
                "api_key": "dummy",
                "default_model": "local-model",
            }
        },
        "model_routes": {
            "relaylm-default": {
                "backend": "local_backend",
                "backend_model": "local-model",
                "mode": mode,
                "character_id": "char1",
                "memory_namespace": "ns1",
                "user_id": "user1",
            "session_id": "sess1",
            }
        },
        "evidence_capture_enabled": evidence_enabled,
        "evidence_capture_dry_run_only": evidence_dry_run_only,
        "evidence_capture_apply_enabled": evidence_apply_enabled,
        "evidence_data_root": evidence_data_root,
    }
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def chat_request(**overrides: object) -> dict:
    payload: dict = {
        "model": "relaylm-default",
        "messages": [{"role": "user", "content": "Hi, please help me today"}],
    }
    payload.update(overrides)
    return payload


def evidence_files(root: Path) -> list[Path]:
    return list(root.rglob("*.json")) if root.exists() else []


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1. disabled: no Contract 1 files, records, or behavior.
        evidence_root = tmp_path / "disabled" / "evidence"
        config_path = write_config(tmp_path / "disabled", evidence_enabled=False)
        client = TestClient(create_app(str(config_path)))
        with respx.mock(assert_all_called=False) as mock:
            mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
                return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
            )
            response = client.post("/v1/chat/completions", json=chat_request())
        require(response.status_code == 200, response.text)
        require(evidence_files(evidence_root) == [], "disabled posture wrote evidence files")
        print("PASS: feature disabled creates no Contract 1 files")

        # 2. dry-run: validation/plan available, no durable writes.
        evidence_root = tmp_path / "dryrun" / "evidence"
        config_path = write_config(
            tmp_path / "dryrun",
            evidence_enabled=True,
            evidence_dry_run_only=True,
            evidence_apply_enabled=False,
            evidence_data_root=str(evidence_root),
        )
        client = TestClient(create_app(str(config_path)))
        with respx.mock(assert_all_called=False) as mock:
            mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
                return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
            )
            response = client.post("/v1/chat/completions", json=chat_request())
        require(response.status_code == 200, response.text)
        require(evidence_files(evidence_root) == [], "dry-run posture wrote durable files")
        print("PASS: dry-run validates without durable writes")

        # 3. apply (non-stream): current managed user input and assistant
        #    response each become one admitted SourceEvent.
        evidence_root = tmp_path / "apply" / "evidence"
        config_path = write_config(
            tmp_path / "apply",
            evidence_enabled=True,
            evidence_dry_run_only=False,
            evidence_apply_enabled=True,
            evidence_data_root=str(evidence_root),
        )
        client = TestClient(create_app(str(config_path)))
        with respx.mock(assert_all_called=False) as mock:
            mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
                return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
            )
            response = client.post("/v1/chat/completions", json=chat_request())
        require(response.status_code == 200, response.text)
        store = EvidenceRecordStore(str(evidence_root))
        space_dirs = [path for path in evidence_root.iterdir() if path.is_dir()]
        require(len(space_dirs) == 1, f"expected exactly one evidence space, got {space_dirs}")
        evidence_space_id = space_dirs[0].name
        source_events_dir = space_dirs[0] / "records" / "source_event"
        source_event_files = list(source_events_dir.glob("*.json"))
        require(
            len(source_event_files) == 2,
            f"expected 2 admitted SourceEvents (user + assistant), got {len(source_event_files)}",
        )
        origins = set()
        for path in source_event_files:
            record = store.read_record(
                evidence_space_id=evidence_space_id,
                record_kind="source_event",
                record_id=path.stem,
            )
            origins.add(record["origin_kind"])
            # Canary: opaque IDs and manifest text must never leak the raw
            # request/response text as a recognizable substring of the ID.
            require("Hi, please help me today" not in path.stem, "canary leaked into filename")
        require(origins == {"participant", "assistant"}, origins)
        print("PASS: apply admits one user-origin and one assistant-origin SourceEvent")

        # 4. apply (stream): fail closed until cross-process Contract 1E
        #    recovery support is implemented.
        evidence_root = tmp_path / "apply_stream" / "evidence"
        config_path = write_config(
            tmp_path / "apply_stream",
            evidence_enabled=True,
            evidence_dry_run_only=False,
            evidence_apply_enabled=True,
            evidence_data_root=str(evidence_root),
        )
        client = TestClient(create_app(str(config_path)))
        with respx.mock(assert_all_called=False) as mock:
            mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
                return_value=httpx.Response(
                    200, content=STREAM_BODY, headers={"content-type": "text/event-stream"}
                )
            )
            response = client.post(
                "/v1/chat/completions", json=chat_request(stream=True)
            )
        require(response.status_code == 500, response.status_code)
        require(
            response.json()["error"]["type"] == "evidence_stream_capture_error",
            response.text,
        )
        space_dirs = [path for path in evidence_root.iterdir() if path.is_dir()]
        require(len(space_dirs) == 1, space_dirs)
        source_event_files = list((space_dirs[0] / "records" / "source_event").glob("*.json"))
        require(len(source_event_files) == 1, len(source_event_files))
        print("PASS: streaming apply fails closed before assistant output evidence")

        # 5. pass-through: no capture even with apply enabled.
        evidence_root = tmp_path / "passthrough" / "evidence"
        config_path = write_config(
            tmp_path / "passthrough",
            mode="pass_through",
            evidence_enabled=True,
            evidence_dry_run_only=False,
            evidence_apply_enabled=True,
            evidence_data_root=str(evidence_root),
        )
        client = TestClient(create_app(str(config_path)))
        with respx.mock(assert_all_called=False) as mock:
            mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
                return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
            )
            response = client.post("/v1/chat/completions", json=chat_request())
        require(response.status_code == 200, response.text)
        require(evidence_files(evidence_root) == [], "pass-through wrote evidence files")
        print("PASS: pass-through route creates no capture even with apply enabled")

        # 6. canary: no protected content in response headers.
        canary = "TOP-SECRET-CANARY-af92k"
        evidence_root = tmp_path / "canary" / "evidence"
        config_path = write_config(
            tmp_path / "canary",
            evidence_enabled=True,
            evidence_dry_run_only=False,
            evidence_apply_enabled=True,
            evidence_data_root=str(evidence_root),
        )
        client = TestClient(create_app(str(config_path)))
        with respx.mock(assert_all_called=False) as mock:
            mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
                return_value=httpx.Response(200, json=BACKEND_CHAT_RESPONSE)
            )
            response = client.post(
                "/v1/chat/completions",
                json=chat_request(messages=[{"role": "user", "content": canary}]),
            )
        require(response.status_code == 200, response.text)
        for value in response.headers.values():
            require(canary not in value, "canary leaked into response headers")
        print("PASS: no protected content leaks into response headers")

    print("\nContract 1 v7 EV-1 governed evidence smoke: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
