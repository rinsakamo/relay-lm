from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPLACEMENTS = {
    "docs/PROJECT_STATUS.md": {
        "  - docs/architecture/o1a_two_lane_scheduler_contract.md\n": "  - docs/architecture/o1a_two_lane_scheduler_contract.md\n  - docs/architecture/o1c_eligible_b2_queue_lane.md\n",
        "Scheduler production: O1B through O1F unimplemented": "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete\nScheduler remaining production: O1B and O1D through O1F unimplemented",
        "- O1A pure two-lane round/result/disposition contract.\n": "- O1A pure two-lane round/result/disposition contract;\n- O1C one bounded eligible B2/B3 queue-lane discovery and one existing C2 delegation.\n",
        "  -> queue lane: at most one future O1C discovery and one existing C2 delegation": "  -> queue lane: at most one O1C discovery and one existing C2 delegation",
        "Still separate:\n\n- O1B sealed I1-G record discovery and one I1-GC delegation;\n- O1C eligible B2 discovery and one O0-compatible C2 delegation;": "O1C is complete for one independent bounded queue-root inventory, due/future classification, deterministic selection, canonical reread, server-owned scope resolution, and at most one existing C2 delegation. It does not start a scheduler round or loop.\n\nStill separate:\n\n- O1B sealed I1-G record discovery and one I1-GC delegation;",
        "|| O1C queue-record discovery\n": "",
        "- O1B through O1F, O2, and O3;": "- O1B, O1D through O1F, O2, and O3;",
    },
    "docs/architecture/o0_local_one_job_runner.md": {
        "O1A now defines the future scheduler round and idle contract only. It does not change O0 production behavior. O1C will later extract or reuse a narrow O0-compatible queue discovery/reread/scope/C2-request helper while preserving the O0 CLI and smokes.": "O1A defines the scheduler round and idle contract only. O1C now consumes the same narrow queue discovery/reread/scope/C2-request helper as O0 while preserving the O0 CLI, projection, exit behavior, and smokes.",
        "## Future O1C reuse boundary": "## Shared O0/O1C production helper boundary",
        "O1C must not launch this CLI as a subprocess or parse its stdout as a production interface. It must not reimplement B3 claim or change C2 request semantics.": "O1C does not launch this CLI as a subprocess or parse its stdout as a production interface. It does not reimplement B3 claim or change C2 request semantics.",
        "The intended future refactor target is a narrow production helper containing only:": "The implemented shared production helper contains only:",
        "O1A does not perform this refactor. O0 CLI behavior and existing smokes remain compatibility requirements.": "O1C completes this refactor. O0 CLI behavior and existing functional/security smokes remain compatibility requirements and use the same production helper.",
        "a future O1C queue lane races O0": "the O1C queue lane races O0",
        "O1C  one B2 discovery and C2 delegation": "O1C  one B2/B3 discovery and C2 delegation — complete",
    },
    "docs/architecture/o1a_two_lane_scheduler_contract.md": {
        "  - o0_local_one_job_runner.md\n": "  - o0_local_one_job_runner.md\n  - o1c_eligible_b2_queue_lane.md\n",
        "**Contract and pure deterministic aggregation model complete; production scheduler unimplemented.**": "**Contract and pure deterministic aggregation model complete; O1C queue adapter complete; production scheduler loop unimplemented.**",
        "The following remain unimplemented:\n\n```text\nO1B  one eligible sealed I1-G record discovery and one I1-GC delegation\nO1C  one eligible B2 record discovery and one C2 delegation\nO1D  deterministic within-lane ordering, fairness, retry-time and backoff policy": "O1C is complete as one bounded production queue-lane adapter. The following remain unimplemented:\n\n```text\nO1B  one eligible sealed I1-G record discovery and one I1-GC delegation\nO1D  deterministic within-lane ordering, fairness, retry-time and backoff policy",
        "-> future O1C bounded discovery": "-> O1C bounded discovery",
        "Future O1C eligibility:": "O1C eligibility:",
        "O1A defines the result contract but not production adapters.": "O1A defines the result contract. O1C implements the production queue adapter; O1B replay-lane production remains unimplemented.",
        "O1B may discover and classify but cannot implement replay convergence. O1C may discover and construct the existing exact C2 request but cannot implement B3 transitions or worker execution.": "O1B may discover and classify but cannot implement replay convergence. O1C now discovers, canonically rereads, resolves scope, and constructs the existing exact C2 request, but it cannot implement B3 transitions or worker execution.",
    },
}

for relative, replacements in REPLACEMENTS.items():
    path = ROOT / relative
    body = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        if old not in body:
            raise SystemExit(f"missing anchor: {relative}: {old}")
        body = body.replace(old, new)
    path.write_text(body, encoding="utf-8")

PLAN_FILES = (
    "docs/architecture/pipeline_implementation_plan.md",
    "docs/architecture/post_i3_evaluation_work_roadmap.md",
    "docs/architecture/relaymem_mvp_implementation_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
)
SECTION = """## O1C current reconciliation

O1C is complete for one bounded, non-recursive, secure B2/B3 queue inventory; due/future classification; deterministic one-candidate selection; canonical reread; server-owned character/store resolution; fresh exact C2 request construction; and at most one existing C2 delegation. O0 and O1C share one production candidate helper, while O0 CLI, projection, and exit behavior remain unchanged.

O1B and O1D through O1F remain unimplemented. O1C does not complete a scheduler round loop, polling, sleep, fairness, retry-delay/backoff/jitter, stale recovery, cancellation, graceful shutdown, supervision, or always-on operation.
"""

for relative in PLAN_FILES:
    path = ROOT / relative
    body = path.read_text(encoding="utf-8")
    body = body.replace("O1B through O1F", "O1B and O1D through O1F")
    body = body.replace("future O1C", "O1C")
    body = body.replace("Future O1C", "O1C")
    body = body.replace("O1C queue discovery/C2 delegation remains unimplemented", "O1C queue discovery/C2 delegation is complete")
    body = body.replace("O1C queue discovery and one C2 delegation remain unimplemented", "O1C queue discovery and one C2 delegation are complete")
    body = body.replace("O1C eligible B2 discovery and one C2 delegation remains unimplemented", "O1C eligible B2/B3 discovery and one C2 delegation is complete")
    body = body.replace("O1C  one eligible B2 record discovery and one C2 delegation     unimplemented", "O1C  one eligible B2/B3 record discovery and one C2 delegation  complete")
    if "## O1C current reconciliation" not in body:
        body = body.rstrip() + "\n\n" + SECTION
    path.write_text(body, encoding="utf-8")

print("O1C docs patch applied")
