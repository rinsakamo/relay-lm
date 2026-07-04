#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _write_config(path: Path, *, memory_root: str, character_id: str = "default") -> None:
    cfg = yaml.safe_load((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    cfg["memory"]["store_enabled"] = True
    cfg["memory"]["root_path"] = memory_root
    cfg["relaymem_slp_queue_root"] = str(path.parent / "runtime" / "queue")
    cfg["relaymem_slp_protected_source_root"] = str(path.parent / "runtime" / "protected-source")
    cfg["relaymem_slp_durable_finalization_root"] = str(path.parent / "runtime" / "durable-finalization")
    cfg["trace"]["path"] = str(path.parent / "runtime" / "traces" / "relaylm_trace.jsonl")
    cfg["model_routes"]["relaylm-default"]["character_id"] = character_id
    cfg["model_routes"]["relaylm-default"]["memory_namespace"] = f"character/{character_id}"
    cfg["characters"] = {
        "default": {
            "soul": "examples/profiles/default/SOUL.md",
            "output_policy": "examples/profiles/default/style.md",
        }
    }
    path.write_text(yaml.safe_dump(cfg, sort_keys=True), encoding="utf-8")


def _run_cli(args: list[str]) -> tuple[int, dict[str, Any], str]:
    from relaylm.runtime_install_cli import main as runtime_cli_main

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = runtime_cli_main(args)
    text = stdout.getvalue()
    return code, json.loads(text), text


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        before = sorted(work.iterdir())
        subprocess.run(
            [sys.executable, "-c", "import relaylm.runtime_install"],
            cwd=work,
            env={"PYTHONPATH": str(REPO_ROOT)},
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        require(sorted(work.iterdir()) == before, "runtime_install import wrote files")
        print("ok import has no filesystem side effects")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        cfg_path = work / "config.yaml"
        memory_root = work / "runtime" / "memory"
        _write_config(cfg_path, memory_root=str(memory_root))

        code, payload, text = _run_cli(["--config", str(cfg_path), "--dry-run", "--character-id", "default"])
        require(code == 0, payload)
        require(payload["status"] == "dry_run_missing", payload)
        require(payload["mutated"] is False, payload)
        require(not memory_root.exists(), "dry-run created memory root")
        require(str(work) not in text, "public report leaked path")
        require(payload["content_free"] is True, payload)
        print("ok dry-run is content-free and non-mutating")

        code, payload, _ = _run_cli(["--config", str(cfg_path), "--dry-run", "--character-id", "../bad"])
        require(code == 1, payload)
        require(payload["status"] == "invalid_input", payload)
        require(not memory_root.exists(), "invalid character dry-run created memory root")
        print("ok invalid character id fails closed before write")

        code, payload, text = _run_cli(["--config", str(cfg_path), "--write", "--character-id", "default"])
        require(code == 0, payload)
        require(payload["status"] == "applied_ready", payload)
        require(payload["mutated"] is True, payload)
        require((memory_root / "characters" / "default" / "memory" / "mem" / "primary" / "projects").is_dir(), payload)
        require(str(work) not in text, "public write report leaked path")
        print("ok write creates allowed layout only")

    from relaylm.runtime_install_cli import main as runtime_cli_main

    try:
        runtime_cli_main(["--help"])
    except SystemExit as exc:
        require(exc.code == 0, exc)
    else:
        raise AssertionError("help did not exit")
    print("ok help works")

    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    require('relaylm-runtime-install = "relaylm.runtime_install_cli:main"' in pyproject, "entrypoint missing")
    print("RelayLM PM-D7 runtime install hook fold-in smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
