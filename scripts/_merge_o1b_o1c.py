from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONFLICT_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/architecture/o1a_two_lane_scheduler_contract.md",
    "docs/architecture/pipeline_implementation_plan.md",
    "docs/architecture/post_i3_evaluation_work_roadmap.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "scripts/relaylm_documentation_current_boundary_smoke.py",
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, body: str) -> None:
    (ROOT / path).write_text(body, encoding="utf-8")


def replace(path: str, old: str, new: str, *, required: bool = True) -> None:
    body = read(path)
    if old not in body:
        if required:
            raise AssertionError(f"{path}: missing anchor {old!r}")
        return
    write(path, body.replace(old, new))


def append_main_marker(path: str) -> None:
    body = read(path)
    main = subprocess.check_output(
        ["git", "show", f"origin/main:{path}"], text=True
    )
    markers = [
        marker
        for marker in (
            "<!-- O1B_CURRENT_BOUNDARY -->",
            "<!-- O1B_DOC_INDEX -->",
            "<!-- O1B_LANDED_HANDOFF -->",
        )
        if marker in main
    ]
    if not markers:
        return
    marker = markers[-1]
    if marker in body:
        return
    section = main[main.index(marker):].rstrip()
    write(path, body.rstrip() + "\n\n" + section + "\n")


def merge_project_status() -> None:
    path = "docs/PROJECT_STATUS.md"
    replace(
        path,
        "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete\n"
        "Scheduler remaining production: O1B and O1D through O1F unimplemented",
        "Scheduler replay lane: O1B one bounded sealed-record discovery/reread/I1-GC adapter complete\n"
        "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete\n"
        "Scheduler remaining production: O1D through O1F unimplemented",
    )
    replace(
        path,
        "- O1A pure two-lane round/result/disposition contract;\n"
        "- O1C one bounded eligible B2/B3 queue-lane discovery and one existing C2 delegation.",
        "- O1A pure two-lane round/result/disposition contract;\n"
        "- O1B one bounded eligible sealed I1-G replay-lane discovery and one existing I1-GC delegation;\n"
        "- O1C one bounded eligible B2/B3 queue-lane discovery and one existing C2 delegation.",
    )
    replace(
        path,
        "  -> replay lane: at most one future O1B discovery and one existing I1-GC delegation",
        "  -> replay lane: one bounded O1B discovery and at most one existing I1-GC delegation",
    )
    replace(
        path,
        "O1C is complete for one independent bounded queue-root inventory, due/future classification, deterministic selection, canonical reread, server-owned scope resolution, and at most one existing C2 delegation. It does not start a scheduler round or loop.\n\n"
        "Still separate:\n\n"
        "- O1B sealed I1-G record discovery and one I1-GC delegation;",
        "O1B is complete for one bounded sealed I1-G inventory, deterministic selection, canonical selected-record reread, and at most one existing I1-GC delegation. O1C is complete for one independent bounded queue-root inventory, due/future classification, deterministic selection, canonical reread, server-owned scope resolution, and at most one existing C2 delegation. Neither starts a scheduler round or loop.\n\n"
        "Still separate:",
    )
    replace(path, "|| O1B sealed-record discovery\n", "", required=False)
    replace(path, "- O1B, O1D through O1F, O2, and O3;", "- O1D through O1F, O2, and O3;")
    append_main_marker(path)
    replace(path, "It does not implement O1C queue discovery,", "It does not implement the O1C queue algorithm,", required=False)
    replace(path, "O1C queue discovery,", "O1C queue discovery is complete;", required=False)


def merge_indexes() -> None:
    path = "docs/README.md"
    replace(
        path,
        "O1A is complete as the pure replay-before-queue round and idle contract. O1C is complete for one bounded B2/B3 inventory, due/future classification, canonical reread, server-owned scope resolution, and at most one existing C2 delegation. O1B sealed-record discovery, O1D fairness/backoff, O1E stale recovery/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented.",
        "O1A is complete as the pure replay-before-queue round and idle contract. O1B is complete for one bounded sealed I1-G inventory, canonical selected-record reread, and at most one existing I1-GC delegation. O1C is complete for one bounded B2/B3 inventory, due/future classification, canonical reread, server-owned scope resolution, and at most one existing C2 delegation. O1D fairness/backoff, O1E stale recovery/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented.",
    )
    append_main_marker(path)
    replace(path, "O1C through O1F, O2, and O3 remain unimplemented", "O1D through O1F, O2, and O3 remain unimplemented", required=False)

    path = "docs/architecture/README.md"
    replace(
        path,
        "O1A remains the pure replay-before-queue round/idle contract. O1C now implements one bounded queue-lane opportunity using an O0-compatible shared candidate helper and one existing C2 delegation. O1B and O1D through O1F remain production scheduling work;",
        "O1A remains the pure replay-before-queue round/idle contract. O1B now implements one bounded sealed-record replay-lane opportunity using the existing I1-GC authority. O1C implements one bounded queue-lane opportunity using an O0-compatible shared candidate helper and one existing C2 delegation. O1D through O1F remain production scheduling work;",
    )
    append_main_marker(path)
    replace(path, "O1C queue discovery and the production round loop remain unimplemented", "O1C queue discovery is complete; the production round loop remains unimplemented", required=False)


