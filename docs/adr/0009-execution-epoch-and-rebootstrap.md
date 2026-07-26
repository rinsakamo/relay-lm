---
relaylm_doc_type: adr
relaylm_authority: agent_execution_epoch_rebootstrap_and_single_writer_safety
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-24
relaylm_volatility: low
relaylm_owner: implementation
relaylm_update_trigger:
  - this decision is superseded
  - execution-governance authority changes
  - the PR execution receipt or writer model changes
  - failure-signature or P6-stop semantics change
  - branch-writing automation policy changes
relaylm_not_authoritative_for:
  - current implementation completion
  - exact runtime, storage, schema, contract, or API behavior
  - authorization to merge a PR that has not passed required review and validation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - 0007-architecture-first-stable-implementation.md
  - 0008-lane-local-continuation-safety.md
  - ../contracts/agent-execution-safety.md
  - ../planning/workstream-orchestration.md
  - ../../AGENTS.md
  - ../../skills/relaylm-stable-implementation/SKILL.md
  - ../../skills/relaylm-github-operations/SKILL.md
relaylm_supersedes: []
relaylm_superseded_by: null
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - AI coding agents
  - repository reviewers
  - pull-request validation workflows
relaylm_authority_level: exact_contract
---
# ADR 0009: Execution epoch, mandatory re-bootstrap, and single-writer safety

## Decision summary

RelayLM introduces a deterministic execution-governance epoch. An active PR must carry a current execution receipt before ordinary repository work continues.

Initial thread prompts and handoffs are bootstrap orientation. They cannot grandfather an old loop after `AGENTS.md`, the RelayLM Skills, execution ADRs, the safety contract, or orchestration authority changes.

A stale or missing receipt stops branch writes and returns the lane to P0/P1/P2. New rules are not partially overlaid on an old P6 loop.

RelayLM also adopts:

- one logical writer per active PR branch;
- repository-content read-only test and validation workflows;
- no temporary validation PR or transfer branch;
- no automatic retry after a head collision;
- machine-owned consecutive-failure state;
- automatic `P6-STOP` at the third materially identical failure;
- rejection of patch, probe, transfer, and self-pushing execution artifacts.

## Context

Lane C, Lane D, and Lane R began from thread-specific prompts before the stable-implementation Skill and later execution ADRs existed.

The D1 episode demonstrated that adding governance prose to `main` did not reliably change an already-running loop. The branch repeatedly modified documentation while an external `--check-model` consumer remained the real blocker. The same failure continued across many heads. Auto-correct and implementation writers competed, temporary patch files and probe workflows entered the diff, and Actions were repeatedly consumed.

Lane C independently contained a branch-writing structural-refactor workflow. The failure mode was therefore systemic rather than Lane D-specific.

The architecture-first and three-failure rules were valid intent, but model compliance alone did not enforce them.

## Decisions

### 1. Current repository governance overrides bootstrap prompts

Current `main` execution authorities override:

- thread initial prompts and uploaded handoffs;
- conversation memory and previous plans;
- PR descriptions and historical receipts.

Older sources remain useful only for lane identity and task orientation.

### 2. Execution governance has a deterministic epoch

The epoch is a SHA-256 digest over ordered Git blob identities for:

```text
AGENTS.md
skills/relaylm-stable-implementation/SKILL.md
skills/relaylm-github-operations/SKILL.md
docs/adr/0007-architecture-first-stable-implementation.md
docs/adr/0008-lane-local-continuation-safety.md
docs/adr/0009-execution-epoch-and-rebootstrap.md
docs/contracts/agent-execution-safety.md
docs/planning/workstream-orchestration.md
```

The exact algorithm is owned by `scripts/relaylm_agent_execution_guard.py`. It uses no wall clock or mutable external state.

### 3. Every active PR has one execution receipt

Before ordinary writes, the PR body records:

- receipt version;
- lane;
- bootstrap `main` SHA;
- current governance epoch;
- one logical writer ID;
- `single` writer mode;
- absence of temporary artifacts.

The bootstrap SHA must be an ancestor of the PR head. Missing, malformed, duplicate, or stale receipts fail closed.

Failure counts do not live in this receipt. They are machine-owned PR state so an agent cannot forget or reset them by editing its own process declaration.

### 4. Governance drift requires complete re-bootstrap

When the epoch changes:

