---
name: relaylm-github-operations
description: Operate RelayLM from ChatGPT through connected GitHub tools using one fresh normalized snapshot, ChatGPT-first implementation routing, governed Claude Code handoff when connected writes are unsafe, lane and execution gates, serialized mutations, postcondition reads, and expected-head merge protection.
---

# RelayLM GitHub Operations

## Purpose

Use this Skill whenever ChatGPT reads or mutates RelayLM repository, branch, pull-request, review, workflow, label, Draft, or merge state.

The exact snapshot, implementation-transport, and gate rules are in [ChatGPT GitHub Operations Contract](../../docs/contracts/chatgpt-github-operations.md). This Skill is the procedure; it does not replace `relaylm-stable`, execution safety, P0-P8, CI, or domain review.

## Scope and source rules

Resolve exactly one lane or bounded PR from current authority before operating. Other lanes remain read-only except for conflict and dependency inspection.

Use connected GitHub state. Do not substitute web search, conversation memory, a PR-body claim, an old handoff, or a truncated diff.

Use local `git` or `gh` only when the task explicitly provides a local checkout and no connected operation can perform the exact action. A governed Claude Code handoff is the checkout-based implementation exception defined below; it does not authorize ChatGPT to reconstruct an unverified local repository state.

## One operation cycle

```text
bind scope
  -> read current authority
  -> build fresh normalized snapshot
  -> select one implementation backend when branch content will change
  -> evaluate one action gate
  -> perform at most one mutation
  -> re-read target and refs
  -> verify postcondition
  -> continue or stop
```

Independent reads may run together. Mutations are serialized.

## Implementation backend selection

ChatGPT connected GitHub implementation is the default. Keep a bounded slice in ChatGPT whenever complete-file or independently valid bounded writes can be transmitted and verified safely. Do not hand work to Claude Code merely because the code is long, multi-file, difficult, or likely to require substantial reasoning.

Use ChatGPT when:

- every changed file can be sent as one complete UTF-8 replacement or independently valid bounded mutation;
- sequential mutations cannot create an unsafe semantic intermediate state;
- expected-head and postcondition reads protect every write;
- no agent-managed Base64 splitting, payload chunking, partial-file assembly, placeholder/noop write, or repository temporary helper is required.

Use Claude Code only when the reviewed bounded slice cannot be executed safely through connected writes without those workarounds, or when correct implementation requires checkout-bound edit/test iteration unavailable through the connector.

Before Claude Code writes:

1. build the complete snapshot and re-read exact main and exact head;
2. stop ChatGPT branch-content mutations;
3. keep the same repository, PR, and branch;
4. transfer the single logical writer role for one bounded slice;
5. provide exact main/head, lane and P0-P8 state, allowed paths, invariants, negative cases, non-goals, required tests, and prohibited mechanisms.

The handoff prohibits new or transfer branches, corrective PRs, automatic rebase, force-push, Base64/payload splitting, partial-file reconstruction, placeholder/noop files, repository patch/apply helpers, temporary workflows, and scope expansion. Claude Code edits in a checkout, tests, commits intentionally, and pushes only to the existing branch.

After a reported push, independently re-read the actual exact head, complete diff, changed paths, checks, reviews, receipt, failure state, current-main relation, and temporary-artifact state. Treat Claude's reported SHA and test output as orientation only. Return to P1/P2 if the observed diff changes the reviewed design, authority, compatibility, scope, or change budget.

An uncertain connected write outcome never authorizes immediate switching to Claude Code. Re-read first and prove whether the mutation applied.

## Build the snapshot

### Exact main

1. Resolve the repository default branch name.
2. Resolve that ref's exact SHA with an exact-ref-capable connected operation, such as comparing the default ref to itself.
3. Do not use repository-wide recent-commit search as current-main authority.

### Pull request

Read state, merged/Draft state, base and head refs/SHAs, complete body and receipt, labels, mergeability, reviewers, and the complete changed-path set.

### Reviews

Read top-level comments, submitted reviews, and inline review threads separately. Absence of comments does not prove zero unresolved threads.

### Checks

Read workflow runs and status for the exact current head. For failures, read jobs and the first failed step. Never carry green evidence from an older head.

### Execution and failure state

Verify exactly one receipt, current bootstrap main, governance epoch from exact-main authority blobs, one writer, `writer_mode: single`, no branch-writing workflow or transfer branch, and no temporary artifact.

Read labels and all issue comments. Normalize the machine-owned failure state as exactly one of:

```text
none
failure_1
failure_2
p6_stop
unknown
```

Require at most one `relaylm-failure-budget-state` marker comment. Duplicate markers or unreadable disagreement between the marker, execution labels, and Draft state are `unknown` and fail closed. `failure_1` and `failure_2` permit only authorized root-cause correction; `p6_stop` prohibits ordinary writes. Ready and merge require `none`.

### Cross-lane state

Inspect open PRs only for path, authority, caller, workflow, registry, status-owner, stack, merge-order, and stale-base conflicts. Do not mutate another lane.

## Action cards

### Read or report