def merge_o1a() -> None:
    path = "docs/architecture/o1a_two_lane_scheduler_contract.md"
    replace(path, "  - o0_local_one_job_runner.md\n", "  - o0_local_one_job_runner.md\n  - o1b_sealed_i1g_replay_lane.md\n", required=False)
    replace(
        path,
        "**Contract and pure deterministic aggregation model complete; O1C queue adapter complete; production scheduler loop unimplemented.**",
        "**Contract and pure deterministic aggregation model complete; O1B replay adapter and O1C queue adapter complete; production scheduler loop unimplemented.**",
    )
    replace(
        path,
        "O1C is complete as one bounded production queue-lane adapter. The following remain unimplemented:\n\n```text\nO1B  one eligible sealed I1-G record discovery and one I1-GC delegation\nO1D",
        "O1B and O1C are complete as bounded production lane adapters. The following remain unimplemented:\n\n```text\nO1D",
    )
    replace(path, "-> future O1B bounded discovery", "-> O1B bounded discovery")
    replace(path, "Future O1B eligibility:", "O1B eligibility:")
    replace(
        path,
        "O1A defines the result contract. O1C implements the production queue adapter; O1B replay-lane production remains unimplemented.",
        "O1A defines the result contract. O1B implements the production replay adapter and O1C implements the production queue adapter.",
    )
    replace(
        path,
        "O1B may discover and classify but cannot implement replay convergence. O1C now discovers, canonically rereads, resolves scope, and constructs the existing exact C2 request, but it cannot implement B3 transitions or worker execution.",
        "O1B discovers, classifies, canonically rereads, and delegates once to I1-GC but cannot implement replay convergence. O1C discovers, canonically rereads, resolves scope, and constructs the existing exact C2 request, but it cannot implement B3 transitions or worker execution.",
    )
    append_main_marker(path)


def merge_plan_docs() -> None:
    paths = (
        "docs/architecture/pipeline_implementation_plan.md",
        "docs/architecture/post_i3_evaluation_work_roadmap.md",
        "docs/architecture/relaymem_mvp_implementation_plan.md",
        "docs/architecture/relaymem_slp_current_target.md",
    )
    for path in paths:
        body = read(path)
        replacements = {
            "O1B and O1D through O1F": "O1D through O1F",
            "O1B through O1F": "O1D through O1F",
            "future O1B": "O1B",
            "Future O1B": "O1B",
            "O1B sealed-record discovery/delegation\n": "",
            "O1C queue-record discovery/delegation\n": "",
            "O1B sealed-record discovery/delegation — complete\n": "",
            "O1C queue-record discovery/delegation — complete\n": "",
        }
        for old, new in replacements.items():
            body = body.replace(old, new)
        body = body.replace(
            "O1A two-lane round / adapter / idle contract: contract complete\n  O1D through O1F production scheduling: unimplemented",
            "O1A two-lane round / adapter / idle contract: contract complete\n  O1B sealed replay-lane adapter: complete\n  O1C eligible queue-lane adapter: complete\n  O1D through O1F production scheduling: unimplemented",
        )
        body = body.replace(
            "### O1B and O1D through O1F: unimplemented",
            "### O1B and O1C: complete; O1D through O1F unimplemented",
        )
        body = body.replace(
            "O1B and O1D through O1F remain unimplemented.",
            "O1D through O1F remain unimplemented.",
        )
        write(path, body)
        append_main_marker(path)
        replace(path, "O1C through O1F remain unimplemented", "O1D through O1F remain unimplemented", required=False)
        replace(path, "O1C queue discovery and one C2 delegation remain unimplemented", "O1C queue discovery and one C2 delegation are complete", required=False)
        replace(path, "O1C eligible B2 discovery and one C2 delegation remains unimplemented", "O1C eligible B2/B3 discovery and one C2 delegation is complete", required=False)


