---
relaylm_doc_type: contract
relaylm_authority: chatgpt_github_connector_snapshot_gate_and_mutation_protocol
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: repository_maintenance
relaylm_update_trigger:
  - ChatGPT GitHub connector capabilities change
  - normalized repository or pull-request snapshot fields change
  - GitHub mutation preconditions or postconditions change
  - execution receipt, expected-head, review, or merge gates change
relaylm_not_authoritative_for:
  - runtime, storage, schema, API, UI, memory, or documentation semantics
  - lane selection or cross-lane authorization
  - authorization to merge a pull request that has not passed P0-P7
  - GitHub platform behavior outside observed connector results
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../AGENTS.md
  - ../../skills/relaylm-stable-implementation/SKILL.md
  - ../../skills/relaylm-github-operations/SKILL.md
  - agent-execution-safety.md
  - ../planning/workstream-orchestration.md
  - ../architecture/repository-maintenance-system.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - ChatGPT GitHub connector sessions
  - RelayLM pull-request operators
  - RelayLM reviewers
relaylm_authority_level: exact_contract
---
# ChatGPT GitHub Operations Contract

## Authority

This contract owns the normalized GitHub snapshot, action gates, mutation transaction, and failure behavior used when ChatGPT operates the RelayLM repository through the connected GitHub tool surface.

It does not replace the execution-safety contract, the P0-P8 lifecycle, lane ownership, or domain review. Fresh repository state remains evidence; this contract defines how ChatGPT gathers, normalizes, checks, and mutates that state without rebuilding the procedure in each conversation.

## Core separation

RelayLM distinguishes two responsibilities:

```text
fresh observation
  exact current main, PR head, checks, reviews, labels, paths, comments,
  workflow state, receipt, mergeability, and cross-lane conflicts

stable operation procedure
  one normalized snapshot, one action gate, one mutation, one verification
```

Fresh observation is repeated because GitHub state changes. The procedure is not improvised per thread.

## Operating inputs

Every operation begins with:

```yaml
repository: rinsakamo/relay-lm
scope_mode: lane_local | explicit_portfolio
selected_lane: C | D | R | governance
selected_pr: integer | null
requested_action: read | create_pr | branch_write | pr_metadata | review_mutation | ready | merge | post_merge
```

The selected scope comes from current repository authority and the current instruction. This contract does not infer or broaden scope.

## Normalized snapshot v1

Before an ordinary mutation, ChatGPT constructs one logical snapshot with this shape. The snapshot may remain internal, but each field must be resolved or marked unavailable; missing evidence must not be silently treated as success.

```yaml
version: 1
repository:
  full_name: string
  default_branch: string
  main_sha: 40-lowercase-hex
scope:
  mode: lane_local | explicit_portfolio
  lane: C | D | R | governance
  pr_number: integer | null
  branch: string | null
pull_request:
  state: open | closed | merged | absent
  draft: boolean | null
  base_ref: string | null
  base_sha: 40-lowercase-hex | null
  head_ref: string | null
  head_sha: 40-lowercase-hex | null
  mergeable: boolean | unknown | null
  labels: [string]
  changed_paths: [string]
checks:
  head_sha: 40-lowercase-hex | null
  pending: [string]
  failed: [string]
  successful: [string]
  unavailable: [string]
reviews:
  unresolved_thread_ids: [string]
  requested_changes: [string]
  pending_reviewers: [string]
execution:
  receipt_count: integer
  receipt_lane: C | D | R | governance | null
  bootstrap_main_sha: 40-lowercase-hex | null
  governance_epoch: 64-lowercase-hex | null
  writer_id: string | null
  writer_mode: single | null
  temporary_artifacts: none | detected | unknown
  receipt_valid: boolean
  bootstrap_matches_main: boolean
  main_is_head_ancestor: boolean | unknown
  p6_stop: boolean
  branch_writing_workflows: [string]
conflicts:
  path: [string]
  authority: [string]
  caller: [string]
  registry: [string]
  status_owner: [string]
  stack_or_merge_order: [string]
freshness:
  observed_main_sha: 40-lowercase-hex
  observed_head_sha: 40-lowercase-hex | null
  checks_head_sha: 40-lowercase-hex | null
```

An empty list means the source was read and no item was found. `unknown`, `null`, or `unavailable` means the evidence was not established and must be handled by the requested action gate.

## Connector capability mapping

ChatGPT uses connector capabilities by responsibility rather than inventing a new command sequence:

| Responsibility | Preferred connected operation |
|---|---|
| exact current main | recent commit lookup on the repository default branch |
| PR identity, refs, body, Draft, mergeability | pull-request metadata fetch |
| complete changed-path set | paginated changed-filename listing |
| complete PR discussion | PR comments and review submissions fetch |
| unresolved review state | review-thread listing |
| exact-head workflow evidence | workflow runs, jobs, steps, and combined status for the head SHA |
| main/head relation and path diff | commit comparison |
| repository files and authority blobs | exact-ref file fetch |
| branch creation | create branch from an exact SHA |
| branch content mutation | connector file or Git object mutation against the selected branch |
| PR creation and metadata mutation | dedicated pull-request mutation |
| Draft transition | dedicated Draft or ready-for-review mutation |
| merge | expected-head-protected pull-request merge |

