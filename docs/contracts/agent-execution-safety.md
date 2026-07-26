---
relaylm_doc_type: contract
relaylm_authority: agent_execution_receipt_governance_epoch_single_writer_and_failure_stop
relaylm_status: current
relaylm_volatility: low
relaylm_owner: implementation
relaylm_update_trigger:
  - execution receipt fields or validation change
  - governance epoch inputs or algorithm change
  - single-writer or workflow-write policy changes
  - failure signature or P6-stop semantics change
  - temporary artifact rejection changes
relaylm_not_authoritative_for:
  - runtime, storage, API, UI, memory, or documentation domain semantics
  - current implementation completion
  - lane sequencing beyond execution safety
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0009-execution-epoch-and-rebootstrap.md
relaylm_related_authority:
  - ../../AGENTS.md
  - ../../skills/relaylm-stable-implementation/SKILL.md
  - ../../skills/relaylm-github-operations/SKILL.md
  - ../planning/workstream-orchestration.md
relaylm_verified_by:
  - ../../scripts/relaylm_agent_execution_guard.py
  - ../../scripts/relaylm_agent_failure_budget.js
  - ../../.github/workflows/agent-execution-safety.yml
  - ../../.github/workflows/agent-failure-budget.yml
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - AI coding agents
  - pull-request reviewers
  - GitHub Actions
relaylm_authority_level: exact_contract
---
# Agent Execution Safety Contract

## Authority

This contract owns the exact execution-governance epoch, PR receipt, single-writer, branch-workflow, failure-budget, and temporary-artifact rules used before RelayLM repository work may continue.

It does not decide domain semantics or authorize a merge that has not passed the owning lane's P0-P8 gates.

## Governance epoch

The ordered epoch inputs are:

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

For each path, resolve its Git blob ID from the selected governance ref and feed this UTF-8 record to SHA-256 in listed order:

```text
<path> NUL <40-lowercase-hex-blob-id> LF
```

The resulting 64-lowercase-hex digest is the governance epoch. Missing input, non-Git input, unordered input, wall-clock data, or content hashing that omits path identity fails closed.

The governance ref is always exact current `origin/main`. A stacked PR may use a different base branch for its diff, but that base must not replace `origin/main` as the epoch or receipt authority.

## PR execution receipt

Every active implementation, documentation, maintenance, migration, correction, or governance PR contains exactly one block:

```text
<!-- relaylm-execution-receipt
version: 1
lane: <C | D | R | governance>
bootstrap_main_sha: <exact current origin/main 40-hex SHA>
governance_epoch: <64 lowercase hex>
writer_id: <lowercase stable logical identifier>
writer_mode: single
temporary_artifacts: none
-->
```

Rules:

- unknown, duplicate, or missing fields fail;
- duplicate or unterminated receipt blocks fail;
- `bootstrap_main_sha` equals the exact commit resolved from current `origin/main` and is an ancestor of the PR head;
- `governance_epoch` equals the epoch from that same `origin/main` ref;
- `writer_id` matches `^[a-z0-9][a-z0-9._-]{0,63}$`;
- `writer_mode` is exactly `single`;
- `temporary_artifacts` is exactly `none`.

Consecutive failure state is machine-owned and does not live in the receipt.

## Re-bootstrap transition

A missing or stale receipt, current-main mismatch, changed epoch, writer collision, or P6-stop condition requires:

```text
active
  -> write_stop
  -> containment
  -> read-only current-main comparison
  -> one controlled exact-main integration or reconstruction
  -> P0/P1 reclassification
  -> P2 stability review
  -> new receipt
  -> guard pass
  -> active
```

While stopped, only these writes are allowed, in order:

1. one containment change that disables branch-writing automation or removes temporary execution machinery;
2. one exact-main integration or reconstruction after containment and read-only comparison;
3. one PR-body edit that adds or replaces only the receipt after read-only P0/P1/P2 review of the resulting head.

The exact-main integration or reconstruction must:

- capture the expected branch head immediately before writing and fail on mismatch;
- use exact current `origin/main` as its integration parent or reconstruction base;
- preserve already reviewed domain intent without adding a feature, workaround, fallback, compatibility path, or scope expansion;
- keep all mechanical conflict resolution visible for complete-diff review;
- stop without writing when any conflict requires a policy, authority, lifecycle, migration, rollback, state, or semantic decision;
- avoid automatic retry, rebase, force-push, or conflict resolution after a mismatch.

The receipt edit contains no branch write, review disposition, merge action, title/base change, or unrelated body edit. Containment and main integration are re-bootstrap operations, not implementation progress and not correction-attempt counter resets.

## Single-writer invariant

One active PR branch has one logical writer.

Changed PR-local workflows must not grant `contents: write`, contain a `git push` command, commit generated source, delete themselves after a transform, write a transfer branch, or act as auto-correct beside an implementation writer.

Test and validation workflows may install dependencies, compile, test, inspect Git history, and upload diagnostics with repository-content read permission.

The failure-budget monitor is not a branch writer. It may modify only its hidden state comment, execution labels, and Draft state.

