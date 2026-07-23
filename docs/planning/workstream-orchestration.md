---
relaylm_doc_type: planning
relaylm_authority: chatgpt_continuation_command_parallel_workstream_and_pr_convergence
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - the shorthand continuation command changes
  - the project critical path or parallel lane registry changes
  - the universal PR convergence lifecycle changes
  - PR concurrency or conflict rules change
  - the authoritative status or sequencing source moves
  - the historical-retirement or retained-record policy changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, contract, or API behavior
  - authorization to merge a PR that has not passed its required review and validation
  - background or asynchronous execution
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/project_execution_plan.md
  - repository-structure-migration.md
  - ../DOCUMENTATION_MODEL.md
  - ../adr/0006-repository-structure-and-maintenance-sequencing.md
---
# Workstream Orchestration, Continuation Command, and PR Convergence

## Purpose and authority

This document defines how ChatGPT selects and advances RelayLM work when the user gives a shorthand continuation instruction such as `次に進めて`, `進めて`, or `続けて`.

It also defines one universal pull-request lifecycle for every workstream. Lane C implementation, Lane D documentation, and Lane R repository maintenance use the same convergence sequence:

```text
normal implementation
  -> baseline validation and reviewable PR
  -> thorough review
  -> correction and exact-head validation
  -> final review
  -> repeat correction / validation / final review until clean
  -> merge gate
  -> merge
  -> post-merge convergence
```

The shorthand instruction is an execution command, not a request for a recommendation. ChatGPT must inspect the current repository state, advance the highest-priority executable work, and also advance eligible path- and authority-disjoint parallel work when doing so does not weaken atomicity or reviewability.

Parallel work means maintaining and advancing multiple independent workstreams within the same project portfolio. It does not mean hidden background execution, delayed delivery, or asynchronous work after the current response.

## Authoritative reading order

At the start of every continuation turn, read or verify:

1. current repository `main` and open pull requests;
2. `docs/PROJECT_STATUS.md` for implemented state and active caveats;
3. `docs/architecture/project_execution_plan.md` for project-wide ordering;
4. the owning planning document for each active workstream;
5. exact contracts, ADRs, changed files, checks, review threads, callers, and entry points required by the selected atomic action.

Conversation memory, handoff prompts, PR bodies, retired files recovered from Git, and historical records are useful orientation but do not override current repository authorities.

## Meaning of continuation commands

The following instructions invoke the same default orchestration behavior unless the user narrows the scope:

```text
次に進めて
進めて
続けて
次へ
```

On receipt, ChatGPT must:

1. refresh repository and PR state rather than rely only on the previous turn;
2. identify each active PR's current convergence stage;
3. converge existing PRs before opening overlapping replacements;
4. advance the earliest executable critical-path item;
5. use CI, sequencing, or owner-only blockers as a trigger to advance eligible parallel work;
6. advance at least one parallel lane when meaningful safe work exists;
7. avoid asking the user to choose between candidates when documented priority resolves the choice;
8. report the resulting critical, parallel, and portfolio state with the next automatically selected action.

A scope-specific instruction such as `LC-1だけ進めて`, `ドキュメント整理を進めて`, or `#668を進めて` limits lane selection for that turn but does not weaken the universal PR convergence lifecycle.

## Workstream registry

### Lane C: critical implementation path

```text
Cutover 1C-57 convergence where still open
  -> LC-1A convergence where still open
  -> LC-1B Forget
  -> LC-1C Pin / Unpin
  -> LC-1D Restore
  -> LC-1E Consolidate
  -> RT-1 Retrieval projection and one-authority hard cutover
```

Only one authority-changing LC-1 or RT-1 implementation PR may be active at a time unless the project execution plan explicitly authorizes a coordinated atomic set.

### Lane D: documentation canonicalization and historical retirement

```text
D0 finish the last already-open legacy cutover slice
  -> D1 canonical active graph, retained-record allowlist, and retirement-manifest lock
  -> D2 stable-domain synthesis waves
  -> D3 completed evidence and source-document bulk historical retirement
  -> D4 lifecycle and mutation canonicalization after LC-1
  -> D5 Retrieval and Primary MEM canonicalization after RT-1
  -> D6 final historical retirement and legacy cutover-tool retirement
```

