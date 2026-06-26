from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPLACEMENTS = {
    "docs/PROJECT_STATUS.md": {
        "Scheduler production: O1B through O1F unimplemented": "Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete\nScheduler remaining production: O1B and O1D through O1F unimplemented",
        "  -> queue lane: at most one future O1C discovery and one existing C2 delegation": "  -> queue lane: at most one O1C discovery and one existing C2 delegation",
        "- O1B through O1F, O2, and O3;": "- O1B, O1D through O1F, O2, and O3;",
    },
    "docs/architecture/o0_local_one_job_runner.md": {
        "## Future O1C reuse boundary": "## Shared O0/O1C production helper boundary",
        "The intended future refactor target is a narrow production helper containing only:": "The implemented shared production helper contains only:",
        "a future O1C queue lane races O0": "the O1C queue lane races O0",
        "O1C  one B2 discovery and C2 delegation": "O1C  one B2/B3 discovery and C2 delegation — complete",
    },
    "docs/architecture/o1a_two_lane_scheduler_contract.md": {
        "**Contract and pure deterministic aggregation model complete; production scheduler unimplemented.**": "**Contract and pure deterministic aggregation model complete; O1C queue adapter complete; production scheduler loop unimplemented.**",
        "-> future O1C bounded discovery": "-> O1C bounded discovery",
        "Future O1C eligibility:": "O1C eligibility:",
        "O1A defines the result contract but not production adapters.": "O1A defines the result contract. O1C implements the production queue adapter; O1B replay-lane production remains unimplemented.",
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

print("O1C docs patch applied")
