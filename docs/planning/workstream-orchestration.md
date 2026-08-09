---
relaylm_doc_type: planning
relaylm_authority: lane_local_continuation_explicit_portfolio_and_stable_pr_convergence
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - lane-local or portfolio continuation syntax changes
  - lane binding or cross-lane permissions change
  - the project critical path or lane registry changes
  - the universal P0-P8 lifecycle changes
  - the no-patch or stable-structure gate changes
  - PR concurrency or conflict rules change
  - the authoritative status or sequencing source moves
  - the historical-retirement or retained-record policy changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, contract, or API behavior
  - authorization to merge a PR that has not passed required review and validation
  - background or asynchronous execution
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - repository-structure-migration.md
  - ../DOCUMENTATION_MODEL.md
  - ../adr/0006-repository-structure-and-maintenance-sequencing.md
  - ../adr/0007-architecture-first-stable-implementation.md
  - ../adr/0008-lane-local-continuation-safety.md
  - ../../AGENTS.md
  - ../../skills/relaylm-stable-implementation/SKILL.md
  - ../../skills/relaylm-github-operations/SKILL.md
---
# Workstream Orchestration, Lane-Local Continuation, and Stable PR Convergence

Last reviewed: 2026-08-09 JST

## Purpose

This document defines:

1. lane-local behavior for `次に進めて`, `進めて`, `続けて`, and `次へ`;
2. explicit portfolio behavior for commands that authorize multiple lanes;
3. safe lane binding and cross-lane read-only rules;
4. the architecture-first P0-P8 lifecycle required for every PR;
5. the No-Patch Gate and Stable-Structure Gate;
6. correction, merge, and post-merge convergence boundaries.

A continuation command is an execution command, not a request for a menu. Its execution scope depends on the command mode below.

No command authorizes hidden background execution or delayed work after the current interaction.

## Command modes

### Lane-local continuation mode

The following commands are lane-local by default:

```text
次に進めて
進めて
続けて
次へ
```

They advance only the lane, pull request, branch, or bounded work item already established by the current conversation or repository working context.

A lane-local command does not authorize another lane merely because:

- another lane has a higher repository priority;
- the selected lane is waiting for CI;
- another PR appears path-disjoint;
- portfolio capacity is available;
- a generic Skill can see all open PRs.

### Explicit portfolio mode

Cross-lane execution requires an explicit instruction such as:

```text
全レーンを進めて
ポートフォリオを進めて
Lane C・D・Rを並行で進めて
Lane CとLane Dを進めて
```

Equivalent wording is accepted only when it clearly authorizes all lanes or multiple named lanes.

A scope-specific instruction such as `LC-1だけ進めて`, `ドキュメント整理だけ進めて`, `コード整理を進めて`, or `#672を進めて` selects lane-local mode and does not weaken the lifecycle or stability gates.

## Lane binding

Before any repository write, review, comment, merge, or PR action, resolve scope in this order:

1. explicit lane, PR, branch, or work item in the current user instruction;
2. lane declared by the current thread's initial prompt or handoff;
3. uniquely identified current PR or branch and its lane metadata;
4. one unambiguous work item already selected in the current conversation.

A valid lane-local result is exactly one of:

```text
Lane C
Lane D
Lane R
one named PR or bounded work item belonging to one lane
```

Repository priority, the number of open PRs, and available lane capacity are not lane-binding evidence.

### Ambiguous scope

When exactly one lane cannot be identified:

- do not edit repository files;
- do not create or retarget a PR;
- do not review, comment on, approve, or merge any PR;
- do not select Lane C automatically;
- do not choose a lane because another lane is blocked;
- ask the user to name Lane C, Lane D, Lane R, or a PR.

This is a fail-closed stop condition.

## Cross-lane read-only boundary

A lane-local run may inspect other lanes only to detect:

- changed-path overlap;
- runtime, storage, schema, contract, documentation, record, or import-authority overlap;
- shared callers, workflows, generated registries, or status owners;
- stack and merge-order dependencies;
- a newer `main` change that invalidates selected-lane review or validation.

Without explicit portfolio authorization, other lanes are read-only. Do not:

- edit their branches or files;
- change their PR bodies or metadata;
- post conversation comments, reviews, approvals, or change requests;
- resolve or reopen their review threads;
- merge, close, reopen, retarget, or supersede their PRs;
- create their successor PRs.

