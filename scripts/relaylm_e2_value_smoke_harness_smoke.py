#!/usr/bin/env python3
"""Harness-health smoke for the E2 value smoke comparison harness.

This smoke validates only harness health, never conversation quality:

- both runs complete against stub OpenAI-compatible endpoints;
- run A / run B turn counts match the scenario;
- both runs send the same model-controlled sampling parameters;
- the artifact contains every required section and per-turn probe note;
- the human-judgment section is generated blank;
- the artifact lands under ``local/value_smoke/`` and is gitignored;
- no new file appears in the git-visible tree;
- backend failure fails closed without writing an artifact;
- the shipped scenarios parse with 8-12 probe-annotated turns.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from relaylm_e2_value_smoke import (
    ARTIFACT_DIR,
    ARTIFACT_REQUIRED_SECTIONS,
    JUDGMENT_FIELD_LINES,
    JUDGMENT_INVALID_IF_BLANK_NOTE,
    E2ValueSmokeError,
    load_scenario,
    run_value_smoke,
)

SCENARIO_DIR = REPO_ROOT / "examples" / "value_smoke"
SHIPPED_SCENARIOS = (
    SCENARIO_DIR / "scenario_01_memory_recall.yaml",
    SCENARIO_DIR / "scenario_02_persona_stability.yaml",
)


class _Capture:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.payloads.append(payload)


def _make_stub_server(
    label: str, capture: _Capture, *, status: int = 200
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/chat/completions":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            capture.add(payload)
            if status != 200:
                body = b'{"error":"stub failure"}'
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            user_turns = sum(
                1 for message in payload.get("messages", []) if message.get("role") == "user"
            )
            reply = f"{label} stub reply turn={user_turns}"
            body = json.dumps(
                {
                    "id": "chatcmpl-e2-stub",
                    "object": "chat.completion",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": reply},
                            "finish_reason": "stop",
                        }
                    ],
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _write_stub_config(tmp: Path, backend_base_url: str) -> Path:
    profile_dir = tmp / "profiles"
    profile_dir.mkdir()
    (profile_dir / "SOUL.md").write_text("# Stub SOUL\n", encoding="utf-8")
    (profile_dir / "OUTPUT_POLICY.md").write_text("# Stub policy\n", encoding="utf-8")
    config_path = tmp / "config.yaml"
    config_path.write_text(
        "mode: memory_light\n"
        "listen:\n"
        "  host: 127.0.0.1\n"
        "  port: 8090\n"
        "backends:\n"
        "  stub_backend:\n"
        "    type: openai_compatible\n"
        f"    base_url: {backend_base_url}\n"
        "    api_key: stub-key\n"
        "    default_model: stub-model\n"
        "model_routes:\n"
        "  relaylm-e2-stub:\n"
        "    backend: stub_backend\n"
        "    backend_model: stub-model\n"
        "    character_id: e2_stub\n"
        "    mode: memory_light\n"
        "characters:\n"
        "  e2_stub:\n"
        f"    soul: {profile_dir.as_posix()}/SOUL.md\n"
        f"    output_policy: {profile_dir.as_posix()}/OUTPUT_POLICY.md\n",
        encoding="utf-8",
    )
    return config_path


def _git_visible_tree() -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _assert_shipped_scenarios() -> None:
    for scenario_path in SHIPPED_SCENARIOS:
        scenario = load_scenario(scenario_path)
        assert 8 <= len(scenario.turns) <= 12, scenario_path
        assert all(turn.user and turn.probe for turn in scenario.turns), scenario_path


def _assert_scenario_validation(tmp: Path) -> None:
    bad_id = tmp / "bad_id.yaml"
    bad_id.write_text(
        "scenario_id: '../escape'\nturns:\n"
        + "".join(f"  - {{user: u{i}, probe: p{i}}}\n" for i in range(8)),
        encoding="utf-8",
    )
    try:
        load_scenario(bad_id)
        raise AssertionError("path-escaping scenario_id must be rejected")
    except E2ValueSmokeError:
        pass

    too_short = tmp / "too_short.yaml"
    too_short.write_text(
        "scenario_id: too_short\nturns:\n  - {user: hi, probe: p}\n",
        encoding="utf-8",
    )
    try:
        load_scenario(too_short)
        raise AssertionError("single-turn scenario must be rejected")
    except E2ValueSmokeError:
        pass

    missing_probe = tmp / "missing_probe.yaml"
    missing_probe.write_text(
        "scenario_id: missing_probe\nturns:\n"
        + "".join(f"  - {{user: u{i}}}\n" for i in range(8)),
        encoding="utf-8",
    )
    try:
        load_scenario(missing_probe)
        raise AssertionError("probe-less turn must be rejected")
    except E2ValueSmokeError:
        pass


def _assert_artifact(artifact_path: Path, turn_count: int) -> None:
    assert artifact_path.is_file(), artifact_path
    assert artifact_path.parent == ARTIFACT_DIR.resolve(), artifact_path
    body = artifact_path.read_text(encoding="utf-8")

    for section in ARTIFACT_REQUIRED_SECTIONS:
        assert section in body, f"missing artifact section: {section}"
    assert JUDGMENT_INVALID_IF_BLANK_NOTE in body
    assert body.index(JUDGMENT_INVALID_IF_BLANK_NOTE) < body.index("### 4.1")

    assert body.count("### Turn ") == turn_count
    assert body.count("**Run A (RelayLM):**") == turn_count
    assert body.count("**Run B (direct baseline):**") == turn_count
    for index in range(1, turn_count + 1):
        assert f"run-a stub reply turn={index}" in body
        assert f"run-b stub reply turn={index}" in body

    scenario = load_scenario(SHIPPED_SCENARIOS[0])
    for turn in scenario.turns:
        assert f"- probe: {turn.probe}" in body, f"turn {turn.index} probe missing"

    lines = body.splitlines()
    for field in JUDGMENT_FIELD_LINES:
        blank_fields = [line for line in lines if line == field]
        assert blank_fields, f"blank judgment field missing: {field}"
    judgment_section = body[body.index("## 4. Human judgment") :]
    for line in judgment_section.splitlines():
        if line.startswith("- 判定") or line.startswith("- 根拠") or line.startswith("- RelayLM"):
            assert line.endswith(":"), f"judgment field is not blank: {line}"


def _assert_controlled_payloads(
    run_a: _Capture, run_b: _Capture, turn_count: int
) -> None:
    assert len(run_a.payloads) == turn_count
    assert len(run_b.payloads) == turn_count
    for index, (payload_a, payload_b) in enumerate(
        zip(run_a.payloads, run_b.payloads), start=1
    ):
        assert payload_a["model"] == "relaylm-e2-stub"
        assert payload_b["model"] == "stub-model"
        for key in ("temperature", "max_tokens", "seed", "stream"):
            assert payload_a.get(key) == payload_b.get(key), key
        assert payload_a["temperature"] == 0.3
        assert payload_a["seed"] == 7
        # A naive frontend stacks its own full history: 1, 3, 5, ... messages.
        assert len(payload_a["messages"]) == 2 * index - 1
        assert len(payload_b["messages"]) == 2 * index - 1
        roles = {message["role"] for message in payload_b["messages"]}
        assert "system" not in roles, "baseline run must not send a system message"
        user_texts_a = [
            message["content"]
            for message in payload_a["messages"]
            if message["role"] == "user"
        ]
        user_texts_b = [
            message["content"]
            for message in payload_b["messages"]
            if message["role"] == "user"
        ]
        assert user_texts_a == user_texts_b, "both runs must send identical user turns"


def main() -> None:
    _assert_shipped_scenarios()

    tree_before = _git_visible_tree()
    artifacts_before = (
        set(ARTIFACT_DIR.iterdir()) if ARTIFACT_DIR.is_dir() else set()
    )

    run_a_capture = _Capture()
    run_b_capture = _Capture()
    run_a_server = _make_stub_server("run-a", run_a_capture)
    run_b_server = _make_stub_server("run-b", run_b_capture)
    failing_server = _make_stub_server("run-a", _Capture(), status=500)
    artifact_path: Path | None = None
    try:
        run_a_url = f"http://127.0.0.1:{run_a_server.server_address[1]}/v1"
        run_b_url = f"http://127.0.0.1:{run_b_server.server_address[1]}/v1"
        failing_url = f"http://127.0.0.1:{failing_server.server_address[1]}/v1"

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _assert_scenario_validation(tmp)
            config_path = _write_stub_config(tmp, run_b_url)

            result = run_value_smoke(
                SHIPPED_SCENARIOS[0],
                config_path=config_path,
                relaylm_base_url=run_a_url,
                backend_base_url=run_b_url,
                temperature=0.3,
                seed=7,
                timeout_seconds=10.0,
            )
            artifact_path = result.artifact_path
            assert result.turn_count == result.run_a_turn_count == result.run_b_turn_count
            _assert_artifact(artifact_path, result.turn_count)
            _assert_controlled_payloads(run_a_capture, run_b_capture, result.turn_count)

            # A failing endpoint must fail closed without writing an artifact.
            artifacts_mid = set(ARTIFACT_DIR.iterdir())
            try:
                run_value_smoke(
                    SHIPPED_SCENARIOS[0],
                    config_path=config_path,
                    relaylm_base_url=failing_url,
                    backend_base_url=run_b_url,
                    timeout_seconds=10.0,
                )
                raise AssertionError("failing endpoint must raise E2ValueSmokeError")
            except E2ValueSmokeError:
                pass
            assert set(ARTIFACT_DIR.iterdir()) == artifacts_mid

        ignored = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", str(artifact_path)],
        )
        assert ignored.returncode == 0, "value smoke artifact must be gitignored"
        assert _git_visible_tree() == tree_before, (
            "harness run must not add files to the git-visible tree"
        )
    finally:
        run_a_server.shutdown()
        run_b_server.shutdown()
        failing_server.shutdown()
        if artifact_path is not None and artifact_path.exists():
            artifact_path.unlink()
        if ARTIFACT_DIR.is_dir():
            leftovers = set(ARTIFACT_DIR.iterdir()) - artifacts_before
            for leftover in leftovers:
                leftover.unlink()

    print("E2 value smoke harness smoke passed")


if __name__ == "__main__":
    main()
