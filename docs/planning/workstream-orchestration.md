---
relaylm_doc_type: planning
relaylm_authority: chatgpt_continuation_command_parallel_workstream_and_stable_pr_convergence
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - the shorthand continuation command changes
  - the project critical path or parallel lane registry changes
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
  - ../../AGENTS.md
  - ../../skills/relaylm-stable-implementation/SKILL.md
---
# Workstream Orchestration, Continuation Command, and Stable PR Convergence

Last reviewed: 2026-07-24 JST

## Purpose

This document defines:

1. what ChatGPT or Codex does when the user says `次に進めて`, `進めて`, `続けて`, or `次へ`;
2. how critical and parallel workstreams are selected;
3. the architecture-first P0-P8 lifecycle required for every PR;
4. the No-Patch Gate and Stable-Structure Gate;
5. when correction must return to design instead of adding another local fix.

The shorthand instruction is an execution command, not a request for a menu of recommendations.

Parallel work means advancing independent workstreams in the current project portfolio. It does not mean hidden background execution, delayed delivery, or asynchronous work after the current response.

## Automatic execution entry point

The repository root `AGENTS.md` requires agents to load `skills/relaylm-stable-implementation/SKILL.md` before acting on a bare continuation command.

The following phrases invoke the same default behavior unless the user narrows scope:

```text
次に進めて
進めて
続けて
次へ
```

On receipt, ChatGPT or Codex must:

1. refresh `main`, open PRs, checks, reviews, unresolved threads, exact heads, mergeability, and relevant authorities;
2. read the stable-implementation skill and the current repository authorities;
3. identify each active PR's current P0-P8 state;
4. converge existing PRs before opening overlapping replacements;
5. advance the earliest executable Lane C action;
6. use CI, sequencing, permission, or shared-path blockers as a trigger to advance eligible Lane D or Lane R work;
7. advance at least one parallel lane when meaningful path- and authority-disjoint work exists;
8. avoid asking the user to choose when documented order and repository evidence resolve the choice;
9. merge a clean PR when P7 passes unless the user limited the turn to review-only;
10. complete P8 and report the next automatically selected action.

A scope-specific instruction such as `LC-1だけ進めて`, `ドキュメント整理だけ進めて`, `コード整理を進めて`, or `#672を進めて` limits lane selection for that turn. It does not weaken the universal lifecycle or stability gates.

## Authoritative reading order

At the beginning of every continuation turn, read or verify:

1. current `main` and open PR state;
2. `AGENTS.md`;
3. `skills/relaylm-stable-implementation/SKILL.md`;
4. `docs/PROJECT_STATUS.md` for implemented state and caveats;
5. `docs/architecture/project_execution_plan.md` for repository-wide sequencing;
6. the owning plan for each active lane;
7. exact ADRs, contracts, changed files, review threads, callers, workflows, generated registries, and entry points required by the selected action.

Conversation memory, handoff prompts, PR bodies, retired Git blobs, and historical records are orientation only. They do not override current repository authorities.

## Current portfolio snapshot

The current state must always be refreshed rather than trusted from this snapshot. At this review:

```text
Lane C
  PR #672 LC-1B Subjective MEM Forget                  active

Lane D
  PR #670 D1 documentation-governance lock             active

Lane R
  R1 classification and R2 inventory entrypoint        merged
  PR #673 R3-A classification registry and drift check active
```

Detailed stage definitions remain owned by [Repository Structure and Documentation Canonicalization Plan](repository-structure-migration.md).

## Workstream registry

### Lane C: critical implementation

```text
LC-1B Forget
  -> LC-1C Pin / Unpin
  -> LC-1D Restore
  -> LC-1E Consolidate
  -> RT-1 Retrieval projection and one-authority hard cutover
```

Only one authority-changing LC-1 or RT-1 PR may be active at a time unless an accepted plan explicitly authorizes a coordinated atomic set.

### Lane D: documentation canonicalization and historical retirement

```text
D1 active graph / retained-record / retirement-manifest lock
  -> D2 stable-domain synthesis
  -> D3 historical-retirement batches
  -> D4 lifecycle canonicalization after LC-1
  -> D5 Retrieval / Primary MEM canonicalization after RT-1
  -> D6 final retirement and legacy cutover-tool retirement
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

Classification may overlap other lanes. Destructive cleanup, path moves, namespace changes, and historical retirement still require their own reviewed atomic PRs.

## Default portfolio capacity

```text
1 Lane C PR
+ up to 1 Lane D PR
+ up to 1 Lane R PR
```

Three open PRs are a ceiling, not a target. Open fewer when work overlaps, review capacity would be diluted, or an unmerged dependency is likely to invalidate the next PR.

A PR is not opened merely to fill a lane. It requires a bounded scope, identified owner, path and authority non-overlap, implementation strategy, stability-gate result, and validation plan.

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
       -> clean: proceed to P7
  -> P7 merge gate and expected-head-protected merge
  -> P8 post-merge convergence
```

### P0: scope and authority lock

Before substantive changes:

