---
name: relaylm-stable
description: Advance one explicitly bound RelayLM lane or pull request from bare continuation commands such as 次に進めて, 進めて, 続けて, or 次へ. Cross-lane execution requires an explicit portfolio command. Enforces current-main re-bootstrap, lane-local and single-writer execution, architecture-first design, No-Patch and Stable-Structure gates, machine-owned failure stopping, complete-diff review, exact-head verification, and P0-P8 convergence.
---

# RelayLM Stable

## Purpose

Advance RelayLM work without requiring the user to restate the workflow, while preventing an initial prompt from governing after repository authority changes.

Current repository authority is:

1. `AGENTS.md`;
2. `docs/adr/0007-architecture-first-stable-implementation.md`;
3. `docs/adr/0008-lane-local-continuation-safety.md`;
4. `docs/adr/0009-execution-epoch-and-rebootstrap.md`;
5. `docs/contracts/agent-execution-safety.md`;
6. `docs/planning/workstream-orchestration.md`;
7. the selected lane's current authorities and implementation evidence.

Read these from current `main`. Initial prompts, handoffs, conversation memory, PR bodies, and historical files are orientation only.

## Command scope

These commands are lane-local:

```text
次に進めて
進めて
続けて
次へ
```

Resolve one scope from, in order:

1. an explicit lane, PR, branch, or work item in the current instruction;
2. the lane declared by the thread's initial prompt or handoff;
3. a uniquely identified current PR or branch and its lane metadata;
4. one unambiguous work item already selected in the conversation.

If exactly one lane or bounded PR cannot be resolved, fail closed. Do not edit, create, retarget, review, comment on, approve, merge, or select work.

Cross-lane execution requires explicit wording such as:

```text
全レーンを進めて
ポートフォリオを進めて
Lane C・D・Rを並行で進めて
```

In lane-local mode, other lanes are read-only and may be inspected only for path, authority, caller, registry, status-owner, stack, merge-order, and stale-base conflicts.

## Current-main execution gate

Before any ordinary branch write, review mutation, correction, merge, or PR metadata change:

1. refresh exact current `origin/main`;
2. refresh the selected PR head, checks, reviews, threads, labels, mergeability, changed paths, and workflows;
3. read current execution authorities;
4. read `docs/PROJECT_STATUS.md`, `docs/architecture/project_execution_plan.md`, the selected lane plan, and required ADRs, contracts, code, tests, workflows, registries, and operator entry points;
5. run or reproduce `scripts/relaylm_agent_execution_guard.py`;
6. verify one receipt whose `bootstrap_main_sha` equals exact current `origin/main` and is an ancestor of the PR head;
7. verify one writer, no branch-pushing workflow or transfer PR, no `relaylm:p6-stop`, and no temporary artifact.

## Re-bootstrap

When the receipt is missing or stale, current main is not incorporated, or the governance epoch changed:

```text
STOP WRITES
  -> disable branch-pushing automation
  -> remove temporary execution machinery only
  -> do not add a corrective patch
  -> do not create a validation PR or transfer branch
  -> incorporate exact current main
  -> refresh current authority and evidence
  -> reclassify P0 and P1
  -> pass P2 again
  -> replace or add only the receipt
  -> run the guard
  -> resume only when clean
```

Correct domain evidence may be preserved. Old process state is not grandfathered.

Controlled exceptions while stopped:

- one branch change may only disable branch-writing automation or remove temporary execution machinery;
- after read-only P0/P1/P2 re-bootstrap, one PR-body edit may add or replace only the receipt.

The receipt edit contains no branch write, review disposition, merge, title/base change, or unrelated body change.

### Receipt

```text
<!-- relaylm-execution-receipt
version: 1
lane: C
bootstrap_main_sha: <exact current main 40-hex SHA>
governance_epoch: <64 lowercase hex>
writer_id: <stable lowercase logical identifier>
writer_mode: single
temporary_artifacts: none
-->
```

Allowed lanes are `C`, `D`, `R`, and `governance`.

## Single writer

One PR branch has one logical writer. Test and validation workflows are repository-content read-only.

Never use:

- `contents: write` or `git push` in PR-local construction or validation;
- an auto-correct bot beside the implementation writer;
- a second PR or branch only to apply, validate, or transfer a correction;
- automatic retry, rebase, force-push, or conflict resolution after a head mismatch.

The failure-budget monitor may change only its hidden state comment, execution labels, and Draft state. It never changes branch content or the PR body.

Fetch the exact head immediately before a write. A mismatch stops execution and requires re-bootstrap.

## Machine-owned failure budget

One monitor owns consecutive-failure state in one hidden PR comment and mirrors it with one label:

```text
relaylm:failure-1
relaylm:failure-2
relaylm:p6-stop
```

Signature:

```text
workflow + failed job + first failed step + bounded conclusion category
```

A new head, renamed workflow, moved step, or prose-only edit does not reset a materially identical failure.

