# Crystallization Contract

Crystallization is an **off-turn semantic synthesis process**. It is not a new truth authority and is not part of the ordinary synchronous cognitive turn.

## Conceptual boundary

Selection or distillation may reduce the history and evidence that a synthesis step needs to consider. That reduction is a means; **crystallization names the durable semantic result**.

The persistent cognitive result of crystallization has two complementary forms:

- **semantic structure** — durable governed MEMORY semantic units, including their typed temporal/provenance organization, for readable and retrievable long-horizon meaning; and
- **current State** — accepted current machine understanding written only through the existing deterministic Validator / State path.

Persisted Events remain occurrence/provenance evidence. They are not replaced, promoted, or deleted merely because their meaning has been crystallized. Likewise, MEMORY structure does not become a second current-truth authority and prose does not override Canonical State.

```text
history / evidence / prior synthesis
        |
        +--> selection or distillation when needed
        |
        v
semantic synthesis
        |
        v
crystallized semantic structure + current State

Events remain evidence / provenance history.
```

In this sense, crystallization preserves what future cognition needs as **structure + State**, while retaining the underlying evidence needed to explain, validate, correct, or supersede that result.

## Current core

The current provider-agnostic orchestration is:

```text
Identity
+ Canonical State
+ bounded recent Events
+ optional prior memory/MEMORY.md
        |
        v
one off-turn Crystallizer.generate(...)
        |
        v
CrystallizationOutput
  ├─ MemoryUnit[]
  └─ StateCandidate[]
        |
        +--> RelayLM deterministic MEMORY.md renderer
                    |
                    v
              memory/MEMORY.md
        |
        +--> existing Validator / State engine
                    |
                    v
             Canonical State
```

`memory/MEMORY.md` is portable readable synthesis. `memory/state.json` remains the accepted current machine understanding, and `memory/events.jsonl` remains occurrence/provenance history.

The current OpenAI-compatible implementation of the `Crystallizer` protocol is `OpenAICompatibleCrystallizer`. It performs one non-streaming Chat Completions generation per explicit crystallization operation and returns one complete `CrystallizationOutput` or fails closed. It does not retry semantic generation automatically and does not create a second State authority path.

## CrystallizationInput

The current input contains:

- authoritative character Identity;
- current Canonical State;
- a bounded recent Event snapshot selected by count;
- optional prior `memory/MEMORY.md` content.

`max_events` defaults to 100, may be set to zero, and must not be negative. The bounded snapshot constrains what is sent to the crystallizer; it does not delete or rewrite older persisted Events.

State records may refer to Event provenance older than the recent snapshot. Candidate validation therefore checks source IDs against the full persisted Event Journal, not only the bounded crystallizer Event window.

MEMORY Event provenance uses the bounded generation boundary instead: a returned `MemoryUnit` Event source resolves only against `CrystallizationInput.events` supplied to that generation. An Event ID that exists elsewhere in the persisted Journal but was not supplied remains unresolved and receives no typed MEMORY metadata. This does not narrow the full-Journal Validator lookup used for StateCandidate provenance.

The OpenAI-compatible adapter serializes only this existing input boundary. It carries:

- Identity content;
- current State records including State identity, class, key, value, sources, status, and validity fields;
- bounded Events including Event identity, type, actor, timestamp, and payload;
- prior MEMORY Markdown or `null`.

The adapter does not reinterpret these fields into a second persistence model. Event actor/provenance remains visible to the crystallizer, and prior MEMORY remains synthesis input rather than Event evidence.

## CrystallizationOutput

The current output shape is logically:

```text
memory_units: non-empty MemoryUnit[]
state_candidates: StateCandidate[]
```

The model proposes semantic MEMORY units. Each unit contains human-readable `heading` and `content`, a closed `temporal_scope` (`current`, `historical`, or `unknown`), and typed `sources` (`event` or `state`). The model does not emit `memory_id`, `derivation_id`, or `relaylm-memory` control comments. RelayLM resolves supplied sources against canonical Event/State authority and deterministically projects the final portable Markdown. Model prose, headings, and Markdown layout are never machine identity.