- identify lane and program stage;
- identify exact paths and authorities;
- identify current callers, consumers, entry points, workflows, generated registries, and operator paths;
- identify current state, writer, reader, selector, canonical representation, recovery, and rollback where applicable;
- state behavioral and authority non-goals;
- state compatibility, migration, rollback, retirement, and removal boundaries;
- define the validation matrix;
- establish path and authority parallel-safety.

An unclear or expanding scope returns to P0.

### P1: implementation strategy and design review

Do not begin production implementation or destructive cleanup until the strategy is reviewable.

P1 must:

1. investigate current behavior and all relevant invocation roots;
2. define invariants and negative cases before implementation details;
3. compare meaningful implementation alternatives when a real choice exists;
4. map failure points, observable states, retry behavior, conflict classification, forward recovery, migration, and rollback;
5. define temporary compatibility and exact removal gates;
6. map each invariant to unit, integration, process, characterization, negative, exact-head, and post-merge evidence as applicable;
7. confirm that the PR is one complete atomic authority boundary.

Representative RelayLM invariants:

```text
one semantic authority
one exact current selector where selection exists
one authoritative write path
one canonical representation
fail-closed stale or tampered state
forward-only recovery after durable intent
no unauthorized retrieval or disclosure
no permanent fallback, dual-read, or dual-write
```

When only one approach preserves accepted authorities, record why alternatives are invalid rather than inventing false options.

### P2: architecture stability gate

Implementation begins only after both gates pass.

#### No-Patch Gate

Reject an implementation strategy that depends on:

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
- a change whose root cause cannot be explained.

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
```

The PR body or owning design record states the P2 result.

### P3: invariant-first implementation and structural refactor

Implement the smallest complete atomic boundary using the preferred cycle:

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

For documentation and maintenance PRs, RED means failing generic validation or explicit reviewed criteria; GREEN establishes the canonical authority, registry, move, or retirement; REFACTOR removes superseded mechanisms within scope.

Do not stop at passing tests when the resulting structure remains patch-like.

### P4: baseline validation and reviewable PR

Before thorough review:

- branch and PR match the declared atomic scope;
- obvious syntax, format, compile, schema, link, and focused-test failures are fixed;
- PR body records P0-P2 decisions, alternatives, non-goals, validation, rollback, retirement, removal gates, and parallel-safety;
- current exact head is recorded;
- temporary construction artifacts are removed or explicitly bounded;
- no uncommitted or hidden work is required to understand the PR.

A draft PR may exist before P4, but implementation is not complete until P4 passes.

### P5: thorough complete-PR review

Perform a fresh adversarial review of the complete resulting PR, not only the latest commit.

Review includes, where relevant:

- accepted contracts, ADRs, plans, and current status;
- the complete diff and every changed file;
- direct, indirect, dynamic, subprocess, workflow, operator, and documentation callers;
- correctness, authority, state, failure modes, race and crash behavior, security and privacy, migration, rollback, and recovery;
- tests for missing negative cases, false positives, false negatives, and accidental tautologies;
- compatibility surfaces and removal gates;
- duplicate authority, fallback precedence, stale paths, dead wrappers, and scope drift;
- documentation claims against actual behavior;
- deletion or retirement recoverability and replacement coverage;
- whether the final structure still passes P2 rather than merely passing tests.

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

1. classify it as a local implementation defect or an architectural assumption defect;
2. correct the underlying cause rather than only the symptom;
3. add or strengthen regression evidence when practical;
4. update contracts, docs, PR body, manifests, or records when the boundary changed;
5. commit the correction;
6. rerun focused validation and required exact-head CI;
7. perform a fresh final review of the complete exact head.

Loop rule:

```text
local implementation defect
  -> correct -> exact-head validation -> fresh final review -> repeat P6 if needed

architectural assumption defect
  duplicate authority or fallback
  repeated special-case growth
  three failed correction attempts
  -> stop patching -> return to P1 -> redesign -> pass P2 again

clean exact head
  -> P7
```

There is no fixed iteration limit for valid correction. A finding remains open until the corrected exact head is inspected.

### P7: merge gate and merge

A PR is merge-ready only when:

- P0 through P6 are complete;
- P5 and the latest P6 final review covered the complete PR;
- the final structure still passes the No-Patch and Stable-Structure gates;
- final review found no unresolved issue;
- required exact-head checks succeeded and skips are understood;
- no unresolved review thread or requested change remains;
- base and head are intended and mergeable;
- conflict resolution has been reviewed;
- no later repository change invalidated design or evidence;
- destructive and authority-changing effects remain authorized.

When P7 passes and continuation authorization applies, merge without asking the user to repeat a choice already resolved by this plan. Use the repository's accepted merge method and expected-head protection where available.

`レビューだけ`, `マージしないで`, or an equivalent restriction disables automatic merge for that turn.

### P8: post-merge convergence

After merge:

- verify merge result and resulting `main` identity;
- verify required post-merge or main-head validation;
- update shared status, sequencing, generated registries, or bookkeeping only through the owning convergence action;
- close or supersede replaced PRs and branches factually;
- release the lane slot;
- refresh the portfolio and select the next executable action.

A merged PR is not reported complete when required post-merge convergence failed or remains unknown.

## Existing PR adoption rule

An active PR created under the earlier lifecycle adopts this lifecycle at its next executable boundary.

Reliable evidence may preserve completed work, but the PR must still demonstrate before merge:

- a reviewable P1 strategy;
- an explicit P2 gate result;
- no patch-like structure in the complete final diff;
- P5 complete-PR review;
- P6 exact-head final review;
- P7 merge gate.

Do not rewrite correct implementation merely to relabel stages. Do redesign when current evidence reveals an architectural defect.

## Continuation behavior inside a PR

A bare continuation command advances an existing PR toward P8 before opening another PR in the same lane.

```text
no PR exists
  -> P0 -> P1 -> P2 -> P3 -> P4 reviewable PR