1. Build only the snapshot fields required by the question.
2. Separate observed facts, gate results, inferences, and unavailable evidence.
3. Include exact main and head for progress or merge-readiness reports.

A read request authorizes no mutation.

### Start a new bounded PR

1. Resolve exact current main.
2. Confirm lane capacity, path/authority ownership, and no conflicting branch.
3. Define P0-P2, owned paths, non-goals, change budget, implementation backend, and validation.
4. Create one branch from the exact main SHA.
5. Write only the reviewed bounded scope through the selected backend.
6. Open one Draft PR with exactly one current receipt.
7. Re-read the PR, refs, paths, labels, failure state, and checks.
8. Reproduce the execution guard and stop unless clean.

Prefer one atomic initial commit. If connector file writes must be sequential, re-read the branch head before each write and keep one logical writer. Do not use sequential connector writes when their intermediate state is unsafe; select a governed Claude Code handoff before the first workaround write.

### Continue or correct an existing PR

1. Build the complete snapshot.
2. Verify current main, current head, receipt, epoch, ancestry, writer, normalized failure state, and temporary-artifact state.
3. Re-read relevant authorities, code, callers, workflows, and reviews at exact refs.
4. Re-evaluate P0-P2 before substantive correction or scope growth.
5. Select the implementation backend and confirm its single-writer boundary.
6. Immediately before a branch write, verify expected head again.
7. Apply one bounded write permitted by the current failure state.
8. Re-read the branch/PR and confirm the intended diff only.

Do not automatically rebase, retry, force-push, resolve semantic conflicts, or switch transports after a head mismatch or uncertain mutation.

### Update PR body or metadata

1. Read the complete body, exact head, and target field.
2. Declare receipt-only or ordinary metadata change.
3. Preserve unrelated content.
4. Apply one bounded mutation.
5. Re-read and verify only the intended field changed.

A receipt-only edit changes exactly one receipt block and nothing else.

### Comment, review, or resolve a thread

1. Read current head and complete discussion state.
2. Confirm lane and lifecycle authority.
3. Anchor the action to current evidence.
4. Mutate exactly one comment, review, or thread.
5. Re-read and verify it once.

Resolve a thread only after its finding is corrected or explicitly disposed. Never bulk-resolve because CI is green.

### Labels and Draft state

Use targeted mutations:

- add labels additively;
- remove only the named label;
- keep `relaylm:p6-stop` sticky until authorized re-bootstrap and reset;
- mark ready only when `failure_state: none` and the Ready gate passes;
- convert to Draft when lifecycle or failure state requires it.

Re-read labels, marker comments, and Draft state afterward.

### Workflow rerun

1. Read the failed run, jobs, and first failed step.
2. Confirm the head remains current.
3. Classify transient, stale, or materially identical failure.
4. Re-run only the required job or failed jobs when policy permits.

A rerun is not a correction and must not evade the failure budget.

### Ready for review

Require a current receipt and ancestry, `failure_state: none`, P0-P6 evidence, successful exact-head required checks, clean reviews, clean complete-diff review, verified implementation-backend handoff evidence when Claude Code was used, and no newer main/head invalidation. Then mark ready and re-read the PR.

### Merge

1. Build the final complete snapshot.
2. Re-resolve exact current main and PR head.
3. Verify all P7 requirements, intended refs, and `failure_state: none`.
4. Supply the exact head SHA as expected-head protection.
5. Perform one accepted merge mutation.
6. Re-read the PR and resulting main.
7. Verify the accepted change and complete P8 before releasing the lane slot.

Never merge on mergeability alone. Never retry an ambiguous merge before reading PR and main.

## Mutation declaration

Before each mutation, record internally:

```yaml
target_repository: rinsakamo/relay-lm
target_pr: integer | null
target_branch: string | null
action: string
implementation_backend: chatgpt_connector | claude_code | not_applicable
expected_main_sha: 40-hex
expected_head_sha: 40-hex | null
allowed_change: bounded description
```

Afterward verify target identity, resulting ref/state, unrelated fields, single application, backend writer ownership, and lane/lifecycle compliance.

## Uncertain connector outcome

An error, timeout, null/empty response, or incomplete pagination is unknown, not success.

Before retrying or switching implementation backends, re-read the target and prove the mutation did not apply. Do not create duplicate branches, PRs, commits, comments, reviews, labels, receipts, merge attempts, Claude handoffs, or alternate-transport writes as a workaround.

## Stable report

Report only material evidence: selected lane/PR, exact main/head, lifecycle position, selected implementation backend when relevant, changed paths, checks, reviews, normalized failure state, verified mutation or handoff result, and next safe same-lane action. Do not expose internal connector IDs.

## Stop conditions

Stop and name the exact blocker when scope or exact refs are ambiguous; receipt/epoch is stale; checks belong to another head; required paths, labels, reviews, workflow evidence, or failure marker state is unavailable; duplicate failure markers, a writer collision, branch-writing workflow, temporary artifact, or `p6_stop` exists; connector results disagree; the next action crosses lane authority; the required connected capability is unavailable; or the bounded slice cannot be executed safely by ChatGPT and no governed Claude Code handoff can be formed.

Never promise hidden or background GitHub work.
