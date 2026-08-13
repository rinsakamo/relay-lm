---
relaylm_doc_type: implementation_handoff
relaylm_authority: e1r5_primary_mem_recall_candidate_discovery_bridge
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_update_trigger:
  - Primary recall candidate discovery changes
  - namespace token compatibility changes
  - E1 recall proof boundary changes
  - lifecycle eligibility integration changes
  - RT-1 Primary ordinary-reader or fallback retirement changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - MVP roadmap sequencing
  - Subjective MEM ordinary Retrieval authority
  - RT-1D-R5 retirement completion or deletion approval
  - worker, queue, scheduler, or store mutation authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - e1_evaluation_consolidation.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i4d_primary_retrieval_exclusion.md
  - e1r4_retrieval_response_grounding.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../evidence/waves/e1r5_post_wave7_correction_convergence_audit.md
  - project_execution_plan.md
  - ../evidence/implementation/e1r5_completion_report.md
---
# Primary MEM Recall Candidate Discovery Compatibility Handoff

Last reviewed: 2026-08-08 JST

## Transitional status

E1-R5 is completed historical implementation evidence whose former bridge
behavior was folded into the canonical Primary recall implementation by PR #491.
This legacy underscore-named handoff remains transitional while that fallback and
its regression/evaluation consumers still have an accepted compatibility role.
It is not an independent runtime bridge and it is not ordinary Retrieval
authority.

Historical handoff identity: **E1-R5 Primary MEM Recall Candidate Discovery Bridge**.
The historical name is retained here only so evaluation evidence and regression
validation can identify the source slice; it does not restore a separate bridge
authority.

- owner: evaluation / Primary recall compatibility evidence;
- current consumers: Primary-only recall regressions, E1 evaluation evidence, and
  RT-1 retirement review;
- removal gate: RT-1D-R5/R6 proves that no accepted ordinary Primary fallback or
  continuing compatibility consumer needs this handoff as an active source;
- replacement validation: final Subjective-only request-path proof and preserved
  E1 completion/convergence evidence cover every continuing behavior and
  historical claim before this path is retired through the manifest and Git.

Repository-wide implementation and retirement status remain owned by
`docs/PROJECT_STATUS.md` and the RT-1 hard-cutover authority.

## Current compatibility responsibility

The former E1-R5 runtime bridge no longer exists as a second active retrieval
owner. Its bounded fallback discovery was folded into
`relaylm/relaymem_primary_recall.py` and its selection owner.

That behavior is reachable only inside an exact `primary_only` reader decision.
The Primary recall facade checks the RT-1 reader decision before resolving the
character store, opening Primary controls, or running candidate selection. A
missing, malformed, foreign, `neither`, or `subjective_only` decision therefore
cannot reach E1-R5 fallback discovery and releases no Primary evidence.

Within `primary_only`, the compatibility ordering is:

```text
M2 selected Primary candidates
  -> exact scoped/lifecycle narrowing
  -> if no eligible scoped Primary candidate survives,
     bounded E1-R5 fallback discovery
  -> existing RelayCTX / E1-R4 grounded-recall handoff
```

M2 remains the preferred relevance source inside that compatibility path. The
fallback is not a second authority, cannot run after Subjective cutover, and
cannot serve as an empty-result or failure fallback from Subjective Retrieval.

## What the fallback may read

When the exact Primary-only fallback condition is reached, the retained selection
owner may:

1. use only the already-scoped character store root and namespace;
2. read bounded Primary control/index/log/page material;
3. derive bounded page candidates for the exact namespace;
4. validate safe page location, schema, digest, index, and log consistency;
5. reuse the shared Primary retrieval lifecycle/current-state eligibility owner;
6. apply bounded query relevance to validated Primary `summary` and `title`
   fields when query hints are available;
7. construct the same bounded runtime-private evidence shape consumed by RelayCTX
   and E1-R4.

