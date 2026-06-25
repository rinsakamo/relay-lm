"""Check B2 ownership without freezing one status sentence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def body(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check(text: str, *values: str) -> None:
    missing = [value for value in values if value not in text]
    assert not missing, missing


def check_any(text: str, *values: str) -> None:
    assert any(value in text for value in values), values


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
        "C2 one-job claim/rehydrate/execute adapter",
    )
    plan = body("docs/architecture/pipeline_implementation_plan.md")
    check(
        plan,
        "Phase 6-C1-0 through C1-5 are complete",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter is complete",
    )
    check_any(
        plan,
        "B0-B3: complete",
        "B0 through B3: complete",
        "B2 atomic durable enqueue: complete",
    )
    check(
        body("docs/PROJECT_STATUS.md"),
        "B0-B3 durable enqueue and fenced lifecycle",
        "C1-5 keeps queue records content-free and persists the claim-independent protected capture before queue publication",
        "C2 one-job claim/rehydrate/execute adapter: complete",
    )
    check(body("relaylm/relaymem_slp_durable_enqueue.py"), "relaymem.slp_durable_enqueue.v0")
    print("Phase 6-B2 durable enqueue contract smoke: ok")


if __name__ == "__main__":
    main()
