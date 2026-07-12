"""Command-line interface for the spike. All output is JSON.

Run via the launcher::

    python experiments/markdown_sqlite_memory/run_spike.py <command> --root DIR
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path, PurePosixPath

from . import bench, cache, durable_usage, search, slp, verify
from .fixtures import init_fixture
from .slp import Candidate, SpikeEnv


def _emit(payload) -> None:
    if dataclasses.is_dataclass(payload):
        payload = dataclasses.asdict(payload)
    json.dump(payload, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _validated_page_rel(value: str) -> str:
    """Validate a user-facing page argument as a relative POSIX Markdown path."""
    if not value or "\x00" in value or "\\" in value:
        raise argparse.ArgumentTypeError(
            "page must be a non-empty relative POSIX path"
        )
    page = PurePosixPath(value)
    if page.is_absolute() or any(part in ("", ".", "..") for part in page.parts):
        raise argparse.ArgumentTypeError(
            "page must stay within the spike pages directory"
        )
    if page.suffix.lower() != ".md":
        raise argparse.ArgumentTypeError("page must have a .md extension")
    return page.as_posix()


def cmd_init_fixture(env: SpikeEnv, args) -> int:
    _emit(init_fixture(env, pages=args.pages, blocks_per_page=args.blocks,
                       seed=args.seed))
    return 0


def cmd_build_cache(env: SpikeEnv, args) -> int:
    conn = env.open_cache()
    stats = cache.build_from_markdown(conn, env.pages_dir)
    conn.close()
    _emit(stats)
    return 0


def cmd_rebuild_cache(env: SpikeEnv, args) -> int:
    for suffix in ("", "-wal", "-shm"):
        p = env.root / (env.cache_path.name + suffix)
        if p.exists():
            p.unlink()
    conn = env.open_cache()
    stats = cache.build_from_markdown(conn, env.pages_dir)
    conn.close()
    _emit({"rebuilt": True, "stats": dataclasses.asdict(stats)})
    return 0


def cmd_search(env: SpikeEnv, args) -> int:
    plan = search.plan_search(
        args.query,
        kind=args.kind,
        user_tags=_split_csv(args.user_tags),
        system_tags=_split_csv(args.system_tags),
        page_prefix=args.page_prefix,
        limit=args.limit,
    )
    conn = env.open_cache()
    hits = search.execute_search(conn, plan)
    usage = {
        hit.block_id: durable_usage.usage_summary_for_cache(conn, hit.block_id)
        for hit in hits
    }
    conn.close()
    _emit({
        "plan": dataclasses.asdict(plan),
        "hits": [dataclasses.asdict(h) for h in hits],
        "usage": usage,
    })
    return 0


def cmd_apply_candidate(env: SpikeEnv, args) -> int:
    candidate = Candidate(
        candidate_id=args.candidate_id,
        page=args.page,
        content=args.content,
        kind=args.kind,
        user_tags=_split_csv(args.user_tags),
        source_refs=_split_csv(args.source_refs),
        block_id=args.block_id,
    )
    result = slp.apply_candidate(env, candidate, worker=args.worker)
    _emit(result)
    return 0 if result.outcome in ("applied", "duplicate", "duplicate_submission") else 1


def cmd_forget(env: SpikeEnv, args) -> int:
    result = slp.forget(env, args.block_id, reason=args.reason)
    _emit(result)
    return 0 if result.outcome in ("applied", "duplicate", "duplicate_submission") else 1


def cmd_restore(env: SpikeEnv, args) -> int:
    result = slp.restore(env, args.block_id, reason=args.reason)
    _emit(result)
    return 0 if result.outcome in ("applied", "duplicate", "duplicate_submission") else 1


def cmd_simulate_failure(env: SpikeEnv, args) -> int:
    """Deterministically crash an apply at a failpoint, then recover."""
    content = args.content or (
        f"simulated failure drill memory for {args.candidate_id} "
        f"at {args.failpoint}"
    )
    candidate = Candidate(
        candidate_id=args.candidate_id,
        page=args.page,
        content=content,
    )
    env.failpoints.arm(args.failpoint)
    crashed = False
    try:
        result = slp.apply_candidate(env, candidate)
        outcome = dataclasses.asdict(result)
    except slp.InjectedFailure as exc:
        crashed = True
        outcome = {"outcome": "crashed", "failpoint": exc.failpoint}
    report = slp.startup(env) if not args.skip_recovery else None
    _emit({"injected": args.failpoint, "crashed": crashed,
           "apply": outcome, "recovery": report})
    return 0


def cmd_recover(env: SpikeEnv, args) -> int:
    _emit(slp.startup(env))
    return 0


def cmd_verify(env: SpikeEnv, args) -> int:
    report = verify.run_verify(env)
    _emit(report)
    return 0 if report["ok"] else 1


def cmd_benchmark(env: SpikeEnv, args) -> int:
    report = bench.run_benchmark(
        env, pages=args.pages, blocks_per_page=args.blocks, searches=args.searches
    )
    _emit(report)
    ok = report["invariants"]["ok"] and all(
        entry["pass"] for entry in report["recovery"].values()
    )
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdsqlite-spike",
        description="Markdown-authority / SQLite-projection memory spike "
                    "(EXPERIMENT ONLY; not wired to production).",
    )
    parser.add_argument("--root", required=True, help="spike working directory")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-fixture", help="write synthetic Markdown pages")
    p.add_argument("--pages", type=int, default=5)
    p.add_argument("--blocks", type=int, default=8)
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(fn=cmd_init_fixture)

    p = sub.add_parser("build-cache", help="full compile Markdown -> cache")
    p.set_defaults(fn=cmd_build_cache)

    p = sub.add_parser("rebuild-cache", help="delete cache db and recompile")
    p.set_defaults(fn=cmd_rebuild_cache)

    p = sub.add_parser("search", help="FTS + metadata search with durable usage events")
    p.add_argument("query")
    p.add_argument("--kind")
    p.add_argument("--user-tags")
    p.add_argument("--system-tags")
    p.add_argument("--page-prefix")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("apply-candidate", help="SLP apply of one candidate")
    p.add_argument("--candidate-id", required=True)
    p.add_argument("--page", required=True, type=_validated_page_rel)
    p.add_argument("--content", required=True)
    p.add_argument("--kind", default="fact")
    p.add_argument("--user-tags")
    p.add_argument("--source-refs")
    p.add_argument("--block-id", help="update an existing block")
    p.add_argument("--worker", default="cli-worker")
    p.set_defaults(fn=cmd_apply_candidate)

    p = sub.add_parser("forget", help="hide a memory and tombstone it (reversible)")
    p.add_argument("--block-id", required=True)
    p.add_argument("--reason", default="user_forget")
    p.set_defaults(fn=cmd_forget)

    p = sub.add_parser("restore", help="restore a hidden memory and clear its tombstone")
    p.add_argument("--block-id", required=True)
    p.add_argument("--reason", default="user_restore")
    p.set_defaults(fn=cmd_restore)

    p = sub.add_parser("simulate-failure", help="crash at a failpoint, then recover")
    p.add_argument("--failpoint", required=True, choices=slp.FAILPOINTS)
    p.add_argument("--candidate-id", default="simulated-failure")
    p.add_argument("--page", type=_validated_page_rel,
                   default=_validated_page_rel("simulated.md"))
    p.add_argument("--content", help="defaults to unique per candidate/failpoint")
    p.add_argument("--skip-recovery", action="store_true",
                   help="leave the crash state on disk for inspection")
    p.set_defaults(fn=cmd_simulate_failure)

    p = sub.add_parser("recover", help="run startup recovery")
    p.set_defaults(fn=cmd_recover)

    p = sub.add_parser("verify", help="run invariant checks")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("benchmark", help="measurements + drills, JSON output")
    p.add_argument("--pages", type=int, default=20)
    p.add_argument("--blocks", type=int, default=25)
    p.add_argument("--searches", type=int, default=50)
    p.set_defaults(fn=cmd_benchmark)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = SpikeEnv(Path(args.root))
    env.root.mkdir(parents=True, exist_ok=True)
    env.pages_dir.mkdir(parents=True, exist_ok=True)
    return args.fn(env, args)


if __name__ == "__main__":
    raise SystemExit(main())
