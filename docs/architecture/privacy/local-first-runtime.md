---
relaylm_doc_type: concept_policy
relaylm_authority: local_first_runtime_storage_telemetry_and_namespace_privacy_policy
relaylm_status: current
relaylm_volatility: low
relaylm_owner: privacy
relaylm_update_trigger:
  - local-first storage posture changes
  - remote telemetry or external-service defaults change
  - backend destination disclosure requirements change
  - character, user, room, scene, session, memory, or cache namespace isolation policy changes
  - a deployment mode introduces new implicit cross-scope data sharing
relaylm_not_authoritative_for:
  - current repository implementation completion or sequencing
  - exact configuration fields, namespace string formats, filesystem paths, database schemas, cache keys, or deployment topology
  - exact authentication, authorization, encryption, secret-storage, retention, purge, or hosted-service contracts
  - exact memory reader/writer, relationship, scene, or character-source semantics
  - external provider privacy policy or legal compliance guarantees
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - protected-source-and-disclosure.md
  - ../system-overview.md
  - ../runtime/request-response-pipeline.md
  - ../runtime/conversation-capability-boundary.md
  - ../context/context-assembly.md
  - ../memory/storage-and-recovery.md
  - ../archive/product_runtime_hardening.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - privacy, runtime, memory, context, and deployment maintainers
  - configuration, routing, cache, and integration reviewers
  - local-first product and multi-character isolation reviewers
relaylm_authority_level: concept
---
# Local-First Runtime Privacy

## Authority summary

RelayLM treats local ownership, explicit data destinations, and scope isolation as product privacy properties rather than incidental deployment details.

The stable posture is:

```text
character and conversation data
  -> local-first by default where RelayLM owns storage
  -> explicit external destination when remote execution is configured
  -> no hidden remote telemetry
  -> no implicit cross-character / cross-user / cross-room / cross-session mixing
```

This page owns that cross-cutting privacy posture. It does not define exact storage layouts, configuration fields, namespace syntax, provider contracts, or deployment credentials.

## Local-first is the default posture, not a ban on remote backends

RelayLM may use a local or remote LLM backend depending on explicit configuration.

`local-first` means that RelayLM-owned character sources, memory, relationship state, caches, observations, and operational artifacts should not require an external persistence service merely for the base product to function.

It does not mean:

- every backend must run locally;
- remote inference is forbidden;
- every optional integration must be offline;
- local storage is automatically safe without access controls;
- data may be copied to remote services without an explicit configured purpose.

The relevant distinction is ownership and destination visibility.

## Remote execution must have an explicit destination

When a remote or hosted backend is configured, selected backend-bound context necessarily leaves the local RelayLM process.

The stable requirement is:

```text
remote backend selected
  -> destination is explicitly configured / inspectable
  -> only the request material authorized for that backend path is sent
  -> local-first storage posture does not imply backend-bound content stayed local
```

Documentation and management surfaces should not create the impression that all character or memory content remains on-device when the active backend is remote.

Exact UI/config representation belongs to the owning configuration and management contracts.

## No hidden remote telemetry

RelayLM-owned diagnostics, usage observations, traces, crash information, memory statistics, or character metadata must not be silently transmitted to a remote analytics or telemetry service merely because the runtime is online.

A future remote telemetry feature requires an explicit owning boundary that defines at least:

- what is transmitted;
- to which destination;
- under what operator/user authority;
- whether content is included;
- retention and disablement behavior;
- failure behavior.

This concept does not define such a feature.

The default assumption remains:

```text
no explicit remote telemetry authority
  -> no RelayLM-owned hidden remote telemetry
```

## Backend traffic and telemetry are different

Sending an approved request to the configured LLM backend is not the same responsibility as sending product telemetry.

The runtime must preserve this distinction:

```text
backend request
  -> required to obtain the selected model response

telemetry / analytics upload
  -> separate purpose and separate authority
```

A configured remote backend does not automatically authorize unrelated diagnostic upload to the same provider or another service.

## Namespace isolation is a privacy boundary

A single RelayLM process may serve more than one character, route, user/viewer, room, scene, or session.

Shared process ownership does not imply shared semantic scope.