When a selected-lane correction belongs to another lane, record the exact dependency and stop or perform another safe action in the selected lane. Do not fix the other lane as a convenience.

## Authoritative reading order

At the beginning of every continuation turn, read or verify:

1. lane-local or explicit portfolio mode;
2. current `main` and open PR state;
3. `AGENTS.md`;
4. `skills/relaylm-stable-implementation/SKILL.md`;
5. `skills/relaylm-github-operations/SKILL.md`;
6. `docs/adr/0008-lane-local-continuation-safety.md`;
7. `docs/PROJECT_STATUS.md` for implemented state and caveats;
8. `docs/architecture/project_execution_plan.md` for repository-wide sequencing;
9. the owning plan for the selected lane or authorized portfolio lanes;
10. exact ADRs, contracts, changed files, review threads, callers, workflows, generated registries, and entry points required by the selected action.

Conversation memory, handoff prompts, PR bodies, retired Git blobs, and historical records are orientation only. They do not override current repository authorities.

In lane-local mode, repository-wide state is inspected only as far as required for conflict, dependency, and stale-base checks.

## Workstream registry

### Lane C: critical implementation

The first authority-changing Lane C program is complete:

```text
LC-1B Forget
  -> LC-1C Pin / Unpin
  -> LC-1D Restore
  -> LC-1E Consolidate
  -> RT-1 Retrieval projection and one-authority hard cutover
```

Lane C is intentionally idle for new personality implementation until the post-RT-1 structural and documentation gates below are complete. Its next separately gated program is:

```text
PC-1 Personality State
  -> PC-2 Working Self
  -> PC-3 SLP automatic personality updates
  -> PC-4 Reflective Distillation
```

Only one authority-changing Lane C PR may be active at a time unless an accepted plan explicitly authorizes a coordinated atomic set. PC-1 may not start before Lane R R5 and Lane D D6, PD-1, and PD-2 are complete.

### Lane D: documentation canonicalization and historical retirement

```text
D1 active graph / retained-record / retirement-manifest lock
  -> D2 stable-domain synthesis
  -> D3 historical-retirement batches
  -> D4 lifecycle canonicalization after LC-1
  -> D5 Retrieval / Primary MEM canonicalization after RT-1
  -> D6 final retirement and legacy cutover-tool retirement
  -> PD-1 personality responsibility convergence after D6 + Lane R R5
  -> PD-2 exact personality contracts
```

Retired documentation is deleted from the current tree and recovered through Git history. `records/` retains only narrowly typed records with a continuing current function.

### Lane R: repository maintenance

```text
R1 responsibility classification
  -> R2 test / smoke / validation consolidation
  -> R3 generated navigation and drift checks
  -> R4 low-risk independent package moves
  -> R5 governed core package migration after RT-1
  -> R6 Primary MEM retirement-or-move cleanup
```

The RT-1 prerequisite for Lane R R5 is now satisfied. R5 is the next governed core migration stage. R6 remains required repository cleanup but is not a blanket prerequisite for Personality Design or Personality Core; a concrete R6 path, caller, import, recovery, or retained-authority dependency blocks only the affected later slice.

Classification may overlap other lanes semantically. Destructive cleanup, path moves, namespace changes, and historical retirement still require their own reviewed atomic PRs.

Detailed stage definitions remain owned by [Repository Structure and Documentation Canonicalization Plan](repository-structure-migration.md).

### Post-RT-1 successor gate

```text
Lane R R5 complete
       +
Lane D D6 complete
       ↓
Lane D PD-1 responsibility convergence
       ↓
Lane D PD-2 exact contracts
       ↓
Lane C PC-1 -> PC-2 -> PC-3 -> PC-4
       ↓
9B end-to-end evaluation
       ↓
Character Presence
```

This ordering keeps package migration, responsibility/contract authority, and authority-changing runtime implementation separate. A free lane slot never authorizes skipping these prerequisites.

## Portfolio capacity

Explicit portfolio mode uses the ceiling:

```text
1 Lane C PR
+ up to 1 Lane D PR
+ up to 1 Lane R PR
```

Three open PRs are a ceiling, not a target. Open fewer when work overlaps, review capacity would be diluted, or an unmerged dependency is likely to invalidate the next PR.

Lane-local mode does not use free capacity to start another lane.