`StateCandidate[]` uses the existing RelayLM StateCandidate contract. The crystallizer has no privileged mutation path.

### OpenAI-compatible structured-output wire

`OpenAICompatibleCrystallizer` requests strict JSON Schema output with schema name `relaylm_crystallization_output` and exactly these top-level fields:

```json
{
  "memory_units": [
    {
      "heading": "Preferred beverage",
      "content": "The user prefers tea.",
      "temporal_scope": "current",
      "sources": [{"kind": "state", "reference_id": "state-beverage"}]
    }
  ],
  "state_candidates": [
    {
      "state_class": "user.preference",
      "key": "tea",
      "op": "set",
      "value": "likes",
      "sources": ["event-id"]
    }
  ]
}
```

Rules:

- `memory_units` is a non-empty array; each unit contains exactly `heading`, `content`, `temporal_scope`, and `sources`;
- MEMORY unit source references are typed Event or State references. The model cannot supply persistent IDs or metadata comments;
- `state_candidates` is an array and there is no ContinuityCandidate channel;
- each candidate contains exactly `state_class`, `key`, `op`, `value`, and `sources`;
- the strict JSON Schema structurally pairs operations and values: the `set` branch permits only `op: "set"` with a string or exact degree-hint object value, while the `remove` branch permits only `op: "remove"` with `value: null`; both branches retain the existing common-field rules and `additionalProperties: false`;
- `state_class` must be in the current State class registry;
- `set.value` is either a string or the current exact `{semantic, degree_hint}` envelope with finite `degree_hint` in `0..1`;
- `remove.value` is `null` on the wire and is normalized to semantic `remove` without a value;
- candidate `sources` is non-empty and every source must be an Event ID present in the bounded `CrystallizationInput.events` supplied to that generation;
- State IDs, Markdown headings/locations, and prior MEMORY prose cannot become StateCandidate Event sources;
- duplicate JSON object members in either the upstream Chat Completions response envelope or the model-authored structured `message.content` are malformed and fail closed before field selection or semantic materialization;
- unknown top-level/candidate fields, malformed values, invalid classes, invented Event sources, invalid Chat Completions envelopes, invalid JSON, and upstream HTTP failures fail closed with `ProviderProtocolError`;
- a failed generation is not automatically retried semantically, so no partial crystallization output is returned to the existing orchestration for persistence.

The adapter reuses the existing `OpenAICompatibleDecodingConfig` and `OpenAICompatibleDecodingCapabilities` contract. Explicit supported decoding controls are carried exactly; RelayLM does not invent hidden decoding defaults.

## Long-horizon consolidation semantics

The current OpenAI-compatible crystallization instruction treats the operation as **long-horizon semantic consolidation**, not merely chronological Markdown summarization.

The executable provider instruction preserves these boundaries:

- Identity is authoritative and immutable;
- Canonical State is accepted current machine understanding, not irreversible truth;
- Events remain occurrence/provenance evidence and preserve actor authority;
- prior MEMORY is readable prior synthesis, not Event evidence or Canonical State;
- corrections, supersession, uncertainty, comparative meaning, and current-versus-historical distinctions should be preserved rather than flattened;
- assistant-authored Events do not certify user facts, preferences, goals, experiences, or external facts merely because the assistant said them;
- short-lived referents, unresolved questions, and active tasks should not become durable memory merely because they appeared recently;
- when a temporary active task or goal is explicitly completed, cancelled, or withdrawn as a future goal by later user Event evidence, do not replace it with durable semantic `completed`; if corrective State output is warranted, prefer `remove` for the exact existing `state_class + key`, preserve the Event history, and omit short-lived task mechanics from long-horizon MEMORY unless the event has independent durable significance;
- when Canonical State already represents the same durable concept, a corrective proposal should reuse its exact `state_class + key` rather than inventing an alias;
- when correcting an existing exact `state_class + key`, preserve its existing plain-string versus degree-hint representation unless current evidence materially requires new or changed comparative/intensity semantics; `degree_hint` is not confidence, evidence strength, importance, or stylistic emphasis, and categorical values that are adequately represented as strings should remain strings unless graded meaning is required;
- redundant durable concepts and duplicate aliases should be avoided when the evidence permits one coherent representation;
- corrective StateCandidate output is reserved for a genuinely supported change to accepted current understanding; otherwise no State candidate is required;
- Event IDs must never be invented and prior MEMORY prose must never be treated as Event evidence.

