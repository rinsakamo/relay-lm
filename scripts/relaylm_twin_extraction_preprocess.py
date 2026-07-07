#!/usr/bin/env python3
"""Twin Extraction offline preprocessing CLI.

Caller-invoked, bounded, offline preprocessing for the Twin Extraction
material tooling described in docs/tools/twin_extraction_prompts.md. This
script is not part of the RelayLM runtime and does not import the
`relaylm` package.

Sources:
  --source x        parse an X (Twitter) archive `tweets.js` file.
  --source chatgpt   parse a ChatGPT export `conversations.json` file.

Output is JSONL batch files under --out-dir. The stdout summary is
content-free: counts only, never post/utterance bodies or absolute paths.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from relaylm_twin_extraction_common import TwinExtractionInputError, load_json_array, write_batches

DEFAULT_X_BATCH_SIZE = 150
DEFAULT_CHATGPT_BATCH_SIZE = 4

TCO_TRAILING_URL_RE = re.compile(r"(?:\s*https://t\.co/\w+)+\s*$")
X_CREATED_AT_FORMAT = "%a %b %d %H:%M:%S %z %Y"
YEAR_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass
class PreprocessSummary:
    source: str
    total_seen: int = 0
    kept: int = 0
    excluded_retweet: int = 0
    excluded_date_filtered: int = 0
    excluded_empty: int = 0
    excluded_other: int = 0
    batch_count: int = 0
    batch_size: int = 0

    def to_public_dict(self) -> dict:
        return asdict(self)


def _parse_year_month(value: str) -> tuple[int, int]:
    match = YEAR_MONTH_RE.match(value)
    if not match:
        raise ValueError("expected YYYY-MM")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise ValueError("expected YYYY-MM")
    return (year, month)


def _within_range(month_key: tuple[int, int], since: tuple[int, int] | None, until: tuple[int, int] | None) -> bool:
    if since is not None and month_key < since:
        return False
    if until is not None and month_key > until:
        return False
    return True


def _normalize_x_text(full_text: str, is_quote_status: bool) -> str:
    if is_quote_status:
        full_text = TCO_TRAILING_URL_RE.sub("", full_text)
    return full_text.strip()


def extract_x_groups(
    path: Path, since: tuple[int, int] | None, until: tuple[int, int] | None
) -> tuple[list[list[dict]], PreprocessSummary]:
    summary = PreprocessSummary(source="x")
    groups: list[list[dict]] = []
    for entry in load_json_array(path):
        summary.total_seen += 1
        tweet = entry.get("tweet", entry) if isinstance(entry, dict) else None
        if not isinstance(tweet, dict):
            summary.excluded_other += 1
            continue

        full_text = tweet.get("full_text") or tweet.get("text") or ""
        if not isinstance(full_text, str) or not full_text.strip():
            summary.excluded_empty += 1
            continue

        if full_text.startswith("RT @"):
            summary.excluded_retweet += 1
            continue

        text = _normalize_x_text(full_text, bool(tweet.get("is_quote_status", False)))
        if not text:
            summary.excluded_empty += 1
            continue

        created_at_raw = tweet.get("created_at")
        month_key: tuple[int, int] | None = None
        if isinstance(created_at_raw, str):
            try:
                dt = datetime.strptime(created_at_raw, X_CREATED_AT_FORMAT)
                month_key = (dt.year, dt.month)
            except ValueError:
                month_key = None

        if (since is not None or until is not None):
            if month_key is None:
                summary.excluded_other += 1
                continue
            if not _within_range(month_key, since, until):
                summary.excluded_date_filtered += 1
                continue

        record = {
            "id": tweet.get("id_str") or tweet.get("id"),
            "created_at": created_at_raw,
            "text": text,
        }
        reply_id = tweet.get("in_reply_to_status_id_str") or tweet.get("in_reply_to_status_id")
        if reply_id:
            record["in_reply_to_status_id"] = reply_id

        groups.append([record])
        summary.kept += 1
    return groups, summary


def _epoch_to_month(epoch: object) -> tuple[int, int] | None:
    try:
        dt = datetime.fromtimestamp(float(epoch), tz=timezone.utc)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return (dt.year, dt.month)


def _ordered_messages(mapping: dict) -> list[tuple[str, str, object]]:
    staged: list[tuple[float, int, str, str, object]] = []
    for index, node in enumerate(mapping.values()):
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        author = message.get("author") or {}
        role = author.get("role") if isinstance(author, dict) else None
        if role not in ("user", "assistant"):
            continue
        content = message.get("content") or {}
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            continue
        text = " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())
        if not text:
            continue
        create_time = message.get("create_time")
        sort_key = float(create_time) if isinstance(create_time, (int, float)) else float("inf")
        staged.append((sort_key, index, role, text, create_time))
    staged.sort(key=lambda item: (item[0], item[1]))
    return [(role, text, create_time) for _sort_key, _index, role, text, create_time in staged]


def extract_chatgpt_groups(
    path: Path, since: tuple[int, int] | None, until: tuple[int, int] | None
) -> tuple[list[list[dict]], PreprocessSummary]:
    summary = PreprocessSummary(source="chatgpt")
    groups: list[list[dict]] = []
    for conv in load_json_array(path):
        summary.total_seen += 1
        if not isinstance(conv, dict):
            summary.excluded_other += 1
            continue

        conversation_id = conv.get("conversation_id") or conv.get("id")
        if not conversation_id:
            summary.excluded_other += 1
            continue

        create_time = conv.get("create_time")
        month_key = _epoch_to_month(create_time) if create_time is not None else None
        if (since is not None or until is not None):
            if month_key is None:
                summary.excluded_other += 1
                continue
            if not _within_range(month_key, since, until):
                summary.excluded_date_filtered += 1
                continue

        mapping = conv.get("mapping")
        if not isinstance(mapping, dict):
            summary.excluded_other += 1
            continue

        conv_records = []
        for role, text, ts in _ordered_messages(mapping):
            record_role = "user" if role == "user" else "context"
            conv_records.append(
                {
                    "conversation_id": conversation_id,
                    "created_at": ts,
                    "role": record_role,
                    "text": text,
                }
            )

        if not any(record["role"] == "user" for record in conv_records):
            summary.excluded_empty += 1
            continue

        groups.append(conv_records)
        summary.kept += 1
    return groups, summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("x", "chatgpt"), required=True)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--since", default=None, help="YYYY-MM inclusive lower bound")
    parser.add_argument("--until", default=None, help="YYYY-MM inclusive upper bound")
    parser.add_argument("--batch-size", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    batch_size = args.batch_size or (DEFAULT_X_BATCH_SIZE if args.source == "x" else DEFAULT_CHATGPT_BATCH_SIZE)
    if batch_size <= 0:
        print("error: --batch-size must be positive", file=sys.stderr)
        return 2

    try:
        since = _parse_year_month(args.since) if args.since else None
        until = _parse_year_month(args.until) if args.until else None
    except ValueError as exc:
        print(f"error: --since/--until: {exc}", file=sys.stderr)
        return 2

    if not args.input.is_file():
        print("error: input file not found", file=sys.stderr)
        return 2

    try:
        if args.source == "x":
            groups, summary = extract_x_groups(args.input, since, until)
        else:
            groups, summary = extract_chatgpt_groups(args.input, since, until)
    except TwinExtractionInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary.batch_size = batch_size
    batch_paths = write_batches(groups, args.out_dir, batch_size, prefix="batch")
    summary.batch_count = len(batch_paths)

    print(json.dumps(summary.to_public_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
