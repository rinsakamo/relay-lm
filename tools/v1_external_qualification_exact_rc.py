"""Installed-artifact boundary for the accepted RelayLM RC.

This module never builds RelayLM.  It verifies the immutable wheel bytes,
installs those exact bytes into a checkout-external environment, and proves
that the imported distribution comes from that environment rather than the
qualification checkout.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sysconfig
import time
import venv
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import httpx


class ExactRCError(RuntimeError):
    """The accepted RC artifact could not be proven or isolated."""


@dataclass(frozen=True, slots=True)
class ExactRCInstallation:
    python: Path
    console: Path
    root: Path
    dependency_overlay: Path
    wheel_path: Path
    wheel_sha256: str
    version: str
    distribution: str
    import_origin: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "python": str(self.python),
            "console": str(self.console),
            "root": str(self.root),
            "dependency_overlay": str(self.dependency_overlay),
            "wheel_path": str(self.wheel_path),
            "wheel_sha256": self.wheel_sha256,
            "version": self.version,
            "distribution": self.distribution,
            "import_origin": self.import_origin,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _python_path(root: Path) -> Path:
    path = root / "bin" / "python"
    if not path.is_file():
        path = root / "Scripts" / "python.exe"
    if not path.is_file():
        raise ExactRCError(f"isolated RC Python is missing: {path}")
    return path


def _console_path(root: Path) -> Path:
    candidates = (
        root / "bin" / "relaylm",
        root / "Scripts" / "relaylm.exe",
        root / "Scripts" / "relaylm",
    )
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise ExactRCError("isolated RC relaylm console entrypoint is missing")
    resolved = path.resolve()
    resolved_root = root.resolve()
    if resolved_root != resolved and resolved_root not in resolved.parents:
        raise ExactRCError("isolated RC console entrypoint escaped the runtime root")
    return resolved


def _prepare_dependency_overlay(runtime_root: Path) -> Path:
    """Copy only policy-controlled dependencies into the exact-RC runtime."""

    source = Path(sysconfig.get_paths()["purelib"]).resolve()
    if not source.is_dir():
        raise ExactRCError(f"persistent Python dependency source is unavailable: {source}")
    runtime_root = runtime_root.resolve()
    if runtime_root == source or runtime_root in source.parents:
        raise ExactRCError("exact RC dependency source must be outside the runtime root")
    destination = runtime_root / "controlled-dependencies"
    destination.mkdir(parents=True, exist_ok=False)
    copied_files = 0
    for item in sorted(source.iterdir(), key=lambda path: path.name):
        normalized = item.name.lower()
        if (
            normalized == "relaylm"
            or normalized.startswith("relaylm-")
            or normalized.startswith("relaylm_")
            or normalized.startswith("__editable__.relaylm")
            or item.suffix == ".pth"
        ):
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
        copied_files += 1
    if not copied_files:
        raise ExactRCError("exact RC controlled dependency overlay is empty")
    return destination.resolve()


def _runtime_environment(*, dependency_overlay: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    for name in (
        "RELAYLM_CONFIG",
        "RELAYLM_PROVIDER_BASE_URL",
        "RELAYLM_PROVIDER_MODEL",
        "RELAYLM_PROFILE_ROOT",
        "RELAYLM_PROFILE_NAME",
        "RELAYLM_HOST",
        "RELAYLM_PORT",
    ):
        env.pop(name, None)
    env["PYTHONNOUSERSITE"] = "1"
    if dependency_overlay is not None:
        env["PYTHONPATH"] = str(dependency_overlay.resolve())
    return env


def _run_console_version(
    console: Path,
    *,
    dependency_overlay: Path | None = None,
) -> str:
    env = _runtime_environment(dependency_overlay=dependency_overlay)
    completed = subprocess.run(
        [str(console), "--version"],
        cwd=Path("/"),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ExactRCError(
            "exact RC console --version failed: "
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    line = completed.stdout.strip()
    prefix = "relaylm "
    if not line.startswith(prefix) or not line[len(prefix) :].strip():
        raise ExactRCError("exact RC console --version output was not recognized")
    return line[len(prefix) :].strip()


def _run_identity_probe(python: Path, *, checkout_root: Path) -> tuple[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONPATH"] = str(checkout_root)
    completed = subprocess.run(
        [
            str(python),
            "-m",
            "tools.v1_external_qualification_exact_rc_probe",
            "--checkout-root",
            str(checkout_root),
        ],
        cwd=Path("/"),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ExactRCError(
            "exact RC import probe failed: "
            + (completed.stderr.strip() or completed.stdout.strip())
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ExactRCError("exact RC import probe was not JSON") from exc
    version = payload.get("version")
    origin = payload.get("origin")
    if not isinstance(version, str) or not isinstance(origin, str):
        raise ExactRCError("exact RC import probe omitted version or origin")
    origin_path = Path(origin).resolve()
    if checkout_root.resolve() == origin_path or checkout_root.resolve() in origin_path.parents:
        raise ExactRCError("exact RC import resolved to the qualification checkout")
    return version, str(origin_path)


def install_exact_rc(
    *,
    wheel_path: Path,
    wheel_sha256: str,
    expected_version: str,
    expected_distribution: str,
    checkout_root: Path,
    runtime_root: Path,
) -> ExactRCInstallation:
    """Install exact wheel bytes with no source build and verify import origin."""

    wheel_path = wheel_path.resolve()
    if not wheel_path.is_file():
        raise ExactRCError(f"accepted RC wheel is not a file: {wheel_path}")
    observed = _sha256(wheel_path)
    if observed != wheel_sha256:
        raise ExactRCError(
            f"accepted RC wheel SHA256 drifted: expected {wheel_sha256}, observed {observed}"
        )
    runtime_root = runtime_root.resolve()
    if runtime_root.exists():
        raise ExactRCError(f"exact RC runtime root is not fresh: {runtime_root}")
    runtime_root.parent.mkdir(parents=True, exist_ok=True)
    try:
        venv.EnvBuilder(with_pip=True, system_site_packages=True, clear=False).create(
            runtime_root
        )
        python = _python_path(runtime_root)
        dependency_overlay = _prepare_dependency_overlay(runtime_root)
        env = _runtime_environment(dependency_overlay=dependency_overlay)
        completed = subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-index",
                "--disable-pip-version-check",
                str(wheel_path),
            ],
            cwd=Path("/"),
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise ExactRCError(
                "exact RC wheel installation failed: "
                + (completed.stderr.strip() or completed.stdout.strip())
            )
        if _sha256(wheel_path) != wheel_sha256:
            raise ExactRCError("accepted RC wheel changed during installation")
        version, origin = _run_identity_probe(python, checkout_root=checkout_root)
        if version != expected_version:
            raise ExactRCError(
                f"installed RC version drifted: expected {expected_version}, observed {version}"
            )
        if expected_distribution != "relaylm":
            raise ExactRCError(
                "only the repository-owned relaylm distribution is supported"
            )
        console = _console_path(runtime_root)
        console_version = _run_console_version(
            console,
            dependency_overlay=dependency_overlay,
        )
        if console_version != expected_version:
            raise ExactRCError(
                "installed RC console version drifted: "
                f"expected {expected_version}, observed {console_version}"
            )
        return ExactRCInstallation(
            python=python,
            console=console,
            root=runtime_root,
            dependency_overlay=dependency_overlay,
            wheel_path=wheel_path,
            wheel_sha256=wheel_sha256,
            version=version,
            distribution=expected_distribution,
            import_origin=origin,
        )
    except BaseException as exc:
        try:
            shutil.rmtree(runtime_root)
        except FileNotFoundError:
            pass
        except OSError as cleanup_error:
            if isinstance(exc, Exception):
                exc.add_note(f"exact RC runtime cleanup failed: {cleanup_error}")
        raise


def cleanup_exact_rc(installation: ExactRCInstallation) -> Mapping[str, object]:
    """Remove only the runtime root owned by this installation."""

    errors: list[str] = []
    try:
        shutil.rmtree(installation.root)
    except FileNotFoundError:
        pass
    except OSError as exc:
        errors.append(str(exc))
    return {
        "runtime_root": str(installation.root),
        "removed": not installation.root.exists(),
        "errors": errors,
    }


class ExactRCAdapterSession:
    """Persistent installed-RC transcript replay/frozen-query bridge."""

    def __init__(
        self,
        installation: ExactRCInstallation,
        *,
        config_path: Path,
        config_sha256: str,
        checkout_root: Path,
        workspace_root: Path,
    ) -> None:
        self.installation = installation
        self.config_path = config_path.resolve()
        self.config_sha256 = config_sha256
        self.checkout_root = checkout_root.resolve()
        self.workspace_root = workspace_root.resolve()
        self.process: subprocess.Popen[str] | None = None
        self.start_count = 0
        self.query_count = 0
        self._request_counter = 0
        self.log_path = self.workspace_root.with_name(
            f"{self.workspace_root.name}.stderr.log"
        )

    def _environment(self) -> dict[str, str]:
        env = _runtime_environment(
            dependency_overlay=self.installation.dependency_overlay,
        )
        env["PYTHONPATH"] = os.pathsep.join(
            [
                str(self.checkout_root),
                str(self.installation.dependency_overlay.resolve()),
            ]
        )
        return env

    @staticmethod
    def _read_message(stream: object, *, label: str) -> Mapping[str, object]:
        readline = getattr(stream, "readline", None)
        if not callable(readline):
            raise ExactRCError(f"exact RC adapter {label} stream is unavailable")
        line = readline()
        if not isinstance(line, str) or not line:
            raise ExactRCError(f"exact RC adapter {label} closed unexpectedly")
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ExactRCError(f"exact RC adapter {label} was not JSON") from exc
        if not isinstance(payload, Mapping):
            raise ExactRCError(f"exact RC adapter {label} was not an object")
        return payload

    def start(self) -> Mapping[str, object]:
        if not self.config_path.is_file():
            raise ExactRCError(f"exact RC config is not a file: {self.config_path}")
        if _sha256(self.config_path) != self.config_sha256:
            raise ExactRCError("exact RC config content drifted during adapter setup")
        if not self.checkout_root.is_dir():
            raise ExactRCError("qualification checkout root is unavailable")
        if self.workspace_root.exists():
            raise ExactRCError("exact RC adapter workspace must be fresh")
        if self.process is not None:
            raise ExactRCError("exact RC adapter was started twice")
        self.workspace_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            log_handle = self.log_path.open("xb")
        except OSError as exc:
            raise ExactRCError(
                f"cannot create exact RC adapter log: {self.log_path}"
            ) from exc
        try:
            self.process = subprocess.Popen(
                [
                    str(self.installation.python),
                    "-m",
                    "tools.v1_external_qualification_exact_rc_adapter",
                    "--config",
                    str(self.config_path),
                    "--workspace-root",
                    str(self.workspace_root),
                ],
                cwd=Path("/"),
                env=self._environment(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=log_handle,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise ExactRCError("exact RC adapter launch failed") from exc
        finally:
            log_handle.close()
        self.start_count += 1
        assert self.process.stdout is not None
        ready = self._read_message(self.process.stdout, label="ready response")
        if ready.get("status") != "ready" or ready.get("protocol_version") != 1:
            raise ExactRCError("exact RC adapter did not report ready")
        if ready.get("relaylm_version") != self.installation.version:
            raise ExactRCError("exact RC adapter imported the wrong RelayLM version")
        origin = ready.get("relaylm_origin")
        if not isinstance(origin, str) or Path(origin).resolve() != Path(
            self.installation.import_origin
        ).resolve():
            raise ExactRCError("exact RC adapter imported RelayLM outside accepted RC")
        adapter_origin = ready.get("adapter_origin")
        if not isinstance(adapter_origin, str):
            raise ExactRCError("exact RC adapter omitted qualification adapter origin")
        resolved_adapter = Path(adapter_origin).resolve()
        if (
            resolved_adapter != self.checkout_root
            and self.checkout_root not in resolved_adapter.parents
        ):
            raise ExactRCError(
                "exact RC adapter tools module did not resolve from qualification checkout"
            )
        return dict(ready)

    def query(
        self,
        *,
        axis_id: str,
        question_id: str,
        question: str,
        sessions: Sequence[Mapping[str, object]],
    ) -> Mapping[str, object]:
        if self.process is None or self.process.poll() is not None:
            raise ExactRCError("exact RC adapter is not running")
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self._request_counter += 1
        request_id = f"exact-rc-{self._request_counter:08d}"
        request = {
            "op": "query",
            "protocol_version": 1,
            "request_id": request_id,
            "axis_id": axis_id,
            "question_id": question_id,
            "question": question,
            "sessions": [dict(item) for item in sessions],
        }
        try:
            self.process.stdin.write(
                json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n"
            )
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise ExactRCError("exact RC adapter request pipe failed") from exc
        response = self._read_message(self.process.stdout, label="query response")
        if response.get("status") == "error":
            error_type = response.get("error_type")
            message = response.get("error")
            raise ExactRCError(
                "exact RC adapter query failed"
                + (
                    f": {error_type}: {message}"
                    if isinstance(error_type, str) and isinstance(message, str)
                    else ""
                )
            )
        if (
            response.get("status") != "ok"
            or response.get("protocol_version") != 1
            or response.get("request_id") != request_id
        ):
            raise ExactRCError("exact RC adapter query response identity is invalid")
        self.query_count += 1
        return dict(response)

    def cleanup(self) -> Mapping[str, object]:
        errors: list[str] = []
        if self.process is not None and self.process.poll() is None:
            try:
                assert self.process.stdin is not None
                assert self.process.stdout is not None
                self.process.stdin.write(
                    json.dumps(
                        {"op": "close", "protocol_version": 1},
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                self.process.stdin.flush()
                closed = self._read_message(
                    self.process.stdout,
                    label="close response",
                )
                if closed.get("status") != "closed":
                    errors.append("exact RC adapter close acknowledgement was invalid")
                self.process.wait(timeout=20)
            except (OSError, BrokenPipeError, subprocess.TimeoutExpired, ExactRCError) as exc:
                errors.append(str(exc))
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=10)
        return {
            "start_count": self.start_count,
            "query_count": self.query_count,
            "terminated": self.process is None or self.process.poll() is not None,
            "exit_code": None if self.process is None else self.process.poll(),
            "log_path": str(self.log_path),
            "workspace_root": str(self.workspace_root),
            "errors": errors,
        }


class ExactRCServerSession:
    """Fixed installed-RC server boundary used only by a citable owner."""

    def __init__(
        self,
        installation: ExactRCInstallation,
        *,
        config_path: Path,
        config_sha256: str,
        port: int,
    ) -> None:
        self.installation = installation
        self.config_path = config_path.resolve()
        self.config_sha256 = config_sha256
        self.port = port
        self.process: subprocess.Popen[bytes] | None = None
        self.start_count = 0
        self.client = httpx.Client(timeout=20.0, trust_env=False)
        self.log_path = self.config_path.with_name(
            f"{self.config_path.name}.server-{self.port}-{os.getpid()}.log"
        )

    def start(self) -> None:
        if not self.config_path.is_file():
            raise ExactRCError(f"exact RC config is not a file: {self.config_path}")
        if _sha256(self.config_path) != self.config_sha256:
            raise ExactRCError("exact RC config content drifted during setup")
        if self.process is not None:
            raise ExactRCError("exact RC server was started twice")
        console = self.installation.console.resolve()
        runtime_root = self.installation.root.resolve()
        if runtime_root != console and runtime_root not in console.parents:
            raise ExactRCError("exact RC console entrypoint escaped the runtime root")
        if not console.is_file():
            raise ExactRCError(f"exact RC console entrypoint is missing: {console}")
        env = _runtime_environment(
            dependency_overlay=self.installation.dependency_overlay,
        )
        try:
            log_handle = self.log_path.open("xb")
        except OSError as exc:
            raise ExactRCError(
                f"cannot create exact RC server log: {self.log_path}"
            ) from exc
        try:
            self.process = subprocess.Popen(
                [
                    str(console),
                    "serve",
                    "--config",
                    str(self.config_path),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                ],
                cwd=Path("/"),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
        except OSError as exc:
            raise ExactRCError(
                f"exact RC server launch failed; log={self.log_path}"
            ) from exc
        finally:
            log_handle.close()
        self.start_count += 1
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            return_code = self.process.poll()
            if return_code is not None:
                raise ExactRCError(
                    "exact RC server exited before health: "
                    f"exit_code={return_code} log={self.log_path}"
                )
            try:
                response = self.client.get(f"http://127.0.0.1:{self.port}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        raise ExactRCError(
            f"exact RC server health did not become ready; log={self.log_path}"
        )

    def query(self, prompt: str) -> Mapping[str, object]:
        if self.process is None or self.process.poll() is not None:
            raise ExactRCError("exact RC server is not running")
        try:
            response = self.client.post(
                f"http://127.0.0.1:{self.port}/v1/chat/completions",
                json={
                    "model": "relaylm-exact-rc",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "stream": False,
                },
            )
        except httpx.HTTPError as exc:
            raise ExactRCError("exact RC query failed") from exc
        if response.status_code != 200:
            raise ExactRCError(f"exact RC query returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExactRCError("exact RC query response was not JSON") from exc
        if not isinstance(payload, Mapping):
            raise ExactRCError("exact RC query response was not an object")
        return payload

    def cleanup(self) -> Mapping[str, object]:
        errors: list[str] = []
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    errors.append("exact RC server did not terminate")
        try:
            self.client.close()
        except Exception as exc:  # pragma: no cover - defensive close boundary
            errors.append(str(exc))
        return {
            "start_count": self.start_count,
            "terminated": self.process is None or self.process.poll() is not None,
            "exit_code": None if self.process is None else self.process.poll(),
            "log_path": str(self.log_path),
            "errors": errors,
        }