Retired documents are deleted from the current tree and recovered through Git history. `records/` retains only narrowly typed records with a continuing release, migration, audit, recovery, rollback, or repository-governance role. It is not a free-form archive.

### Lane R: repository maintenance and structure

```text
R1 script, workflow, code, and validation responsibility classification
  -> R2 bounded smoke, test, and validation consolidation
  -> R3 generated active-document and retained-record navigation
  -> R4 low-risk independent package moves
  -> R5 governed core package migration after RT-1
  -> R6 Primary MEM retirement-or-move cleanup
```

R1 and candidate analysis may overlap other lanes. Destructive cleanup, path moves, namespace changes, and historical retirement require separately reviewed atomic PRs.

## Default portfolio capacity

```text
1 critical-path PR
+ up to 1 documentation-canonicalization PR
+ up to 1 repository-maintenance PR
```

Three open PRs are a ceiling, not a target. Open fewer when work overlaps, review capacity would be diluted, or a pending convergence is likely to invalidate the next slice.

A new PR must not be opened merely to fill a lane. It requires a complete bounded scope, an identified owner, path and authority non-overlap, and a validation plan.

## Universal PR convergence lifecycle

Every PR in every lane passes through the following states. A PR may enter at a later state only when reliable repository evidence proves the earlier state complete.

### P0: scope and authority lock

Before substantive changes:

- identify the owning lane and program stage;
- identify exact paths and authorities;
- identify current callers, consumers, entry points, and generated registries;
- state behavioral and authority non-goals;
- state compatibility, migration, rollback, and removal boundaries;
- define the validation matrix;
- establish path and authority parallel-safety.

An unclear or expanding scope returns to P0 before implementation continues.

### P1: normal implementation

Implement the smallest complete atomic boundary under ordinary engineering discipline.

The implementation must include the tests, process validation, documentation, records, migrations, and negative-reference updates required to make the boundary reviewable. It must not defer known in-scope correctness work merely to open a PR earlier.

For documentation or cleanup PRs, `implementation` includes synthesis, link repair, manifest updates, caller updates, deletions, and validation tooling required by the accepted scope.

### P2: baseline validation and reviewable PR

Before thorough review:

- the branch and PR represent the declared atomic scope;
- obvious formatting, syntax, compile, schema, link, and focused test failures are corrected;
- the PR body records scope, non-goals, validation, rollback, and parallel-safety;
- the current head SHA is recorded;
- the PR is reviewable without relying on uncommitted or hidden work.

A draft PR may exist before P2, but it is not considered implementation-complete until P2 passes.

### P3: thorough review

Perform a fresh, adversarial review of the complete PR, not only the latest patch.

The review must inspect:

- accepted contracts, ADRs, planning, and current status boundaries;
- the full diff and all changed files;
- direct, indirect, dynamic, subprocess, workflow, operator, and documentation callers where relevant;
- correctness, failure modes, race or crash behavior, security and privacy boundaries, migration and rollback behavior where relevant;
- tests and validation for false positives, false negatives, missing negative cases, and accidental tautologies;
- compatibility surfaces and their removal gates;
- authority duplication, fallback precedence, stale paths, dead wrappers, and scope drift;
- documentation claims against implemented behavior;
- deletion or retirement recoverability and replacement coverage.

Lane-specific emphasis:

```text
Lane C
  runtime semantics, state transitions, schemas, authorization, concurrency,
  crash recovery, idempotency, migration, rollback, and behavioral regression

Lane D
  authority and granularity, current-versus-target distinction, normative extraction,
  links and routers, retained-record allowlist, Git recoverability, and omission risk

Lane R
  caller and invocation coverage, behavioral equivalence, process boundaries,
  import and workflow surfaces, characterization removal gates, and negative references
```

The thorough review produces explicit findings or an explicit no-finding result. CI success alone is not a thorough review.

### P4: correction and exact-head validation

For every actionable finding:

1. correct the underlying issue rather than only the reported symptom;
2. add or strengthen regression coverage when practical;
3. update contracts, docs, PR body, manifests, or records when the correction changes the reviewed boundary;
4. commit the correction;
5. rerun the affected focused validation and required exact-head CI;
6. verify that the correction did not expand scope or create a new authority conflict.

