#!/usr/bin/env python3
"""Twin Extraction bounded batch runner CLI.

Caller-invoked, bounded execution against an OpenAI-compatible chat
completions endpoint (default: a local LM Studio instance). This script is
not part of the RelayLM runtime and does not import the `relaylm` package.

The run is bounded by the discovered batch count and --max-batches. There
is no daemon, polling loop, scheduler, or worker pool. Progress logs and
the final summary are content-free: batch id, record count, status, and
elapsed time only. Response bodies are never logged; a batch whose
response cannot be parsed as the expected extraction schema is recorded
under --out-dir/failed/ (fail-closed) instead of being partially applied.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

from relaylm_twin_extraction_common import read_jsonl

DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_RETRIES = 1
REQUEST_TIMEOUT_SECONDS = 120.0

CompletionFn = Callable[[dict], dict]


def discover_batches(batch_dir: Path) -> list[Path]:
    return sorted(batch_dir.glob("batch_*.jsonl"))


def build_payload(model: str, prompt_text: str, records: list[dict]) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": json.dumps(records, ensure_ascii=False)},
        ],
    }


def call_chat_completions(base_url: str, payload: dict, timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict:
    url = f"{base_url.rstrip('/')}/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - local/user-configured endpoint
        body = response.read().decode("utf-8")
    return json.loads(body)


def _extract_content(response_json: dict) -> str:
    return response_json["choices"][0]["message"]["content"]


def _parse_extraction(content: str) -> dict:
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("response JSON top level is not an object")
    style_observations = data.get("style_observations")
    fact_candidates = data.get("fact_candidates")
    if not isinstance(style_observations, list) or not isinstance(fact_candidates, list):
        raise ValueError("response JSON missing style_observations/fact_candidates arrays")
    return data


def run_batch(
    completion_fn: CompletionFn,
    model: str,
    prompt_text: str,
    records: list[dict],
    retries: int,
) -> dict:
    payload = build_payload(model, prompt_text, records)
    attempts = max(1, retries + 1)
    last_error = "unknown_error"
    for attempt in range(1, attempts + 1):
        try:
            response_json = completion_fn(payload)
            content = _extract_content(response_json)
            extraction = _parse_extraction(content)
            return {"status": "ok", "attempts": attempt, "extraction": extraction}
        except Exception as exc:  # fail-closed: any malformed/unreachable response retries then fails
            last_error = type(exc).__name__
            continue
    return {"status": "failed", "attempts": attempts, "error": last_error}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--batch-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--max-batches", type=int, default=None)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.retries < 0:
        print("error: --retries must be >= 0", file=sys.stderr)
        return 2
    if args.max_batches is not None and args.max_batches < 0:
        print("error: --max-batches must be >= 0", file=sys.stderr)
        return 2
    if not args.batch_dir.is_dir():
        print("error: batch directory not found", file=sys.stderr)
        return 2
    if not args.prompt_file.is_file():
        print("error: prompt file not found", file=sys.stderr)
        return 2

    prompt_text = args.prompt_file.read_text(encoding="utf-8")
    batches = discover_batches(args.batch_dir)
    if args.max_batches is not None:
        batches = batches[: args.max_batches]

    if args.dry_run:
        total_records = 0
        total_payload_bytes = 0
        for batch_path in batches:
            records = read_jsonl(batch_path)
            total_records += len(records)
            payload_bytes = json.dumps(
                build_payload(args.model, prompt_text, records), ensure_ascii=False
            ).encode("utf-8")
            total_payload_bytes += len(payload_bytes)
        print(
            json.dumps(
                {
                    "mode": "dry_run",
                    "batch_count": len(batches),
                    "total_records": total_records,
                    "total_payload_bytes": total_payload_bytes,
                },
                sort_keys=True,
            )
        )
        return 0

    results_dir = args.out_dir / "results"
    failed_dir = args.out_dir / "failed"
    results_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    def completion_fn(payload: dict) -> dict:
        return call_chat_completions(args.base_url, payload)

    ok_count = 0
    failed_count = 0
    for batch_path in batches:
        batch_id = batch_path.stem
        records = read_jsonl(batch_path)
        started = time.monotonic()
        outcome = run_batch(completion_fn, args.model, prompt_text, records, args.retries)
        elapsed = time.monotonic() - started

        # A rerun into the same --out-dir must not leave a stale marker from
        # a previous run's opposite outcome for this batch id (for example a
        # prior success's results/<id>.result.json surviving a current
        # failure), since merge reads every *.result.json it finds.
        (results_dir / f"{batch_id}.result.json").unlink(missing_ok=True)
        (failed_dir / f"{batch_id}.failed.json").unlink(missing_ok=True)

        if outcome["status"] == "ok":
            ok_count += 1
            (results_dir / f"{batch_id}.result.json").write_text(
                json.dumps(outcome["extraction"], ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
        else:
            failed_count += 1
            (failed_dir / f"{batch_id}.failed.json").write_text(
                json.dumps(
                    {
                        "batch_id": batch_id,
                        "record_count": len(records),
                        "attempts": outcome["attempts"],
                        "error_type": outcome["error"],
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

        print(
            json.dumps(
                {
                    "batch_id": batch_id,
                    "record_count": len(records),
                    "status": outcome["status"],
                    "attempts": outcome["attempts"],
                    "elapsed_seconds": round(elapsed, 3),
                },
                sort_keys=True,
            )
        )

    print(json.dumps({"batch_count": len(batches), "ok": ok_count, "failed": failed_count}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
