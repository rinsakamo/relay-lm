from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import v1_external_qualification_exact_rc as exact_rc
from tools.v1_external_qualification_exact_rc import (
    ExactRCAdapterSession,
    ExactRCError,
    ExactRCInstallation,
    ExactRCServerSession,
    install_exact_rc,
)


def test_replaced_wheel_at_frozen_path_is_rejected_before_runtime_creation(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "relaylm-1.0.0rc1-py3-none-any.whl"
    wheel.write_bytes(b"replacement-bytes")
    runtime_root = tmp_path / "exact-rc-runtime"

    with pytest.raises(ExactRCError, match="SHA256 drifted"):
        install_exact_rc(
            wheel_path=wheel,
            wheel_sha256="0" * 64,
            expected_version="1.0.0rc1",
            expected_distribution="relaylm",
            checkout_root=tmp_path / "qualification-checkout",
            runtime_root=runtime_root,
        )

    assert not runtime_root.exists()


def _installation(tmp_path: Path) -> tuple[ExactRCInstallation, Path, str]:
    root = tmp_path / "exact-rc-runtime"
    console = root / "bin" / "relaylm"
    python = root / "bin" / "python"
    console.parent.mkdir(parents=True)
    console.write_text("#!/bin/sh\n", encoding="utf-8")
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    wheel = tmp_path / "relaylm-1.0.0rc1-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    config = tmp_path / "exact-rc.yaml"
    config.write_text("server: {}\n", encoding="utf-8")
    config_sha = hashlib.sha256(config.read_bytes()).hexdigest()
    return (
        ExactRCInstallation(
            python=python,
            console=console,
            root=root,
            dependency_overlay=root / "controlled-dependencies",
            wheel_path=wheel,
            wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
            version="1.0.0rc1",
            distribution="relaylm",
            import_origin=str(root / "lib/python3.12/site-packages/relaylm/__init__.py"),
        ),
        config,
        config_sha,
    )


class _Process:
    def __init__(self, returncode: int | None = None) -> None:
        self.returncode = returncode

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def kill(self) -> None:
        self.returncode = -9


class _Client:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.closed = False

    def get(self, url: str) -> SimpleNamespace:
        assert url.startswith("http://127.0.0.1:")
        return SimpleNamespace(status_code=self.status_code)

    def close(self) -> None:
        self.closed = True


def test_console_version_uses_installed_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    console = tmp_path / "relaylm"
    console.write_text("#!/bin/sh\n", encoding="utf-8")
    seen: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, "relaylm 1.0.0rc1\n", "")

    monkeypatch.setattr(exact_rc.subprocess, "run", fake_run)

    assert exact_rc._run_console_version(console) == "1.0.0rc1"
    assert seen == [[str(console), "--version"]]


def test_dependency_overlay_excludes_relaylm_and_pth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "persistent-site-packages"
    source.mkdir()
    (source / "httpx").mkdir()
    (source / "relaylm").mkdir()
    (source / "relaylm-1.0.0.dist-info").mkdir()
    (source / "dependency.py").write_text("value = 1\n", encoding="utf-8")
    (source / "override.pth").write_text("/untrusted/path\n", encoding="utf-8")
    monkeypatch.setattr(exact_rc.sysconfig, "get_paths", lambda: {"purelib": str(source)})

    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    overlay = exact_rc._prepare_dependency_overlay(runtime_root)

    assert (overlay / "httpx").is_dir()
    assert (overlay / "dependency.py").is_file()
    assert not (overlay / "relaylm").exists()
    assert not (overlay / "relaylm-1.0.0.dist-info").exists()
    assert not (overlay / "override.pth").exists()


def test_server_launch_uses_installed_console_not_module(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installation, config, config_sha = _installation(tmp_path)
    seen: list[list[str]] = []
    process = _Process()

    def fake_popen(command: list[str], **kwargs: object) -> _Process:
        seen.append(command)
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        assert environment["PYTHONPATH"] == str(installation.dependency_overlay)
        assert environment["PYTHONNOUSERSITE"] == "1"
        return process

    monkeypatch.setattr(exact_rc.subprocess, "Popen", fake_popen)
    session = ExactRCServerSession(
        installation,
        config_path=config,
        config_sha256=config_sha,
        port=18092,
    )
    session.client.close()
    session.client = _Client()

    session.start()
    cleanup = session.cleanup()

    assert seen[0][0] == str(installation.console.resolve())
    assert seen[0][1] == "serve"
    assert "relaylm.cli" not in seen[0]
    assert "-m" not in seen[0]
    assert cleanup["terminated"] is True
    assert cleanup["errors"] == []
    assert Path(str(cleanup["log_path"])).is_file()


def test_server_pre_health_exit_preserves_exit_code_and_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installation, config, config_sha = _installation(tmp_path)
    process = _Process(returncode=2)

    monkeypatch.setattr(
        exact_rc.subprocess,
        "Popen",
        lambda command, **kwargs: process,
    )
    session = ExactRCServerSession(
        installation,
        config_path=config,
        config_sha256=config_sha,
        port=18093,
    )
    session.client.close()
    session.client = _Client()

    with pytest.raises(ExactRCError, match=r"exit_code=2 log="):
        session.start()

    assert session.log_path.is_file()
    cleanup = session.cleanup()
    assert cleanup["exit_code"] == 2
    assert cleanup["log_path"] == str(session.log_path)
    assert cleanup["errors"] == []


class _LineInput:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, value: str) -> int:
        self.lines.append(value)
        return len(value)

    def flush(self) -> None:
        return None