A head mismatch immediately before a branch write is `writer_collision`. Stop without retry, rebase, force-push, or automatic conflict resolution.

## Failure signature

A normalized signature contains:

```text
stable_workflow_id
failed_job_name
first_failed_step_name
bounded_conclusion_category
```

The bounded category is one of:

```text
failure
cancelled
timed_out
action_required
startup_failure
stale
other_non_success
```

The current workflow display name is retained for diagnostics but excluded from the signature digest. Renaming a workflow therefore does not reset its state while GitHub preserves the workflow ID.

A moved or renamed job/step may start a new signature only when the monitor cannot map it to the same stable failing responsibility. Review must treat obvious rename-only evasion as the existing signature.

## Failure-budget state

`agent-failure-budget.yml` owns one hidden PR comment:

```text
<!-- relaylm-failure-budget-state
<canonical compact JSON>
-->
```

The JSON contains:

```text
version
workflows: {
  <stable workflow ID>: {
    workflow_name
    signature_digest | null
    signature_fields | null
    consecutive_count
    last_run_id
  }
}
p6_stop
```

Rules:

- one marker comment per PR;
- only the monitor edits it;
- duplicate marker comments fail closed;
- each workflow owns its own `last_run_id`, so out-of-order completion of another workflow cannot suppress processing;
- a run ID is processed at most once for that workflow;
- a successful run stores count zero and advances only that workflow's `last_run_id`;
- `skipped` and `neutral` runs advance only that workflow's `last_run_id` while preserving its signature and count;
- a changed signature starts at one;
- the same signature increments by one;
- up to 64 most-recent workflow entries are retained by `last_run_id`;
- `p6_stop` is sticky until reviewed re-bootstrap;
- state is bounded and contains no logs or source payloads.

The monitor mirrors the highest current state with exactly one label:

```text
relaylm:failure-1
relaylm:failure-2
relaylm:p6-stop
```

It removes obsolete lower labels when state changes.

## P6-STOP

The third consecutive identical signature sets `p6_stop: true`, adds `relaylm:p6-stop`, removes lower failure labels, and converts the PR to Draft.

The same stop is required immediately for architectural assumption error, duplicate authority, duplicate writer or branch collision, branch-writing validation, temporary-artifact recurrence, or a temporary validation PR/transfer branch.

While stopped:

- static execution safety fails;
- no ordinary branch writes or auto-correct;
- no temporary workflow or transfer PR;
- merge is prohibited;
- a later green run does not clear the stop;
- clearing requires reviewed P0/P1/P2 re-bootstrap, exact current-main incorporation, a current receipt, removal of the cause, and explicit authorized reset.

## Temporary artifact rejection

The static guard rejects root-level hidden Python files and workflow basenames containing `probe`, `structural-refactor`, `hardening-validate`, `final-build`, `build-transfer`, or `auto-correct`.

It also rejects changed workflows containing `contents: write` or a `git push` command. P5 still reviews equivalent mechanisms under other names.

## Static workflow contract

`.github/workflows/agent-execution-safety.yml`:

- runs on PR open, reopen, synchronize, edit, ready-for-review, labeled, and unlabeled events;
- uses `contents: read` and `pull-requests: read` only;
- fetches exact current `origin/main`, the PR diff base, and full history;
- uses `origin/main` only for epoch and receipt validation;
- uses the PR base only to enumerate the proposed diff, including stacked PRs;
- validates receipt, exact bootstrap, stop label, writer workflow, and temporary diff;
- runs both execution-core self-tests;
- uses PR-number concurrency with `cancel-in-progress: true`;
- never changes branch content or PR metadata.

## Failure-monitor workflow contract

`.github/workflows/agent-failure-budget.yml`:

- runs on completed `workflow_run` events;
- ignores itself and the static guard;
- processes only open PRs in this repository, using associated PR metadata or same-repository head-branch lookup;
- uses `actions: read`, `contents: read`, `issues: write`, and `pull-requests: write`;
- reads job and step conclusions through the GitHub API;
- updates only its marker comment, three execution labels, and Draft state;
- never modifies branch content or the PR body;
- uses stable branch/PR concurrency and workflow-local run ordering;
- supports explicit `workflow_dispatch` reset with PR number and reviewed reason.

A reset clears monitor state and execution labels but leaves the PR Draft. Returning to ready-for-review remains a separate P7 action.

## Existing PR migration

Every pre-contract open PR remains Draft and merge-prohibited until branch-writing automation and temporary artifacts are absent, one controlled exact-main integration or reconstruction is complete, P0/P1/P2 are refreshed against the resulting head, the receipt is valid, and no stop label or unresolved failure state remains.

Correct domain code and evidence need not be discarded merely because process state is stale.

## Failure behavior

The static guard emits bounded invariant diagnostics and exits nonzero. It does not print credentials, receipt-external PR text, source payloads, or user data.

The workflows cannot revoke external writer credentials. Every actor observing a guard failure or stop label must stop rather than making a symptom patch.