Where a subsystem uses scoped data, the stable rule is:

```text
same process
  != same character scope
  != same user / viewer scope
  != same room / audience scope
  != same session scope
  != same memory namespace
  != same cache namespace
```

Cross-scope access requires an explicit validated relationship owned by the relevant subsystem.

## Namespace labels are not identity proof

A namespace or route label can help isolate data, but a string value alone must not be treated as authenticated identity or permission.

For example:

- a `character_id` identifies a configured character scope; it does not authenticate the caller;
- a viewer/user label does not prove the current transport peer is that person;
- a room or scene label does not independently establish audience authority;
- a cache namespace does not create permission to read protected character sources;
- matching textual IDs do not override a stricter relationship, scene, privacy, or access-control boundary.

Identity, authentication, authorization, and semantic scope remain separate responsibilities.

## Character isolation

Character-specific sources and derived state should not leak across characters merely because they share a backend process or model family.

Relevant state may include:

- character source projections;
- relationship state;
- scene state;
- memory;
- compiled context caches;
- instruction/context projections;
- optional retrieval/index artifacts;
- presentation or adapter configuration where it contains character-specific data.

Exact storage and cache-key mechanics belong to their owners.

The privacy invariant is that one character's protected state does not become another character's input through an implicit shared default.

## User and relationship isolation

Relationship or memory data associated with one governed target must not be silently reused for another target because both interact with the same character.

Multi-user support may require richer identity and relationship models, but absence of that implementation is not permission to collapse users together.

When exact target identity cannot be established for a feature that requires it, the safe behavior is to narrow or disable that feature rather than use a convenient global user scope.

## Room, audience, and scene isolation

Group, private, broadcast, and other scene contexts may have different disclosure and memory scopes.

A room/session identifier can participate in isolating temporary state, but disclosure authority remains with scene/privacy owners.

The stable rule is:

```text
state observed in scope A
  -> not automatically reusable in scope B
  -> explicit owning policy must permit the transition or reuse
```

A process restart, reconnect, missing room label, or cache miss must not silently broaden to an unrestricted shared scope.

## Session state is not automatically durable identity

Session-local working state may be useful for continuity within one interaction period.

It should not become a universal durable namespace merely because a caller omitted a stronger identity dimension.

Likewise, durable relationship or memory state should not be keyed only by ephemeral transport/session identity when the owning contract requires a stable subject.

This concept does not prescribe exact identifiers. It requires that volatile and durable scopes remain intentionally distinct.

## Memory and cache namespaces are separate purposes

A cache namespace exists to isolate or reuse derived/computational state under its owner.

A memory namespace exists to scope durable or governed semantic memory under its owner.

They are not interchangeable authority tokens.

```text
cache hit
  != memory eligibility

memory eligibility
  != permission to reuse a cached prompt from another scope
```

A shared cache optimization must not weaken memory, identity, or disclosure isolation.

## Prefix/KV optimization remains subordinate to privacy

Stable character prefixes and backend cache reuse may improve latency.

Optimization does not authorize cross-character or cross-user mixing.

If an optimization cannot prove that the reusable prefix belongs to the exact compatible scope, it must miss the cache rather than trade privacy for reuse.

Backend-specific KV/cache behavior remains outside RelayLM semantic authority unless an explicit integration contract says otherwise.

## Local files are still protected data

Local-first storage does not make stored content non-sensitive.

Character sources, memories, relationship state, conversation-derived artifacts, credentials, and traces may remain protected even when they never leave the machine.

Local files therefore remain subject to:

- least-content diagnostics;
- source/provenance boundaries;
- explicit mutation ownership;
- deletion/forgetting semantics where applicable;
- deployment filesystem/access-control assumptions owned elsewhere.

`local` is a destination property, not a disclosure permission.

## Clear deletion and lifecycle ownership

A local-first product should make it possible to identify the owner of durable RelayLM state and the correct lifecycle action for it.

That does not mean every local file can be safely deleted directly.

For example:

- Subjective MEM follows its lifecycle/mutation authority;
- Character Workspace sources follow source/commit authority;
- caches may be rebuildable under their owning contracts;
- protected evidence may have provenance/recovery requirements;
- credentials follow deployment/secret-management rules.

