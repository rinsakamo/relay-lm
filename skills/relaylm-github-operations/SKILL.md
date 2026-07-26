---
name: relaylm-github-operations
description: Operate the RelayLM GitHub repository from ChatGPT through the connected GitHub tool surface without reconstructing the procedure per thread. Builds one fresh normalized snapshot, applies lane and execution gates, serializes mutations, verifies postconditions, and uses expected-head protection for merge.
---

# RelayLM GitHub Operations

## Purpose

Use this Skill whenever ChatGPT reads or mutates RelayLM repository, branch, pull-request, review, workflow, label, Draft, or merge state through the connected GitHub tools.

This Skill standardizes the procedure. It does not cache repository facts. Build fresh state from GitHub for every action that can be invalidated by another actor.

The exact data and gate contract is [ChatGPT GitHub Operations Contract](../../docs/contracts/chatgpt-github-operations.md). Current execution safety remains owned by `AGENTS.md`, `relaylm-stable`, and the Agent Execution Safety Contract.

## Scope binding

First resolve exactly one lane or bounded PR using current repository authority.

Lane-local commands operate only on the already selected lane. Other lanes are read-only for path, authority, caller, workflow, registry, status-owner, stack, merge-order, and stale-base conflict checks.

Do not use this Skill to pick another lane because the selected lane is blocked or CI is pending.

## Connector-first rule

Use the connected GitHub operations for repository-private and current state. Do not replace connected repository reads with web search, conversation memory, a PR-body claim, or an old handoff.

Use local `git` or `gh` only when a current task explicitly provides a local checkout and the connected operation cannot perform the exact required action. ChatGPT connector sessions normally remain connector-only.

## Operation cycle

Every GitHub operation uses this cycle:

```text
bind scope
  -> read current authority
  -> build normalized snapshot
  -> evaluate one action gate
  -> perform at most one mutation
  -> re-read target and refs
  -> verify postcondition
  -> continue or stop
```

Independent reads may be issued together. Mutations are serialized.

## Build the normalized snapshot

Resolve the fields in the contract using the following connected capabilities.

### Repository and main

- Read the repository default branch when it is not already exact.
- Resolve exact current main from the latest commit on that branch.
- Never use a remembered main SHA for a mutation.

### Pull request

For an existing PR, read:

- state and merged state;
- Draft state;
- base ref and SHA;
- head ref and SHA;
- body and execution receipt;
- labels and mergeability;
- requested reviewers.

Use the complete changed-filename operation rather than a truncated diff summary when path ownership matters.

### Reviews and discussion

Read separately:

- top-level PR comments;
- submitted reviews;
- inline review threads and their resolved state.

Do not infer zero unresolved threads from the absence of top-level comments.

### Checks and workflows

Read workflow and status evidence for the exact current head SHA.

- Associate every check result with its commit SHA.
- Read jobs and first failed steps when a workflow failed.
- Distinguish pending, failed, successful, skipped/neutral, and unavailable evidence.
- Never carry a green result from an older head into the current snapshot.

### Execution state

Parse exactly one `relaylm-execution-receipt` from the PR body. Verify:

- lane;
- current bootstrap main;
- governance epoch from exact current main authority blobs;
- one stable writer identity;
- `writer_mode: single`;
- `temporary_artifacts: none`.

Read stop and failure labels, changed workflows, temporary artifacts, and branch-writing mechanisms. Reproduce the execution guard when required.

### Cross-lane conflict state

Inspect open PRs only as far as needed to establish:

- changed-path overlap;
- semantic or document authority overlap;
- shared caller, workflow, generated registry, or status owner;
- stacked dependency or merge-order conflict.

Do not mutate another lane during this inspection.

## Action cards

### Read or report

1. Bind repository and scope.
2. Build the required snapshot fields.
3. Separate observed facts, gate results, inferences, and unavailable evidence.
4. Report the exact head and main when the result concerns current progress or merge readiness.

No mutation is implied by a read request.

### Start a new bounded PR

Use only when the user authorized the selected work and lane capacity is available.

1. Refresh exact current main.
2. Read open PRs and check path and authority conflicts.
3. Confirm the intended branch does not exist.
4. Define P0-P2, owned paths, non-goals, change budget, and validation.
5. Create one branch from the exact main SHA.
6. Write only the reviewed initial atomic scope.
7. Open one Draft PR against the intended base.
8. Put exactly one current execution receipt in the PR body.
9. Immediately read the new PR, exact head, paths, labels, and checks.
10. Reproduce the execution guard and stop if the bootstrap is not clean.

Prefer one atomic commit for the initial bounded scope. When the connector must write files sequentially, verify the current branch head before each write and keep one logical writer.

### Continue an existing PR