def merge_documentation_smoke() -> None:
    path = "scripts/relaylm_documentation_current_boundary_smoke.py"
    replace(path, "O1A/O1C, and roadmap docs", "O1A/O1B/O1C, and roadmap docs")
    replace(
        path,
        '    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",\n',
        '    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md",\n    "docs/architecture/o1b_sealed_i1g_replay_lane.md",\n',
    )
    replace(
        path,
        '        "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete",\n        "Scheduler remaining production: O1B and O1D through O1F unimplemented",',
        '        "Scheduler replay lane: O1B one bounded sealed-record discovery/reread/I1-GC adapter complete",\n        "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete",\n        "Scheduler remaining production: O1D through O1F unimplemented",',
    )
    additions = {
        '        "## O1C current reconciliation",\n    ),\n    "docs/architecture/post_i3_evaluation_work_roadmap.md"': '        "## O1C current reconciliation",\n        "O1B sealed replay-lane discovery — complete",\n    ),\n    "docs/architecture/post_i3_evaluation_work_roadmap.md"',
        '        "## O1C current reconciliation",\n    ),\n    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md"': '        "## O1C current reconciliation",\n        "O1B sealed replay-lane discovery — complete",\n    ),\n    "docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md"',
        '        "### I1-GE — unimplemented",\n    ),\n    "docs/architecture/relaymem_mvp_implementation_plan.md"': '        "### I1-GE — unimplemented",\n        "O1B sealed replay-lane discovery — complete",\n    ),\n    "docs/architecture/relaymem_mvp_implementation_plan.md"',
        '        "No production hidden-state filtering exists yet because I-4D integration is not implemented",\n        "## O1C current reconciliation",': '        "No production hidden-state filtering exists yet because I-4D integration is not implemented",\n        "O1B sealed replay-lane discovery — complete",\n        "## O1C current reconciliation",',
        '        "Forget is not product-complete until I-4C2 through I-4F",\n        "## O1C current reconciliation",': '        "Forget is not product-complete until I-4C2 through I-4F",\n        "O1B sealed replay-lane discovery — complete",\n        "## O1C current reconciliation",',
        '        "I1-GA, I1-GB, and I1-GC are complete",\n        "Phase I-4C1 is complete",': '        "I1-GA, I1-GB, and I1-GC are complete",\n        "O1B is complete",\n        "Phase I-4C1 is complete",',
        '        "I1-GC provides the caller-selected one-record convergence authority",\n        "Phase I-4C1 Primary Forget Hidden-Successor Commit",': '        "I1-GC provides the caller-selected one-record convergence authority",\n        "O1B connects O1A",\n        "Phase I-4C1 Primary Forget Hidden-Successor Commit",',
    }
    for old, new in additions.items():
        replace(path, old, new, required=False)
    replace(
        path,
        '    "docs/architecture/o1a_two_lane_scheduler_contract.md": (\n',
        '    "docs/architecture/o1b_sealed_i1g_replay_lane.md": (\n'
        '        "Production replay-lane adapter complete",\n'
        '        "bounded non-recursive secure inventory",\n'
        '        "lexicographically first sealed-pending locator",\n'
        '        "existing I1-GC delegation at most once",\n'
        '        "content-free",\n'
        '    ),\n'
        '    "docs/architecture/o1a_two_lane_scheduler_contract.md": (\n',
    )
    replace(
        path,
        '        "O1C queue adapter complete; production scheduler loop unimplemented.",',
        '        "O1B replay adapter and O1C queue adapter complete; production scheduler loop unimplemented.",',
    )
    replace(
        path,
        "STALE_O1C = (",
        'STALE_O1B = (\n'
        '    "Scheduler production: O1B through O1F unimplemented",\n'
        '    "O1B through O1F, O2, and O3",\n'
        '    "O1B sealed-record discovery: unimplemented",\n'
        '    "O1B sealed-record discovery — unimplemented",\n'
        ')\n\n\nSTALE_O1C = (',
    )
    replace(
        path,
        "        forbid(path, *STALE_I1GC)\n        forbid(path, *STALE_O1C)",
        "        forbid(path, *STALE_I1GC)\n        forbid(path, *STALE_O1B)\n        forbid(path, *STALE_O1C)",
    )


def main() -> None:
    merge_project_status()
    merge_indexes()
    merge_o1a()
    merge_plan_docs()
    merge_documentation_smoke()

    for path in CONFLICT_DOCS:
        body = read(path)
        if "<<<<<<<" in body or ">>>>>>>" in body or "=======" in body:
            raise AssertionError(f"unresolved conflict marker in {path}")

    required = {
        "docs/PROJECT_STATUS.md": (
            "Scheduler replay lane: O1B one bounded sealed-record discovery/reread/I1-GC adapter complete",
            "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete",
            "Scheduler remaining production: O1D through O1F unimplemented",
        ),
        "docs/README.md": ("O1B is complete", "O1C is complete"),
        "docs/architecture/README.md": ("O1B connects O1A", "O1C Eligible B2/B3 Queue Lane"),
        "docs/architecture/o1a_two_lane_scheduler_contract.md": (
            "O1B replay adapter and O1C queue adapter complete",
            "O1B landed handoff",
            "O1B and O1C are complete as bounded production lane adapters",
        ),
        "scripts/relaylm_documentation_current_boundary_smoke.py": (
            "STALE_O1B",
            "STALE_O1C",
            "docs/architecture/o1b_sealed_i1g_replay_lane.md",
            "docs/architecture/o1c_eligible_b2_queue_lane.md",
        ),
    }
    for path, anchors in required.items():
        body = read(path)
        missing = [anchor for anchor in anchors if anchor not in body]
        if missing:
            raise AssertionError(f"{path}: missing merged anchors {missing!r}")

    print("O1B/O1C documentation merge reconciliation complete")


if __name__ == "__main__":
    main()
