---
relaylm_doc_type: concept_policy
relaylm_authority: governed_external_source_ingestion_concept_policy
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - external-source ingestion responsibility or provenance policy changes
  - a new ingestion source class or continuous-sync boundary is accepted
  - imported-source disclosure or third-party-author policy changes
  - ingestion candidate/approval responsibilities move into an exact contract
relaylm_not_authoritative_for:
  - current implementation completion or sequencing
  - exact ingestion source enums, schemas, adapters, APIs, sync protocols, or credentials
  - exact Evidence, Shared Assessment, Subjective MEM, SOUL, or lifecycle schemas
  - direct memory or character-source mutation authority
  - email, Notion, recording, ASR, filesystem-watch, or cloud-provider implementation
  - browser upload, remote registry, or background synchronization behavior
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../memory/formation.md
  - ../memory/scene-memory-scope.md
  - ../character/identity-and-source-authority.md
  - ../attention/reflex-layer.md
  - ../post_v01_strategic_direction_vision.md
relaylm_related_contracts:
  - ../../contracts/governed-source-capture-admission.md
  - ../../contracts/governed-evidence-contract-family.md
  - ../../contracts/source-metadata-lineage-derived-artifacts.md
  - ../../contracts/shared-assessment-subjective-mem.md
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - future ingestion and source-adapter maintainers
  - Evidence, RelaySLP, RelayMEM, RelaySOUL, and Character Workspace maintainers
  - privacy, provenance, disclosure, and third-party-data reviewers
relaylm_authority_level: concept
---
# Governed External-Source Ingestion

## Authority summary

This page defines the target concept-policy for bringing **external authored material** into RelayLM without making an import adapter a new memory, SOUL, relationship, disclosure, or source-of-truth authority.

The stable conceptual pipeline is:

```text
external source
  -> source-specific capture adapter
  -> governed source / provenance boundary
  -> bounded candidate interpretation
  -> existing assessment / character-conditioned formation paths
  -> explicit approval, hold, or separately authorized commit
```

The ingestion layer owns source-class-aware capture and provenance interpretation. It does not directly write durable character truth merely because content was successfully imported.

This page is target architecture. It does not claim that generalized email, Notion, recording, continuous-sync, or other ingestion adapters are implemented.

## Problem

RelayLM already has durable character state, governed Evidence, Subjective MEM formation, Character Workspace sources, and explicit mutation/approval boundaries.

External material introduces a different risk profile from ordinary conversation:

- one file may contain many independent claims and authors;
- imported material can be stale while still looking authoritative;
- email and recordings contain third-party information by default;
- bulk import and continuous synchronization have different consistency problems;
- imported facts can feel invasive when surfaced without context;
- arbitrary external text can contain prompt injection or style-contamination material;
- a connector can accidentally become a shadow persistence authority;
- source deletion or revocation may require lineage-aware invalidation rather than ordinary memory forgetting;
- imported style or values can be mistaken for permission to rewrite SOUL.

The ingestion concept therefore separates **capture, provenance, interpretation, approval, persistence, and disclosure**.

## External source is evidence input, not character authority

An external source may provide material from which RelayLM derives governed Evidence or later candidates.

It is not, by itself:

- SOUL authority;
- SELF authority;
- relationship authority;
- scene authority;
- memory lifecycle authority;
- disclosure permission;
- a command to the character runtime;
- proof that every statement inside the source is true;
- permission to persist every extracted detail.

The central invariant is:

```text
successful import
  != accepted fact
  != accepted belief
  != accepted SOUL change
  != permission to disclose
```

## Thin source adapters

Source-specific adapters should remain thin.

Their durable responsibility is limited to source mechanics such as:

- acquiring an explicitly authorized source;
- preserving source identity and provenance needed by the governed Evidence boundary;
- reporting source-class and capture-time context through an accepted schema;
- bounding bytes/items/pages/records per operation;
- detecting source-level revision or deletion where the connector can do so reliably;
- failing closed when authorization, identity, scope, or parsing is ambiguous.

Adapters should not independently decide:

- whether extracted content becomes durable memory;
- whether an imported statement changes SOUL;
- whether a third party is trusted;
- whether content is appropriate to disclose in the current scene;
- whether contradictory information replaces existing character state;
- whether content is safe merely because it came from a known provider.