It does not materialize an unbounded tree, create a compatibility symlink, repair
Primary data, mutate a page or control, or bypass the RT-1 reader fence.

## Namespace compatibility

The retained Primary-only path accepts the namespace token shape used by the
queue/worker formation side, including slash-style values such as
`character/default`. This prevents formation-success / Primary-only-recall-reject
drift while the compatibility path remains present.

Character ids, namespaces, roots, page paths, and exact identities remain
runtime-private and are not public diagnostic fields.

## Lifecycle eligibility

E1-R5 owns no independent lifecycle policy. Fallback candidates pass through the
shared I-4D current-state eligibility index documented by the transitional
Primary retrieval-exclusion boundary. That phrase names the continuing shared
eligibility dependency; it does not make I-4D a universal reader authority.

Currentness, active lifecycle, mutation-none state, exact scope, safe page and
control state, and retrieval eligibility are mandatory. Prior, hidden, prepared,
recovery-required, corrupt, unresolved, unsafe, or cross-scope candidates fail
closed. A hidden successor never causes fallback to an earlier active revision.

## Grounded recall boundary

When a Primary-only fallback selects evidence, it produces the same private
selected-memory shape as the preferred Primary path and delegates grounding to
E1-R4. E1-R5 does not own response rewriting or unsupported-detail policy.

The private grounding contract remains: remembered facts must come only from the
admitted grounded-recall evidence, and unsupported details must not be invented.

## Public projection

Public diagnostics remain content-free. Bounded fields may include:

```text
primary_candidate_discovery_attempted
primary_candidate_count
grounding_enabled
grounded_item_count
unsupported_detail_policy
evidence_content_included=false
runtime_private_evidence_omitted=true
```

They must not expose raw memory or transcript text, protected source bodies,
queue payloads, store roots, paths, claim/lease material, digests, lineage, or
exact private identifiers.

## Historical evidence and R5 removal gate

The E1-R5 completion report and post-Wave-7 convergence audit remain historical
evidence for why the fallback was introduced and what PR #491 folded into the
Primary recall owner. Those records do not keep the live fallback authoritative.

RT-1D-R5 owns removal of replaced Primary ordinary reader/fallback surfaces after
its exact post-transfer, restart, request-path, and negative-call-graph gates.
This handoff does not pre-authorize deletion and does not predict whether a
read-only historical or evaluation consumer survives that retirement.

The former compatibility no-op runtime module has no semantic authority. Its
final disposition belongs to the owning retirement wave, not this document.

## Validation boundary

While the compatibility surface remains live, the existing E1-R5, I-4D, I-1,
and E1-R4 tests/smokes remain regression evidence for the responsibility they
already own. In addition, RT-1 request-path tests must prove that a non-
`primary_only` reader decision reaches none of the Primary fallback read path.

The E1 consolidation validator retains this exact current regression anchor:

```bash
PYTHONPATH=. python scripts/relaylm_primary_recall_post_retirement_structure_smoke.py
```

Other relevant existing validation includes the retained audit projection,
two-turn recall, Primary lifecycle exclusion, and E1-R4 grounding/security
smokes. The exact current workflow/registry remains
the command authority; this handoff is not a second smoke registry.

## Source evidence

- [E1-R5 completion report](../evidence/implementation/e1r5_completion_report.md)
- [E1-R5 Post-Wave-7 Correction Convergence Audit](../evidence/waves/e1r5_post_wave7_correction_convergence_audit.md)
- Source PR: #439
- Canonical fold-in PR: #491

## Non-goals

No Subjective MEM selection/ranking/projection semantics, RT-1D-R5 completion,
Primary deletion, writer or lifecycle mutation, O2/O3 supervision, queue/worker
ownership, browser trust, automatic migration/repair, Pin/Unpin, Held, Forget,
Correct, Consolidate, RelaySOUL mutation, media runtime work, or post-hoc visible
response rewriting is authorized here.
