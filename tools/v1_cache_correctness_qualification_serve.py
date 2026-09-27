"""Installed-wheel RelayLM server with read-only continuity observation.

This qualification entry point prepares and serves the same installed wheel
through RelayLM's normal runtime-config and app factories. The ASGI wrapper
records aggregate State and in-process Continuity materialization facts after
each public completion; it never serializes semantic contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import uvicorn

from relaylm.runtime_config_loader import resolve_runtime_config
from relaylm.runtime_preflight import prepare_runtime
from relaylm.server import create_app
from relaylm.storage.filesystem import CharacterDataError, CharacterDirectory


class _MaterializationObserver:
    def __init__(self, app: Any, profiles: Any, output_path: Path) -> None:
        self.app = app
        self.profiles = profiles
        self.output_path = output_path
        self.requests: list[dict[str, Any]] = []
        self._write()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if (
            scope.get("type") == "http"
            and scope.get("method") == "GET"
            and scope.get("path") == "/__qualification/flush"
        ):
            self._write()
            body = json.dumps(
                {
                    "observation": "read_only",
                    "request_count": len(self.requests),
                    "profiles": self._profile_observations(),
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body, "more_body": False})
            return
        if scope.get("type") != "http" or not (
            scope.get("method") == "POST"
            and scope.get("path") == "/v1/chat/completions"
        ):
            await self.app(scope, receive, send)
            return

        status_code: int | None = None
        response_digest = hashlib.sha256()
        response_bytes = 0
        completed = False

        async def observed_send(message: dict[str, Any]) -> None:
            nonlocal status_code, response_bytes, completed
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 0))
            elif message.get("type") == "http.response.body":
                body = message.get("body", b"")
                if isinstance(body, bytes):
                    response_digest.update(body)
                    response_bytes += len(body)
                completed = not bool(message.get("more_body", False))
            await send(message)

        await self.app(scope, receive, observed_send)
        if completed:
            self.requests.append(
                {
                    "request_index": len(self.requests) + 1,
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "response_bytes": response_bytes,
                    "response_sha256": f"sha256:{response_digest.hexdigest()}",
                    "profiles": self._profile_observations(),
                }
            )
            self._write()

    def _profile_observations(self) -> dict[str, Any]:
        observations: dict[str, Any] = {}
        for profile in self.profiles.profiles:
            root = Path(profile.package.root)
            state_path = root / "memory" / "state.json"
            state_count: int | None = None
            state_valid = False
            try:
                canonical_state = CharacterDirectory(root).load_state()
            except CharacterDataError:
                pass
            else:
                state_count = len(canonical_state.states)
                state_valid = True

            continuity_runtime = profile.continuity_runtime
            continuity: dict[str, Any] | None = None
            if continuity_runtime is not None:
                context = continuity_runtime.context
                continuity = {
                    "configured": True,
                    "revision": context.revision,
                    "item_count": len(context.items),
                    "max_items": context.max_items,
                    "within_bound": len(context.items) <= context.max_items,
                }
            observations[profile.name] = {
                "state_file_present": state_path.is_file(),
                "state_schema_valid": state_valid,
                "state_record_count": state_count,
                "event_record_count": _event_record_count(root / "memory" / "events.jsonl"),
                "continuity": continuity,
            }
        return observations

    def _write(self) -> None:
        payload = {
            "format_version": 1,
            "observation": "read_only_after_public_completion",
            "semantic_payloads_serialized": False,
            "request_count": len(self.requests),
            "requests": self.requests,
            "current_profiles": self._profile_observations(),
        }
        _atomic_json(self.output_path, payload)


def _event_record_count(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except (OSError, UnicodeError):
        return 0


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    fd, raw_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw_path)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--observation-path", required=True)
    args = parser.parse_args(argv)
    resolved = resolve_runtime_config(config_path=args.config, environ=os.environ)
    prepared = prepare_runtime(resolved)
    app = create_app(**prepared.assembly.app_kwargs())
    observer = _MaterializationObserver(
        app,
        prepared.assembly.profiles,
        Path(args.observation_path).resolve(),
    )
    uvicorn.run(
        observer,
        host=resolved.config.server.host,
        port=resolved.config.server.port,
        log_level="info",
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
