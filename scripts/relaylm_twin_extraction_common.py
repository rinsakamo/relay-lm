#!/usr/bin/env python3
"""Shared stdlib-only helpers for the Twin Extraction offline tooling.

These helpers are used by the preprocessing, batch runner, and merge CLIs.
None of this module imports the `relaylm` runtime package; the Twin
Extraction tools are caller-invoked, bounded, offline scripts and are not
part of the RelayLM runtime.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

DEFAULT_STREAMING_THRESHOLD_BYTES = 50 * 1024 * 1024
DEFAULT_CHUNK_SIZE = 65536


class TwinExtractionInputError(Exception):
    """Fail-closed input error. Messages must stay content-free."""


def iter_json_array_stream(fh, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Iterator[object]:
    """Yield top-level elements of a JSON array read incrementally.

    Works for plain JSON arrays and for text with a non-JSON prefix before
    the first ``[`` (for example a JS variable-assignment prefix), since it
    scans forward for the first ``[`` before decoding elements.
    """
    decoder = json.JSONDecoder()
    buf = ""
    started = False
    while True:
        chunk = fh.read(chunk_size)
        if chunk:
            buf += chunk
        if not started:
            idx = buf.find("[")
            if idx == -1:
                if not chunk:
                    raise TwinExtractionInputError("no JSON array found in input")
                continue
            buf = buf[idx + 1 :]
            started = True
        buf = buf.lstrip(" \t\r\n,")
        if buf.startswith("]"):
            return
        if not buf:
            if not chunk:
                # EOF with no closing bracket ever seen: a truncated array
                # must fail closed rather than silently look like a clean
                # end-of-array (which would make truncated archive input
                # produce a partial batch set with exit code 0).
                raise TwinExtractionInputError("truncated JSON array: missing closing bracket")
            continue
        try:
            obj, end = decoder.raw_decode(buf)
        except ValueError:
            if not chunk:
                raise TwinExtractionInputError("malformed JSON array element")
            continue
        yield obj
        buf = buf[end:]


def _stream_json_array_from_path(path: Path, chunk_size: int) -> Iterator[object]:
    with path.open("r", encoding="utf-8") as fh:
        yield from iter_json_array_stream(fh, chunk_size=chunk_size)


def load_json_array(
    path: Path,
    streaming_threshold_bytes: int = DEFAULT_STREAMING_THRESHOLD_BYTES,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[object]:
    """Iterate elements of a top-level JSON array at ``path``.

    Uses a single in-memory ``json.loads`` for files at or under the
    streaming threshold, and falls back to bounded incremental parsing for
    larger files or when the in-memory parse fails (oversized file or a
    trailing non-JSON suffix after the closing bracket).
    """
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise TwinExtractionInputError("input file is not readable") from exc

    if size > streaming_threshold_bytes:
        yield from _stream_json_array_from_path(path, chunk_size)
        return

    try:
        text = path.read_text(encoding="utf-8")
    except MemoryError:
        yield from _stream_json_array_from_path(path, chunk_size)
        return
    except (OSError, UnicodeDecodeError) as exc:
        raise TwinExtractionInputError("input file is not readable as UTF-8 text") from exc

    start = text.find("[")
    if start == -1:
        raise TwinExtractionInputError("no JSON array found in input")

    try:
        data = json.loads(text[start:])
    except json.JSONDecodeError:
        yield from _stream_json_array_from_path(path, chunk_size)
        return

    if not isinstance(data, list):
        raise TwinExtractionInputError("input JSON top level is not an array")
    yield from data


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            fh.write("\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def write_batches(groups: list[list[dict]], out_dir: Path, batch_size: int, prefix: str = "batch") -> list[Path]:
    """Write ``groups`` (each a list of one or more related records) into
    JSONL batch files of up to ``batch_size`` groups per file, flattening
    each batch's records into one file.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    out_dir.mkdir(parents=True, exist_ok=True)

    # A rerun into the same --out-dir must not leave higher-numbered batch
    # files behind when the new run produces fewer batches than a previous
    # one, since batch discovery globs every "<prefix>_*.jsonl" file.
    for stale_path in out_dir.glob(f"{prefix}_*.jsonl"):
        stale_path.unlink()

    paths: list[Path] = []
    for batch_index, start in enumerate(range(0, len(groups), batch_size), start=1):
        chunk_groups = groups[start : start + batch_size]
        records = [record for group in chunk_groups for record in group]
        path = out_dir / f"{prefix}_{batch_index:04d}.jsonl"
        write_jsonl(path, records)
        paths.append(path)
    return paths