class _LineOutput:
    def __init__(self, values: list[dict[str, object]]) -> None:
        self.values = list(values)

    def readline(self) -> str:
        if not self.values:
            return ""
        return json.dumps(self.values.pop(0), sort_keys=True) + "\n"


class _AdapterProcess:
    def __init__(self, values: list[dict[str, object]]) -> None:
        self.stdin = _LineInput()
        self.stdout = _LineOutput(values)
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9


def test_adapter_session_separates_installed_relaylm_from_checkout_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installation, config, config_sha = _installation(tmp_path)
    checkout = tmp_path / "qualification-checkout"
    (checkout / "tools").mkdir(parents=True)
    workspace = tmp_path / "adapter-workspace"
    process = _AdapterProcess(
        [
            {
                "protocol_version": 1,
                "status": "ready",
                "relaylm_version": installation.version,
                "relaylm_origin": installation.import_origin,
                "adapter_origin": str(
                    checkout / "tools" / "memconflict_adapter.py"
                ),
                "profile": "relaylm-exact-rc",
            },
            {
                "protocol_version": 1,
                "request_id": "exact-rc-00000001",
                "status": "ok",
                "external_evidence": {"answer": "synthetic"},
                "history_session_ids": ["session-0"],
                "new_history_session_count": 1,
                "new_history_pass2_calls": 1,
                "model_call_count": 3,
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "snapshot_fingerprint": "sha256:" + "1" * 64,
            },
            {"protocol_version": 1, "status": "closed"},
        ]
    )
    seen: list[tuple[list[str], dict[str, object]]] = []

    def fake_popen(command: list[str], **kwargs: object) -> _AdapterProcess:
        seen.append((command, kwargs))
        return process

    monkeypatch.setattr(exact_rc.subprocess, "Popen", fake_popen)
    session = ExactRCAdapterSession(
        installation,
        config_path=config,
        config_sha256=config_sha,
        checkout_root=checkout,
        workspace_root=workspace,
    )

    ready = session.start()
    result = session.query(
        axis_id="memconflict",
        question_id="Q_001",
        question="synthetic question",
        sessions=[
            {
                "session_id": "session-0",
                "order": 0,
                "items": [
                    {
                        "role": "user",
                        "content": "history",
                        "timestamp": None,
                    }
                ],
            }
        ],
    )
    cleanup = session.cleanup()

    assert ready["relaylm_origin"] == installation.import_origin
    assert result["model_call_count"] == 3
    command, kwargs = seen[0]
    assert command[:3] == [
        str(installation.python),
        "-m",
        "tools.v1_external_qualification_exact_rc_adapter",
    ]
    environment = kwargs["env"]
    assert isinstance(environment, dict)
    pythonpath = environment["PYTHONPATH"].split(exact_rc.os.pathsep)
    assert pythonpath == [
        str(checkout.resolve()),
        str(installation.dependency_overlay.resolve()),
    ]
    assert str(checkout / "src") not in pythonpath
    sent = json.loads(process.stdin.lines[0])
    assert sent["axis_id"] == "memconflict"
    assert sent["question_id"] == "Q_001"
    assert sent["sessions"][0]["session_id"] == "session-0"
    assert cleanup["terminated"] is True
    assert cleanup["errors"] == []


def test_adapter_session_rejects_existing_workspace_before_child_launch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installation, config, config_sha = _installation(tmp_path)
    checkout = tmp_path / "qualification-checkout"
    checkout.mkdir()
    workspace = tmp_path / "adapter-workspace"
    workspace.mkdir()
    called = False

    def fail_popen(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(exact_rc.subprocess, "Popen", fail_popen)
    session = ExactRCAdapterSession(
        installation,
        config_path=config,
        config_sha256=config_sha,
        checkout_root=checkout,
        workspace_root=workspace,
    )

    with pytest.raises(ExactRCError, match="workspace must be fresh"):
        session.start()
    assert called is False
