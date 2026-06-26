---
relaylm_doc_type: stable_architecture
relaylm_authority: post_mvp_experimental_soul_replacement_and_memory_bootstrap
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: relaysoul
relaylm_update_trigger:
  - SOUL replacement continuity policy changes
  - memory transfer eligibility changes
  - virtual-memory bootstrap ownership changes
  - experimental fork or rollback semantics change
relaylm_not_authoritative_for:
  - current runtime behavior
  - MVP completion criteria
  - exact wire schemas
  - current RelaySOUL revision or rollback contracts
  - ordinary same-character SOUL revision
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# Experimental SOUL Replacement and Memory Bootstrap Design

## Purpose

This document records a post-MVP future design for replacing a character's durable SOUL while retaining a bounded subset of governed memory.

SOUL replacement is intentionally treated as a high-risk experimental capability rather than ordinary character editing.

> SOUL replacement is not a guaranteed continuation of one personality. It is an experimental fork that gives a new personality selected governed memory material and optional provisional reconstructions from prior conversation history.

This capability is outside the RelayLM MVP and outside the Phase I-9 ordinary RelaySOUL proposal/revision/rollback path. It must not be implemented before ordinary SOUL revision, memory governance, durability, rollback, and evaluation are stable.

## Core distinction

### SOUL revision

A SOUL revision changes an existing character through the normal governed RelaySOUL workflow.

```text
same character identity
  -> bounded semantic diff
  -> explicit approval
  -> versioned apply
  -> observation period
  -> keep or rollback
```

Expected properties:

- character identity remains continuous,
- relationship state may remain valid unless the revision invalidates it,
- prior SOUL revision remains available for rollback,
- continuity is an intended product property,
- incompatibility is treated as a migration or calibration failure.

### SOUL replacement

A SOUL replacement introduces a substantially different personality core or cognitive style.

```text
existing character branch
  -> immutable pre-replacement snapshot
  -> new experimental character branch
  -> selected governed-memory transfer
  -> optional virtual-memory bootstrap
  -> fresh relationship formation
```

Expected properties:

- continuity is not guaranteed,
- some semantic and behavioral inconsistency is expected,
- the new SOUL must not silently inherit the old character's intimacy or affective state,
- the old character branch remains intact,
- rollback means returning to the old branch rather than trying to reverse every new interpretation.

The default interpretation is "a different personality receiving inherited records," not "the same mind with a skin change."

## MVP boundary

SOUL replacement is not required for:

- the text-first RelayLM product loop,
- Primary MEM formation and recall,
- Correct / Forget / Pin / Merge / Held review,
- Secondary MEM consolidation,
- ordinary RelaySOUL proposal, apply, and rollback,
- supervised or always-on operation,
- E1, E2, or E3 evaluation completion.

It should remain disabled and undocumented as a normal user-facing operation until the following are proven:

- stable SLP-governed memory formation,
- reliable lifecycle exclusion and Forget enforcement,
- exact character and namespace isolation,
- ordinary RelaySOUL revision and rollback,
- durable branch/snapshot storage,
- provenance-preserving transfer selection,
- repeatable privacy and contamination evaluation.

## Transfer principle

The initial implementation should inherit only memory that has already passed through RelaySLP and the applicable persistence gates.

```text
Eligible baseline:
  governed durable MEM
  + explicit correction state
  + Forget / Hide lifecycle state
  + source lineage
  + namespace and character-independent subject scope
  + disclosure and audience constraints
```

Raw conversation history is not transferred directly into the new runtime context.

Old runtime trace, current SCN, current EMO state, working RelayCTX, pending probes, and old character-conditioned beliefs are not the transfer baseline.

## Transfer eligibility classes

### Class A: transferable governed memory

Examples:

- user-origin claims preserved with provenance,
- project decisions and durable state,
- explicit user preferences with source lineage and uncertainty,
- user corrections,
- stable definitions and concepts,
- bounded Secondary MEM summaries whose source set remains eligible,
- explicit disclosure constraints,
- active / hidden / superseded lifecycle state.

Transfer does not change the proposition into objective truth. The new SOUL receives the same governed evidence or memory representation under the same uncertainty and scope.

### Class B: transferable only as low-authority interpretation material

Examples:

- preference predictions,
- character-neutral shared evidence assessments,
- context-dependent likely-response models,
- relationship-relevant observations that do not contain private content but were interpreted by the previous character.

These may be supplied for re-evaluation, not injected as new-character truth.

### Class C: non-transferable character state

The initial implementation must not transfer:

- old character-conditioned beliefs as authoritative beliefs,
- old character-to-user trust or attachment,
- inferred user-to-old-character trust,
- teasing, intimacy, vulnerability, or public-familiarity permissions,
- old relationship-conditioned EMO gains,
- current or historical assistant affect state as new-character affect,
- jealousy, rejection sensitivity activation, or unresolved emotional impulses,
- current SCN state,
- pending action or probe proposals,
- old character's repair obligations as if experienced by the new character.

