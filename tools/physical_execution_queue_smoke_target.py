from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path


FORMAT_VERSION = "relaylm-physical-queue-smoke-v1"
DEFAULT_ARTIFACT_ROOT = Path("/tmp/relaylm/physical/smoke")


def _default_artifact_path() -> Path:
    return DEFAULT_ARTIFACT_ROOT / f"queue-smoke-{os.getpid()}-{time.time_ns()}.json"


def build_payload() -> dict[str, object]:
    return {
        "format_version": FORMAT_VERSION,
        "kind": "physical_queue_smoke_child",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "cwd": str(Path.cwd().resolve()),
        "provider_calls": 0,
        "semantic_calls": 0,
        "scientific_transaction_consumed": False,
    }


def write_artifact(path: Path) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Infrastructure-only child for the RelayLM llama.cpp queue smoke. "
            "It performs no provider/model/semantic calls."
        )
    )
    parser.add_argument("--artifact", type=Path)
    args = parser.parse_args(argv)
    artifact = args.artifact or _default_artifact_path()
    try:
        write_artifact(artifact)
    except OSError as exc:
        print(f"queue smoke artifact blocked: {exc}", file=sys.stderr)
        return 2
    print(str(artifact.expanduser().resolve()), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