1. stop branch writers;
2. disable branch-pushing automation;
3. refresh current `main`, PR head, checks, reviews, callers, workflows, registries, and authorities;
4. reclassify P0 and P1;
5. preserve only evidence still valid under current authority;
6. pass P2 again;
7. write one fresh receipt;
8. run the guard;
9. resume only when clean.

Controlled containment may remove branch-writing automation or temporary execution artifacts. After read-only P0/P1/P2 re-bootstrap, one PR-body edit may add or replace only the receipt. Neither exception authorizes implementation progress.

### 5. One branch has one logical writer

An active PR branch has one writer identity.

Test and validation workflows use `contents: read`. They may test and upload diagnostics, but may not commit, push, transform, or transfer implementation state.

Prohibited:

- implementation agent plus auto-correct writer;
- `git push` from a PR-local workflow;
- self-editing or self-deleting transform workflows;
- a second PR or branch used only to apply or validate a correction;
- automatic retry, rebase, or force-push after non-fast-forward rejection.

A changed head immediately before a write is a stop condition.

### 6. Failure state is machine-owned

One failure-budget workflow consumes completed PR workflow runs and maintains one hidden state comment. It mirrors the highest active state with one label:

```text
relaylm:failure-1
relaylm:failure-2
relaylm:p6-stop
```

A signature is:

```text
workflow + failed job + first failed step + bounded conclusion category
```

The monitor preserves materially identical signatures across heads and workflow renames. A successful run of the owning workflow clears its non-stop consecutive state. `relaylm:p6-stop` is sticky and is not cleared by a later green run.

### 7. P6-STOP is a mechanical state transition

The third consecutive identical signature adds `relaylm:p6-stop` and converts the PR to Draft.

The same stop is required immediately for:

- architectural assumption error;
- duplicate semantic authority or writer;
- branch-write collision;
- branch-writing validation;
- temporary-artifact recurrence;
- temporary validation PR or transfer branch.

While stopped:

- no branch writes or auto-correct;
- no temporary workflow or transfer PR;
- merge is prohibited;
- return to P1 through current-epoch re-bootstrap;
- clear the label only after the new receipt and P2 evidence are reviewed.

### 8. Temporary execution artifacts are rejected

The final diff must not contain:

- root-level hidden Python patch/apply/fix scripts;
- probe workflows;
- branch-mutating structural-refactor workflows;
- hardening/final-build/build-transfer workflows;
- generated syntax-fix scripts;
- other self-deleting or self-pushing construction mechanisms.

Construction helpers run outside the repository tree when possible. Permanent automation requires accepted authority, stable responsibility naming, tests, repository-content read-only behavior unless separately governed, and rollback/removal analysis.

### 9. Existing PR adoption is not partial

A PR created under an older epoch must re-bootstrap before its next ordinary write, review mutation, or merge.

Correct domain code and evidence may remain. Process state is re-established from current authority. This narrows the earlier “adopt at the next executable action” wording.

## Activation sequence

Because this ADR and its contract are new epoch inputs, their introduction PR cannot be validated by a workflow that expects them on the base ref.

Activation is therefore atomic in two ordered PRs:

1. merge the authority, Skill, and guard implementation;
2. add the static execution-safety workflow and failure-budget monitor against the now-current epoch.

The second PR may write PR labels, one hidden state comment, and Draft state. It never writes branch content or the PR body.

## Consequences

- Existing lane threads can still use `次に進めて`, after current-epoch re-bootstrap.
- Open pre-ADR PRs remain Draft and merge-prohibited until refreshed.
- Self-pushing Actions are no longer implementation agents.
- Execution-governance changes intentionally pause all active lanes.
- Repeated identical failures become durable PR state rather than agent memory.
- Some implementation evidence is reused, but old loop state is discarded.

## Rejected alternatives

### Tell each thread to reread the Skill

Rejected because there is no stale-state proof and the D1 episode showed compliance can fail.

### Keep a manual failure count in the receipt

Rejected because the same agent that failed to stop could omit or reset the count.

### Allow self-pushing workflows that delete themselves

Rejected because they create a second writer and cleanup can fail.

### Reset on each new head

Rejected because symptom patches naturally create new heads without changing the failure.

### Use a second validation PR

Rejected because it creates a second lane-owned branch and transfers unreviewed state outside the owning PR.
