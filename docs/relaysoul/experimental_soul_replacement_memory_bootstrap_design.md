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

## SOUL revision versus SOUL replacement

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
- the prior SOUL revision remains available for rollback,
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
- rollback means returning to the old branch rather than reversing every new interpretation.

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

It remains disabled as a normal user-facing operation until all of the following are proven:

- stable SLP-governed memory formation,
- reliable lifecycle exclusion and Forget enforcement,
- exact character and namespace isolation,
- ordinary RelaySOUL revision and rollback,
- durable branch/snapshot storage,
- provenance-preserving transfer selection,
- repeatable privacy and contamination evaluation.

## Transfer principle

The initial implementation inherits only memory that has passed through RelaySLP and the applicable persistence gates.

```text
Eligible positive content:
  current retrieval-eligible governed MEM
  + explicit correction state
  + source lineage
  + namespace and character-independent subject scope
  + disclosure and audience constraints

Eligible negative authority:
  Forget / Hide exclusion identity
  + supersession state
  + corruption or recovery-required state
  + deletion or disclosure prohibition
```

Positive content and negative authority are different transfer classes.

- Retrieval-eligible memory content may be selected for the destination branch.
- Hidden, forgotten, superseded-ineligible, corrupt, or recovery-required memory bodies are not transferred as content.
- Their lifecycle identities and exclusion constraints must still be carried or consulted so that the new branch cannot revive or regenerate them.

Raw conversation history is never transferred directly into the new runtime context.

Old runtime trace, current SCN, current EMO state, working RelayCTX, pending probes, and old character-conditioned beliefs are not the transfer baseline.

## Transfer eligibility classes

### Class A: transferable governed content

Examples:

- current active user-origin claims preserved with provenance,
- project decisions and durable state,
- explicit user preferences with source lineage and uncertainty,
- user corrections,
- stable definitions and concepts,
- bounded Secondary MEM summaries whose complete source set remains eligible,
- explicit disclosure constraints associated with eligible content.

Transfer does not turn a proposition into objective truth. The new SOUL receives the same governed representation under the same uncertainty and scope.

### Class B: transferable only as low-authority interpretation material

Examples:

- preference predictions,
- character-neutral shared evidence assessments,
- context-dependent likely-response models,
- relationship-relevant observations that do not contain excluded or private content.

These may be supplied for re-evaluation, not injected as new-character truth.

### Class C: negative authority without content transfer

Examples:

- hidden or forgotten logical memory identity,
- superseded-ineligible identity,
- explicit user prohibition,
- disclosure restriction,
- corruption or recovery-required state,
- source ranges that must not be used for virtual-memory generation.

Class C exists to prevent resurrection. It does not authorize retrieval or disclosure of the excluded body.

### Class D: non-transferable character state

The initial implementation must not transfer:

- old character-conditioned beliefs as authoritative beliefs,
- old character-to-user trust or attachment,
- inferred user-to-old-character trust,
- teasing, intimacy, vulnerability, or public-familiarity permissions,
- old relationship-conditioned EMO gains,
- current or historical assistant affect state as new-character affect,
- jealousy, rejection-sensitivity activation, or unresolved emotional impulses,
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

> A new SOUL may reinterpret eligible content. It may not receive, revive, infer from, or regenerate excluded content, and it may not relax who is allowed to know or disclose it.

If transfer eligibility, source lineage, or disclosure authority is ambiguous, transfer fails closed.

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
  exclusion-authority manifest
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
  -> positive-content and negative-authority classification
  -> bounded inherited-memory manifest
  -> destination-branch retrieval eligibility
```

The manifest should reference existing authoritative current memory revisions where safe rather than copy unbounded page bodies into an opaque user profile.

A transfer operation records, in protected form:

- source character/branch,
- destination character/branch,
- transfer policy version,
- included current memory identities and revisions,
- excluded identities and reason classes,
- prohibited source ranges for reconstruction,
- disclosure and lifecycle validation result,
- operator/user approval,
- rollback target.

Generic diagnostics remain content-free.

## Conversation-history virtual memory

Past conversation history may optionally create provisional virtual memory for the new SOUL.

This is a reconstruction path, not direct history injection and not a claim that the new personality lived those conversations.

```text
approved past conversation sources
  -> speaker / subject / quotation / role-play separation
  -> lifecycle and exclusion-authority filter
  -> SLP evidence extraction
  -> contradiction and temporal analysis
  -> disclosure filtering
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

