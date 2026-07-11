---
relaylm_doc_type: reference
relaylm_authority: canonical_documentation_and_system_vocabulary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - canonical component or documentation term changes
  - a deprecated term is removed during cutover
relaylm_not_authoritative_for:
  - exact runtime schemas
  - current implementation status
  - execution sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0002-documentation-information-architecture.md
---
# RelayLM Canonical Glossary

This reference is the draft canonical home for RelayLM documentation vocabulary. It defines stable terms used across architecture, contracts, planning, and evidence. Exact field names and runtime schemas remain authoritative in contracts and code.

## Documentation authority terms

### Active document

A current or target document used to guide implementation, operation, or interpretation. Historical evidence is not active authority.

### Authority

The bounded subject for which a document is the canonical source. A document may provide context about other subjects but must identify one primary authority.

### Authority summary

A short opening statement that says what a document is and is not authoritative for so partial retrieval does not misclassify it.

### Canonical path

The single live repository path for an authority at a given merged commit. Hard cutover does not provide dual live paths.

### Contract

A normative document containing exact schemas, fields, gates, APIs, artifacts, states, transitions, or must/must-not invariants.

### Evidence

A non-normative record of implementation, evaluation, release validation, migration, proposal disposition, or historical convergence.

### Frozen receipt

An immutable evidence record tied to a specific commit, date, checks, and result. It may receive metadata or link repairs but not rewritten conclusions.

### Hard cutover

A migration that replaces old paths and metadata without redirect stubs, legacy manifests, or permanent compatibility aliases.

### Normative block

A contract section whose exact wording defines a boundary. During cutover it is moved verbatim and verified by digest or literal-anchor checks.

### Proposal

An undecided recommendation. A proposal does not become authoritative merely because it is detailed or merged into the repository.

### ADR

An Architecture Decision Record that captures an accepted, rejected, or superseded durable decision and its consequences. Acceptance does not prove implementation.

### Retained document

A baseline document that already fits the target model and remains at the same canonical path.

### Synthesized document

A new canonical document assembled from multiple older sources after separating their authorities and granularity.

### Absorbed document

An older document whose still-valid content is incorporated into another canonical document and whose original path is removed.

### Git-history-only document

A document removed from the active tree because it has no continuing authority or evidence value beyond repository history.

## Architecture terms

### System architecture

A repository-wide or system-wide description of context, responsibility map, major flows, ownership boundaries, and system-level invariants.

### Subsystem architecture

The design of an independently changing component or service, including its inputs, outputs, lifecycle, responsibilities, and failure boundaries.

### Concept or policy design

A cross-component semantic concept or policy defined by its meaning, invariants, interactions, trade-offs, and non-goals.

### Responsibility boundary

The durable division of owned and explicitly non-owned behavior between components.

### Stable concept name

A name based on enduring product or system meaning rather than a PR number, phase, wave, or implementation slice ID.

## Lifecycle and verification terms

### Current

Implemented behavior or currently authoritative guidance.

### Target

An adopted or proposed design that is not yet fully implemented or activated.

### Historical

Non-normative evidence from a completed or superseded context.

### Frozen

A preserved record whose substantive result must not change.

### MUST check

An objective, low-false-positive audit that blocks merge or cutover completion.

### WARN check

A non-blocking quality signal used to review structure, granularity, naming, navigation, or possible staleness.

### Deferred check

A useful validation that requires post-cutover tooling and does not block the structural migration.

### Update trigger

A concrete code, contract, decision, release, or ownership change that requires a document review. It is preferred over calendar-only freshness markers.

### Verified-by relation

A conditional metadata link to a real test, script, or workflow that verifies a named boundary. Its absence is valid when no such verification exists.

## RelayLM system terms

### RelayLM

The repository-wide local conversational system and OpenAI-compatible proxy that coordinates character, memory, context, and backend-model behavior.

### Character Workspace

The file-first editable character source environment and its compiled runtime projections.

### RelayMEM

The memory subsystem responsible for governed memory artifacts, lifecycle, retrieval, and mutation boundaries.

### RelaySLP

The asynchronous analysis and formation layer that evaluates observations and produces governed candidate artifacts.

### RelayCTX

The context-selection and injection layer that assembles bounded runtime context for a request.

### RelayREL

The relationship layer that represents target-specific relationship state and relationship-conditioned interaction policy.

### RelaySCN

The scene and situation layer that represents scene knowledge, audience, and contextual behavior.

### RelayEMO

The transient affect layer that modulates reactions without independently rewriting durable identity or memory.

### RelaySOUL

The durable character identity, values, cognitive priors, and repair-style layer.

### Primary MEM

The durable governed memory path used by the current end-to-end formation, retrieval, and mutation flows.

### Protected source

Runtime-private source material retained under explicit privacy and provenance boundaries and never copied into public diagnostics or documentation.

## Deprecated vocabulary handling

Deprecated names may appear in the frozen migration receipt or in a bounded old-name table here. They must not be repeated throughout active architecture as parallel aliases.

This glossary remains a draft target until the hard cutover completes. Terms already governed by an exact contract retain that contract as the source for exact spelling and values.