A PR is not opened merely to fill a slot. It requires a bounded scope, identified owner, path and authority safety, implementation strategy, stability-gate result, and validation plan.

## Universal architecture-first P0-P8 lifecycle

Every PR in every lane passes through the following states. Reliable repository evidence may prove an earlier state complete, but no required stage is skipped merely for speed.

```text
P0 scope and authority lock
  -> P1 implementation strategy and design review
  -> P2 architecture stability gate
  -> P3 invariant-first implementation and structural refactor
  -> P4 baseline validation and reviewable PR
  -> P5 thorough complete-PR review
  -> P6 root-cause correction, exact-head validation, and fresh final-review loop
       -> local defect: repeat P6
       -> architecture defect: return to P1
       -> cross-lane defect: record blocker; do not edit other lane
       -> clean: proceed to P7
  -> P7 merge gate and expected-head-protected merge
  -> P8 post-merge convergence inside the selected lane
```

### P0: scope and authority lock

Before substantive changes:

- identify one selected lane and program stage unless explicit portfolio mode was invoked;
- identify exact paths and authorities;
- identify current callers, consumers, entry points, workflows, generated registries, and operator paths;
- identify current state, writer, reader, selector, canonical representation, recovery, and rollback where applicable;
- state behavioral and authority non-goals;
- state compatibility, migration, rollback, retirement, and removal boundaries;
- define the validation matrix;
- establish path and authority safety against other lanes;
- state whether other lanes are read-only or explicitly authorized.

An unclear, expanding, or unauthorized cross-lane scope returns to P0.

### P1: implementation strategy and design review

Do not begin production implementation or destructive cleanup until the strategy is reviewable.

P1 must:

1. investigate current behavior and all relevant invocation roots;
2. define invariants and negative cases before implementation details;
3. compare meaningful implementation alternatives when a real choice exists;
4. map failure points, observable states, retry behavior, conflict classification, forward recovery, migration, and rollback;
5. define temporary compatibility and exact removal gates;
6. map each invariant to unit, integration, process, characterization, negative, exact-head, and post-merge evidence as applicable;
7. confirm one complete atomic authority boundary owned by the selected lane.

Representative invariants:

```text
one semantic authority
one exact current selector where selection exists
one authoritative write path
one canonical representation
fail-closed stale or tampered state
forward-only recovery after durable intent
no unauthorized retrieval or disclosure
no permanent fallback, dual-read, or dual-write
no cross-lane ownership transfer
```

When only one approach preserves accepted authorities, record why alternatives are invalid rather than inventing false options.

### P2: architecture stability gate

Implementation begins only after both gates pass.

#### No-Patch Gate

Reject a strategy that depends on:

- caller-, fixture-, test-, OS-, or environment-specific bypasses that do not express the domain rule;
- a new semantic authority, selector, writer, or canonical representation beside an existing one;
- fallback or precedence that hides disagreement;
- wrapper-only indirection without ownership transfer;
- swallowed errors or retry loops that conceal invalid durable state;
- compatibility without owner, current consumer, removal gate, and replacement validation;
- current and target both treated as canonical;
- weakening tests to match implementation;
- editing generated output instead of source authority;
- permanent milestone-oriented production names;
- known in-scope structural debt deferred to later cleanup;
- a change whose root cause cannot be explained;
- changing another lane to unblock the selected lane without explicit portfolio authorization.

A small root-cause correction is valid. Patch size is not the criterion.

#### Stable-Structure Gate

The chosen design must establish or preserve:

```text
one semantic authority
one owner per responsibility
one current selector where applicable
one authoritative write path
one recovery model
one canonical representation
explicit dependency direction
bounded compatibility with removal gates
function-oriented permanent names
no speculative abstraction without a concrete accepted consumer
one lane owner for the complete atomic change
```

The PR body or owning design record states the P2 result.

### P3: invariant-first implementation and structural refactor

Implement the smallest complete atomic boundary using:

```text
RED
  add failing evidence for the invariant

GREEN
  implement the smallest correct behavior

REFACTOR
  remove duplication, special cases, unstable ownership, unnecessary wrappers,
  wrong dependency direction, and temporary structure while evidence stays green
```

Implementation includes tests, process validation, documentation, records, migrations, link repairs, caller updates, deletions, and negative-reference checks required to make the boundary complete.