The third consecutive identical signature adds `relaylm:p6-stop` and converts the PR to Draft. Architectural assumption error, duplicate authority or writer, branch collision, branch-writing validation, temporary-artifact recurrence, or temporary transfer PR triggers the same stop immediately.

After P6-STOP:

- no branch writes or auto-correct;
- no temporary workflow or transfer PR;
- the label is sticky;
- return to P1 through current-main re-bootstrap;
- clear only after the new receipt and P2 evidence are reviewed.

## P0-P8 lifecycle

```text
P0 scope and authority lock
  -> P1 implementation strategy and design review
  -> P2 architecture stability gate
  -> P3 invariant-first implementation and structural refactor
  -> P4 baseline validation and reviewable PR
  -> P5 thorough complete-PR review
  -> P6 root-cause correction and exact-head final-review loop
       -> local defect: correct within the machine failure budget
       -> architecture defect: P6-STOP and P1 re-bootstrap
       -> third identical failure: P6-STOP
       -> writer collision or temporary recurrence: P6-STOP
       -> cross-lane dependency: record blocker; do not edit other lane
       -> clean: P7
  -> P7 expected-head-protected merge
  -> P8 same-lane post-merge convergence
```

## P0: Scope and authority lock

Identify:

- selected lane and ordered stage;
- owned paths and authorities;
- direct, indirect, dynamic, subprocess, workflow, registry, operator, and documentation invocation roots;
- state, writer, reader, selector, representation, recovery, and rollback;
- non-goals;
- compatibility, migration, retirement, and removal boundaries;
- validation matrix;
- cross-lane conflicts;
- expected exact head, machine failure state, and temporary-artifact inventory.

## P1: Strategy

Before substantive implementation:

- investigate every relevant invocation root;
- define invariants and negative cases;
- compare meaningful alternatives;
- map failure, recovery, migration, and rollback;
- define compatibility owners and removal gates;
- map invariants to validation;
- confirm one complete atomic lane-owned boundary;
- confirm validation cannot mutate branch content.

Typical invariants:

```text
one semantic authority
one owner per responsibility
one selector where applicable
one authoritative write path
one canonical representation
one recovery model
one branch writer
exact current-main bootstrap
fail-closed stale or tampered state
forward-only recovery
no permanent fallback or dual authority
no cross-lane ownership transfer
repository-content read-only validation
```

## P2: Stability gates

Reject:

- caller-, fixture-, test-, platform-, or environment-specific bypasses;
- duplicate authorities, selectors, writers, or representations;
- fallback or precedence hiding disagreement;
- wrapper-only indirection without ownership transfer;
- swallowed errors or masking retries;
- compatibility without owner, consumer, removal gate, and replacement validation;
- current and target both canonical;
- weakened tests or direct generated-output edits;
- permanent milestone production names;
- deferred known in-scope debt;
- unexplained root cause;
- changing another lane as a convenience;
- branch-writing validation or auto-correct;
- temporary validation PRs or transfer branches.

Require one semantic authority, one lane owner, one owner per responsibility, one selector/write path/recovery model/canonical representation where applicable, one branch writer, explicit dependency direction, bounded compatibility, stable names, and repository-content read-only validation.

## P3-P6

Use RED → GREEN → structural REFACTOR. Construction helpers stay outside the repository tree where possible.

Before P5, make the PR complete, atomic, documented, exact-head testable, and free of temporary artifacts.

P5 reviews the complete diff, every file, callers, workflows, registries, authority, state, failure modes, recovery, compatibility, negative cases, documentation claims, deletion recoverability, lane ownership, writer ownership, labels, and receipt.

CI success does not replace review. Correct local defects at the root, validate the exact head, and perform a fresh complete review. A P6-STOP condition ends branch correction.

## Temporary artifact rejection

Reject root hidden patch/apply/fix scripts, probe workflows, branch-mutating structural-refactor workflows, hardening/final-build/build-transfer workflows, auto-correct workflows, self-deleting or self-pushing mechanisms, generated syntax-fix scripts, and temporary validation branches or PRs.

Permanent automation requires accepted authority, stable naming, tests, repository-content read-only operation unless separately governed, ownership, rollback, and removal analysis.

## P7 and P8

Merge only when:

- receipt epoch and bootstrap match exact current main;
- no stop or unresolved failure label exists;
- P0-P6 and fresh complete review are clean;
- exact-head checks pass and review threads are resolved;
- base/head are intended and mergeable;
- no newer change invalidated evidence;
- no temporary artifact or branch-writing workflow exists.

A lane-local command authorizes only the selected lane's merge unless the user says review-only or do not merge.

After merge, verify the merge and resulting `main`, verify post-merge checks, perform same-lane bookkeeping, release the slot, and select only the next item in the same lane.

## Stop conditions

Stop when scope is ambiguous, receipt/main/epoch is stale, re-bootstrap is incomplete, writer collision or branch-writing workflow exists, `relaylm:p6-stop` is present, temporary artifacts recur, the lane is complete, a genuine decision or unavailable authority is required, another lane blocks all safe same-lane work, or repository state cannot be read safely.

Name the exact blocker. Never promise hidden background work.
