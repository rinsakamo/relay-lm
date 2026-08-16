---
relaylm_doc_type: architecture_report
relaylm_authority: primary_mem_retrieval_exclusion_compatibility_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Primary ordinary reader or fallback retirement changes
  - Primary lifecycle eligibility or read-only historical consumer changes
  - RT-1 one-authority reader decisions or removal gates change
relaylm_not_authoritative_for:
  - current runtime implementation completion status
  - Subjective MEM ordinary Retrieval, ranking, projection, or usage semantics
  - RT-1D-R5 completion, deletion approval, or Primary asset retirement status
  - Primary writer, mutation, recovery, API, or UI behavior
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - subjective-mem-retrieval-projection-hard-cutover.md
  - memory/retrieval-and-grounding.md
  - ../contracts/grounded-recall.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i4b_primary_current_state_shared_fence.md
  - project_execution_plan.md
---
# Primary MEM Retrieval Exclusion Compatibility Boundary

Last reviewed: 2026-08-08 JST

## Transitional status

This legacy underscore-named page remains an explicitly transitional D5 source
while current Primary compatibility and read-only historical consumers still
exist. It is not activated as a permanent canonical path.

- owner: memory / Lane D documentation canonicalization;
- current consumers: Primary-only retrieval compatibility reviewers, Soul Lab
  historical lifecycle projection consumers, and RT-1 retirement reviewers;
- removal gate: RT-1D-R5/R6 proves the final disposition of every remaining
  Primary ordinary-reader and read-only operational consumer;
- replacement validation: the final canonical Retrieval/Primary documentation
  graph preserves every still-current eligibility, disclosure, operational, and
  historical contract before this path is retired through the retirement
  manifest and Git history.

Current implementation completion and the exact retirement decision remain owned
by `docs/PROJECT_STATUS.md`, the RT-1 hard-cutover authority, and the owning R5/R6
atomic waves.

## Scope

This page defines the remaining read-only Primary MEM retrieval eligibility and
exclusion boundary. It no longer defines a universal ordinary Retrieval
authority.

`relaylm/relaymem_primary_recall.py` owns the compatibility facade
`apply_relaymem_primary_recall_scope(...)`. That facade is usable only when the
exact RT-1 reader decision class is `primary_only`. The facade checks the reader
decision before resolving a Primary store root, opening the store, preparing
selection, or discovering a candidate.

A missing, foreign, malformed, `neither`, or `subjective_only` decision releases
no Primary runtime-private evidence. It returns the bounded fenced artifact with
no Primary store read and cannot become an empty-result or failure fallback for
Subjective Retrieval.

This page does not authorize deletion of any Primary asset.

## Primary-only compatibility flow

When the exact reader decision is `primary_only`, the retained compatibility path
is:

```text
existing M2 retrieval artifact
  -> exact Primary reader-decision gate
  -> scoped Primary store and namespace validation
  -> lifecycle/current-revision eligibility filtering
  -> bounded Primary candidate selection or authorized legacy fallback discovery
  -> runtime-private RelayCTX grounding handoff
```

M2 and the retained Primary selection owner continue to own relevance, ordering,
candidate caps, and budgets inside this compatibility path. This page owns only
the lifecycle/currentness exclusion rules applied before Primary evidence may be
released.

## Eligibility and exclusion

A Primary candidate survives only when it was admitted by the retained Primary
selection path and all of the following remain exact:

- the request is in `primary_only` reader state;
- character store root and namespace are valid and scoped;
- page and control state are canonical and safe;
- physical identity maps to one logical memory;
- the candidate is the canonical current physical revision;
- lifecycle state is active;
- mutation state is none;
- retrieval eligibility is true.

The following fail closed:

```text
prior revision
hidden
prepared
recovery required
corrupt or ambiguous authority
unresolved physical-to-logical identity
scope mismatch
unsafe or changed file state
reader decision other than primary_only
```

A hidden successor remains lifecycle authority. The Primary compatibility reader
never falls back to an earlier active physical revision.

The retained eligibility owner uses the following closed reason vocabulary:

```text
eligible_current_active
excluded_prior_revision
excluded_hidden
excluded_prepared
excluded_recovery_required
excluded_corrupt
excluded_unresolved_identity
excluded_scope_mismatch
excluded_unsafe
```

Its public/log projection is content-free: it does not expose Primary paths,
namespaces, logical or physical identities, digests, operation data, or raw
exceptions.

## One-authority boundary

The RT-1 cutover owner is the sole authority that decides whether ordinary memory
Retrieval is `primary_only`, `neither`, or `subjective_only`.

This compatibility boundary must not infer serving authority from configuration,
projection presence, Primary store availability, or an empty Subjective result.
After a finalized Subjective transfer, Primary recall remains fenced even when
Subjective retrieval is empty, stale, corrupt, unavailable, or unsupported.
There is no dual-read, precedence, or cross-authority fallback rule.

## Read-only historical and operational use

Primary lifecycle/current-state scanners and historical projections may continue
only for explicitly accepted read-only operational, migration, characterization,
rollback-evidence, or history consumers. Such use does not restore ordinary
Primary serving authority and does not authorize a Primary writer.

The durable `relaylm.lab.memory_used.v0` historical receipt and the read-only
`relaylm.lab.memory_used_lifecycle.v1` projection remain separate from ordinary
reader authority. Their continuing disposition is reviewed independently from
ordinary Retrieval retirement.

Each lifecycle projection item retains the historical `injected_summary` and may
overlay only the current read-only fields:

```text
current_summary
current_lifecycle_state
representation_changed
lifecycle_changed
```

`current_summary` is null for hidden or unresolved state. Mutation reasons,
tokens, internal identifiers, paths, digests, and artifact bodies are not
projected. The dedicated strict TypeScript parser remains a consumer of this
read-only versioned projection; the projection adds no mutation route or mutation
UI.

## R5 removal gate

RT-1D-R5 owns retirement of replaced Primary ordinary reader/fallback surfaces
and temporary shadow/rehearsal execution surfaces. Removal occurs only after its
exact post-transfer validation, restart/request-path proof, and negative caller
search pass.

This page deliberately does not predict which read-only Primary components will
remain after that gate. A component may survive only when a continuing accepted
historical, operational, migration, rollback, or recovery responsibility is
proved. Otherwise retirement is handled by the owning R5/R6 atomic wave and Git
history remains the recovery mechanism.

## Validation boundary

The Primary compatibility reader remains read-only. It does not recover, write,
lock for mutation, poll, repair, or retry. Prepared and partial hidden states are
ineligible, and bounded rereads reject unsafe or changed files.

Existing I-4D and Primary-recall tests/smokes remain characterization and
compatibility evidence while their owning callers still exist. RT-1 request-path
coverage additionally proves that non-`primary_only` decisions release no
Primary evidence and perform no Primary store read.
