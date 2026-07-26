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

This contract owns the normalized GitHub snapshot, action gates, mutation transaction, and failure behavior used when ChatGPT operates RelayLM through connected GitHub tools.

It does not replace lane ownership, P0-P8, execution safety, CI, or complete-diff review. GitHub facts are always refreshed; the procedure for handling them is stable and must not be reconstructed per conversation.

## Inputs

Every operation resolves:

```yaml
repository: rinsakamo/relay-lm
scope_mode: lane_local | explicit_portfolio
selected_lane: C | D | R | governance
selected_pr: integer | null
requested_action: read | create_pr | branch_write | pr_metadata | review_mutation | ready | merge | post_merge
```

This contract never selects or broadens the lane.

## Normalized snapshot v1

Before an ordinary mutation, ChatGPT builds one logical snapshot:

```yaml
version: 1
repository:
  full_name: string
  default_branch: string
  main_sha: 40-hex
scope:
  mode: lane_local | explicit_portfolio
  lane: C | D | R | governance
  pr_number: integer | null
  branch: string | null
pull_request:
  state: open | closed | merged | absent
  draft: boolean | null
  base_ref: string | null
  base_sha: 40-hex | null
  head_ref: string | null
  head_sha: 40-hex | null
  mergeable: true | false | unknown | null
  labels: [string]
  changed_paths: [string]
checks:
  head_sha: 40-hex | null
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
  bootstrap_main_sha: 40-hex | null
  governance_epoch: 64-hex | null
  writer_id: string | null
  writer_mode: single | null
  temporary_artifacts: none | detected | unknown
  receipt_valid: boolean
  bootstrap_matches_main: boolean
  main_is_head_ancestor: true | false | unknown
  failure_state: none | failure_1 | failure_2 | p6_stop | unknown
  failure_state_comment_count: integer | unknown
  branch_writing_workflows: [string]
conflicts:
  path: [string]
  authority: [string]
  caller_or_registry: [string]
  status_or_merge_order: [string]
freshness:
  observed_main_sha: 40-hex
  observed_head_sha: 40-hex | null
  checks_head_sha: 40-hex | null
```

An empty list means the source was read and nothing was found. `unknown`, `null`, or `unavailable` means the evidence was not established and cannot be treated as success.

## Exact-ref rule

The default branch name and its exact commit SHA are separate facts.

Resolve current main with a connector operation that resolves the default-branch ref itself, for example comparing that ref to itself or another exact-ref-capable operation. A repository-wide recent-commit search is not sufficient because it may return a non-default branch commit.

PR head, base, checks, comparisons, file reads, and merge protection must likewise be tied to exact refs or SHAs.

## Capability responsibilities

Use connected operations by responsibility:

| Need | Connected capability |
|---|---|
| exact main | default-branch ref resolution |
| PR refs, body, Draft, labels, mergeability | PR metadata fetch |
| complete paths | paginated changed-filename listing |
| comments, reviews, unresolved threads | their dedicated complete reads |
| exact-head CI | workflow runs, jobs, steps, and status for the head SHA |
| ancestry and path relation | commit comparison |
| authority files and blobs | exact-ref file fetch |
| branch, file, PR, label, review, Draft mutations | dedicated bounded mutations |
| merge | expected-head-protected merge |

Do not substitute web search, conversation memory, a PR-body claim, or a partial diff for connected repository state.

## Gates

### New PR

A new PR has no receipt before creation. The only bootstrap sequence is:

```text
resolve exact main
  -> confirm lane slot, ownership, and no branch conflict
  -> create one branch from that SHA
  -> write the reviewed bounded scope
  -> open one Draft PR with exactly one current receipt
  -> rebuild the snapshot and reproduce the execution guard
```

A branch-name collision is inspected, never overwritten.

### Existing PR write

Immediately before each branch write require:

- exact selected PR, lane, current main, and current head;
- expected head equals observed head;
- exactly one valid receipt matches current main and governance epoch;
- current main is an ancestor of head;
- failure state is neither `p6_stop` nor an unreadable duplicate state;
- no writer collision, branch-writing validation, transfer branch, or temporary artifact;
- the change remains in reviewed lane-owned scope.

A mismatch stops the operation. Do not automatically rebase, retry, force-push, or reconstruct.

### PR metadata and review mutation

Rebuild the snapshot, verify the exact head and lifecycle authority, preserve unrelated content, and mutate only the declared field or review object.

A receipt-only edit changes only the single receipt block. It does not alter lifecycle prose, title, base, Draft state, review state, branch content, or merge state.

### Ready

Require current receipt and ancestry, `failure_state: none`, P0-P6 evidence, successful exact-head required checks, clean review state, clean complete-diff review, and no newer main or head invalidation.

### Merge

Require the full P7 gate, freshly observed exact main and head, intended refs, established mergeability, successful exact-head checks, clean reviews, and expected-head protection. No mutation may occur between the final snapshot and merge.

## Mutation transaction

Every mutation has one shape:

```text
1. build fresh snapshot
2. declare target, action, expected main, expected head, and allowed change
3. evaluate the action gate
4. execute exactly one bounded mutation
5. re-read the target and relevant refs
6. verify only the intended state changed
7. record the result or stop
```

Independent reads may run in parallel. Mutations against the same branch, PR body, labels, review thread, Draft state, or merge state are serialized.

## Uncertain outcomes and retries

An error, timeout, null response, empty response, or incomplete pagination is not success.

Before retrying, re-read the target and determine whether the mutation applied. Never create a duplicate branch, PR, commit, comment, review, label, receipt, or merge attempt to compensate for uncertainty.

A branch at an unexpected SHA is a collision. A merge uses the exact expected head. Label addition is additive; removal targets only the named label.

## Post-merge

Verify the PR is merged, resulting main contains the accepted change, required post-merge evidence is read, P8 bookkeeping is completed or blocked explicitly, and the lane slot is released only after convergence.

## Failure behavior

Fail closed when scope, exact refs, paths, checks, reviews, labels, receipt, failure state, or connector outcome is ambiguous or unavailable for the requested action; when connector results disagree; when the expected head changes; or when a cross-lane write would be required.

State the exact missing or conflicting evidence. Never claim a mutation, review, merge, or completion without a postcondition read.

## Non-goals

This layer does not create a bot, background writer, cache, second repository authority, parallel branch writer, CI bypass, review bypass, or domain-correctness oracle.