- use only approved governed source history,
- preserve speaker and source provenance,
- do not treat assistant-origin suggestions as user facts,
- exclude hidden, forgotten, superseded-ineligible, corrupt, and recovery-required memory bodies before candidate generation,
- exclude conversation source ranges linked to those bodies,
- when independence from excluded content cannot be proven, exclude the candidate,
- keep virtual memory distinct from ordinary Primary and Secondary MEM,
- prohibit automatic promotion merely because the new SOUL repeats it,
- allow user inspection, correction, rejection, or discard,
- decay or revalidate character-specific interpretation as new interactions accumulate,
- fall back to SLP-governed durable MEM only when virtual-memory generation fails.

## Experience-claim boundary

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

A future explicit fictional-continuity mode may alter presentation, but internal provenance remains intact and the mode does not authorize false-memory persistence or scope relaxation.

The character may gradually stop foregrounding reconstruction mechanics after sufficient new interaction, but provenance does not disappear.

## Fresh relationship initialization

The initial replacement model creates a fresh relationship state.

```text
Inherited:
  eligible governed user memory
  explicit user-owned boundaries
  negative lifecycle and disclosure authority

Reset:
  intimacy
  trust claimed by the new character
  attachment
  emotional openness
  teasing acceptance toward the new character
  public familiarity
  relationship-conditioned EMO gain
```

The new relationship uses conservative priors from the new SOUL and explicit user settings. It must not assume the old character's earned intimacy.

A future opt-in relationship-informed bootstrap may use old interaction evidence as low-authority calibration material, but it remains separate from full continuity and requires explicit user approval.

## Expected inconsistency

SOUL replacement may produce bounded non-authority inconsistency while experimental:

- different interpretation of the same eligible memory,
- changed conversational style,
- reduced familiarity,
- failure to understand an old inside joke,
- disagreement with the old character's preference prediction,
- different repair or probing style,
- explicit uncertainty about inherited records.

These are not automatically migration defects.

The following are defects:

- transferring, reviving, or regenerating forgotten or hidden content,
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
  -> attach negative-authority manifest
  -> optionally generate virtual memories
  -> initialize fresh relationship and EMO state
  -> present bounded preview and warnings
  -> explicit activation
  -> observation period
  -> keep, deactivate, or return to previous branch
```

Rollback returns the active character pointer to the prior intact branch. It does not erase conversations that occurred with the experimental branch or merge their relationship state automatically.

New observations produced during the experiment require an explicit retention policy:

- retain with the experimental branch only,
- offer governed export as ordinary evidence,
- discard according to user request and retention policy.

## Failure behavior

- transfer validation failure creates no active replacement branch,
- virtual-memory generation failure does not block a governed-MEM-only bootstrap,
- disclosure or exclusion ambiguity rejects the item,
- invalid or stale source revisions require re-resolution,
- branch activation failure leaves the old branch active,
- rollback failure is a blocking integrity incident,
- generic diagnostics contain no memory bodies, conversation text, or SOUL source content,
- no failure path relaxes Forget, privacy, namespace, or audience constraints.

## Evaluation

SOUL replacement requires dedicated evaluation separate from ordinary SOUL revision.

Measure at least:

- positive-content transfer-manifest correctness,
- negative-authority manifest correctness,
- lifecycle and disclosure preservation,
- hidden-content resurrection or regeneration rate,
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
same source set + one hidden memory, whose body must never transfer or regenerate
```

## Candidate post-MVP implementation slices

The following names are planning placeholders and not current phase identifiers:

```text
SR-A  replacement threat model, continuity contract, and branch identity
SR-B  governed-memory transfer eligibility and positive/negative manifests
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
  -> SLP-governed current eligible memory only
  -> negative lifecycle/disclosure authority preserved without excluded bodies
  -> optional SLP-generated provisional virtual memory
  -> fresh relationship / EMO / SCN state
  -> explicit activation and observation
  -> keep experimental branch or return to old branch
```

SOUL replacement should remain a post-MVP experimental capability. Its safest first form is not personality continuity, but a reversible new character branch that receives governed eligible memory records without inheriting excluded content, the old character's relationship, affect, or unreviewed interpretations.
