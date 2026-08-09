#!/usr/bin/env python3
"""LC-1E process smoke for immutable Subjective MEM Consolidate."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS = REPO_ROOT / "tests"
for path in (REPO_ROOT, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from relaylm.evidence.store import EvidenceRecordStore
from test_subjective_mem_commit_runtime import _commit, _make_workspace
from test_subjective_mem_consolidate_runtime import (
    _call,
    _current_page,
    _lifecycle_config,
    _proposal,
    _selector_events,
)
from test_subjective_mem_runtime import CHARACTER_CONFIG, _asm_ready, _character, _create


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        workspace = _make_workspace(root)
        store = EvidenceRecordStore(str(root / "evidence"))
        captured, assessment_revision, assessment_state = _asm_ready(store)
        sm1 = _create(store, captured, assessment_revision, assessment_state)
        commit_config = CHARACTER_CONFIG.model_copy(
            update={"subjective_mem_workspace_root": str(workspace)}
        )
        env = {
            "store": store,
            "captured": captured,
            "workspace": workspace,
            "workspace_root": workspace,
            "config": commit_config,
            "authority": _character(),
            "assessment_revision": assessment_revision,
            "assessment_state": assessment_state,
            "sm1": sm1,
        }
        st1 = _commit(env)
        require(st1.status == "committed" and st1.current_state is not None, st1)
        env.update({
            "st1": st1,
            "config": _lifecycle_config(workspace),
            "page_path": workspace / "char1/memory/episodes/subjective-mem-v1.md",
        })

        primary = _current_page(env).blocks[0].revision
        require(primary.memory_revision == 1, primary)
        require(primary.formation_stage == "primary", primary)
        require(primary.lifecycle_state == "active", primary)

        before = env["page_path"].read_bytes()
        dry = _call(env, _proposal(env), key="smoke-dry", apply=False)
        require(dry.status == "dry_run_ready", dry)
        require(env["page_path"].read_bytes() == before, dry)

        proposal = _proposal(env)
        applied = _call(env, proposal, key="smoke-consolidate", seconds=2)
        require(applied.status == "committed" and applied.current_state is not None, applied)

        blocks = _current_page(env).blocks
        require([item.revision.memory_revision for item in blocks] == [1, 2], blocks)
        successor = blocks[-1].revision
        require(successor.formation_stage == "secondary", successor)
        require(successor.lifecycle_state == "active", successor)
        require(successor.retrieval_visible is True, successor)
        require(successor.predecessor_revision_or_null == 1, successor)
        require(successor.subjective_meaning == primary.subjective_meaning, successor)
        require(successor.strength.to_dict() == primary.strength.to_dict(), successor)
        require(successor.memory_kind == primary.memory_kind, successor)

        state = applied.current_state
        require(state.current_revision == 2, state)
        require(state.lifecycle_state == "active", state)
        require(state.mutation_state == "none", state)
        require(state.retrieval_eligible is True, state)
        events = _selector_events(env, proposal.expected_current_selector_id)
        require(events is not None and len(events) == 1, events)
    print("PASS: LC-1E Consolidate appended one exact active Secondary successor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
