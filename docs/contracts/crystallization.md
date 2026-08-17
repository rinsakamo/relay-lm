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

## CrystallizationInput

The current input contains:

- authoritative character Identity;
- current Canonical State;
- a bounded recent Event snapshot selected by count;
- optional prior `memory/MEMORY.md` content.

`max_events` defaults to 100, may be set to zero, and must not be negative. The bounded snapshot constrains what is sent to the crystallizer; it does not delete or rewrite older persisted Events.

State records may refer to Event provenance older than the recent snapshot. Candidate validation therefore checks source IDs against the full persisted Event Journal, not only the bounded crystallizer Event window.

## CrystallizationOutput

The current output shape is logically:

```text
memory_markdown: non-empty Markdown
state_candidates: StateCandidate[]
```

The Markdown body is the readable synthesis produced by the crystallizer. Provenance should be represented in the Markdown when the synthesis depends on specific Events or accepted State, but readable Markdown does not gain Canonical State authority merely by mentioning a source.

`StateCandidate[]` uses the existing RelayLM StateCandidate contract. The crystallizer has no privileged mutation path.

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

Crystallization does not reinterpret Validator rejection as success and does not promote Markdown prose into State automatically.

## Markdown persistence

`memory/MEMORY.md` is optional. Missing readable memory is represented as no prior crystallized memory.

Writes use temporary-file replacement at the filesystem boundary. If the generated Markdown is byte-for-byte unchanged from the existing file, RelayLM does not rewrite it and reports `memory_changed = false`.

This stability rule avoids needless Markdown churn on unchanged crystallization output. It does not claim semantic equivalence detection between differently worded prose.

## Ordinary-turn boundary

Crystallization is explicitly off-turn. Adding a Crystallizer protocol does not change the ordinary-turn invariant:

> one ordinary user turn targets exactly one cognitive LLM generation.

A future crystallizer provider may itself use an LLM, but that invocation is a separate crystallization operation, not a hidden second call inside ordinary conversation.

## Deferred work

Still owned by #1260:

- an actual OpenAI-compatible / local-model crystallizer adapter and prompt/schema contract;
- richer provenance conventions for human/Obsidian presentation beyond the governed typed metadata contract;
- `memory/notes/*.md` splitting, linking, and wiki organization;
- autonomous scheduling or background crystallization policy;
- manual/external Markdown import and governed write-back;
- richer idempotence/semantic churn evaluation.

Retrieval of crystallized memory into ordinary cognitive Context remains owned by #1267. The canonical `MemoryChunk` retrieval representation now carries typed temporal/provenance metadata for that downstream consumer; Context Compiler authority behavior remains separately owned by #1267.