The instruction asks the model to propose only durable structured MEMORY units. RelayLM, not the model, emits the governed `relaylm-memory:v1` metadata convention after resolving canonical Event/State references. This is separate from the stricter StateCandidate rule that candidate `sources` are supplied Event IDs only.

This instruction is current executable provider behavior. It is **not** evidence that the prompt is already product-optimal or that a target model reliably performs all of these semantic tasks. Real-model crystallization-quality evidence and prompt/schema tuning remain separate work.

## Typed MEMORY temporal/provenance model

RelayLM defines a #1260-owned typed authority model for the temporal role and lineage of a retrievable crystallized MEMORY semantic unit. The model-facing `MemoryUnit` is a semantic proposal; `MemoryProvenance` is RelayLM-owned projected authority.

The closed temporal domain is:

- `current` — explicitly classified as currently applicable MEMORY;
- `historical` — explicitly classified as historical/not-current MEMORY;
- `unknown` — no current/historical classification is authorized.

`unknown` is first-class. RelayLM does not derive a stronger classification from years, date literals, words such as `previous` or `formerly`, grammatical tense, heading names, or arbitrary prose.

Classified `current` or `historical` authority requires typed provenance. Provenance carries:

- a stable logical `memory_id`, independent of Markdown path/heading organization;
- a `derivation_id` identifying the semantic derivation that produced the MEMORY unit;
- one or more typed source references whose source kind is `event` or `state`.

MEMORY should be organized around stable semantic units rather than transient wording or arbitrary heading choices. When current and historical aspects of one durable concept are both represented, keep their semantic units and stable logical identities coherent across updates; do not split or merge them solely because of Markdown organization.

The source vocabulary follows existing RelayLM authority roots: persisted Events are occurrence/provenance records and Canonical State is accepted current machine understanding. A Markdown path, heading, retrieval score, or fluent memory sentence is not itself a provenance source kind. A source that cannot be resolved in the supplied canonical authority fails closed to unclassified/unknown; RelayLM never guesses identity from prose similarity and does not introduce a second semantic authority.

This model does not promote MEMORY into Canonical State and does not change retrieval relevance/ranking.

## Governed MEMORY metadata convention

A heading-scoped MEMORY unit may carry its typed temporal/provenance authority in one reserved HTML comment placed as the **first nonblank, non-fenced body line immediately under that heading**. This comment is emitted only by the deterministic RelayLM renderer:

```markdown
## Preferred beverage

<!-- relaylm-memory:v1 {"memory_id":"memory-preferred-beverage","derivation_id":"derivation-2026-08-18-a","temporal_scope":"current","sources":[{"kind":"state","reference_id":"state-preferred-beverage"}]} -->
Rin prefers coffee.
```

The `v1` payload is a JSON object with exactly these fields:

- `memory_id`: non-empty stable logical MEMORY identity;
- `derivation_id`: non-empty derivation identity;
- `temporal_scope`: exactly `current`, `historical`, or `unknown`;
- `sources`: a non-empty array of objects containing exactly `kind` and `reference_id`, where `kind` is exactly `event` or `state` and `reference_id` is non-empty.

The renderer derives `memory_id` and `derivation_id` from a canonical JSON basis containing only the unit temporal scope and sorted, resolved typed source references, using SHA-256 with deterministic compact JSON. Content, heading, Markdown order, and formatting are excluded from this identity basis. A duplicate or unresolved basis receives no typed metadata. The existing retrieval parser consumes the rendered comment; it remains the sole Markdown metadata parser and does not become a parallel authority.

An ordinary unannotated section receives typed `unknown` with no provenance. A malformed payload, unsupported metadata version, unsupported temporal scope, unsupported source kind, duplicate JSON key, or unsupported payload shape also fails closed to typed `unknown` with no provenance.