Those decisions belong to existing governed owners or to later explicit contracts.

## Source classes are policy inputs, not trust shortcuts

Different source classes have different reliability, sensitivity, update, and third-party characteristics.

Examples may include:

```text
explicit local document
personal notes or workspace page
email or message archive
structured export
recording transcript
application event history
```

These examples are conceptual categories, not a registered enum.

A source class may inform conservative defaults and review requirements. It must not create implicit trust such as:

```text
email provider authenticated
  -> every email assertion is true
```

or:

```text
local file selected by owner
  -> every statement may become SOUL
```

Source identity and semantic authority remain separate.

## Provenance survives extraction

Ingestion must preserve enough provenance to answer questions such as:

- where did this candidate originate?
- which source revision or capture event produced it?
- who authored or spoke the relevant material, when known?
- was the material explicitly authored by the primary user, authored by a third party, or mixed/ambiguous?
- is the source still authorized and current enough for the intended use?

Extraction must not collapse provenance into a text-only candidate whose origin can no longer be checked.

The exact lineage schema belongs to governed Evidence/source contracts.

## Author is independent from owner

The person who authorizes ingestion is not necessarily the author of the imported content.

This distinction is critical for:

- forwarded email;
- group messages;
- meeting transcripts;
- recordings;
- copied notes quoting another person;
- collaborative documents.

The stable policy is:

```text
owner authorized capture
  != owner authored every statement
```

Where authorship cannot be resolved safely, the system should retain uncertainty rather than silently attributing the content to the primary user.

## Third-party data requires stricter handling

Third-party material can be useful to context while also creating privacy and disclosure risk.

The ingestion layer should preserve a distinction between:

- information about the primary user;
- information authored by the primary user;
- information authored by or about another person;
- mixed or uncertain authorship.

Later formation and disclosure policy may apply stricter defaults to third-party-derived information.

No ingestion adapter may decide that third-party content is freely referenceable merely because capture was authorized.

## Imported knowledge and conversation-formed knowledge need not share disclosure defaults

A fact learned directly in a private conversation and a similar fact mined from an imported archive may have different social expectations.

A useful target distinction is:

```text
conversation-formed knowledge
  -> may be naturally referenceable under its owning scene/privacy policy

import-derived knowledge
  -> may require more conservative volunteered-disclosure policy
```

This is a policy direction, not an exact disclosure enum.

The exact future disclosure contract may distinguish source provenance more finely, but the stable rule is that ingestion provenance must remain available so such a policy is possible.

## Capture and interpretation are separate stages

A connector should be able to prove that it captured an authorized source without pretending it has already interpreted that source correctly.

The conceptual split is:

```text
capture
  -> source identity, authorization, revision, bounded raw evidence

interpretation
  -> candidate facts, events, style observations, values, relationships, or other derived structure
```

Interpretation may use deterministic parsing, local models, or other governed analyzers in future implementations.

Regardless of method, interpretation output remains a candidate until the owning downstream authority accepts it.

## Candidate routing follows semantic responsibility

Different extracted observations belong to different downstream owners.

Conceptually:

```text
facts / events
  -> Evidence / Shared Assessment / Subjective MEM candidate path

style observations
  -> character-style or SELF-related candidate path when an accepted owner exists

relationship observations
  -> RelayREL-related candidate path when authorized

scene-context observations
  -> RelaySCN-related candidate path when authorized

values or identity observations
  -> never silently rewrite SOUL
```

The ingestion layer should route candidate classes; it should not centralize every semantic decision into one broad import object.

## SOUL remains protected

Imported text can contain statements about values, identity, rules, preferences, or personality.

That does not grant autonomous SOUL mutation authority.

The durable rule is:

```text
external content
  -> may inform a reviewable candidate or explicit human proposal
  -> must not silently rewrite SOUL
```

If future ingestion supports explicit character-source revision proposals, those proposals must remain behind the existing human/source-authority boundary.

## SELF and other evolving character state still require governed formation

Dynamic character state may be more open to experience than SOUL, but ingestion must not bypass its update owner.

A future SELF, REL, GOAL, or workspace-maintenance candidate derived from import should remain:

- provenance-bound;
- reviewable or policy-gated as required by its owner;
- separate from raw source capture;
- unable to overwrite canonical source merely because extraction confidence is high.

Model confidence is not mutation authority.