1. Build a complete snapshot.
2. Verify current main, current head, receipt, epoch, ancestry, writer, stop state, and temporary-artifact state.
3. Re-read relevant code, authorities, callers, workflows, and reviews at exact refs.
4. Evaluate P0-P2 before substantive correction or expansion.
5. Immediately before a branch write, verify the expected head again.
6. Apply one bounded write.
7. Re-read the branch or PR and confirm the intended diff only.

Do not automatically rebase, retry, force-push, or resolve semantic conflicts after a head mismatch.

### Update a PR body

1. Read the complete current body and exact head.
2. Declare whether the change is receipt-only or an ordinary lifecycle/body update.
3. Preserve all unrelated text byte-for-byte where practical.
4. Ensure exactly one receipt block.
5. Apply one body update.
6. Re-read the PR body and verify only the intended block or prose changed.

A receipt-only re-bootstrap edit must not change title, base, Draft state, reviews, branch content, or lifecycle prose.

### Comment or review

1. Read current head and the complete discussion state.
2. Confirm the selected lane owns the review action.
3. Anchor findings to current files and current head evidence.
4. Add one comment or review action.
5. Re-read the discussion and verify it exists once.

Do not post duplicate findings to compensate for an uncertain connector response.

### Resolve a review thread

Resolve only after the exact finding is corrected or explicitly disposed by current evidence.

1. Read the thread and current head.
2. Verify the correction or disposition.
3. Resolve exactly that thread ID.
4. Re-read thread state.

Do not bulk-resolve threads merely because CI is green.

### Change labels or Draft state

Use targeted operations.

- Add labels additively.
- Remove only the named label.
- Treat `relaylm:p6-stop` as sticky until authorized re-bootstrap and reset are complete.
- Mark ready only after the Ready gate passes.
- Convert to Draft when required by failure or lifecycle state.

Re-read labels and Draft state after the mutation.

### Re-run workflow evidence

A rerun is not a correction.

1. Read the failed run, jobs, and first failed step.
2. Confirm the head remains current.
3. Classify whether the failure is transient, stale, or materially identical.
4. Re-run only the required job or failed jobs when current policy permits.
5. Do not use reruns to evade the failure budget or avoid root-cause correction.

### Ready for review

Build a fresh complete snapshot and require:

- valid current receipt and current-main ancestry;
- no P6 stop or unresolved failure state;
- P0-P6 evidence complete;
- exact-head required checks successful;
- no unresolved review thread or requested change;
- complete-diff review clean;
- no newer main or head invalidation.

Then mark ready and re-read the PR.

### Merge

1. Build the final complete snapshot.
2. Re-read exact current main and exact PR head.
3. Verify all P7 requirements from current authority.
4. Supply the exact head SHA as expected-head protection.
5. Perform one merge mutation using the accepted merge method.
6. Re-read the PR and resulting main.
7. Verify the accepted change is present and record the merge result.
8. Perform P8 and release the lane slot only after convergence.

Never merge on mergeability alone. Never retry an ambiguous merge without first reading the PR and main.

## Mutation safety

Before every mutation, declare internally:

```yaml
target_repository: rinsakamo/relay-lm
target_pr: integer | null
target_branch: string | null
action: string
expected_main_sha: 40-hex
expected_head_sha: 40-hex | null
allowed_change: bounded description
```

After the mutation, verify:

- target identity is unchanged;
- branch or PR head is the expected result;
- unrelated fields did not change;
- the mutation appears exactly once;
- current state remains within lane and lifecycle authority.

## Connector uncertainty

Treat an error, timeout, null response, missing response, or partial pagination as unknown outcome.

Before retrying:

1. re-read the target object;
2. determine whether the prior mutation applied;
3. stop on disagreement or collision;
4. retry only when the operation is proven absent and the gate still passes.

Do not create a second branch, PR, comment, review, label, commit, receipt, or merge attempt as an uncertainty workaround.

## Stable output

For progress and final reports, include only the material evidence:

- selected lane and PR;
- exact current main and head;
- current lifecycle position;
- changed-path scope;
- checks and review state;
- stop or blocker state;
- mutation performed and verified postcondition;
- next safe same-lane action.

Do not expose internal connector IDs or low-level response payloads.

## Stop conditions

Stop and name the exact blocker when:

- scope is ambiguous;
- exact current main or head is unavailable;
- the receipt or epoch is stale;
- checks belong to another head;
- labels, reviews, changed paths, or workflow state cannot be read when required;
- a writer collision or branch-writing workflow exists;
- `relaylm:p6-stop` is active;
- connector results disagree;
- the next action crosses lane authority;
- a required connected capability is unavailable.

Never promise hidden or background GitHub work.
