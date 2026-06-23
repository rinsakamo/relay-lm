from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/pipeline_implementation_plan.md",
    "docs/architecture/phase6_async_relayslp_bounded_slice.md",
    "docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md",
    "docs/architecture/phase6c1_primary_mem_worker_contract.md",
    "docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md",
    "docs/architecture/phase6c1_durable_protected_source_persistence.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
)

MARKER_START = "<!-- phase6c2-status:start -->"
MARKER_END = "<!-- phase6c2-status:end -->"

COMMON_BOUNDARY = """{start}
## Phase 6-C2 completion alignment

The bounded E-to-F integration is complete for one caller-selected canonical queued job:

```text
I1-B producer: complete
B3 lifecycle: complete
C1-0 through C1-5: complete
C2 one-job claim/rehydrate/execute adapter: complete
next-turn recall and scope isolation: next
SOUL Lab real observation: later
auditable Correct operation: later
```

C2 delegates claim mutation to canonical B3, protected-source preparation to C1-5, and execution plus retry/terminal transition to the unchanged C1-2 worker. It does not add queue scanning, scheduling, polling, daemon/service lifecycle, a worker pool, pre-enqueue background-finalizer crash recovery, next-turn recall, memory correction, or Secondary MEM.

See [Phase 6-C2 One Queued Primary Worker Integration](phase6c2_one_queued_primary_worker_integration.md).
{end}
""".format(start=MARKER_START, end=MARKER_END)

ROOT_COMMON_BOUNDARY = COMMON_BOUNDARY.replace(
    "(phase6c2_one_queued_primary_worker_integration.md)",
    "(architecture/phase6c2_one_queued_primary_worker_integration.md)",
)


def replace_marker(text: str, section: str) -> str:
    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END) + r"\n?",
        re.DOTALL,
    )
    text = pattern.sub("", text).rstrip() + "\n\n"
    return text + section


def project_status(text: str) -> str:
    text = text.replace(
        "  - docs/architecture/phase6c1_durable_protected_source_persistence.md\n",
        "  - docs/architecture/phase6c1_durable_protected_source_persistence.md\n"
        "  - docs/architecture/phase6c2_one_queued_primary_worker_integration.md\n",
    )
    text = text.replace(
        "- Phase 6-C1-5 durable protected source persistence and restart rehydration.\n",
        "- Phase 6-C1-5 durable protected source persistence and restart rehydration,\n"
        "- Phase 6-C2 one queued-job claim / rehydrate / execute integration adapter.\n",
    )
    text = text.replace(
        "Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete",
        "Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete; C2 one-job adapter complete",
    )
    text = text.replace(
        "- C1-5 source-before-queue durable protected artifact publication and restart rehydration.\n",
        "- C1-5 source-before-queue durable protected artifact publication and restart rehydration,\n"
        "- C2 exact queued-record claim, durable rehydrate, C1-2 execution, and terminal-only cleanup.\n",
    )
    text = re.sub(
        r"(?m)^- the ordinary runtime still lacks a thin one-job adapter.*\n", "", text
    )
    text = re.sub(
        r"(?m)^- an explicit one-job claim/rehydrate/execute adapter.*\n", "", text
    )
    text = re.sub(
        r"(?m)^- a bounded ordinary-runtime one-job claim/rehydrate/execute adapter,\n",
        "",
        text,
    )
    text = text.replace(
        "  -> one-job claim/rehydrate/execute adapter     next integration boundary",
        "  -> C2 one-job claim/rehydrate/execute adapter: complete",
    )
    text = re.sub(
        r"Immediate sequence:\n\n1\. Add a thin one-job integration adapter:.*?\n6\. Treat the visible-response-to-background-finalizer crash window as a separate I1 durability boundary; C1-5 does not claim to close it\.\n",
        "Immediate sequence:\n\n"
        "1. Add a two-turn smoke proving next-turn recall and character/namespace isolation.\n"
        "2. Add real SOUL Lab read APIs for latest run, formed/held/blocked memory, and used memory.\n"
        "3. Add one auditable Correct operation whose result changes later retrieval behavior.\n"
        "4. Treat the visible-response-to-background-finalizer crash window as a separate I1 durability boundary; C1-5 and C2 do not claim to close it.\n",
        text,
        flags=re.DOTALL,
    )
    text = text.replace(
        "I1-B, B3, and C1-0 through C1-5 are complete prerequisites, not the final product goal.",
        "I1-B, B3, C1-0 through C1-5, and C2 are complete prerequisites, not the final product goal.",
    )
    text = text.replace(
        "C1-5 adds restart-safe protected-source recovery for durably enqueued work; it does not make queue scheduling or next-turn recall automatic.",
        "C1-5 and C2 provide restart-safe protected-source recovery and one exact queued-job execution; they do not make queue scheduling or next-turn recall automatic.",
    )
    return replace_marker(text, ROOT_COMMON_BOUNDARY)


def durable_source_doc(text: str) -> str:
    text = text.replace(
        "The pre-enqueue background-finalizer window, one-job queue-to-worker adapter, next-turn recall, and SOUL Lab observation remain unimplemented.",
        "The pre-enqueue background-finalizer window, next-turn recall and scope isolation, and SOUL Lab observation remain unimplemented; the C2 one-job queue-to-worker adapter is now complete.",
    )
    return replace_marker(text, COMMON_BOUNDARY)


def contract_doc(text: str) -> str:
    text = text.replace(
        "one-job queued-record claim/rehydrate/execute adapter",
        "C2 one-job queued-record claim/rehydrate/execute adapter",
    )
    return replace_marker(text, COMMON_BOUNDARY)


def generic_doc(path: str, text: str) -> str:
    text = text.replace(
        "one-job claim/rehydrate/execute integration adapter: next",
        "Phase 6-C2 one-job claim/rehydrate/execute adapter: complete",
    )
    text = text.replace(
        "one-job claim/rehydrate/execute adapter: next",
        "C2 one-job claim/rehydrate/execute adapter: complete",
    )
    text = text.replace(
        "one-job claim/rehydrate/execute adapter is next",
        "C2 one-job claim/rehydrate/execute adapter is complete",
    )
    text = text.replace(
        "one-job queue-to-worker adapter remains unimplemented",
        "C2 one-job queue-to-worker adapter is complete",
    )
    section = ROOT_COMMON_BOUNDARY if path == "docs/README.md" else COMMON_BOUNDARY
    return replace_marker(text, section)


def main() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"missing required docs: {missing!r}")

    for path in REQUIRED_DOCS:
        target = ROOT / path
        original = target.read_text(encoding="utf-8")
        if path == "docs/PROJECT_STATUS.md":
            updated = project_status(original)
        elif path == "docs/architecture/phase6c1_durable_protected_source_persistence.md":
            updated = durable_source_doc(original)
        elif path == "docs/architecture/phase6c1_primary_mem_worker_contract.md":
            updated = contract_doc(original)
        else:
            updated = generic_doc(path, original)
        if updated == original:
            raise SystemExit(f"no Phase 6-C2 update produced for {path}")
        target.write_text(updated, encoding="utf-8")

    print("Phase 6-C2 documentation alignment applied.")


if __name__ == "__main__":
    main()