## Bulk bootstrap and continuous synchronization are different systems

A bounded one-time import has a relatively simple lifecycle:

```text
capture snapshot
  -> interpret snapshot
  -> review / form candidates
  -> commit accepted outcomes
```

Continuous synchronization introduces additional responsibilities:

- source revision identity;
- incremental cursors or checkpoints;
- duplicate suppression;
- deletion/revocation handling;
- stale derived-candidate invalidation;
- contradiction between old and new source revisions;
- restart convergence;
- rate limits and backpressure;
- long-lived credential handling;
- source availability and partial failure.

Therefore:

```text
one-time import capability
  != continuous-sync authority
```

A later sync implementation requires its own bounded design/contracts instead of extending a batch importer implicitly.

## Source deletion is not ordinary Forget

If an external source is deleted, revoked, or becomes unauthorized, that event concerns source lineage and authorization.

It is not automatically equivalent to a user invoking Subjective MEM Forget on one memory item.

A later implementation must decide, under explicit authority, how source revocation affects:

- raw governed Evidence;
- derived assessments;
- Subjective MEM that depended on the source;
- rebuildable projections;
- disclosure eligibility;
- audit/recovery evidence.

The ingestion layer must preserve lineage so this decision remains possible.

## Contradiction is not last-write-wins

Continuous or repeated imports can surface claims that conflict with earlier sources or with conversation-formed knowledge.

The target policy rejects naive overwrite semantics:

```text
newer imported text
  != automatically truer character state
```

Contradiction handling belongs to the relevant assessment/formation/relationship/character owner.

The ingestion layer contributes provenance, source revision, timing, and candidate identity needed for that decision.

## Recordings require a stronger boundary

Recordings and transcripts differ from explicitly authored notes because they can contain:

- multiple speakers;
- uncertain speaker attribution;
- incidental private speech;
- third-party statements;
- ASR errors;
- background audio;
- consent constraints that differ from text import.

Accordingly, recording ingestion should remain a separate future adapter family rather than being enabled as a trivial extension of local-document import.

ASR execution is outside this concept's current implementation authority.

## Untrusted-content boundary

External source text is untrusted input even when the owner intentionally imports it.

The ingestion path must not treat embedded instructions as runtime control.

Examples of unsafe behavior include:

- executing prompt-like instructions from an imported email as system policy;
- treating markdown front matter from an arbitrary document as RelayLM config;
- following external URLs automatically without an explicit connector contract;
- accepting a document's claim that it is `SOUL.md` authority merely from filename/text;
- letting imported text select another memory or character namespace.

Parsing and candidate extraction must remain data processing under existing source and scope authority.

## Boundedness

Every ingestion surface should have explicit bounds appropriate to its source class.

Potential bounds include:

- number of source objects per invocation;
- bytes or characters per object;
- archive size and expansion ratio;
- nested attachment depth;
- number of extracted candidates;
- time window or sync page size;
- retry and rate-limit behavior;
- maximum retained request-local working state.

Exact numbers belong to later contracts or adapters.

An unbounded import loop is not justified by this concept.

## Local/private/user-owned direction

External-source ingestion should preserve RelayLM's local, private, user-owned character-data direction.

That means the architecture should not require sending personal archives to a cloud provider when a local implementation can satisfy the accepted semantic contract.

This is not a ban on every remote adapter or cloud model. It is a boundary condition:

- remote processing must be explicit;
- the source and disclosure consequences must be understandable;
- credentials remain outside generic diagnostics and character data;
- a cloud dependency must not become hidden authority over canonical character state.

## Disclosure is downstream but provenance-sensitive

Ingestion does not own final response disclosure.

However, ingestion must preserve provenance needed by later disclosure owners.

A later disclosure policy may legitimately distinguish:

- owner-authored private notes;
- third-party email;
- public imported material;
- conversation-formed memory;
- uncertain-attribution transcript evidence.

If ingestion discards that provenance, the disclosure layer cannot safely make the distinction later.

Therefore provenance preservation is an ingestion responsibility even though final disclosure is not.

## Scene and audience interaction

The canonical scene-memory policy may narrow use of imported knowledge for a particular audience.

For example, a future public/broadcast scene can be stricter about import-derived and third-party information than a private owner-only scene.

The ingestion concept does not register a broadcast scene or define its exact rules. It only ensures source provenance is preserved so RelaySCN/retrieval/disclosure policy can apply stricter audience rules later.