For documentation and maintenance PRs, RED means failing generic validation or explicit reviewed criteria; GREEN establishes canonical authority, registry, move, or retirement; REFACTOR removes superseded mechanisms inside the selected lane's scope.

Do not stop at passing tests when the resulting structure remains patch-like.

### P4: baseline validation and reviewable PR

Before thorough review:

- branch and PR match the declared atomic and lane scope;
- obvious syntax, format, compile, schema, link, and focused-test failures are fixed;
- PR body records P0-P2 decisions, alternatives, non-goals, validation, rollback, retirement, removal gates, and cross-lane safety;
- current exact head is recorded;
- temporary construction artifacts are removed or explicitly bounded;
- no uncommitted or hidden work is required to understand the PR.

A draft PR may exist before P4, but implementation is not complete until P4 passes.

### P5: thorough complete-PR review

Perform a fresh adversarial review of the complete resulting PR, not only the latest commit.

Review includes:

- accepted contracts, ADRs, plans, and current status;
- the complete diff and every changed file;
- direct, indirect, dynamic, subprocess, workflow, operator, and documentation callers;
- correctness, authority, state, failure modes, race and crash behavior, security and privacy, migration, rollback, and recovery;
- tests for missing negative cases, false positives, false negatives, and accidental tautologies;
- compatibility surfaces and removal gates;
- duplicate authority, fallback precedence, stale paths, dead wrappers, and scope drift;
- documentation claims against actual behavior;
- deletion or retirement recoverability and replacement coverage;
- whether the final structure still passes P2;
- whether any unauthorized cross-lane action or ownership assumption entered the PR.

Lane emphasis:

```text
Lane C
  runtime semantics, state transitions, schemas, authorization, concurrency,
  crash recovery, idempotency, migration, rollback, and regression

Lane D
  authority, granularity, current-versus-target separation, normative extraction,
  links and routers, retained records, Git recoverability, and omission risk

Lane R
  caller and invocation coverage, behavioral equivalence, process boundaries,
  imports and workflows, characterization removal gates, and negative references
```

P5 ends with explicit findings or an explicit no-finding result. CI success alone is not P5.

### P6: root-cause correction and fresh final-review loop

For every actionable finding:

1. classify it as a local implementation defect, architectural assumption defect, or cross-lane dependency;
2. correct the underlying cause rather than only the symptom;
3. keep corrections inside the selected lane unless portfolio mode explicitly authorizes more;
4. add or strengthen regression evidence when practical;
5. update contracts, docs, PR body, manifests, or records when the selected boundary changed;
6. commit the correction;
7. rerun focused validation and required exact-head CI;
8. perform a fresh final review of the complete exact head.

```text
local implementation defect
  -> correct -> exact-head validation -> fresh final review -> repeat P6 if needed

architectural assumption defect
  duplicate authority or fallback
  repeated special-case growth
  three failed correction attempts
  -> stop patching -> return to P1 -> redesign -> pass P2 again

cross-lane dependency
  -> do not edit the other lane -> record exact blocker -> stop or continue same-lane work

clean exact head
  -> P7
```

A finding remains open until the corrected exact head is inspected.

### P7: merge gate and merge

A PR is merge-ready only when:

- P0-P6 are complete;
- P5 and the latest P6 final review covered the complete PR;
- the final structure still passes the No-Patch and Stable-Structure gates;
- final review found no unresolved issue;
- required exact-head checks succeeded and skips are understood;
- no unresolved review thread or requested change remains;
- base and head are intended and mergeable;
- conflict resolution has been reviewed;
- no later repository change invalidated design or evidence;
- destructive and authority-changing effects remain authorized;
- the merge is inside the selected lane or explicitly authorized portfolio scope.

When P7 passes, merge the selected PR without asking the user to repeat authorization unless the user said `レビューだけ`, `マージしないで`, or equivalent. Use expected-head protection where available.

A lane-local command never authorizes merging another lane's PR.

### P8: post-merge convergence

After merge:

- verify merge result and resulting `main` identity;
- verify required post-merge or main-head validation;
- update shared status, sequencing, generated registries, or bookkeeping only through the selected lane's authorized owner;
- close or supersede replaced PRs and branches in the selected lane factually;
- release the selected lane slot;
- select the next executable action only in the same lane.

