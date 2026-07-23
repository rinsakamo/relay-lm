---
relaylm_doc_type: adr
relaylm_authority: lane_local_continuation_and_explicit_portfolio_execution
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-24
relaylm_volatility: low
relaylm_owner: implementation
relaylm_update_trigger:
  - this decision is superseded
  - lane binding or continuation-command scope changes
  - cross-lane read or write permissions change
  - explicit portfolio execution syntax changes
  - the P0-P8 post-merge selection boundary changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, contract, or API behavior
  - authorization to merge a PR that has not passed required review and validation
  - hidden background or asynchronous execution
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - 0006-repository-structure-and-maintenance-sequencing.md
  - 0007-architecture-first-stable-implementation.md
  - ../planning/workstream-orchestration.md
  - ../../AGENTS.md
  - ../../skills/relaylm-stable-implementation/SKILL.md
relaylm_supersedes: []
relaylm_superseded_by: null
---
# ADR 0008: Lane-local continuation safety and explicit portfolio execution

## Decision summary

RelayLM changes the default scope of bare continuation commands.

The following commands are lane-local:

```text
次に進めて
進めて
続けて
次へ
```

They advance only the lane, pull request, branch, or bounded work item already established by the current conversation or repository working context.

Cross-lane execution requires an explicit portfolio instruction such as:

```text
全レーンを進めて
ポートフォリオを進めて
Lane C・D・Rを並行で進めて
```

This decision narrows the portfolio-selection language in ADR 0006 and the continuation scope in ADR 0007. Their architecture-first, No-Patch, Stable-Structure, review, merge, and post-merge requirements remain unchanged.

A lane-local run may read other lanes to detect conflicts and dependencies. It may not modify, review, comment on, merge, retarget, close, supersede, or start work in another lane.

If exactly one lane or bounded PR cannot be resolved, execution fails closed and asks for a lane or PR instead of choosing from repository priority.

## Context

RelayLM intentionally uses three concurrent workstreams:

```text
Lane C  critical implementation
Lane D  documentation canonicalization and historical retirement
Lane R  repository maintenance
```

Each lane has a separate thread, authority boundary, PR slot, review loop, and sequencing responsibility. A global continuation command that automatically advances another lane can violate those boundaries even when changed paths appear disjoint.

The risks include:

- modifying a PR owned by another thread;
- merging a lane whose reviewer has not completed its own final loop;
- posting comments that alter another lane's convergence state;
- consuming a shared-file or generated-registry decision without the owning lane;
- starting a successor while the lane owner is still correcting the current PR;
- interpreting pending CI in one lane as authority to act in another;
- allowing a generic repository Skill to override a lane-specific initial prompt.

Path-disjointness is not sufficient protection because review ownership and semantic authority can still overlap.

## Decisions

### 1. Bare continuation is lane-local

A bare continuation command advances one scope only.

Scope is resolved in this order:

1. explicit lane, PR, branch, or work item in the current user instruction;
2. lane declared by the current thread's initial prompt or handoff;
3. uniquely identified current PR or branch and its lane metadata;
4. one unambiguous work item already selected in the current conversation.

The result must be one lane or one bounded work item belonging to one lane.

Repository-wide priority is not a lane-binding signal.

### 2. Ambiguous scope fails closed

When more than one lane is plausible and none is explicitly bound, the agent must not:

- edit repository content;
- create or retarget a PR;
- review, comment on, approve, or merge a PR;
- choose the critical lane automatically;
- choose a lane merely because another lane is waiting for CI.

The agent asks the user to identify Lane C, Lane D, Lane R, or a PR.

### 3. Other lanes are read-only in lane-local mode

Cross-lane inspection is permitted only to detect:

- changed-path overlap;
- semantic-authority overlap;
- shared generated registries and status owners;
- stack or merge-order dependencies;
- newer `main` changes that invalidate selected-lane evidence.

Inspection does not grant mutation authority.

Without explicit portfolio authorization, the agent must not:

- push or edit another lane's branch;
- change another PR body or metadata;
- post a review or conversation comment;
- resolve another lane's review thread;
- merge, close, reopen, retarget, or supersede another lane's PR;
- open the next PR in another lane.

### 4. Cross-lane blockers remain blockers

When the selected lane depends on a correction owned by another lane, the agent records the exact dependency and stops or performs another safe action within the selected lane.

It does not fix the other lane as a convenience.

Pending CI may therefore be a valid lane-local stop condition when no other same-lane action is safe.

### 5. Explicit portfolio mode is separate

Only an explicit command authorizing all lanes or multiple named lanes enters portfolio mode.

Portfolio mode may:

- determine P0-P8 state for every authorized lane;
- converge more than one authorized PR;
- use blockers to advance another authorized lane;
- merge clean authorized PRs;
- open successor work within the accepted lane-capacity ceiling.

Portfolio mode still requires:

- one PR slot per lane;
- path and authority disjointness;
- one owner for shared files and registries;
- complete P0-P8 convergence per PR;
- no speculative work merely to fill capacity.

### 6. P8 remains inside the selected lane

After a lane-local merge, P8:

- verifies the merge and resulting `main`;
- performs selected-lane post-merge convergence;
- releases that lane slot;
- selects only the next executable item in the same lane.

It does not automatically move to another lane.

### 7. Lane-specific prompts override generic portfolio selection

The three lane initial prompts declare exclusive lane ownership unless the user explicitly broadens scope.

The root `AGENTS.md` and portable Skill must preserve that boundary. A generic Skill cannot reinterpret `次に進めて` as portfolio execution inside a lane-specific thread.

### 8. Existing work adopts the safety rule immediately

Open Lane C, Lane D, and Lane R PRs do not need to repeat correct P0-P8 work. At their next action, agents must:

- confirm the thread's lane binding;
- treat other lane PRs as read-only;
- record cross-lane dependencies without mutating them;
- select only same-lane successor work after merge.

## Consequences

- Each lane thread can safely use only `次に進めて`.
- A stalled lane no longer causes silent work in another lane.
- Portfolio orchestration remains available but becomes explicit.
- Some generic threads will require one lane-selection question before repository writes.
- Cross-lane dependency resolution may require the user to switch to the owning thread.
- Read-only global inspection remains available for conflict prevention.
- The architecture-first and no-patch discipline remains identical inside each lane.

## Rejected alternatives

### Keep automatic parallel advancement but prohibit only merges

Rejected because comments, reviews, branch edits, PR creation, and correction commits can also alter another lane's state.

### Infer the lane from repository priority

Rejected because priority identifies what should happen globally, not which thread owns the action.

### Treat pending CI as authority to advance another lane

Rejected because CI waiting does not transfer ownership between threads.

### Prohibit all cross-lane reads

Rejected because conflict, dependency, and stale-base detection require repository-wide visibility.

### Remove portfolio execution entirely

Rejected because explicit coordinated portfolio operation remains useful when the user intentionally authorizes it.