PR lacks strategy or stability evidence
  -> complete P1 and P2 before more substantive implementation

PR awaits thorough review
  -> P5

local review findings exist
  -> P6 correction and final-review loop

architecture finding exists
  -> return to P1 and redesign

PR is clean but CI is pending
  -> verify CI and advance a parallel-safe lane

PR passes P7
  -> merge -> P8 convergence
```

Do not call a PR complete while deferring a known correction or structural problem to a later PR. Do not start the next item in the same lane while the current PR can still be converged.

## Portfolio action-selection algorithm

### Step 1: converge existing work

Determine the P0-P8 state of every active PR and perform the next executable convergence action. Existing clean or correctable PRs take priority over replacements.

### Step 2: advance Lane C

Choose the earliest incomplete executable Lane C item. Advance its current PR through the lifecycle or create a bounded P0-P4 PR when no owner exists.

Do not skip an earlier lifecycle dependency to begin a later lifecycle or Retrieval slice.

### Step 3: use blockers to trigger parallel work

When Lane C is temporarily blocked by pending CI, permission, merge sequencing, or a shared-path dependency, select the highest-priority executable Lane D or Lane R action that is path- and authority-disjoint.

Pending CI alone is not a stop condition while another safe bounded action exists.

### Step 4: fill remaining safe capacity

After Lane C, advance one additional eligible parallel lane when:

- it shares no path, authority, caller, or generated registry;
- it will not be invalidated by a pending merge;
- its PR remains atomic and reviewable;
- it does not create a second runtime, storage, documentation, record, or import authority;
- its strategy and stability gates can be reviewed independently;
- the current interaction can complete a meaningful bounded action.

Do not create speculative work only to appear parallel.

### Step 5: update shared authorities at convergence points

Implementation PRs update code, tests, contracts that must ship atomically, and slice-owned validation. Shared status and sequencing documents are updated only by their owning convergence or planning PR.

`docs/PROJECT_STATUS.md` changes only after exact-head evidence proves implemented state.

## Parallel-safety rules

Two work items are not parallel-safe when either changes:

- the same file or generated registry;
- the same runtime, storage, schema, contract, documentation, or record authority;
- a caller or entry point the other moves or removes;
- shared status or sequencing without one convergence owner;
- an unmerged semantic dependency;
- competing canonical paths, import surfaces, record classes, or precedence rules.

Textual path-disjointness is necessary but not sufficient. Authority overlap also blocks parallel execution.

When two lanes require one shared file, assign one owner PR and make the other depend on it.

## Documentation execution rule

Documentation work is selected by canonical target domain, not by the next legacy filename.

Each synthesis and retirement PR must identify target authority and granularity, enumerate sources, extract live normative content, build canonical documents, classify retained records, repair current links, record retiring blobs and replacements, delete retired sources, and verify Git recoverability.

Memory lifecycle canonicalization waits for LC-1. Retrieval and Primary MEM canonicalization waits for RT-1.

## Code, smoke, and tooling execution rule

Each asset is classified as:

```text
active
transitional
retired
```

Active assets have a current supported caller or protected boundary and move toward function-oriented names through their owning migration.

Transitional assets must identify owner, protected boundary, current caller, removal gate, and replacement validation.

Retired assets are deleted from the current tree and recovered through Git history. Do not create a general executable archive tree.

## Progress report contract

Every continuation response reports:

```text
Critical lane
  PR and P0-P8 stage
  action completed
  exact head
  strategy or stability-gate decision when changed
  validation, review, and merge state

Parallel lanes
  PR and P0-P8 stage where applicable
  action completed or exact reason no safe action existed

Portfolio state
  active PR count
  path or authority conflicts
  next automatically selected action
```

Do not present a menu unless a genuine unresolved policy decision requires the user rather than repository evidence.

## Stop conditions

A continuation turn may stop without opening or changing work only when:

- all registered lanes are complete;
- every remaining item requires a genuine user decision or unavailable external authority;
- no path- and authority-disjoint bounded action exists;
- repository state cannot be read reliably enough to act safely.

The response must name the exact condition. Pending CI alone is not a stop condition while another eligible lane exists.