A missing connector capability does not authorize guessing. Use a narrower available capability or stop with the exact unavailable evidence. Do not substitute web search for connected private repository state.

## Read gate

Read-only inspection requires resolved repository and scope. It may inspect other lanes only within the cross-lane read-only boundary.

A read result must distinguish:

- observed fact;
- contract-derived gate result;
- inference;
- unavailable evidence.

## New-PR bootstrap gate

A new bounded PR has no receipt before the PR exists. Its permitted bootstrap sequence is:

```text
refresh exact current main
  -> confirm lane slot, path ownership, and no conflicting branch
  -> create one branch from the exact main SHA
  -> write only the reviewed initial atomic scope
  -> open one Draft PR with exactly one current execution receipt
  -> immediately rebuild the normalized snapshot
  -> run or reproduce the execution guard
```

The initial branch must not be created from a symbolic or previously remembered main when an exact SHA is available. A branch-name collision is inspected, not overwritten.

## Existing-PR branch-write gate

Immediately before each branch write, all of the following are required:

- the selected PR and lane are exact;
- current main and current head were freshly read;
- the expected head equals the observed head;
- exactly one valid receipt matches current main and governance epoch;
- current main is an ancestor of the head;
- no `relaylm:p6-stop` state exists;
- no branch-writing validation, transfer branch, writer collision, or temporary artifact exists;
- the write stays inside the reviewed lane-owned scope.

A mismatch stops the operation. ChatGPT must not retry by rebasing, force-pushing, or reconstructing implicitly.

## PR-metadata and review-mutation gate

Before editing a PR body, title, base, labels, Draft state, comments, reviews, or review threads:

- rebuild the snapshot;
- verify the selected PR and exact head;
- verify that the mutation is authorized by the current lane and lifecycle state;
- preserve unrelated user-authored content;
- change only the declared field or review object.

A receipt-only re-bootstrap edit replaces or adds only the receipt block. It does not alter lifecycle prose, review disposition, branch content, title, base, or merge state.

## Ready gate

Moving a Draft PR to ready-for-review requires:

- current receipt and exact-main bootstrap;
- no stop or unresolved failure state;
- P0-P6 completion recorded by current evidence;
- exact-head required checks successful;
- no unresolved review thread or requested change;
- complete-diff review clean;
- no newer main or head change invalidating the evidence.

Draft state is not removed merely because CI is green.

## Merge gate

Merge requires the full P7 gate plus:

- freshly observed current main and exact PR head;
- base and head are the intended refs;
- mergeability is established;
- all required exact-head checks are successful;
- review state is clean;
- expected-head protection is supplied to the merge operation;
- no mutation occurred after the final snapshot.

A head mismatch or ambiguous merge response is not retried automatically. Re-read the PR and repository before deciding what happened.

## Mutation transaction

Every mutation follows one transaction shape:

```text
1. build fresh normalized snapshot
2. declare target, action, expected main, and expected head
3. evaluate the action-specific gate
4. execute exactly one bounded mutation
5. re-read the mutated object and relevant refs
6. verify only the intended state changed
7. record the result or stop on disagreement
```

Multiple independent reads may run in parallel. Mutations against the same branch, PR body, label set, review thread, or merge state are serialized.

## Idempotency and retry behavior

- A connector error, empty response, or timeout is not success.
- Before retrying an apparently failed mutation, re-read the target to determine whether it applied.
- Do not duplicate comments, reviews, labels, receipt blocks, branches, PRs, or commits to compensate for uncertainty.
- A branch already existing at an unexpected SHA is a collision.
- A requested label addition uses additive mutation; removal targets only the named label.
- A PR body update preserves all unrelated content and exactly one receipt block.
- A merge uses the exact expected head SHA.

## Post-merge gate

After merge, ChatGPT verifies:

- the PR reports merged and exposes the merge result;
- resulting main contains the accepted change;
- post-merge checks or required convergence evidence are read;
- the selected lane's bookkeeping is completed or an exact blocker is recorded;
- the lane slot is released only after P8 convergence.

## Failure behavior

Fail closed when:

- repository, lane, PR, branch, or action is ambiguous;
- exact main or exact head cannot be established;
- checks are reported for a different head;
- changed paths, reviews, labels, receipt, or stop state cannot be read when required;
- connector results disagree;
- the expected head changed before mutation;
- a cross-lane write would be required;
- a requested capability is unavailable and no equivalent connected operation exists.

State the exact missing or conflicting evidence. Never claim a mutation, review, merge, or completion without the postcondition read.

## Non-goals

This layer does not:

- create an auto-correct bot or background writer;
- bypass execution receipts, failure budgets, reviews, or CI;
- infer domain correctness from GitHub metadata;
- merge because a PR is merely mergeable;
- allow parallel writers on one branch;
- make generated snapshots a new repository authority;
- replace current-main re-bootstrap or complete-diff review.
