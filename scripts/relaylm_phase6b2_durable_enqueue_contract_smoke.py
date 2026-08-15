"""Check B2 contract ownership without coupling to status or roadmap prose."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def body(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check(text: str, *values: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, missing


def main() -> None:
    check(
        body("docs/contracts/slp/durable-queue.md"),
        "B2 may inspect or atomically create one durable queue record",
        "enqueued_new",
        "duplicate_existing",
        "write_failed",
    )
    check(
        body("relaylm/relaymem_slp_durable_enqueue.py"),
        "relaymem.slp_durable_enqueue.v0",
        "exact_b1_preflight_result_required",
    )
    print("Phase 6-B2 durable enqueue contract smoke: ok")


if __name__ == "__main__":
    main()
