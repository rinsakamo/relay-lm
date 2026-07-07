#!/usr/bin/env python3
"""LAT-1 offline bench fixture generator: synthetic Primary MEM stores.

TEST FIXTURE GENERATOR ONLY. This tool builds fully synthetic memory stores
under ``runtime/bench/`` that mimic the Primary MEM on-disk page/index/log
format closely enough for ``scripts/relaylm_lat1_retrieval_bench.py`` to
exercise the real M2 retrieval code path at scale.

It is NOT a substitute for Primary MEM page issuance authority (M3e):
generated pages never go through relaymem primary page publication,
promotion, or reconciliation. This tool must never be pointed at a
production store root or a configured character store root, and generated
stores must never be wired into the production request path. See
``docs/architecture/lat1_latency_measurement.md`` for the reproduction
runbook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm._relaymem_primary_page_writer_common import FRONT_MATTER_KEYS, PAGE_SCHEMA

ALLOWED_ROOT = (REPO_ROOT / "runtime" / "bench").resolve()
DEFAULT_OUT_ROOT = ALLOWED_ROOT / "stores"
DEFAULT_SIZES = (100, 500, 2000, 5000)
DEFAULT_SEED = 20260707
_MAX_INDEX_LOG_ENTRIES = 100

# (memory_layer, subdir, target_category) -- mirrors the real Primary MEM
# layout's candidate directories (relaylm/_relaymem_store_impl.py).
_CANDIDATE_DIRS: tuple[tuple[str, str, str], ...] = (
    ("primary", "sessions", "primary_sessions"),
    ("primary", "scenes", "primary_scenes"),
    ("primary", "relationships", "primary_relationships"),
    ("primary", "projects", "primary_projects"),
    ("secondary", "projects", "secondary_projects"),
    ("secondary", "concepts", "secondary_concepts"),
    ("secondary", "claims", "secondary_claims"),
    ("secondary", "summaries", "secondary_summaries"),
    ("secondary", "relations", "secondary_relations"),
)

_SYNTHETIC_WORDS = (
    "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima "
    "mike november oscar papa quebec romeo sierra tango uniform victor whiskey "
    "xray yankee zulu orbit lattice signal harbor meadow canyon ember quartz "
    "vector prism cinder marble willow ridge basin tundra glacier plateau "
    "current channel current beacon compass anchor drift current relay bench"
).split()


def _synthetic_words(rng: random.Random, count: int) -> str:
    return " ".join(rng.choice(_SYNTHETIC_WORDS) for _ in range(count))


def _synthetic_body(rng: random.Random) -> str:
    paragraph_count = rng.randint(2, 4)
    paragraphs = []
    for _ in range(paragraph_count):
        sentence_count = rng.randint(3, 6)
        sentences = [
            _synthetic_words(rng, rng.randint(6, 16)).capitalize() + "."
            for _ in range(sentence_count)
        ]
        paragraphs.append(" ".join(sentences))
    return "\n\n".join(paragraphs)


def _digest(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _front_matter_block(values: dict[str, str]) -> str:
    lines = [f"{key}: {json.dumps(values[key], ensure_ascii=False)}" for key in FRONT_MATTER_KEYS]
    return "---\n" + "\n".join(lines) + "\n---\n"


def _build_page(rng: random.Random, index: int, layer: str, subdir: str) -> tuple[str, str]:
    """Return (filename, markdown) for one synthetic page."""

    filename = f"lat1_bench_{index:06d}.md"
    body = _synthetic_body(rng)
    values = {
        "summary": f"LAT-1 synthetic bench page {index:06d} ({layer}/{subdir}).",
        "schema_version": PAGE_SCHEMA,
        "memory_layer": layer,
        "memory_kind": subdir,
        "source_event_kind": "turn",
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "namespace": "lat1-bench",
        "lineage_fingerprint": _digest("lat1-bench-lineage", str(index)),
        "idempotency_key": _digest("lat1-bench-idempotency", str(index)),
        "summary_origin": "synthetic_bench_generator",
        "content_role": "memory_body",
        "title": f"LAT-1 Bench Page {index:06d}",
    }
    markdown = _front_matter_block(values) + body + "\n"
    return filename, markdown


def _index_entry_line(
    *, entry_id: str, page_relative_path: str, page_digest: str, target_category: str
) -> str:
    payload = {
        "entry_id": entry_id,
        "idempotency_key": _digest("lat1-bench-idempotency", entry_id),
        "memory_kind": target_category,
        "namespace": "lat1-bench",
        "page_digest": page_digest,
        "page_relative_path": page_relative_path,
        "promotion_policy": "free_to_update",
        "safety_scope": "ordinary_memory",
        "schema_version": "relaymem.primary_index_entry.v0",
        "source_event_kind": "turn",
        "target_category": target_category,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"<!-- relaymem-primary-index-entry-v0 {encoded} -->"


def _log_entry_line(*, entry_id: str, page_digest: str) -> str:
    payload = {
        "index_entry_id": entry_id,
        "lineage_fingerprint": _digest("lat1-bench-lineage", entry_id),
        "operation": "primary_page_published",
        "page_digest": page_digest,
        "schema_version": "relaymem.primary_log_entry.v0",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"<!-- relaymem-primary-log-entry-v0 {encoded} -->"


def _generate_store(store_root: Path, *, size: int, seed: int) -> None:
    rng = random.Random(seed)
    mem_root = store_root / "memory" / "mem"
    index_lines = ["# Index"]
    log_lines = ["# Log"]

    for index in range(size):
        layer, subdir, target_category = _CANDIDATE_DIRS[index % len(_CANDIDATE_DIRS)]
        page_dir = mem_root / layer / subdir
        page_dir.mkdir(parents=True, exist_ok=True)
        filename, markdown = _build_page(rng, index, layer, subdir)
        (page_dir / filename).write_text(markdown, encoding="utf-8")
        if index < _MAX_INDEX_LOG_ENTRIES:
            page_digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
            entry_id = _digest("lat1-bench-entry", str(index))
            relative_path = f"memory/mem/{layer}/{subdir}/{filename}"
            index_lines.append(
                _index_entry_line(
                    entry_id=entry_id,
                    page_relative_path=relative_path,
                    page_digest=page_digest,
                    target_category=target_category,
                )
            )
            log_lines.append(_log_entry_line(entry_id=entry_id, page_digest=page_digest))

    if size > _MAX_INDEX_LOG_ENTRIES:
        omitted = size - _MAX_INDEX_LOG_ENTRIES
        note = (
            f"<!-- lat1-bench-note: {omitted} further synthetic pages omitted from "
            "index/log for control-file size; M2 retrieval reads page files "
            "directly and does not require one index/log entry per page. -->"
        )
        index_lines.append(note)
        log_lines.append(note)

    (mem_root / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    (mem_root / "log.md").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


def _validate_out_root(out_root: Path) -> Path:
    resolved = out_root.resolve()
    try:
        resolved.relative_to(ALLOWED_ROOT)
    except ValueError:
        raise SystemExit(
            f"error: --out-root must resolve under {ALLOWED_ROOT} "
            f"(got {resolved}); refusing to write outside the gitignored "
            "LAT-1 bench directory"
        )
    return resolved


def _validate_target_dir(path: Path) -> Path:
    if path.is_symlink():
        raise SystemExit(
            "error: refusing to write through symlinked bench store directory "
            f"(fail-closed): {path}"
        )
    resolved = path.resolve()
    try:
        resolved.relative_to(ALLOWED_ROOT)
    except ValueError:
        raise SystemExit(
            f"error: bench store directory must resolve under {ALLOWED_ROOT} "
            f"(got {resolved}); refusing to write outside the gitignored "
            "LAT-1 bench directory"
        )
    if path.exists() and not path.is_dir():
        raise SystemExit(
            f"error: refusing to overwrite existing non-directory bench store target: {path}"
        )
    return path


def _parse_sizes(raw: str) -> list[int]:
    sizes = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        size = int(token)
        if size <= 0:
            raise SystemExit(f"error: --sizes entries must be positive integers (got {token})")
        sizes.append(size)
    if not sizes:
        raise SystemExit("error: --sizes must list at least one positive integer")
    return sizes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default=",".join(str(s) for s in DEFAULT_SIZES))
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    sizes = _parse_sizes(args.sizes)
    out_root = _validate_out_root(Path(args.out_root))

    target_dirs = {size: _validate_target_dir(out_root / f"size_{size}") for size in sizes}
    existing_nonempty = [
        str(path) for path in target_dirs.values() if path.exists() and any(path.iterdir())
    ]
    if existing_nonempty:
        joined = ", ".join(existing_nonempty)
        raise SystemExit(
            "error: refusing to overwrite existing non-empty bench store "
            f"directories (fail-closed): {joined}"
        )

    for size, path in target_dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        _generate_store(path, size=size, seed=args.seed + size)
        print(f"generated size={size} path={path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())