## Approval is a semantic boundary

An approval gate should answer a bounded question such as whether a derived candidate may advance into the next owning stage.

Approval must not be overloaded to mean all of:

- source capture consent;
- semantic truth;
- SOUL mutation;
- memory publication;
- public disclosure permission;
- continuous-sync authorization.

Those are distinct authorities and may require distinct decisions.

A future UI may present them together for usability, but server-side authority remains separated.

## No hidden background ingestion

This concept does not authorize background syncing, filesystem watching, mailbox polling, recording, or unattended capture.

A later always-on ingestion implementation must define:

- explicit enablement;
- source credentials and authorization lifecycle;
- cancellation and shutdown;
- restart checkpointing;
- bounded retry/backoff;
- user-visible state;
- revocation behavior;
- safe diagnostics.

Existing scheduler capability does not automatically authorize recurring external-source collection.

## Evaluation before widening source classes

A source adapter should be evaluated on more than extraction accuracy.

Relevant dimensions include:

- provenance preservation;
- false attribution rate;
- third-party-data handling;
- contradiction behavior;
- stale-source behavior;
- approval ergonomics;
- disclosure surprises;
- source revocation handling;
- content leakage in diagnostics;
- restart/idempotency behavior for repeated imports.

A second source class should not be added merely because the first adapter shares code with it.

## Extension sequence

The target extension direction is deliberately incremental:

```text
shared governed-ingestion concept
  -> one bounded source adapter
  -> evaluate provenance / approval / disclosure behavior
  -> refine shared contracts only from demonstrated needs
  -> add another source class
  -> continuous sync only after snapshot import semantics are stable
  -> recording/ASR only under its stronger author/consent boundary
```

This is dependency guidance inside the ingestion concept, not repository-wide execution authorization.

## Stable invariants

The ingestion concept preserves these durable invariants:

1. imported material remains provenance-bound;
2. owner authorization does not imply owner authorship;
3. capture does not imply semantic acceptance;
4. extraction confidence does not imply mutation authority;
5. source adapters remain thinner than semantic owners;
6. SOUL is not silently rewritten from imported content;
7. third-party data may require stricter disclosure defaults;
8. scene/audience policy can narrow use of imported knowledge but does not gain source authority;
9. batch import does not imply continuous-sync authority;
10. source revocation and memory Forget are distinct responsibilities;
11. imported instructions remain untrusted data;
12. generic diagnostics remain content-free and credential-free;
13. no adapter becomes a second canonical character store;
14. implementation proceeds one bounded source class at a time.

## Relationship to existing governed Evidence contracts

This concept sits above the existing governed source/Evidence contract family.

Those contracts own exact capture, admission, lineage, source metadata, and derived-artifact invariants where already defined.

This page does not redefine those fields.

Instead it states how a future family of external-source adapters must consume them:

```text
adapter-specific mechanics
  -> existing governed source/evidence boundary
  -> semantic candidate formation under existing owners
```

If ingestion needs a new exact source-class field or lineage state, that change belongs in a separately reviewed contract transaction.

## Relationship to memory formation

`docs/architecture/memory/formation.md` owns durable Subjective memory formation semantics.

Ingestion may create governed source material and candidates that later enter that path. It does not bypass Shared Assessment, character-conditioned formation, approval, publication, or lifecycle authority.

This preserves one formation owner regardless of whether evidence originated in conversation or an imported source.

## Relationship to Character Workspace

Character Workspace owns canonical character source files and approved source-authority boundaries.

An ingestion adapter may propose material that could eventually affect workspace-maintained content, but it must not directly overwrite canonical uppercase source or other protected character-authority files without the owning explicit approval workflow.

Imported archive contents are not canonical Character Workspace source merely because they are stored beside it.

## Source synthesis boundary

This concept extracts the durable generalized-ingestion direction from:

```text
docs/architecture/post_v01_strategic_direction_vision.md
```

It does not absorb that source's independent full-duplex/attention, multi-user/broadcast, persona, longitudinal-evaluation, or broad product-strategy responsibilities.

## Source-retirement boundary

This transaction does not retire the strategic source.

The source remains until its remaining independent responsibilities are either absorbed into canonical authorities or explicitly classified for Git-history retirement in a separate bounded transaction.
