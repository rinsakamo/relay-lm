"""Check B2 ownership and the current Phase 6-C1 status."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def body(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check(text: str, *values: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, missing


def main() -> None:
    check(
        body("docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md"),
        "Phase 6-B2 is implemented",
        "atomic create-if-absent publication",
        "enqueued_new",
        "duplicate_existing",
        "write_failed",
    )
    check(
        body("docs/architecture/relaymem_slp_current_target.md"),
        "Phase 6-B2 performs atomic durable enqueue",
        "one-job claim/rehydrate/execute adapter",
    )
    check(
        body("docs/architecture/pipeline_implementation_plan.md"),
        "B2 atomic durable enqueue: complete",
        "Phase 6-C1-0 through C1-5 are complete",
    )
    check(
        body("docs/PROJECT_STATUS.md"),
        "B2 atomic durable enqueue",
        "C1-5 source-before-queue durable protected artifact publication",
        "B3 claim -> C1-5 rehydrate -> C1-2 execute",
    )
    check(body("relaylm/relaymem_slp_durable_enqueue.py"), "relaymem.slp_durable_enqueue.v0")
    print("Phase 6-B2 durable enqueue contract smoke: ok")


if __name__ == "__main__":
    main()
