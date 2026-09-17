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
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import time
import venv

import httpx


class ExactRCError(RuntimeError):
    """The accepted RC artifact could not be proven or isolated."""


@dataclass(frozen=True, slots=True)
class ExactRCInstallation:
    python: Path
    root: Path
    wheel_path: Path
    wheel_sha256: str
    version: str
    distribution: str
    import_origin: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "python": str(self.python),
            "root": str(self.root),
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
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONNOUSERSITE"] = "1"
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
        return ExactRCInstallation(
            python=python,
            root=runtime_root,
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

    def start(self) -> None:
        if not self.config_path.is_file():
            raise ExactRCError(f"exact RC config is not a file: {self.config_path}")
        if _sha256(self.config_path) != self.config_sha256:
            raise ExactRCError("exact RC config content drifted during setup")
        if self.process is not None:
            raise ExactRCError("exact RC server was started twice")
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONNOUSERSITE"] = "1"
        self.process = subprocess.Popen(
            [
                str(self.installation.python),
                "-m",
                "relaylm.cli",
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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.start_count += 1
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise ExactRCError("exact RC server exited before health")
            try:
                response = self.client.get(f"http://127.0.0.1:{self.port}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        raise ExactRCError("exact RC server health did not become ready")

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
            "errors": errors,
        }
