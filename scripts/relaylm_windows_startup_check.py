"""Windows startup smoke check for RelayLM.

PR-1 removed unconditional ``import fcntl`` from the codebase (see
``relaylm/portable_lock.py``) so that ``relaylm`` is importable on Windows.
This script is the regression check for that fix: it exercises the exact
import path that used to crash at module load time on Windows, then boots
the FastAPI app in-process (via ``fastapi.testclient.TestClient``, never a
real uvicorn server/socket) and exercises the portable file lock backend.

It is intentionally platform-neutral so it can be run locally on POSIX for
fast iteration, in addition to being the verification step of the Windows CI
workflow (``.github/workflows/windows.yml``).

Exit code is 0 on success and non-zero on any failure.
"""
from __future__ import annotations

import sys
import tempfile
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_MINIMAL_CONFIG_YAML = """\
listen:
  host: 127.0.0.1
  port: 8090

backends:
  local_backend:
    type: openai_compatible
    base_url: http://127.0.0.1:8000/v1
    api_key: dummy
    default_model: local-model
    timeout_seconds: 60.0

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_imports() -> None:
    # These are the modules that historically failed to import on Windows
    # because of an unconditional `import fcntl` somewhere in their import
    # graph. Importing them here is the regression guard for that bug.
    import relaylm.app  # noqa: F401
    import relaylm.portable_lock  # noqa: F401
    import relaylm.soul_lab_app  # noqa: F401


def check_app_healthz(config_path: Path) -> None:
    from fastapi.testclient import TestClient

    from relaylm.app import create_app

    # Deliberately do NOT start a real uvicorn server here: binding a real
    # port on Windows CI runners is flaky. TestClient drives the ASGI app
    # in-process instead.
    app = create_app(str(config_path))
    with TestClient(app) as client:
        response = client.get("/healthz")
        require(
            response.status_code == 200,
            f"expected /healthz to return 200, got {response.status_code}",
        )
        require(
            response.json() == {"status": "ok"},
            f"expected /healthz body {{'status': 'ok'}}, got {response.json()!r}",
        )


def check_portable_lock(tmpdir: Path) -> None:
    from relaylm.portable_lock import portable_lock

    lock_path = tmpdir / "portable_lock_check.lock"
    with lock_path.open("w+b") as fh:
        with portable_lock(fh, mode="exclusive", blocking=True):
            fh.write(b"locked")
            fh.flush()


def main() -> int:
    try:
        check_imports()

        with tempfile.TemporaryDirectory(prefix="relaylm-windows-startup-") as tmpdir_raw:
            tmpdir = Path(tmpdir_raw)
            config_path = tmpdir / "config.yaml"
            config_path.write_text(_MINIMAL_CONFIG_YAML, encoding="utf-8")

            check_app_healthz(config_path)
            check_portable_lock(tmpdir)
    except Exception:  # noqa: BLE001 - surface any failure with a traceback
        traceback.print_exc()
        return 1

    print("relaylm_windows_startup_check: OK (imports, /healthz, portable_lock all passed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