All review findings remain open until the corrected exact head is inspected. A verbal response or passing pre-correction run does not resolve a finding.

### P5: final review loop

Perform a fresh final review against the latest exact head after corrections.

The final review checks:

- every prior finding is factually resolved;
- the full resulting diff remains within the accepted scope;
- no new issue was introduced by corrections;
- required focused and broad validation is complete on the exact head;
- review threads are resolved or factually dispositioned;
- the PR body and evidence describe the actual final state;
- the PR is mergeable against the intended base;
- shared status and sequencing changes are owned by the correct convergence PR.

If any issue is found, return to P4:

```text
P4 correction and exact-head validation
  -> P5 final review
  -> finding exists? yes -> P4
  -> finding exists? no  -> P6
```

There is no fixed maximum number of loops. The loop ends only when the exact head has no unresolved correctness, scope, validation, authority, or mergeability issue.

### P6: merge gate

A PR is merge-ready only when all applicable conditions are true:

- P0 through P5 are complete;
- thorough review and final review were performed on the complete PR;
- the final review found no unresolved issue;
- required exact-head checks are successful, with skips understood and acceptable;
- no unresolved review thread or requested change remains;
- base and head are the intended commits;
- the PR is mergeable and has no unreviewed conflict resolution;
- no later repository change invalidated the review;
- destructive or authority-changing effects remain within the accepted authorization.

Do not merge a failing, unresolved, conflicting, stale, or semantically unreviewed PR merely because it is next in sequence.

### P7: merge

When the merge gate passes and the user's continuation authorization applies, merge without asking the user to repeat a choice already resolved by this plan.

Use the repository's accepted merge method and an expected-head guard where available. Do not silently merge a moved head.

A user instruction that explicitly says `レビューだけ`, `マージしないで`, or otherwise limits the action overrides automatic merge for that turn.

### P8: post-merge convergence

After merge:

- verify the merge result and resulting `main` identity;
- verify required post-merge or main-head validation when applicable;
- update shared status, sequencing, generated registries, or bookkeeping only through their owning convergence action;
- close or supersede replaced PRs and branches with a factual disposition where appropriate;
- release the lane slot;
- select the next executable portfolio action.

A merged PR is not reported as complete if required post-merge convergence has failed or remains factually unknown.

## Continuation behavior within a PR

A bare continuation command advances an existing PR from its current state toward P8 before opening another PR in the same lane.

Default interpretation:

```text
no PR exists
  -> P0 scope -> P1 implementation -> P2 reviewable PR

PR awaits thorough review
  -> P3 thorough review

review findings exist
  -> P4 correction and validation -> P5 final review loop

PR is clean but checks are pending
  -> verify checks; advance a parallel-safe lane while pending

PR passes merge gate
  -> P7 merge -> P8 post-merge convergence
```

Do not label a PR `final review complete` and then defer known corrections to a later PR. Do not start the next item in the same lane while the current PR can still be converged.

## Portfolio action-selection algorithm

### Step 1: converge existing work first

For each active PR, determine its P0-P8 state and perform the next executable convergence action. Existing clean or correctable PRs have priority over opening replacements.

### Step 2: advance the critical path

Choose the earliest incomplete executable Lane C item. Advance its active PR through the universal lifecycle or create its bounded P0-P2 implementation PR when no owner PR exists.

Do not skip an earlier critical dependency to begin a later lifecycle or Retrieval slice.

### Step 3: use blockers as a parallel-work trigger

When the critical action is temporarily non-executable because of pending CI, owner-only validation, merge sequencing, or a shared-path dependency, select the highest-priority executable Lane D or Lane R action that is path- and authority-disjoint.

Pending CI is not a stop condition while another safe bounded action exists.

### Step 4: fill remaining safe capacity

After the critical action, advance one additional eligible parallel lane when:

- it does not touch the same paths or authority references;
- it will not be invalidated by the pending critical merge;
- its PR lifecycle remains atomic and understandable;
- it does not create a second runtime, storage, documentation, record, or import authority;
- the current interaction can complete a meaningful bounded action.