A merged PR is not reported complete when required post-merge convergence failed or remains unknown.

## Existing PR adoption

An active PR created under earlier wording adopts this safety boundary at its next executable action.

Reliable evidence may preserve completed P0-P8 work, but before merge the PR must demonstrate:

- one explicit lane binding;
- a reviewable P1 strategy;
- an explicit P2 gate result;
- no patch-like structure in the complete final diff;
- P5 complete-PR review;
- P6 exact-head final review;
- no unauthorized cross-lane mutation;
- P7 merge gate.

Do not rewrite correct implementation merely to relabel stages. Do redesign when current evidence reveals an architectural defect.

## Lane-local action algorithm

### Step 1: converge the selected lane

Determine the selected PR's P0-P8 state and perform its next executable action. Existing clean or correctable work takes priority over a replacement.

### Step 2: select only same-lane work

If no PR exists, choose the earliest incomplete executable item in the selected lane. Do not skip an earlier dependency to begin a later slice.

### Step 3: handle blockers inside the lane

When the selected PR waits for CI, permission, merge sequencing, or another lane:

- inspect additional evidence or perform another safe action in the same lane;
- if no same-lane action exists, report the exact blocker and stop.

Pending CI alone may be a lane-local stop condition.

### Step 4: remain lane-local after merge

P8 selects the next item only in the same lane. The user switches lanes by using that lane's thread or explicitly naming another lane.

## Explicit portfolio algorithm

Only after an explicit portfolio command:

1. determine P0-P8 state for each authorized lane;
2. converge existing authorized PRs before opening replacements;
3. respect one PR slot per lane;
4. advance the earliest executable critical item and additional authorized disjoint work;
5. use blockers to advance another lane only within the explicitly authorized set;
6. assign one owner for every shared file, registry, or authority;
7. merge clean authorized PRs after their independent P7 gates;
8. perform P8 for each merged lane.

Do not create speculative work merely to appear parallel.

## Parallel-safety rules

Two work items are not parallel-safe when either changes:

- the same file or generated registry;
- the same runtime, storage, schema, contract, documentation, or record authority;
- a caller or entry point the other moves or removes;
- shared status or sequencing without one convergence owner;
- an unmerged semantic dependency;
- competing canonical paths, import surfaces, record classes, or precedence rules.

Textual path-disjointness is necessary but not sufficient. Authority and ownership overlap also block parallel execution.

When two lanes require one shared file, assign one owner PR and make the other depend on it. Lane-local mode may record this dependency but may not modify the owner lane.

## Documentation execution rule

Documentation work is selected by canonical target domain, not by the next legacy filename.

Each synthesis and retirement PR identifies target authority and granularity, enumerates sources, extracts live normative content, builds canonical documents, classifies retained records, repairs current links, records retiring blobs and replacements, deletes retired sources, and verifies Git recoverability.

Memory lifecycle canonicalization waits for LC-1. Retrieval and Primary MEM canonicalization waits for RT-1.

## Code, smoke, and tooling execution rule

Each asset is classified as:

```text
active
transitional
retired
```

Active assets have a current supported caller or protected boundary and move toward function-oriented names through their owning migration.

Transitional assets identify owner, protected boundary, current caller, removal gate, and replacement validation.

Retired assets are deleted from the current tree and recovered through Git history. Do not create a general executable archive tree.

## Progress reports

### Lane-local mode

```text
Selected lane
  PR and P0-P8 stage
  action completed
  exact head
  strategy or stability-gate decision when changed
  validation, review, and merge state

Cross-lane safety
  read-only conflicts or dependencies discovered
  confirmation that no other lane was modified

Next
  next same-lane action or exact blocker
```

### Explicit portfolio mode

Report each authorized lane separately, followed by portfolio conflicts, capacity, and the next authorized portfolio action.

Do not present a menu unless lane scope or a genuine policy decision cannot be resolved safely.

## Stop conditions

A lane-local continuation turn stops without changing another lane when:

- lane binding is ambiguous;
- the selected lane is complete;
- every remaining selected-lane item requires a genuine user decision or unavailable authority;
- the selected lane is blocked by another lane or pending evidence and no same-lane action exists;
- repository state cannot be read reliably enough to act safely.

An explicit portfolio turn may additionally stop when no authorized path- and authority-disjoint bounded action exists.

The response names the exact condition. Never promise hidden background work.