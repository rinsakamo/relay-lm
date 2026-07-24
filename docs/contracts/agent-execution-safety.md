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
  - ../planning/workstream-orchestration.md
relaylm_verified_by:
  - ../../scripts/relaylm_agent_execution_guard.py
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
- `bootstrap_main_sha` must equal the exact commit resolved from the selected current-main ref;
- that commit must also be an ancestor of the PR head;
- `governance_epoch` must equal the epoch from the same current-main ref;
- `writer_id` matches `^[a-z0-9][a-z0-9._-]{0,63}$`;
- `writer_mode` is exactly `single`;
- `temporary_artifacts` is exactly `none`.

Consecutive failure state is not stored in the receipt. It is owned by the failure-budget monitor.

## Re-bootstrap transition

A missing or stale receipt, current-main mismatch, changed epoch, writer collision, or P6-stop condition requires:

```text
active
  -> write_stop
  -> exact current-main incorporation
  -> P0/P1 reclassification
  -> P2 stability review
  -> new receipt
  -> guard pass
  -> active
```

No branch write is allowed between `write_stop` and the new receipt except one controlled containment change that disables branch-writing automation or removes temporary execution machinery. Containment is not implementation progress.

After read-only P0/P1/P2 re-bootstrap, exactly one controlled PR-body edit may add or replace only the receipt. It must not include a branch write, review disposition, merge action, title/base change, or unrelated body edit. The static guard must pass immediately afterward.

## Single-writer invariant

One active PR branch has one logical writer.

Changed PR-local workflows must not:

- grant `contents: write`;
- run any `git push` command;
- commit generated source changes;
- delete themselves after a transform;
- checkout and write a transfer branch;
- act as auto-correct beside an implementation writer.

Test and validation workflows may install dependencies, compile, execute tests, inspect Git history, and upload diagnostics with repository-content read permission.

The failure-budget monitor is not a branch writer. It may modify only its hidden state comment, execution labels, and Draft state.

A head mismatch immediately before a branch write is `writer_collision`. Stop without retry, rebase, force-push, or automatic conflict resolution.

## Failure signature

A normalized signature contains exactly:

```text
workflow_name
failed_job_name
first_failed_step_name
bounded_conclusion_category
```

The conclusion category is one of:

```text
failure
cancelled
timed_out
action_required
startup_failure
stale
other_non_success
```

A new commit, workflow rename, moved step, or prose-only change does not reset state when the monitor can map it to the same materially failing responsibility. The monitor records workflow and job identifiers in addition to names when GitHub supplies them.

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
last_processed_run_id
workflows: {
  <stable workflow identity>: {
    signature_digest
    signature_fields
    consecutive_count
    last_run_id
  }
}
p6_stop
```

Rules:

- one marker comment per PR;
- only the monitor edits it;
- duplicate marker comments fail closed and require review;
- a run ID is processed at most once;
- a successful run resets only that workflow's non-stop consecutive state;
- a changed signature starts at one;
- the same signature increments by one;
- `p6_stop` is sticky until reviewed re-bootstrap;
- comment state is bounded and contains no logs or source payloads.

The monitor mirrors the highest current state with exactly one label:

```text
relaylm:failure-1
relaylm:failure-2
relaylm:p6-stop
```

It removes obsolete lower labels when state changes.

## P6-STOP

The third consecutive identical signature sets `p6_stop: true`, adds `relaylm:p6-stop`, removes failure-1/failure-2 labels, and converts the PR to Draft.

The same stop is required immediately when current evidence establishes:

- architectural assumption error;
- duplicate semantic authority;
- duplicate branch writer or non-fast-forward collision;
- branch-writing validation;
- temporary-artifact recurrence;
- temporary validation PR or transfer branch.

While stopped:

- static execution safety fails;
- no branch writes or auto-correct;
- no temporary workflow or transfer PR;
- merge is prohibited;
- a later green run does not clear the stop;
- clearing requires reviewed P0/P1/P2 re-bootstrap, exact current-main incorporation, a current receipt, removal of the cause, and an explicit authorized state reset.

## Temporary artifact rejection

The static guard rejects changed paths that are:

- root-level hidden Python files;
- workflow basenames containing `probe`;
- workflow basenames containing `structural-refactor`;
- workflow basenames containing `hardening-validate`;
- workflow basenames containing `final-build`;
- workflow basenames containing `build-transfer`;
- workflow basenames containing `auto-correct`.

It also rejects any changed workflow containing `contents: write` or a `git push` command.

This is a minimum generic guard. P5 still reviews equivalent mechanisms under other names.

## Static workflow contract

After this contract merges, `.github/workflows/agent-execution-safety.yml` is activated in one follow-up PR. It:

- runs on PR open, reopen, synchronize, edit, ready-for-review, labeled, and unlabeled events;
- uses `contents: read` and `pull-requests: read` only;
- fetches exact current `origin/main` and full history;
- validates event receipt, exact bootstrap, stop label, and proposed diff;
- runs the committed self-test;
- uses PR-number concurrency with `cancel-in-progress: true`;
- never changes branch content or PR metadata.

## Failure-monitor workflow contract

The same follow-up activates `.github/workflows/agent-failure-budget.yml`. It:

- runs on completed `workflow_run` events;
- ignores itself and the static guard;
- processes only runs associated with open pull requests in this repository;
- uses `actions: read`, `contents: read`, `issues: write`, and `pull-requests: write`;
- reads job and step conclusions through the GitHub API;
- updates only its marker comment, three execution labels, and Draft state;
- never modifies branch content or the PR body;
- uses stable per-PR concurrency and idempotent run-ID handling.

Until activation merges, agents and reviewers reproduce the static guard directly and treat repeated failures conservatively as stopped when evidence is ambiguous.

## Existing PR migration

After this contract becomes current, every previously open PR remains Draft and merge-prohibited until:

- branch-pushing automation and temporary artifacts are absent;
- exact current `main` is incorporated into the PR head;
- current epoch is calculated from that same main ref;
- P0/P1/P2 are refreshed;
- the PR body contains a valid receipt;
- no stop label or unresolved failure state remains.

Correct domain code and evidence need not be discarded merely because process state is stale.

## Failure behavior

The static guard emits bounded invariant diagnostics and exits nonzero. It does not print credentials, receipt-external PR text, source payloads, or user data.

The workflows cannot revoke external writer credentials. Every actor observing a guard failure or stop label must stop rather than making a symptom patch.