Model-authored `relaylm-memory:` control comments are stripped by the renderer outside fenced code before persistence and therefore cannot become machine metadata authority. The same text inside a Markdown code fence remains ordinary quoted/example content and never becomes metadata authority. The existing parser preserves its fail-closed behavior for malformed persisted Markdown.

Therefore no year, date literal, `previous`, `formerly`, tense, heading wording, or other free-form lexical cue can silently produce `current` or `historical` authority.

## Governed State write-back

Candidate write-back follows the existing deterministic Validator/State engine:

- candidate source IDs must resolve to persisted Events;
- user State still requires user-authored provenance;
- unsupported classes/keys/value forms are rejected by existing rules;
- equal accepted values remain noops;
- accepted changes persist through the normal Canonical State writer.

The State supplied to `Crystallizer.generate(...)` is a generation snapshot, not a write lease. After the asynchronous model call completes, RelayLM reloads current Canonical State before validating any candidate. A candidate may be deterministically rebased onto that fresh State only when the active record for its exact `state_class + key` is unchanged from the generation snapshot. If that exact slot changed while crystallization was in flight, the candidate is rejected with reason `stale_state_slot`; a newer accepted value or provenance record is never replaced by the older proposal merely because the proposal arrived later.

Non-conflicting candidates are then validated in output order against the fresh State through the existing Validator. This preserves independent newer State updates while still allowing a supported crystallization proposal for an untouched slot to converge without a second model generation.

If rebased validation changes State, persistence uses the fresh State content revision as `expected_revision`. A revision mismatch before replacement raises `StateRevisionConflictError` and aborts stale write-back. RelayLM does not retry semantic generation to obtain a commit. State persistence occurs before MEMORY persistence when State changes, and the subsequent MEMORY write is itself conditioned on the State revision used for rendering. If State moves again first, stale MEMORY is not persisted.

The OpenAI-compatible adapter adds an earlier source-grounding check: a crystallization StateCandidate may cite only Event IDs that were actually supplied in that bounded crystallization input. The existing Validator remains the final authority gate and may still reject a source-grounded candidate for provenance, class, key, value, scope, transition, or stale-slot reasons.

Crystallization does not reinterpret Validator rejection as success and does not promote Markdown prose into State automatically.

## Markdown persistence

`memory/MEMORY.md` is optional. Missing readable memory is represented as no prior crystallized memory.

The renderer uses the fresh/rebased State result described above rather than the pre-generation State snapshot. Writes use temporary-file replacement at the filesystem boundary and are guarded by that State revision. If State changed after rendering, the Markdown write fails closed instead of installing synthesis against stale State authority.

If the generated Markdown is byte-for-byte unchanged from the existing file, RelayLM does not rewrite it and reports `memory_changed = false`.

This stability rule avoids needless Markdown churn on unchanged crystallization output. It does not claim semantic equivalence detection between differently worded prose.

## Ordinary-turn boundary

Crystallization is explicitly off-turn. The current OpenAI-compatible crystallizer may use an LLM, but that invocation is a separate explicit crystallization operation and not a hidden second call inside ordinary conversation.

The ordinary-turn invariant remains:

> one ordinary user turn targets exactly one cognitive LLM generation.

## Deferred work

Still owned by #1260 or its explicitly delegated evaluation owner:

- real target-model crystallization-quality evidence and evidence-backed prompt/schema tuning, coordinated with #1386 after this provider contract exists;
- richer provenance conventions for human/Obsidian presentation beyond the governed typed metadata contract;
- `memory/notes/*.md` splitting, linking, and wiki organization;
- autonomous scheduling or background crystallization policy;
- manual/external Markdown import and governed write-back;
- richer semantic idempotence/churn evaluation across differently worded but equivalent crystallizations.

Retrieval of crystallized memory into ordinary cognitive Context remains owned by #1267. The canonical `MemoryChunk` retrieval representation carries typed temporal/provenance metadata for that downstream consumer; Context Compiler authority behavior remains separately owned by #1267.