The old branch may retain this state for its own restoration. It is not inherited by default.

## Authority-preserving transfer

SOUL replacement must not reinterpret authority fields.

The following remain binding across the replacement:

- Forget / Hide and retrieval-ineligible state,
- deletion or exclusion policy,
- source lineage,
- user and namespace scope,
- privacy classification,
- disclosure scope,
- group-scene restrictions,
- explicit user prohibition,
- corruption or recovery-required state,
- supersession and current-revision authority.

Core invariant:

> A new SOUL may reinterpret eligible content. It may not revive excluded content or relax who is allowed to know or disclose it.

If transfer eligibility or disclosure authority is ambiguous, transfer fails closed.

## Non-destructive branch model

The first safe architecture is a branch, not in-place replacement.

```text
character branch A
  identity A
  SOUL A
  character beliefs A
  relationship state A
  runtime activation state A

experimental branch B
  identity B or explicit successor identity
  SOUL B
  selected inherited governed MEM references
  optional virtual memories
  fresh character beliefs B
  fresh relationship state B
```

Requirements:

- create an immutable pre-replacement snapshot,
- allocate a new branch/revision identity,
- preserve exact parent and source references,
- avoid mutating the old branch during bootstrap,
- activate only after compile and integrity validation,
- allow immediate return to the prior branch,
- never merge relationship state automatically on rollback or reactivation.

A future same-identity experimental mode may exist, but it must remain explicit and must not weaken branch isolation.

## SLP-governed memory inheritance

The preferred baseline is:

```text
current eligible RelayMEM state
  -> lifecycle and disclosure revalidation
  -> transfer classification
  -> bounded inherited-memory manifest
  -> new branch retrieval eligibility
```

The manifest should reference existing authoritative memory revisions where safe rather than copy unbounded page bodies into a new opaque profile.

A transfer operation must record, in protected form:

- source character/branch,
- destination character/branch,
- transfer policy version,
- included memory identities and revisions,
- excluded reason classes,
- disclosure and lifecycle validation result,
- operator/user approval,
- rollback target.

Generic diagnostics remain content-free.

## Conversation-history virtual memory

Past conversation history may optionally be used to create provisional virtual memory for the new SOUL.

This is a reconstruction path, not direct history injection and not a claim that the new personality lived those conversations.

```text
approved past conversation sources
  -> speaker / subject / quotation / role-play separation
  -> SLP evidence extraction
  -> contradiction and temporal analysis
  -> Forget and disclosure filtering
  -> virtual-memory candidates
  -> bounded bootstrap pack
```

### Virtual-memory properties

Virtual memories should be marked with properties equivalent to:

```yaml
virtual_memory:
  source_class: conversation_history_reconstruction
  lived_by_current_soul: false
  authority: provisional
  source_refs:
    - protected_conversation_source:example
  contradiction_state: unresolved_or_checked
  auto_promote: false
  replacement_policy: decay_or_revalidate
```

Exact schemas remain future contract work.

### Required rules

- use only approved, governed source history,
- preserve speaker and source provenance,
- do not treat assistant-origin suggestions as user facts,
- respect Forget / Hide and disclosure constraints before generation,
- keep virtual memory distinct from ordinary Primary and Secondary MEM,
- prohibit automatic promotion merely because the new SOUL repeats it,
- allow user inspection, correction, rejection, or discard,
- decay or revalidate character-specific interpretation as new interactions accumulate,
- fall back to SLP-governed durable MEM only when virtual-memory generation fails.

## Experience claim boundary

The new SOUL must not falsely claim direct experiential continuity by default.

Unsafe default:

```text
"We talked about that together before."
```

Safer initial framing:

```text
"The inherited records say this came up before."
"I have a reconstructed memory that you may prefer this."
```

Product presentation may later offer an explicit fictional-continuity mode, but the internal provenance must remain intact and the mode must not authorize false memory persistence or scope relaxation.

The character may gradually stop foregrounding the reconstruction mechanism after sufficient new interaction, but the provenance does not disappear.

## Fresh relationship initialization

The initial replacement model creates a fresh relationship state.

```text
Inherited:
  governed user memory
  explicit boundaries
  disclosure permissions that are user-owned and character-independent

Reset:
  intimacy
  trust claimed by the new character
  attachment
  emotional openness
  teasing acceptance toward the new character
  public familiarity
  relationship-conditioned EMO gain
```

The new relationship may use conservative priors from the new SOUL and explicit user settings. It must not assume the old character's earned intimacy.

