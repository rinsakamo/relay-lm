# Crystallization Contract

Crystallization is an **off-turn semantic synthesis process**. It is not a new truth authority and is not part of the ordinary synchronous cognitive turn.

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
  ├─ memory_markdown
  └─ StateCandidate[]
        |
        +--> memory/MEMORY.md
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

The OpenAI-compatible adapter serializes only this existing input boundary. It carries:

- Identity content;
- current State records including State identity, class, key, value, sources, status, and validity fields;
- bounded Events including Event identity, type, actor, timestamp, and payload;
- prior MEMORY Markdown or `null`.

The adapter does not reinterpret these fields into a second persistence model. Event actor/provenance remains visible to the crystallizer, and prior MEMORY remains synthesis input rather than Event evidence.

## CrystallizationOutput

The current output shape is logically:

```text
memory_markdown: non-empty Markdown
state_candidates: StateCandidate[]
```

The Markdown body is the readable synthesis produced by the crystallizer. Provenance should be represented in the Markdown when the synthesis depends on specific Events or accepted State, but readable Markdown does not gain Canonical State authority merely by mentioning a source.

`StateCandidate[]` uses the existing RelayLM StateCandidate contract. The crystallizer has no privileged mutation path.

### OpenAI-compatible structured-output wire

`OpenAICompatibleCrystallizer` requests strict JSON Schema output with schema name `relaylm_crystallization_output` and exactly these top-level fields:

```json
{
  "memory_markdown": "# Memory\n...",
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

- `memory_markdown` is a non-empty string;
- `state_candidates` is an array and there is no ContinuityCandidate channel;
- each candidate contains exactly `state_class`, `key`, `op`, `value`, and `sources`;
- `state_class` must be in the current State class registry;
- `set.value` is either a string or the current exact `{semantic, degree_hint}` envelope with finite `degree_hint` in `0..1`;
- `remove.value` is `null` on the wire and is normalized to semantic `remove` without a value;
- candidate `sources` is non-empty and every source must be an Event ID present in the bounded `CrystallizationInput.events` supplied to that generation;
- State IDs, Markdown headings/locations, and prior MEMORY prose cannot become StateCandidate Event sources;
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
- when Canonical State already represents the same durable concept, a corrective proposal should reuse its exact `state_class + key` rather than inventing an alias;
- redundant durable concepts and duplicate aliases should be avoided when the evidence permits one coherent representation;
- corrective StateCandidate output is reserved for a genuinely supported change to accepted current understanding; otherwise no State candidate is required;
- Event IDs must never be invented and prior MEMORY prose must never be treated as Event evidence.

The instruction may also ask the model to emit the governed `relaylm-memory:v1` metadata convention for MEMORY units whose temporal/provenance role is supported. MEMORY metadata provenance may refer to supplied Event or State authority roots according to the metadata contract below; this is separate from the stricter StateCandidate rule that candidate `sources` are supplied Event IDs only.

This instruction is current executable provider behavior. It is **not** evidence that the prompt is already product-optimal or that a target model reliably performs all of these semantic tasks. Real-model crystallization-quality evidence and prompt/schema tuning remain separate work.

## Typed MEMORY temporal/provenance model

RelayLM defines a #1260-owned typed authority model for the temporal role and lineage of a retrievable crystallized MEMORY semantic unit.

The closed temporal domain is:

- `current` — explicitly classified as currently applicable MEMORY;
- `historical` — explicitly classified as historical/not-current MEMORY;
- `unknown` — no current/historical classification is authorized.

`unknown` is first-class. RelayLM does not derive a stronger classification from years, date literals, words such as `previous` or `formerly`, grammatical tense, heading names, or arbitrary prose.

Classified `current` or `historical` authority requires typed provenance. Provenance carries:

- a stable logical `memory_id`, independent of Markdown path/heading organization;
- a `derivation_id` identifying the semantic derivation that produced the MEMORY unit;
- one or more typed source references whose source kind is `event` or `state`.

The source vocabulary follows existing RelayLM authority roots: persisted Events are occurrence/provenance records and Canonical State is accepted current machine understanding. A Markdown path, heading, retrieval score, or fluent memory sentence is not itself a provenance source kind.

This model does not promote MEMORY into Canonical State and does not change retrieval relevance/ranking.

## Governed MEMORY metadata convention

A heading-scoped MEMORY unit may carry its typed temporal/provenance authority in one reserved HTML comment placed as the **first nonblank, non-fenced body line immediately under that heading**:

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

The parser preserves these values exactly as typed provenance. It does not synthesize Event IDs, translate Markdown locations into provenance, resolve MEMORY into Canonical State, or infer missing metadata.

An ordinary unannotated section receives typed `unknown` with no provenance. A malformed payload, unsupported metadata version, unsupported temporal scope, unsupported source kind, duplicate JSON key, or unsupported payload shape also fails closed to typed `unknown` with no provenance.

Reserved `relaylm-memory:` control comments outside the one valid metadata position are not authority. Reserved control comments are removed from the semantic MEMORY chunk so their IDs or control terms cannot affect lexical relevance or retrieved-content character accounting. The same text inside a Markdown code fence remains ordinary quoted/example content and never becomes metadata authority.

Therefore no year, date literal, `previous`, `formerly`, tense, heading wording, or other free-form lexical cue can silently produce `current` or `historical` authority.

## Governed State write-back

Candidate write-back follows the existing deterministic Validator/State engine:

- candidate source IDs must resolve to persisted Events;
- user State still requires user-authored provenance;
- unsupported classes/keys/value forms are rejected by existing rules;
- equal accepted values remain noops;
- accepted changes persist through the normal Canonical State writer.

The OpenAI-compatible adapter adds an earlier source-grounding check: a crystallization StateCandidate may cite only Event IDs that were actually supplied in that bounded crystallization input. The existing Validator remains the final authority gate and may still reject a source-grounded candidate for provenance, class, key, value, scope, or transition reasons.

Crystallization does not reinterpret Validator rejection as success and does not promote Markdown prose into State automatically.

## Markdown persistence

`memory/MEMORY.md` is optional. Missing readable memory is represented as no prior crystallized memory.

Writes use temporary-file replacement at the filesystem boundary. If the generated Markdown is byte-for-byte unchanged from the existing file, RelayLM does not rewrite it and reports `memory_changed = false`.

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
