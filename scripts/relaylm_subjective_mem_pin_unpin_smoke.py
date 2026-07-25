#!/usr/bin/env python3
"""LC-1C process smoke for immutable Subjective MEM Pin / Unpin."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS = REPO_ROOT / "tests"
for path in (REPO_ROOT, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from relaylm.evidence_store import EvidenceRecordStore
from test_subjective_mem_commit_runtime import _commit, _make_workspace
from test_subjective_mem_pin_runtime import _call, _current_page, _proposal
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
        config = CHARACTER_CONFIG.model_copy(
            update={"subjective_mem_workspace_root": str(workspace)}
        )
        env = {
            "store": store,
            "captured": captured,
            "workspace": workspace,
            "workspace_root": workspace,
            "config": config,
            "authority": _character(),
            "assessment_revision": assessment_revision,
            "assessment_state": assessment_state,
            "sm1": sm1,
        }
        st1 = _commit(env)
        require(st1.status == "committed" and st1.current_state is not None, st1)
        env.update({
            "st1": st1,
            "page_path": workspace / "char1/memory/episodes/subjective-mem-v1.md",
        })

        dry = _call(env, _proposal(env, "pin"), key="smoke-dry", apply=False)
        require(dry.status == "dry_run_ready", dry)
        require([item.revision.memory_revision for item in _current_page(env).blocks] == [1], dry)

        pinned = _call(env, _proposal(env, "pin"), key="smoke-pin", seconds=2)
        require(pinned.status == "committed" and pinned.current_state is not None, pinned)
        require(pinned.current_state.lifecycle_state == "pinned", pinned.current_state)

        unpinned = _call(
            env,
            _proposal(env, "unpin", state=pinned.current_state),
            key="smoke-unpin",
            seconds=4,
        )
        require(unpinned.status == "committed" and unpinned.current_state is not None, unpinned)
        require(unpinned.current_state.lifecycle_state == "active", unpinned.current_state)
        require(
            [item.revision.lifecycle_state for item in _current_page(env).blocks]
            == ["active", "pinned", "active"],
            _current_page(env),
        )
    print("PASS: LC-1C Pin / Unpin appended exact immutable lifecycle successors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