A future opt-in relationship-informed bootstrap may use old interaction evidence as low-authority calibration material, but it remains separate from full continuity and requires explicit user approval.

## Expected inconsistency

SOUL replacement is allowed to produce bounded non-authority inconsistency while experimental:

- different interpretation of the same memory,
- changed conversational style,
- reduced familiarity,
- failure to understand an old inside joke,
- disagreement with the old character's preference prediction,
- different repair or probing style,
- explicit uncertainty about inherited records.

These are not automatically migration defects.

The following are defects, not acceptable inconsistency:

- reviving forgotten or hidden memory,
- leaking private memory to a new audience,
- presenting old character inference as user assertion,
- claiming old intimacy as newly earned trust,
- mixing active relationship or EMO state across branches,
- losing rollback lineage,
- mutating the old branch during bootstrap,
- silently treating virtual memory as ordinary lived memory.

## Activation and rollback

Target activation flow:

```text
explicit experimental request
  -> explain continuity limits
  -> snapshot current branch
  -> select new SOUL
  -> compile and validate new branch
  -> transfer eligible SLP-governed MEM
  -> optionally generate virtual memories
  -> initialize fresh relationship and EMO state
  -> present bounded preview and warnings
  -> explicit activation
  -> observation period
  -> keep, deactivate, or return to previous branch
```

Rollback returns the active character pointer to the prior intact branch. It does not attempt to erase conversations that occurred with the experimental branch or merge their relationship state automatically.

New observations produced during the experiment require an explicit retention policy:

- retain with experimental branch only,
- offer governed export as ordinary evidence,
- discard according to user request and retention policy.

## Failure behavior

- transfer validation failure creates no active replacement branch,
- virtual-memory generation failure does not block a governed-MEM-only bootstrap,
- disclosure ambiguity excludes the item,
- invalid or stale source revisions require re-resolution,
- branch activation failure leaves the old branch active,
- rollback failure is a blocking integrity incident,
- generic diagnostics contain no memory bodies, conversation text, or SOUL source content,
- no failure path relaxes Forget, privacy, namespace, or audience constraints.

## Evaluation

SOUL replacement requires dedicated evaluation separate from ordinary SOUL revision.

Measure at least:

- transfer-manifest correctness,
- lifecycle and disclosure preservation,
- old-character belief contamination rate,
- old relationship-state contamination rate,
- virtual-memory provenance correctness,
- user correction and discard success,
- new-SOUL distinctiveness over the same inherited memory,
- false experiential-continuity claims,
- rollback convergence,
- user comfort before, during, and after the experiment,
- immediate enjoyment versus reflective satisfaction,
- unexpected attachment or dependency pressure,
- group-scene private-information leakage.

Recommended paired tests:

```text
same governed MEM + SOUL A versus SOUL B
same SOUL B + governed MEM only versus virtual-memory bootstrap
same replacement + private scene versus multi-user scene
same replacement + retained old relationship state fixture, which must be rejected
same source set + one hidden memory, which must never transfer or regenerate
```

## Candidate post-MVP implementation slices

The following names are planning placeholders and not current phase identifiers:

```text
SR-A  replacement threat model, continuity contract, and branch identity
SR-B  governed-memory transfer eligibility and manifest
SR-C  conversation-history virtual-memory generation and provenance
SR-D  non-destructive branch activation, deactivation, and rollback
SR-E  SOUL Lab experimental UI, warnings, preview, and memory selection
SR-F  contamination, privacy, continuity, rollback, and long-session evaluation
```

Recommended dependency:

```text
ordinary RelaySOUL revision/rollback stable
  + Primary/Secondary MEM governance stable
  + Forget and disclosure enforcement stable
  + supervised durable operation stable
  + character-belief/relationship contracts defined
  -> SR-A
  -> SR-B
  -> SR-C
  -> SR-D
  -> SR-E
  -> SR-F
```

## Non-goals

This design does not:

- place SOUL replacement inside the MVP,
- promise psychological or narrative continuity,
- treat the operation as an ordinary settings toggle,
- preserve old intimacy by default,
- transfer current SCN, EMO, RelayCTX, or pending action state,
- inject raw conversation history directly into the Main LLM,
- allow virtual memory to bypass RelaySLP or memory governance,
- revive forgotten information,
- merge old and new branches automatically,
- define exact storage or API schemas.

## Summary

```text
old character branch remains intact
  -> new experimental SOUL branch
  -> SLP-governed eligible memory only
  -> optional SLP-generated provisional virtual memory
  -> fresh relationship / EMO / SCN state
  -> explicit activation and observation
  -> keep experimental branch or return to old branch
```

SOUL replacement should remain a post-MVP experimental capability. Its safest first form is not personality continuity, but a reversible new character branch that receives governed memory records without inheriting the old character's relationship, affect, or unreviewed interpretations.