Do not create speculative work whose only purpose is to appear parallel.

### Step 5: update shared authorities only at convergence points

Implementation slice PRs update their own code, tests, contracts that must ship atomically, and slice-owned validation. Shared status and sequencing documents are updated only by the owning convergence or planning PR.

`docs/PROJECT_STATUS.md` changes only after exact-head evidence proves implemented state. Planning registration alone never changes completion state.

## Conflict rules

Two work items are not parallel-safe when either one:

- changes the same file or generated registry;
- changes the same runtime, storage, schema, contract, documentation, or record authority;
- changes a caller or entry point that the other item moves or removes;
- changes a shared status or sequencing document without an explicit convergence owner;
- depends on the other's unmerged path or semantic result;
- would create competing canonical paths, import surfaces, record classes, or precedence rules.

Textual path-disjointness is necessary but not sufficient. Authority overlap also blocks parallel execution.

When two lanes need one shared file, choose one owner PR and make the other depend on it. Do not let both independently edit and later reconcile an avoidable conflict.

## Documentation-specific execution

Documentation work is selected by canonical target domain, not by the next legacy source filename.

Each synthesis and retirement PR must:

1. identify final active authority and granularity;
2. enumerate source documents and code or contract anchors;
3. extract current durable architecture and exact normative content;
4. build or revise canonical active documents;
5. distinguish current implementation from accepted target;
6. classify still-current records against the retained-record allowlist;
7. record retiring path, last-live commit, blob identity, replacement, and disposition;
8. repair current links, routers, and generated navigation;
9. delete consumed historical sources from the current tree;
10. verify Git recoverability and update one generated retirement manifest.

Memory lifecycle canonicalization waits for LC-1. Retrieval and Primary MEM canonicalization waits for RT-1.

## Code-, smoke-, and tooling-specific execution

Every asset is classified as:

```text
active
transitional
retired
```

Active assets have a current supported caller or protected boundary and move toward function-oriented names through their owning migration.

Transitional assets include characterization, compatibility, rollback, and migration validation. Each must identify:

```text
owner
protected boundary
current caller
removal gate
replacement validation
```

Retired assets have no supported runtime, operator, migration, rollback, characterization, or repository-governance responsibility. They are deleted from the current tree and recovered through Git history.

Preferred execution order:

1. remove proven wrapper or duplicate-entry-point pairs;
2. move pure regression into maintained test suites;
3. retain process validation for crash, restart, subprocess, security, concurrency, filesystem, platform, CLI, and operator boundaries;
4. place migration characterization in a maintained location with an explicit removal gate;
5. consolidate repository validators and generated registries;
6. generate mechanical active-document and retained-record indexes;
7. perform low-risk package moves with complete caller evidence;
8. perform governed core package migration after RT-1.

Do not create a general executable `frozen/`, `archive/`, or `legacy/` Python tree. An exceptional reproduction snapshot may remain only as a non-executable typed record outside imports and test discovery, with source commit and digest.

## Progress report contract

At the end of each continuation turn, report:

```text
Critical lane
  PR and current P0-P8 stage
  action completed
  exact head
  validation, review, and merge state

Parallel lanes
  PR and current P0-P8 stage where applicable
  action completed or exact reason no safe action was available

Portfolio state
  active PR count
  conflicts or blockers
  next automatically selected action
```

Do not present a menu of next steps unless the plan contains a genuine unresolved policy decision that repository evidence cannot resolve.

## Stop conditions

A continuation turn may stop without opening or changing work only when:

- all registered lanes are complete;
- every remaining item is blocked by a genuine user decision or unavailable external authority;
- no path- and authority-disjoint bounded action exists;
- repository state cannot be read reliably enough to act safely.

The response must state the exact condition. Pending CI alone is not a stop condition while another eligible lane exists.

## Current continuation intent

Until superseded, a bare `次に進めて` means:

```text
converge each active PR through P0-P8
  -> advance the earliest executable LC-1 / RT-1 critical item
  -> advance canonical documentation and historical retirement for a stable domain
  -> advance one bounded repository-maintenance family when safe
```

The detailed item order remains governed by the Project Execution Plan and each owning planning document.