The stable requirement is **clear ownership and lifecycle**, not an ungoverned filesystem-delete shortcut.

## Diagnostics are local-first and content-minimized

Runtime diagnostics should remain content-free by default under the protected-source/disclosure architecture.

This concept adds the destination posture:

```text
default diagnostic artifact
  -> local unless another explicit authority says otherwise
  -> content-minimized under the owning diagnostic contract
```

Making diagnostics content-free does not itself authorize sending them remotely.

Likewise, keeping them local does not authorize including arbitrary protected bodies.

Both destination and content policy apply.

## Configuration visibility

An operator should be able to determine which backend or external service RelayLM is configured to use without relying on hidden code defaults or undocumented network behavior.

This does not require exposing secrets.

Useful configuration visibility may include non-secret facts such as:

- backend class or name;
- local versus remote destination class;
- enabled/disabled external integration;
- whether a feature requires network access;
- whether an optional remote service is configured.

Exact fields and redaction rules belong to configuration and management owners.

## External services do not inherit character authority

A remote inference backend, TTS service, embedding service, vector database, or future integration may receive bounded data for one purpose.

That service does not become authoritative for:

- SOUL;
- SELF;
- relationships;
- scene policy;
- memory lifecycle;
- disclosure decisions;
- runtime mutation authority.

RelayLM must not treat provider possession of data as a reason to widen later use.

## Failure must not broaden destination or scope

When local storage, a scoped cache, or a configured remote backend is unavailable, fallback must not silently switch to a broader data destination or namespace simply to keep serving.

Unsafe examples include:

- using a global memory namespace after a scoped store error;
- using another character's cache after a cache miss;
- sending data to a different remote provider without explicit route authority;
- enabling telemetry because local diagnostics storage failed;
- mixing sessions after a missing identity field.

The safe pattern is:

```text
required scope / destination unavailable
  -> use an explicitly authorized fallback if one exists
  -> otherwise narrow, miss, block, or error
```

## Hosted deployment does not erase the concept

RelayLM may eventually be deployed on a server, appliance, private cloud, or hosted environment.

The concept remains useful even when the process is not literally on the user's laptop.

`local-first` should then be interpreted as:

- RelayLM-owned persistence remains within the explicitly chosen deployment boundary by default;
- external destinations remain explicit;
- cross-tenant/cross-character/cross-user mixing is not implicit;
- hidden third-party telemetry remains disallowed without a separate authority.

Exact multi-tenant security requires its own architecture and contracts.

## Relationship to protected-source disclosure

`protected-source-and-disclosure.md` owns whether protected semantic content may be used or disclosed for a purpose/audience.

This concept owns a complementary dimension: **where RelayLM-owned state lives and whether scopes/destinations are explicit**.

The two compose:

```text
content eligible for internal use
  + destination/scope allowed
  -> eligible for that bounded processing step
```

Neither dimension can override the other.

## Relationship to runtime capability authority

Network access, filesystem access, credential access, and persistent mutation are executable capabilities under `conversation-capability-boundary.md` when RelayLM would perform them as effects.

This local-first privacy concept does not grant those effects.

It provides the privacy posture that their owning contracts must preserve.

## Relationship to ingestion

External-source ingestion may intentionally import material from a configured source.

The ingestion adapter's explicit source does not create a general remote-service permission.

Likewise, imported material that is stored locally remains provenance-bound and does not become freely shareable simply because the ingestion succeeded.

## Non-goals

This concept does not:

- require air-gapped operation;
- ban remote inference;
- define exact network allowlists;
- define authentication or encryption;
- define multi-tenant hosting;
- define exact namespace values;
- define database/file layouts;
- promise that external providers retain no data;
- replace memory lifecycle or character-source governance;
- create a remote telemetry feature.

## Durable invariants

```text
local-first != local-only
configured remote backend != hidden telemetry permission
same process != same semantic scope
namespace label != authenticated identity
cache namespace != memory authority
local storage != public content
cache reuse != privacy bypass
fallback != scope widening
external service possession != character authority
```
