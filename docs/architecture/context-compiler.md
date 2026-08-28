# Context Compiler

The Context Compiler constructs the smallest sufficient cognitive context for the current turn **as the character**.

## Inputs

- Identity Core;
- relevant Canonical State;
- already-accepted Continuity Context when supplied;
- RelayLM-owned recent message Events used as Working Context;
- retrieved crystallized memory and targeted Event evidence when those layers are enabled;
- the current governed Event;
- minimum protocol/tool state;
- applicable audience/privacy/capability narrowing.

## Output

A bounded `CognitiveInput` object.

The durable memory model and the per-turn cognitive working set are intentionally different:

```text
Durable semantic layer
  Event Journal       what occurred / provenance
  Canonical State     accepted current understanding
  MEMORY.md / notes   crystallized long-term semantic synthesis

          ↓ selection / compilation

Per-turn cognitive layer
  Identity            protected
  Current Event       protected
  Relevant State      current accepted understanding
  Accepted Continuity accepted temporary referent/unresolved/active-task continuity
  Working Context     recent conversational continuity
  Retrieved Memory    optional long-term semantic context
  Event Evidence      targeted grounding / chronology
```

> **Persistence decides what RelayLM knows. Context selection decides what RelayLM thinks about now.**

## Authority and continuity rules

- Raw client transcript replay is not a trusted context mechanism.
- Accepted Continuity Context is temporary, non-durable continuity authority owned upstream; Context compilation may consume it but never accepts candidates, advances its lifecycle, or infers missing continuity semantics from raw language.
- Projected Continuity preserves its accepted Event sources and epistemic role without pretending that the compiler-generated projection itself was authored by the user or assistant.
- Working Context is built only from RelayLM-owned persisted Events.
- Working Context may contain both user-authored and assistant-authored dialogue and must preserve actor/source provenance.
- Assistant-authored Working Context supports conversational continuity, reference resolution, and unfinished dialogue. It does **not** prove user facts, preferences, goals, experiences, or external events merely because the assistant said them before.
- User-authored Working Context is evidence of what the user said, with the temporal and semantic limits of that utterance; prompt residence does not make it timeless external truth.
- Relevant accepted State may influence the response without being recited.
- Current-state conflicts are resolved by authority/source role before relevance ranking. A stale memory or assistant assertion cannot override active Canonical State for a current-state claim.
- Event Journal remains occurrence/provenance authority for what happened even when current State has changed.
- Retrieval and Context compilation are read/select/project operations. They never mutate Canonical State or durable memory.

> **Continuity relevance does not imply factual authority.**

## Context residency lifecycle

Context residency is distinct from semantic memory lifecycle.

```text
Semantic lifecycle
  Event → State → Crystallization → MEMORY

Context residency lifecycle
  admit → retain → downrank → evict → retrieve again
```

Eviction from Working Context means only that the material is no longer in the current cognitive working set. It does not delete the source Event, Canonical State, or crystallized memory. Older material may later re-enter Context through retrieval.

This distinction prevents token-budget pressure from becoming accidental forgetting.

## Current Working Context implementation

The first bounded Working Context slice was implemented by #1278.

Current defaults:

```text
max message Events: 6
max content chars: 4000
```

The cap applies to Working Context only. Identity, active Canonical State, and the Current Event are not evicted by this cap.

Additional rules:

- the Current Event is excluded from Working Context because it is already carried separately as `input`;
- only RelayLM-persisted user/assistant message Events are eligible;
- selected prior material is returned in chronological order;
- a normal prior `user → assistant` exchange is admitted atomically so budget pressure does not leave an orphan assistant assertion in Context;
- an unmatched user Event may be admitted by itself;
- an unmatched assistant Event is not admitted by itself;
- zero Working Context budget leaves Identity, State, and Current Event intact.

These are deterministic residency rules, not semantic truth rules.

## Current accepted Continuity projection

`compile_cognitive_input(..., continuity_context=...)` accepts an already-validated `ContinuityContext` as an optional input. This is a consumer boundary only: candidate acceptance, replacement/resolution, revision advancement, expiry, and capacity eviction remain owned by the Continuity lifecycle authority.

The current bounded projection covers all three accepted initial Continuity kinds: `referent`, `unresolved`, and `active_task`.

- accepted item order is preserved across all projected kinds;
- accepted `referent`, `unresolved`, and `active_task` items are projected before recent Event-derived Working Context;
- each item becomes a `ContextItem` whose `sources` are the accepted source Event IDs;
- `content` is a compact deterministic JSON object carrying `kind`, `key`, semantic `value`, and `epistemic_role` under a `continuity` field;
- the projection leaves `ContextItem.actor` unset because accepted Continuity is a compiler-generated typed projection, not replayed user- or assistant-authored dialogue;
- immutable Mapping/tuple semantic values are converted only to their JSON projection shape; accepted Continuity itself is not mutated;
- the Working Context Event-count and character budgets do not evict accepted Continuity items, so zero recent-message budget does not erase already-accepted referent, unresolved, or active-task continuity;
- `continuity_context=None`, or an accepted context containing no projected items, preserves the previous cognitive projection.

The compiler does not resolve references from raw language, synthesize unresolved questions, infer active tasks from dialogue, accept Continuity candidates, create a second Continuity lifecycle owner, or infer semantic redundancy with recent dialogue or Event Evidence.

On ordinary turns, Turn supplies the accepted pre-generation Continuity Context from `ContinuityRuntime.context` to this compiler input before provider generation. Continuity lifecycle acceptance remains upstream: Turn/Continuity runtime own candidate acceptance, replacement/resolution, revision advancement, expiry, and capacity; Context Compiler only consumes and projects the accepted snapshot. This realization is process-local and does not imply durable or cross-restart Continuity.

## Current relevance-first State Working Set

`compile_cognitive_input` transforms eligible Active State into a deterministic per-turn State Working Set before applying the optional `max_state_records` capacity envelope.

Eligibility is unchanged: only records with `status == "active"` and no `valid_to` are candidates. Relevance selection never mutates Canonical State, State provenance, Events, Continuity, or MEMORY.

Relevance admission runs on every turn, including when `max_state_records=None`. The initial 1.0 admission order is:

1. `user.identity` as the identity-related State anchor;
2. `self.belief` and `relationship.state` as the initial Subjective Core;
3. context-linked State whose source Events intersect selected Working Context or accepted Continuity sources, or whose bounded lexical content is relevant to those already-selected context layers;
4. direct positive lexical relevance against the Current Event.

No other State class is implicitly anchored. In particular, this does not class-anchor all user facts/preferences/goals or all `self.*` / `relationship.*` State.

Direct/context lexical evidence reuses the shared NFKC/casefold exact-token plus bounded CJK 2/3-gram feature owner. State-specific weighting remains Context Compiler authority: specific key evidence is strongest, then semantic value evidence, then State-class-tail evidence. ASCII/Latin substrings are not features, and the State admission boundary conservatively rejects a lone accidental CJK n-gram overlap unless that overlap constitutes the complete bounded field feature set.

After relevance admission:

- `max_state_records=None` projects all relevance-admitted State, not every eligible Active State;
- `max_state_records=0` explicitly projects zero State;
- if admitted State fits the cap, no unrelated record is inserted merely to fill spare capacity;
- under cap pressure, deterministic priority is identity anchor → Subjective Core → context-linked → direct lexical relevance, then stronger lexical evidence where applicable, then Canonical State order;
- after selection, records are emitted in original Canonical State order for stable/cache-friendly layout;
- anchors and Subjective Core are admission reasons, not infinite protection: both remain inside the State envelope and are evictable when the envelope cannot fit them;
- negative caps fail explicitly.

There is no zero-match fallback. A non-anchor, non-Subjective-Core, non-context-linked State with no positive lexical relevance is absent from the model-facing State projection even when spare capacity exists.

This Working Set changes only cognitive residency. The State-over-MEMORY authority filter remains independent and compares retrieved MEMORY against the **full eligible Active Canonical State set**, including records culled from the current model-facing Working Set. State persistence/lifecycle, StateCandidate schema/validation, and provenance are unchanged.

The selector is deterministic O(N) CPU work over in-RAM State. It does not call an LLM, add embeddings/vector search, create a persistent index, infer synonyms, resolve contradictions, or establish truth from relevance.

The ordinary runtime still does **not** impose a numeric default State cap unless a caller or calibrated runtime profile supplies one, but relevance admission still runs without cap pressure. #1267 owns within-State relevance semantics. The already-realized total-budget, protection, and degradation mechanics are #1387 authority; evidence-backed numeric/default calibration remains #1388 authority.

### Content-free selection diagnostics

Callers that explicitly need selection evidence may use `compile_cognitive_input_with_diagnostics`. It returns the same `CognitiveInput` produced by the ordinary compiler plus a diagnostics tuple. The ordinary `compile_cognitive_input` path does not generate or persist diagnostics.

The diagnostics surface currently covers four compiler-owned layers:

- `canonical_state` — eligible Active State count; relevance-admitted and relevance-culled counts; anchor, Subjective Core, context-linked, and lexical admission counts; final selected count; budget-evicted count; explicit record budget; and budget pressure. Relevance culling is normal Working Set hygiene and does not itself report State-budget pressure; zero-match fallback is always absent;
- `working_context` — eligible prior message count after Current Event exclusion, selected count, explicit Event-window and character budgets, selected character usage, Current Event exclusion count, Event-window eviction count, unmatched-assistant drop count, and character-budget eviction count;
- `retrieved_memory` — number of already-retrieved MEMORY chunks supplied to the compiler, number projected after the active-State authority filter, and deterministic State-shadow suppression count;
- `event_evidence` — number of already-selected Event candidates supplied to the compiler, number projected after Current Event and exact Working Context Event-ID de-duplication, Current Event exclusion count, and the count of supplied non-current Event IDs that were already resident in selected Working Context.

Accepted Continuity projection does not add a fifth diagnostics authority in this slice. `working_context` diagnostics continue to describe only recent Event-derived Working Context, and Event-Evidence exact-ID overlap diagnostics continue to compare against that selected Working Context rather than treating Continuity source provenance as duplicate dialogue residency.

Shared diagnostic fields include layer/mode, aggregate eligible/selected/evicted counts, budget unit/limit/used/pressure, plus bounded reason counters. Working Context additionally reports `character_budget_limit`, `character_budget_used`, `evicted_event_window_count`, `evicted_character_budget_count`, and `evicted_orphan_assistant_count`. Cross-layer additions remain `authority_suppressed_count`, `current_event_excluded_count`, and `redundancy_overlap_count`.

Working Context reason attribution follows the existing selector order without changing it: the Event window is applied first, unmatched assistant Events inside that window are not independently admitted, then complete exchanges are admitted newest-first under the character budget. A zero Event budget is therefore observed as Event-window eviction; with a nonzero Event budget and zero character budget, the remaining eligible window is observed as character-budget eviction. These counters describe residency mechanics only.

Diagnostics deliberately exclude State IDs, keys, values, Event IDs, MEMORY locations/content, Current Event content/ID, and other semantic payload. The Event-overlap counter compares real Event IDs internally but emits only an aggregate count and is computed from supplied Event-evidence candidates before exact overlap residency suppression. Diagnostics are observations about selection/projection mechanics, not a new truth source, persistence layer, ranking authority, or telemetry requirement.

For MEMORY and Event Evidence, `budget_limit=None` and `budget_pressure=False` mean only that the Context Compiler itself did not own the upstream retrieval budget. The compiler does **not** infer MEMORY/Event candidate populations, retrieval-stage ranking pressure, or token costs that were never provided to it. MEMORY/Event retrieval-stage diagnostics are already realized by their retrieval owners, while total serialized-budget accounting, deterministic degradation, and aggregate cross-layer budget diagnostics are #1387 authority. Evidence-backed numeric runtime/default profiles remain #1388 calibration authority.

## Current MEMORY.md retrieval and projection primitives

`select_memory_chunks` provides bounded read/select behavior over crystallized `memory/MEMORY.md` content.

Current retrieval behavior:

- parse ATX Markdown heading sections into locally complete chunks that include the section heading and direct body;
- ignore heading-looking lines inside fenced code blocks;
- retain the current heading path and expose a deterministic current-location reference such as `memory/MEMORY.md#memory/coffee`;
- disambiguate duplicate current heading locations deterministically within the document;
- use simple normalized lexical token matching, with heading matches weighted above body matches;
- select only chunks with a positive lexical match; optional crystallized memory has no zero-match fallback merely because budget remains;
- require explicit caller-supplied chunk-count and character budgets;
- never truncate a chunk to make it fit; an oversized relevant chunk is skipped and a later relevant complete chunk may still fit;
- return selected chunks in original document order after ranking/selection;
- zero budgets return no chunks and negative budgets fail explicitly.

`compile_cognitive_input(..., retrieved_memory=...)` accepts already-selected `MemoryChunk` values and projects them into a dedicated `CognitiveInput.memory` layer. The canonical `MemoryChunk` now also carries #1260/#1409-owned typed `temporal_authority`; the current `RetrievedMemoryItem` provider projection still contains only:

```text
content
location
```

This separation is intentional:

```text
Working Context sources[]      RelayLM Event provenance
MemoryChunk temporal_authority typed MEMORY temporal/provenance authority
Retrieved Memory location      current Markdown document locator
```

A memory `location` is **not** an Event ID and is **not** eligible as StateCandidate provenance. When governed MEMORY metadata is present, stable logical `memory_id`, `derivation_id`, typed Event/State source references, and `current | historical | unknown` temporal scope are carried separately on `MemoryChunk.temporal_authority`; unannotated MEMORY remains typed `unknown`.

The compiler consumes the supplied `retrieved_memory` exactly as already-selected evidence; it does not silently run broader retrieval or change its scope. Projection is read/select/project only and does not mutate `MEMORY.md`, State, Events, or indexes and does not call an LLM.

The OpenAI-compatible provider serializes this layer separately from `context` and instructs the model that crystallized memory is lower authority than active State. That instruction remains a defense-in-depth rule; RelayLM also owns a conservative deterministic State-shadow filter before projection.

### Deterministic State-shadow filtering

Before retrieved chunks become `CognitiveInput.memory`, the Context Compiler compares bounded deterministic State-addressing claims against the full eligible active Canonical State set. It consumes the upstream #1260/#1409 `MemoryChunk.temporal_authority` classification before applying current-State conflict rules.

Current filtering is intentionally narrow:

- typed `historical` MEMORY is explicitly not a current-State shadow and is retained even when its heading path or canonical `key:` / `key=` field structurally addresses an active State key with a different scalar, boolean, or reserved `{semantic, degree_hint}` value;
- typed `current` MEMORY receives no exemption from State-shadow rules: active Canonical State remains current-understanding authority for a conflicting current MEMORY claim;
- typed `unknown` MEMORY receives no historical exemption from the existing structural State-shadow rules, but it does **not** gain the typed-current free-form claim grammar and is not reclassified as current;
- the typed scope is consumed as already-validated authority. Context Compiler does not reinterpret `memory_id`, `derivation_id`, Event/State source references, or other provenance fields to create a second temporal owner;
- authority eligibility uses every State record with `status == "active"` and `valid_to is None`, independently of any later `max_state_records` projection cap;
- a non-historical MEMORY chunk is structurally State-addressing when its heading path contains every normalized lexical term of a State key, or when its body contains the canonical State key as an explicit `key:` / `key=` field assignment;
- inline field detection requires the exact normalized canonical key token and a field delimiter;
- when a non-historical chunk is State-addressing only through a **single** canonical inline `key:` / `key=` assignment for a simple `str`, `int`, or `float` State value, that assignment's same-line value receives bounded exact-leading-`not` handling: `not <active State value>` suppresses the chunk, while `not <different value>` is compatible and retains it;
- this single-inline structural negation rule applies to typed `current` and typed `unknown` MEMORY because both already participate in structural State-shadow filtering; typed `historical` remains exempt before the structural rule is reached;
- for a simple `str`, `int`, or `float` State value with **two or more** same-key canonical inline assignments and a non-addressing heading, C18 applies the same C10 exact lexical semantics to the assignment set only when every assignment has at least one normalized lexical term: an exact active-value assignment is compatible, `not <active State value>` conflicts, `not <different value>` is compatible, and any other positive lexical value different from active State conflicts;
- if any assignment conflicts in that multiple-inline simple-scalar set, the whole MEMORY chunk is suppressed; if all assignments are compatible, the chunk is retained without allowing unrelated whole-chunk current-value tokens to rescue or override the explicit assignment set;
- if even one same-key simple-scalar assignment in that set is empty or has no normalized lexical terms, C18 performs no partial interpretation and processing falls through to the existing structural rule;
- when a simple `str`, `int`, or `float` State key is addressed by **both** the heading and exactly one same-key canonical inline assignment, the heading supplies only key addressing and C19 treats the assignment as the bounded scalar claim when it has non-empty normalized lexical terms;
- in that C19 heading+single-inline scalar boundary, an exact active-value assignment is compatible, `not <active State value>` conflicts, `not <different value>` is compatible, and any other positive lexical value different from active State conflicts; a recognized assignment decides the whole chunk without unrelated whole-chunk current-value tokens rescuing or overriding it;
- an empty or non-lexical heading+single-inline scalar assignment is not partially interpreted by C19 and falls through to the existing structural rule; typed `historical` remains exempt before this rule, while typed `current` and typed `unknown` use the same structural authority boundary;
- when a simple `str`, `int`, or `float` State key is addressed by **both** the heading and **two or more** same-key canonical inline assignments, the heading again supplies only key addressing and C20 treats the assignment set as the bounded scalar claims only when every assignment has at least one normalized lexical term;
- in that C20 heading+multiple-inline scalar boundary, each assignment reuses the C18/C19 exact semantics: exact active value is compatible, `not <active State value>` conflicts, `not <different value>` is compatible, and any other positive lexical value different from active State conflicts; any conflict suppresses the whole chunk, while all-compatible assignments retain it without unrelated whole-chunk current-value rescue or override;
- if even one same-key assignment in the C20 heading+multiple scalar set is empty or non-lexical, C20 does not partially interpret the set and processing falls through to the existing structural rule; typed `historical` remains exempt before this rule, while typed `current` and typed `unknown` use the same structural authority boundary;
- for a boolean State value, the same single-inline boundary recognizes only assignment values whose normalized lexical terms are exactly `true`, `false`, `not true`, or `not false`; `not true` resolves to false and `not false` resolves to true, then a resolved mismatch suppresses the whole chunk while a match retains it without allowing unrelated whole-chunk boolean tokens to override the assignment;
- when a boolean State key is addressed by **both** the heading and exactly one same-key canonical inline assignment, the heading supplies only key addressing and that assignment alone supplies the bounded boolean value; the same exact `true`, `false`, `not true`, or `not false` interpretation decides mismatch/retention and unrelated whole-chunk boolean tokens do not override a recognized assignment;
- if that heading+single-inline boolean assignment is not exact-recognized, C16 does not reinterpret it and processing falls through to the existing conservative structural boolean rule;
- when a boolean State key is addressed by **both** the heading and **two or more** same-key canonical inline assignments, the heading again supplies only key addressing; C17 applies the bounded assignment-set rule only when every assignment value is exactly `true`, `false`, `not true`, or `not false`, suppressing on any resolved mismatch and retaining only when all resolved assignments match active State;
- if even one same-key assignment in that heading+multiple set is not exact-recognized, C17 does not partially interpret the set and processing falls through to the existing conservative structural boolean rule;
- for a boolean State value with **two or more** same-key canonical inline assignments and a non-addressing heading, the compiler applies a bounded assignment-set rule only when every assignment value is exactly `true`, `false`, `not true`, or `not false`; any resolved mismatch suppresses the whole chunk, while all resolved matches retain it without allowing unrelated whole-chunk boolean tokens to override the explicit assignments;
- if even one same-key value in that multiple-assignment boolean set is not exact-recognized, the set is not partially interpreted and processing falls through to the existing conservative structural boolean rule;
- when a non-historical chunk is State-addressing through its heading, has **no** canonical inline assignment for that key, and contains exactly one non-empty body line after its ATX section heading, a simple `str`, `int`, or `float` State value receives the same bounded exact-leading-`not` handling on that sole body line: `not <active State value>` suppresses, while `not <different value>` is compatible and retains the chunk;
- for a boolean State value, that same heading-addressed single-body boundary recognizes only sole-body values whose normalized lexical terms are exactly `true`, `false`, `not true`, or `not false`; `not true` resolves to false and `not false` resolves to true, then a resolved mismatch suppresses the whole chunk while a match retains it;
- this heading-addressed single-body structural negation rule applies to typed `current` and typed `unknown` MEMORY, while typed `historical` remains exempt before structural filtering;
- heading sections with multiple non-empty body lines remain outside the heading-single-body rule except for C33's bounded heading-only multi-line single exact-negated-reserved-pair boundary, C34's bounded heading-only multi-line multiple exact positive reserved-pair set, C35's bounded heading-only multi-line multiple exact all-negated reserved-pair set, C36's bounded heading-only multi-line mixed exact reserved-pair set, and C37's bounded heading-only multi-line single exact positive reserved-pair locality below; exact reserved-degree heading+single-inline assignment locality is bounded by C21, exact reserved-degree inline-only single-assignment locality by C22, exact reserved-degree inline-only multiple-assignment locality by C23, heading+multiple exact reserved-degree locality by C24, heading-only single-body exact reserved-pair negation by C27, inline-only multiple exact all-negated reserved-pair sets by C28, heading-addressed multiple exact all-negated reserved-pair sets by C29, inline-only multiple exact mixed reserved-pair sets by C30, heading-addressed multiple exact mixed reserved-pair sets by C31, the bounded heading-only multi-line single exact negated body claim by C33, the bounded heading-only multi-line multiple exact positive body-pair set by C34, the bounded heading-only multi-line multiple exact all-negated body-pair set by C35, the bounded heading-only multi-line mixed exact body-pair set by C36, and the bounded heading-only multi-line single exact positive body-pair locality by C37 below, while empty/non-lexical simple-scalar assignment sets beyond fallback and partially unrecognized boolean assignment sets remain outside special semantic expansion; ordinary positive heading/assignment matching and mismatch behavior is unchanged;
- temporal wording never classifies MEMORY. `current`, `currently`, `now`, year/date literals, `previous`, `formerly`, grammatical tense, and similar prose do not establish `current` or `historical` scope;
- only after upstream metadata has already classified a chunk as typed `current`, a non-structural free-form claim may address a bounded State key through exactly two line-leading forms: `current <canonical key> is <value>` or optional `the` + `<canonical key> is currently/now <value>`;
- in that typed-current free-form subset, a positive simple `str`, `int`, or `float` claim is retained when its normalized lexical terms equal active State and the whole chunk is suppressed when that positive claim differs;
- for those simple scalar State values only, a captured claim beginning with the exact leading lexical token `not` and at least one following token receives bounded free-form negation handling: `not <active State value>` suppresses the chunk, while `not <different value>` is retained rather than being treated as a positive mismatching scalar;
- the bounded exact-leading-`not` rules do not define aliases, synonyms, contractions, `never`, double-negation semantics, omitted-key inference, multi-line heading-body negation beyond C33/C35/C36's exact structural boundaries, structural heading-plus-inline overlap beyond the bounded C16/C17 boolean, C19/C20 simple-scalar, and C21/C26 reserved-degree rules above, free-form multiple-assignment negation, reserved-degree negation outside those exact structural boundaries and the C32 free-form reserved-pair boundary below, or broader natural-language negation;
- for a typed-current boolean State value in the same free-form grammar, the captured claim is recognized only when its normalized lexical terms are exactly `true`, `false`, `not true`, or `not false`; positive literals keep their ordinary boolean value, `not true` resolves to false, and `not false` resolves to true;
- after that exact boolean interpretation, a resolved value matching active State retains the chunk and a resolved value differing from active State suppresses it; therefore State=true rejects `not true` but accepts `not false`, while State=false rejects `not false` but accepts `not true`;
- boolean aliases/synonyms and non-exact negation are not inferred: `yes/no`, `enabled/disabled`, `never`, contractions, double negation such as `not not true`, composites such as `true or false` or `not true or false`, and other wording remain uninterpreted;
- for a typed-current reserved `{semantic, degree_hint}` State value in the same free-form grammar, a captured claim is recognized only when it has the explicit same-line shape `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>`;
- an explicit positive free-form reserved-degree claim is retained only when the normalized semantic terms equal the active State semantic and the parsed numeric degree exactly equals the active State degree; either recognized mismatch suppresses the whole chunk, and a matching numeric degree never rescues conflicting semantic text;
- C32 extends only this typed-current free-form reserved-pair grammar: when the captured semantic begins with exactly one leading lexical `not` followed by a non-`not` remainder, `(semantic remainder, degree)` is the negated pair; exact equality with the active `(semantic terms, degree)` pair suppresses the whole chunk, while a different semantic or degree pair is compatible and does not become a positive C8 mismatch;
- C32 evaluates all bounded free-form claim lines for the State key, so a compatible negated pair does not hide a later positive conflict or exact active-pair negation, and a positive match does not hide a later exact active-pair negation;
- a bare `not` semantic or double-leading `not` such as `not not likes` gains no C32 negation meaning and remains uninterpreted rather than being reinterpreted by C8 as an ordinary positive semantic mismatch; missing degree, non-exact reserved syntax, aliases/synonyms, `never`, contractions, composites, degree ordering/tolerance/cross-axis comparison, natural-language intensity, and broader NLP remain outside C32;
- missing `degree_hint`, arbitrary prose numbers, natural-language intensity wording, degree ordering/tolerance, and other non-reserved degree expressions are not inferred by the free-form rule;
- if multiple recognized free-form claim lines address the same State key, any explicitly recognized conflicting positive scalar, exact scalar negation, boolean, positive reserved-degree claim, or C32 exact active-pair negation suppresses the whole chunk; compatible C32 negations do not prevent later recognized claims from being evaluated;
- the words `current`, `currently`, and `now` in those two forms are claim syntax only. They supply no temporal authority and the same wording on typed `unknown` MEMORY does not activate this free-form rule;
- an unannotated non-structural sentence such as `Current residence location is Hokkaido.` therefore remains temporally `unknown` and is retained by this free-form rule even when active State differs;
- prefix and key boundaries remain conservative: `Previous current residence location is Hokkaido.` is outside the bounded free-form grammar, and `Rin currently lives in Hokkaido.` does not infer the canonical key `residence_location`;
- prose appearance never overrides typed scope: typed historical MEMORY remains historical even if its wording sounds current, while typed unknown MEMORY is not inferred historical from dates, `previous`, `formerly`, or tense;
- outside that typed-current explicit positive-or-C32-negated reserved-degree pair, reserved `{semantic, degree_hint}` State values continue to use the existing explicitly State-addressing structural rules for non-historical MEMORY;
- for a reserved `{semantic, degree_hint}` State key addressed by both the heading and exactly one same-key canonical inline assignment, C21 positively recognizes the assignment only when its complete value has the exact reserved shape `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>`; the assignment semantic must match active State by normalized lexical terms and its parsed degree must exactly equal active State, otherwise the whole non-historical chunk is suppressed;
- a matching C21 assignment does not weaken C1: every other explicit numeric `degree_hint:` / `degree_hint=` in the heading-owned section remains associated with that key and any stale section degree still suppresses; non-exact assignment values remain under existing C1 fallback, while inline-only exact reserved locality is owned separately by C22/C23 and heading+multiple exact reserved locality is owned separately by C24;
- for a reserved `{semantic, degree_hint}` State key addressed only by exactly one same-key canonical inline assignment under a non-addressing heading, C22 recognizes that assignment only when its complete value has the exact reserved shape `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>`;
- within that C22 boundary, the assignment semantic must match active State by normalized exact lexical terms and its degree must exactly equal active State; either mismatch suppresses the whole non-historical chunk, and unrelated whole-chunk current-semantic text cannot rescue the conflicting explicit same-key assignment;
- C22 is the positive inline-only single exact-reserved-pair rule; a matching C22 assignment does not short-circuit C1 whole-chunk semantic or same-line degree checks, and non-exact exactly-one values remain outside C22 local interpretation;
- at the same inline-only exactly-one structural boundary, C25 recognizes only an exact reserved pair whose normalized semantic terms begin with exactly one lexical `not` followed by a non-`not` remainder; it treats `(semantic remainder, degree)` as the negated reserved pair;
- C25 suppresses the whole chunk when that negated pair exactly equals the active `(semantic terms, degree)` pair; when either semantic or degree differs, the negation is compatible for this State record and skips the older C1 positive semantic/degree fallback rather than allowing that fallback to reinterpret the negation as an active-pair conflict;
- C25 applies structurally to typed `current` and typed `unknown` MEMORY, while typed `historical` remains exempt before structural filtering; it does not interpret heading-addressed reserved-degree negation (C26/C27/C33/C35/C36 below) or multiple-assignment reserved-degree sets (C23/C28/C30 inline-only and C24/C29/C31 heading-addressed); typed-current free-form exact reserved-pair negation is owned separately by C32, while bare or double negation, `never`, contractions, aliases/synonyms, composites, non-exact reserved syntax, degree ordering/tolerance/cross-axis comparison, natural-language intensity, and broader NLP remain outside C25;
- for a reserved `{semantic, degree_hint}` State key addressed by both the heading and exactly one same-key canonical inline assignment, C26 extends the C21 boundary to recognize exactly one leading lexical `not` followed by a non-`not` semantic remainder; it activates only when the assignment is an exact reserved pair and the heading-owned section has exactly one explicit `degree_hint:` / `degree_hint=` assignment, namely the inline assignment itself;
- within C26, `(semantic remainder, degree)` is the negated reserved pair: exact equality with active `(semantic terms, degree)` suppresses the whole chunk, while a different semantic or degree pair is compatible for this State record and skips the older C1 positive semantic/degree fallback;
- C26 preserves C1/#1364 section-wide degree authority: any additional heading-owned explicit degree disables the local compatible-negation decision and falls through to existing C1 checks. C26 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt, and no temporal NLP is added. Heading-only single-body reserved-degree negation is owned separately by C27 below, heading-only bounded multi-line single-negated-pair authority by C33 below, heading-only bounded multi-line multiple-positive-pair authority by C34 below, heading-only bounded multi-line multiple-all-negated-pair authority by C35 below, heading-only bounded multi-line mixed exact-pair authority by C36 below, heading-only bounded multi-line single-positive-pair locality by C37 below, inline-only multiple all-negated reserved-pair sets by C28, inline-only multiple mixed exact sets by C30, heading-addressed multiple all-negated sets by C29, and heading-addressed multiple mixed exact sets by C31. Typed-current free-form exact reserved-pair negation is owned by C32; bare/double negation, non-exact syntax, aliases/synonyms, composites, natural-language intensity, ordering/tolerance/cross-axis comparison, and broader NLP remain deferred;
- for a reserved `{semantic, degree_hint}` State key addressed by the heading with **no** same-key canonical inline assignment, C27 recognizes the sole non-empty body line of the ATX section when that whole line is an exact reserved pair `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>` whose normalized semantic terms begin with exactly one leading lexical `not` followed by a non-`not` remainder;
- within C27, `(semantic remainder, degree)` is the negated reserved pair: exact equality with the active `(semantic terms, degree)` pair suppresses the whole chunk, while a different semantic **or** a different degree makes the negation compatible for this State record and skips the older C1 positive semantic/degree fallback. This is pair-level negation, so `not likes; degree_hint: 0.65` against active `likes` at `0.85` negates a different pair and is compatible;
- C27 requires exactly one non-empty body line and a whole-line exact reserved pair, so no additional heading-owned section-degree guard is needed; positive heading-only reserved pairs are not redefined by C27 and remain under existing C1/#1364 authority;
- C27 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering, and no temporal or currentness NLP is added. C33 below owns the bounded multi-line heading-body case with exactly one exact negated reserved-pair body line and no additional section degree; C37 below owns the bounded multi-line heading-body case with exactly one exact positive reserved-pair body line and no additional section degree; C34 below owns the bounded multiple exact positive body-pair set; C35 below owns the bounded multiple exact all-negated body-pair set; C36 below owns the bounded mixed exact positive+single-negated body-pair set; other heading-body reserved-degree forms and any same-key inline assignment boundary remain outside C27. Typed-current free-form exact reserved-pair negation is owned separately by C32. Bare `not`, double negation such as `not not likes`, `never`, contractions, aliases/synonyms, composites, omitted-key inference, non-exact reserved syntax, natural-language degree/intensity, degree ordering/tolerance/cross-axis comparison, and broader NLP remain deferred to existing authority and fallback;
- for a reserved `{semantic, degree_hint}` State key addressed only by two or more same-key canonical inline assignments under a non-addressing heading, C23 interprets the assignment set only when every complete value has the exact reserved shape `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>` and no parsed semantic begins with the exact leading lexical token `not`;
- within an activated C23 set, every assignment's normalized semantic terms and exact numeric degree must match active State; any mismatch suppresses the whole non-historical chunk and cannot be rescued by unrelated current-semantic prose elsewhere in the chunk;
- when all activated C23 assignments match, processing continues through the existing C1 whole-chunk semantic and same-line degree checks rather than retaining solely because of C23; if any assignment is non-exact, C23 makes no partial set decision and the whole set falls through to C1. C23 is the inline-only multiple exact **positive** reserved-pair set owner; the complementary inline-only multiple exact **all-negated** set is C28 and the exact **mixed positive+negated** set is C30 below;
- for a reserved `{semantic, degree_hint}` State key addressed by both the heading and two or more same-key canonical inline assignments, C24 applies the same exact assignment-set boundary as C23: every complete value must be an exact reserved pair and no parsed semantic may begin with exact leading lexical `not`;
- within an activated C24 set, every assignment's normalized semantic terms and exact numeric degree must match active State; any mismatch suppresses the whole non-historical chunk and unrelated current-semantic text in the heading-owned section cannot rescue it;
- all matching C24 assignments continue through C1 rather than retaining early, so the existing heading-owned section-wide degree check can still suppress; if any member is non-exact, C24 makes no partial set decision and falls through to C1; a heading-addressed set whose members all begin with exact leading `not` is owned by C29 below, while an exact mixed positive+single-negated set is owned by C31 below;
- for a reserved `{semantic, degree_hint}` State key addressed only by two or more same-key canonical inline assignments under a non-addressing heading, C28 interprets the assignment set as an **all-negated** reserved-pair set only when every complete value is an exact reserved pair `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>` **and** every parsed semantic begins with exactly one leading lexical `not` followed by a non-`not` remainder;
- within an activated C28 set, each member's `(semantic remainder, assignment degree)` is that member's negated reserved pair and is compared exactly against the active `(semantic terms, degree)` pair: if **any** member negates the exact active pair, the whole non-historical chunk is suppressed;
- if **every** member negates a different reserved pair, the all-negated set is compatible for this State record and skips the older C1 positive semantic/degree fallback rather than letting that fallback reinterpret the negations as an active-pair conflict;
- C28 compatibility is pair-level, so degree is part of the identity of the negated target: `not likes; degree_hint: 0.65` against active `likes` at `0.85` negates a different pair and is compatible, and it is not collapsed to semantic-only negation;
- C28 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering, and no temporal or currentness NLP is added;
- C28 does not redefine C23 or C30. If any member is positive, C28 itself makes no all-negated set decision; an exact mixed positive+single-negated set under a non-addressing heading is owned by C30 below. Any non-exact, bare `not`, double-negated such as `not not likes`, or otherwise unrecognized member prevents both C28 and C30 partial interpretation and leaves the set on existing fallback authority. Heading-addressed multiple all-negated reserved-pair sets are owned separately by C29;
- for a reserved `{semantic, degree_hint}` State key addressed by **both** an ATX heading and two or more same-key canonical inline assignments, C29 is the heading-addressed complement of C28: it interprets the assignment set as an **all-negated** reserved-pair set only when every complete value is an exact reserved pair `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>` **and** every parsed semantic begins with exactly one leading lexical `not` followed by a non-`not` remainder;
- because the heading addresses the key, the existing C1/#1364 section-wide explicit degree authority owns the whole section, so C29 additionally requires that the heading-owned section carry **no additional explicit `degree_hint:` / `degree_hint=` assignment** beyond the one inside each same-key inline assignment: the section-wide explicit-degree count must exactly equal the same-key assignment count;
- within an activated C29 set, each member's `(semantic remainder, assignment degree)` is that member's negated reserved pair and is compared exactly against the active `(semantic terms, degree)` pair: if **any** member negates the exact active pair, the whole non-historical chunk is suppressed;
- if **every** member negates a different reserved pair, the all-negated set is compatible for this State record and skips the older C1 positive semantic/degree fallback rather than letting that fallback reinterpret the negations as an active-pair conflict;
- C29 compatibility is pair-level, so degree is part of the identity of the negated target: `not likes; degree_hint: 0.65` against active `likes` at `0.85` negates a different pair and is compatible;
- if any additional heading-owned explicit degree exists, C29 makes **no local set decision** — it neither suppresses nor marks the set compatible — and the existing C1/#1364 heading-owned whole-section semantic and degree checks remain decisive. This holds even when one inline member negates the exact active pair, so the section-degree-count guard is evaluated before any active-pair conclusion;
- C29 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering, and no temporal or currentness NLP is added;
- C29 does not redefine C24, C28, C26, C27, C30, or C31. If any member is positive, C29 itself makes no all-negated set decision; heading-addressed exact mixed positive+negated sets are owned by C31 below, while inline-only exact mixed sets are owned by C30 below. Non-exact, bare `not`, double-negated, and broader wording remain on existing fallback authority;
- for a reserved `{semantic, degree_hint}` State key addressed only by two or more same-key canonical inline assignments under a non-addressing heading, C30 interprets a genuinely **mixed positive+negated** assignment set only when every complete value is an exact reserved pair `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>`, at least one parsed semantic is positive, and at least one parsed semantic begins with exactly one leading lexical `not` followed by a non-`not` remainder;
- within an activated C30 set, each positive member denotes `(semantic terms, assignment degree)` and is compatible only when that exact pair equals the active `(semantic terms, degree)` pair; each negated member denotes `(semantic terms after the single leading not, assignment degree)` and conflicts only when that exact negated pair equals the active pair;
- therefore any positive pair mismatch or any exact active-pair negation suppresses the whole non-historical chunk. If every positive member matches and every negated member targets a different semantic or degree pair, the recognized mixed set is compatible and skips older C1 positive semantic/degree reinterpretation;
- C30 comparison is pair-level for both polarities, so degree is part of identity: `likes; degree_hint: 0.85` plus `not likes; degree_hint: 0.65` is compatible against active `likes` at `0.85`, while the same negation at `0.85` suppresses;
- C30 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering, and no temporal/currentness NLP is added;
- C30 does not redefine C23 positive-only, C28 all-negated, or the exactly-one C22/C25 boundaries. If any member is non-exact, bare `not`, double-negated such as `not not likes`, or otherwise outside the exact positive-or-single-negated grammar, C30 makes no partial decision and the whole set falls through to existing authority. Heading-addressed exact mixed positive+negated reserved-pair sets are owned by C31 below; aliases/synonyms, `never`, contractions, composites, omitted-key inference, natural-language degree/intensity, degree ordering/tolerance/cross-axis comparison, and broader NLP are not inferred;
- for a reserved `{semantic, degree_hint}` State key addressed by **both** an ATX heading and two or more same-key canonical inline assignments, C31 is the heading-addressed complement of C30: it interprets a genuinely **mixed positive+negated** assignment set only when every complete value is an exact reserved pair `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>`, at least one parsed semantic is positive, and at least one parsed semantic begins with exactly one leading lexical `not` followed by a non-`not` remainder;
- because the heading addresses the key, C31 preserves C1/#1364 section-wide explicit-degree authority exactly as C29 does: the heading-owned section may contain no additional explicit `degree_hint:` / `degree_hint=` beyond the one inside each same-key assignment, so the section-wide explicit-degree count must exactly equal the same-key assignment count before C31 makes any local decision;
- within an activated C31 set, each positive member denotes `(semantic terms, assignment degree)` and is compatible only when that exact pair equals the active `(semantic terms, degree)` pair; each negated member denotes `(semantic terms after the single leading not, assignment degree)` and conflicts only when that exact negated pair equals the active pair;
- therefore any positive pair mismatch or any exact active-pair negation suppresses the whole non-historical chunk. If every positive member matches and every negated member targets a different semantic or degree pair, the recognized mixed set is compatible and skips older C1 positive semantic/degree reinterpretation;
- C31 comparison is pair-level for both polarities, so degree is part of identity: against active `likes` at `0.85`, `likes; degree_hint: 0.85` plus `not likes; degree_hint: 0.65` is compatible, while the same negation at `0.85` suppresses;
- if any additional heading-owned explicit degree exists, C31 makes **no local set decision** — no positive mismatch suppression, no active-pair-negation suppression, and no compatible-set `continue` — and processing falls through unchanged to C1/#1364. This guard is evaluated before every local C31 pair conclusion, so for example a local `not likes; degree_hint: 0.85` plus an additional section `degree_hint: 0.85` remains for C1/#1364 to retain when active semantic and all section degrees match;
- C31 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering, and no temporal/currentness NLP is added;
- C31 does not redefine C24 positive-only, C29 all-negated, C30 inline-only mixed, or the existing exactly-one/heading-only owners. If any member is non-exact, bare `not`, double-negated such as `not not likes`, or otherwise outside the exact positive-or-single-negated grammar, C31 makes no partial decision and the whole set falls through to existing authority. Typed-current free-form exact reserved-pair negation is owned separately by C32; bounded heading-only multi-line single-negated body authority is owned separately by C33 below; bounded heading-only multi-line single-positive body-pair locality is owned separately by C37 below; bounded heading-only multi-line multiple-positive body-pair authority is owned separately by C34 below; bounded heading-only multi-line multiple-all-negated body-pair authority is owned separately by C35 below; bounded heading-only multi-line mixed exact body-pair authority is owned separately by C36 below; aliases/synonyms, `never`, contractions, composites, omitted-key inference, natural-language degree/intensity, degree ordering/tolerance/cross-axis comparison, and broader NLP remain deferred;
- for a reserved `{semantic, degree_hint}` State key addressed by the heading with **no** same-key canonical inline assignment and at least two non-empty body lines, C33 activates only when exactly one body line is a whole-line exact reserved pair `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>` whose normalized semantic begins with exactly one lexical `not` followed by a non-`not` remainder;
- C33 preserves C1/#1364 section-wide degree authority by requiring the entire heading-owned section to contain exactly one explicit `degree_hint:` / `degree_hint=` assignment — the one inside that exact negated body-line claim. Any additional explicit degree disables C33 completely before any active-pair conclusion and leaves the existing C1/#1364 whole-section checks decisive;
- within an activated C33 boundary, `(semantic remainder, degree)` is the negated reserved pair: exact equality with active `(semantic terms, degree)` suppresses the whole non-historical chunk, while a different semantic or degree pair is compatible for this State record and skips older C1 positive semantic/degree reinterpretation;
- other non-empty C33 body lines are degree-free prose only for this bounded decision: they do not become additional reserved-pair claims and cannot rescue an exact active-pair negation merely by repeating the active semantic. Positive reserved-pair body lines are not redefined by C33; the bounded exactly-one positive multi-line locality is owned by C37 below, while other positive forms remain under their existing owners/fallback;
- C33 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering. The exactly-one positive multi-line body-pair locality is owned by C37 below; multiple exact positive body-pair claims are owned by C34 below; multiple exact all-negated body-pair claims are owned separately by C35 below; mixed positive+negated multi-line body-pair sets are owned by C36 below; any additional section degree outside the bounded owner guards, bare/double/non-exact negation, aliases/synonyms, `never`, contractions, composites, omitted-key inference, natural-language degree/intensity, degree ordering/tolerance/cross-axis comparison, and broader NLP remain on existing fallback/deferred authority;
- for a reserved `{semantic, degree_hint}` State key addressed by the heading with **no** same-key canonical inline assignment and at least two non-empty body lines, C37 activates only when exactly one body line is a whole-line exact reserved pair `<semantic>; degree_hint: <number>` or `<semantic>; degree_hint=<number>` whose normalized semantic terms do **not** begin with `not`;
- C37 preserves C1/#1364 section-wide degree authority by requiring the entire heading-owned section to contain exactly one explicit `degree_hint:` / `degree_hint=` assignment — the one inside that exact positive body-line claim. Any additional explicit degree disables C37 completely before any local pair conclusion and leaves existing C1/#1364 whole-section checks decisive;
- within an activated C37 boundary, the explicit positive `(semantic terms, degree)` pair must exactly equal the active `(semantic terms, degree)` pair. A semantic or degree mismatch suppresses the whole non-historical chunk even when degree-free prose elsewhere in the section contains the active semantic;
- when the C37 pair exactly matches active State, C37 does **not** retain early; processing continues through existing C1/#1364 whole-section checks. Other non-empty body lines are degree-free prose for this bounded decision and are not promoted to reserved-pair claims;
- C37 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering. The exactly-one negated multi-line body-pair case remains C33 authority, while two-or-more exact body-pair sets remain C34/C35/C36 according to polarity. Bare/double/non-exact negation, non-exact reserved syntax, aliases/synonyms, `never`, contractions, composites, omitted-key inference, natural-language degree/intensity, degree ordering/tolerance/cross-axis comparison, and broader NLP remain on existing fallback/deferred authority;
- for a reserved `{semantic, degree_hint}` State key addressed by the heading with **no** same-key canonical inline assignment and at least two whole-line exact reserved-pair body claims, C34 interprets the body-pair set only when every parsed exact body-pair semantic is positive — its normalized lexical terms do not begin with `not`;
- C34 preserves C1/#1364 section-wide degree authority by requiring the entire heading-owned section to contain exactly as many explicit `degree_hint:` / `degree_hint=` assignments as there are exact body-pair claims. Any additional or non-exact degree-bearing body text disables C34 before any local pair conclusion and leaves C1/#1364 fallback unchanged;
- within an activated C34 set, every positive `(semantic terms, degree)` pair must exactly equal the active `(semantic terms, degree)` pair. Any semantic or degree mismatch suppresses the whole non-historical chunk, so one matching positive pair cannot hide another explicit positive mismatch through C1 whole-section semantic presence;
- if every activated C34 pair matches active State, C34 does **not** retain early; processing continues through existing C1/#1364 whole-section checks. Degree-free body prose is not promoted to a C34 claim and does not alter pair identity;
- C34 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering. Any exact body-pair semantic beginning with lexical `not` leaves the body outside C34 positive-only ownership; all-negated exact sets are owned by C35 below and mixed positive+negated exact sets by C36 below. Exactly-one positive multi-line body-pair locality is owned by C37 above. Bare/double/non-exact negation, aliases/synonyms, `never`, contractions, composites, omitted-key inference, natural-language degree/intensity, degree ordering/tolerance/cross-axis comparison, and broader NLP remain on existing fallback/deferred authority;
- for a reserved `{semantic, degree_hint}` State key addressed by the heading with **no** same-key canonical inline assignment and at least two whole-line exact reserved-pair body claims, C35 interprets the body-pair set only when every parsed exact body-pair semantic begins with exactly one leading lexical `not` followed by a non-`not` remainder;
- C35 preserves C1/#1364 section-wide degree authority by requiring the heading-owned section-wide explicit `degree_hint:` / `degree_hint=` count to exactly equal the exact body-pair claim count. Any additional heading-owned explicit degree, including non-exact degree-bearing body text, disables C35 before any local pair conclusion and leaves existing C1/#1364 fallback decisive;
- within an activated C35 set, each member's `(semantic terms after the single leading not, degree)` is a negated reserved pair. If any member exactly equals the active `(semantic terms, degree)` pair, the whole non-historical chunk is suppressed; if every negated pair differs by semantic or degree, the recognized set is compatible for this State record and skips older C1/#1364 positive semantic/degree reinterpretation;
- C35 comparison is pair-level, so degree is part of negated target identity: `not likes; degree_hint: 0.65` is compatible against active `likes` at `0.85`, while `not likes; degree_hint: 0.85` suppresses. Degree-free body prose is not promoted to a C35 claim and cannot rescue an exact active-pair negation;
- C35 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering. C35 does not redefine C33's single exact-negated body claim or C34's positive-only body-pair set. Mixed positive+negated multi-line body-pair sets are owned by C36 below, and any bare `not`, double-leading `not`, non-exact reserved syntax, aliases/synonyms, `never`, contractions, composites, omitted-key inference, natural-language degree/intensity, degree ordering/tolerance/cross-axis comparison, and broader NLP remain on existing fallback/deferred authority;
- for a reserved `{semantic, degree_hint}` State key addressed by the heading with **no** same-key canonical inline assignment and at least two whole-line exact reserved-pair body claims, C36 interprets the body-pair set only when every exact member is either positive or begins with exactly one leading lexical `not` followed by a non-`not` remainder, and the set contains at least one member of each polarity;
- C36 preserves C1/#1364 section-wide degree authority by requiring the heading-owned section-wide explicit `degree_hint:` / `degree_hint=` count to exactly equal the exact body-pair claim count. Any additional heading-owned explicit degree, including non-exact degree-bearing body text, disables C36 before any local pair conclusion and leaves existing C1/#1364 fallback decisive;
- within an activated C36 set, every positive `(semantic terms, degree)` pair must exactly equal the active `(semantic terms, degree)` pair, while each single-leading-`not` member denotes a negated `(semantic remainder, degree)` pair that conflicts only when it exactly equals the active pair. Any positive mismatch or exact active-pair negation suppresses the whole non-historical chunk;
- if every positive C36 member matches active State and every negated member targets a different semantic or degree pair, the recognized mixed set is compatible and skips older C1/#1364 positive semantic/degree reinterpretation. Degree remains part of pair identity for both polarities, so `likes; degree_hint: 0.85` plus `not likes; degree_hint: 0.65` is compatible against active `likes` at `0.85`;
- C36 applies structurally to typed `current` and typed `unknown` MEMORY; typed `historical` remains exempt before structural filtering. Degree-free body prose is not promoted to a C36 member. Bare `not`, double-leading `not`, non-exact reserved syntax, aliases/synonyms, `never`, contractions, composites, omitted-key inference, natural-language degree/intensity, degree ordering/tolerance/cross-axis comparison, and broader NLP remain on existing fallback/deferred authority;
- for State values handled by the structural heading/field rule, the non-historical chunk is retained if at least one current State value appears as an exact lexical token sequence in the chunk, except for the bounded single-inline, multiple-inline simple-scalar, heading+single-inline simple-scalar, heading+multiple-inline simple-scalar, heading+single-inline exact-boolean, heading+multiple-inline exact-boolean, multiple-inline exact-boolean, heading+single-inline and heading+multiple exact-reserved-degree, inline-only single and multiple exact-reserved-degree, heading+single-inline and heading-only single-body exact-reserved-degree negation, heading-only C33 multi-line single exact-negated reserved-pair authority, heading-only C37 multi-line single exact-positive reserved-pair locality, heading-only C34 multi-line multiple exact-positive reserved-pair authority, heading-only C35 multi-line multiple exact-all-negated reserved-pair authority, heading-only C36 multi-line mixed exact reserved-pair authority, inline-only/heading-addressed multiple all-negated reserved-pair sets, inline-only/heading-addressed multiple mixed exact reserved-pair sets, and heading-single-body exact-negation corrections above;
- if a non-historical chunk explicitly addresses the key through those structural heading/field forms but none of the comparable current State values appears, the whole chunk is suppressed from `CognitiveInput.memory`, except when one of those bounded exact-negation rules establishes that the explicit negative claim negates a different scalar value;
- outside the single-inline, heading+single-inline exact-boolean, heading+multiple-inline exact-boolean, multiple-inline exact-boolean, or heading-single-body exact boolean rules, a boolean State-addressing non-historical chunk is suppressed only when it contains the exact opposite `true` / `false` token and does not also contain the current boolean token;
- outside those exact boolean rules, a structurally State-addressing boolean chunk containing the current token remains compatible; a chunk containing neither boolean token, or both tokens, is left untouched rather than being semantically or temporally reclassified;
- for the reserved structured State value `{semantic, degree_hint}`, the current `semantic` must appear as an exact lexical token sequence; a matching numeric degree alone cannot make conflicting semantic text compatible;
- when the State key is identified by the chunk heading, an explicit numeric `degree_hint:` / `degree_hint=` assignment in that section must equal the active State degree or the whole non-historical chunk is suppressed;
- when State addressing exists only through an inline canonical `key:` / `key=` assignment, a degree claim is associated with that key only when `degree_hint:` / `degree_hint=` occurs on the same assignment line; degree fields on another key's line are not borrowed;
- absence of an associated explicit degree assignment is not inferred as a conflict, and arbitrary prose numbers are not interpreted as degree claims;
- exact token sequences are used rather than substring matching, so for example `likes` is not treated as present inside `dislikes`;
- inactive or expired State records do not suppress memory;
- outside the structural forms and the typed-current positive scalar / exact scalar-negation / exact positive-or-negated boolean / explicit positive reserved-degree / C32 exact single-leading-`not` reserved-degree grammar above, free-form MEMORY is left untouched even if its prose happens to mention an older, newer, current-sounding, or different value.

Whole-chunk suppression changes only current cognitive residency. It does not rewrite or delete `MEMORY.md`, mutate State or Events, create a second semantic owner, alter upstream retrieval ranking, or add an LLM call. Historical retention and typed-current scalar/boolean/reserved-degree suppression use the existing retrieved-memory projection and the existing four-layer content-free diagnostics; they do not create a new diagnostics layer or change `RetrievedMemoryItem` shape.

The former C4 **lexical temporal-authority classifier** from #1385 remains retired. C5 consumes `MemoryChunk.temporal_authority` directly; C6, C7, C8, C9, C12, and C32 reuse only the bounded line-leading canonical-key **claim syntax after typed `current` is already established upstream**. C10, C11, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C33, C34, C35, C36, and C37 extend only the pre-existing structural State-addressing boundaries and do not infer temporal/currentness authority from prose.

### Opt-in ordinary-turn MEMORY retrieval

`run_user_turn` and `run_user_turn_streaming` accept `memory_budget: MemoryRetrievalBudget | None`.

Current behavior is intentionally opt-in:

- `memory_budget=None` preserves the previous behavior and does not read `MEMORY.md` at all;
- a supplied `MemoryRetrievalBudget(max_chunks, max_chars)` uses the Current User Event text as the retrieval query and delegates selection to `select_memory_chunks`;
- buffered and streaming turns share the same retrieval/compilation helper and therefore the same selection semantics;
- selected chunks pass through the deterministic State-shadow filter and then enter only the dedicated `CognitiveInput.memory` layer;
- a zero budget is allowed and selects no memory; negative budget values fail explicitly;
- no default runtime MEMORY budget is implied by the existence of this opt-in path;
- the public OpenAI client boundary does not expose a MEMORY-budget control.

The Current User Event is persisted before optional retrieval. If reading `MEMORY.md` fails after that point, the turn fails closed before provider generation: the User Event remains recorded, no Assistant Event is created, and Canonical State is unchanged by the failed turn.

## Current targeted Event evidence retrieval and projection primitives

`select_event_evidence(...)` provides deterministic bounded selection over caller-supplied persisted Events without replaying the whole supplied sequence into cognitive context.

Current retrieval behavior:

- input Event order is treated as Event Journal chronology;
- only `message` Events with non-empty string `payload.content` are eligible;
- explicit `exclude_event_ids` can remove the Current Event or any other occurrence from eligibility;
- query and Event content use NFKC/casefold normalized exact lexical tokens;
- only positive token overlap is eligible; there is no zero-match fallback;
- higher lexical overlap wins admission;
- equal relevance prefers the newer occurrence by source order;
- explicit `max_events` and `max_chars` bound admission;
- Events are admitted whole; an oversized relevant Event is skipped rather than truncated, and a later fitting relevant Event may still be admitted;
- selected Events are returned in original source chronology after ranking/admission;
- the original `Event` objects are returned unchanged; retrieval does not mutate Events, State, MEMORY, indexes, or call an LLM.

`compile_cognitive_input(..., event_evidence=...)` accepts already-selected persisted Events and projects them into a distinct `CognitiveInput.event_evidence` layer. Each item preserves:

```text
event_id
event_type
actor
timestamp
content
```

Projection preserves supplied order among retained evidence. It excludes the Current Event by ID because Current Input is already carried separately, and it excludes an Event whose exact ID is already resident in selected Working Context. The retained Working Context item keeps that Event ID in `sources`, so occurrence provenance is not lost. This is exact occurrence residency de-duplication only: equal or similar content with a different Event ID remains separate evidence. A selected Event without non-empty string `payload.content` fails explicitly rather than being silently dropped or rewritten.

The layer remains distinct by authority and purpose:

```text
Working Context   recent dialogue continuity with Event sources
Retrieved Memory  crystallized synthesis with document location
Event Evidence    targeted persisted occurrence with real Event ID
Current Input     protected current governed Event
```

The OpenAI-compatible provider serializes Event Evidence separately. Real Event-evidence IDs may be used as StateCandidate provenance; MEMORY locations remain ineligible. User/assistant actor role and occurrence time remain visible, and retrieved occurrence evidence is not automatically current Canonical State.

### Opt-in ordinary-turn Event retrieval

`run_user_turn` and `run_user_turn_streaming` now also accept `event_budget: EventRetrievalBudget | None`.

Current runtime behavior is deliberately opt-in:

- `event_budget=None` preserves the previous ordinary-turn behavior and supplies an empty Event-evidence layer;
- a supplied `EventRetrievalBudget(max_events, max_chars)` uses the Current User Event content as the lexical query and explicitly excludes the Current User Event ID;
- buffered and streaming paths share `_compile_turn_cognitive_input` and therefore the same retrieval/projection semantics;
- when Event retrieval is enabled, the current Event Journal sequence is materialized once before provider generation and reused by both Working Context selection and `select_event_evidence`;
- selected Events enter only `CognitiveInput.event_evidence` through the existing projection owner;
- zero budgets are valid and select no evidence; negative budgets fail explicitly;
- no default Event budget and no OpenAI/client-facing Event-budget request field are introduced.

The Current User Event is persisted before the snapshot/retrieval step. Ordinary turns still make exactly one cognitive provider generation. If the same exact Event occurrence is selected both for Working Context and targeted Event Evidence, the Context Compiler keeps the Working Context residency and suppresses only the duplicate Event Evidence projection. Working Context user→assistant exchange admission remains unchanged, and the opt-in diagnostics report the supplied exact Event-ID overlap as a content-free count. Similarity-based or semantic cross-layer deduplication remains deferred.

`CharacterDirectory` now keeps a process-local validated Event snapshot. An unchanged `events.jsonl` is not reopened and reparsed for every later `iter_events()` call in the same directory instance; a successful RelayLM-owned append incrementally extends an already-valid snapshot. File signature changes invalidate the snapshot and force authoritative JSONL revalidation, so malformed external edits are not hidden by cached Events.

This snapshot optimization does **not** make Event retrieval independent of Event count. The first read after process start/reopen or external invalidation still parses the authoritative JSONL, and the current lexical targeted selector still evaluates the supplied Event snapshot. Persistent/segmented indexing, retrieval-scaled targeted discovery beyond O(N) candidate inspection, semantic/vector retrieval, temporal interpretation, and stronger conflict authority remain deferred.

## Budget model

Context budgeting is role-aware rather than one flat relevance competition.

Conceptually:

```text
protected tier    Identity + Current Event
current tier      relevant active Canonical State
continuity tier   accepted referent/unresolved/active-task continuity, bounded upstream
working tier      bounded recent conversational continuity
retrieved tier    MEMORY chunks + targeted Events
reserve tier      prompt / schema / provider overhead
```

Budgets should use floors/caps/residual allocation rather than fixed percentages that must always be consumed. Correct but irrelevant memory should remain out of Context; token availability alone is not a reason to inject it. The accepted Continuity projection does not establish a new runtime/default token budget; it consumes an already capacity/lifecycle-bounded Continuity Context.

## Deferred selection work

#1267 remains the authority for later Context selection and retrieval work, including:

- stronger semantic/multilingual State/MEMORY/Event relevance beyond the current explicit lexical primitives;
- any later Continuity-specific selection/degradation policy beyond the current projection of all accepted initial Continuity kinds;
- State-vs-memory authority beyond the current deterministic structural addressing forms and typed-current positive-scalar/exact-scalar-negation/exact-positive-or-negated-boolean/positive-or-C32-negated explicit-reserved-degree grammar, including omitted-key aliases/synonyms, reserved-degree heading-body forms beyond C33's single exact negated-pair + exactly-one-section-degree boundary, C37's single exact positive-pair + exactly-one-section-degree boundary, C34's multiple exact positive-pair + exact-section-degree-count boundary, C35's multiple exact all-negated-pair + exact-section-degree-count boundary, and C36's multiple exact mixed-pair + exact-section-degree-count boundary, reserved-degree negation outside the C25 inline-only single, C26 heading+single-inline, C27 heading-only single-body, C28 inline-only multiple all-negated, C29 heading-addressed multiple all-negated, C30 inline-only multiple mixed exact-pair, C31 heading-addressed multiple mixed exact-pair, C32 typed-current free-form exact single-leading-`not` pair, C33 heading-only multi-line single exact-negated-pair, C37 heading-only multi-line single exact-positive-pair, C34 heading-only multi-line multiple exact positive-pair, C35 heading-only multi-line multiple exact all-negated-pair, and C36 heading-only multi-line mixed exact-pair boundaries, any recognized structural set carrying an additional heading-owned explicit degree beyond its bounded guard, typed-current free-form reserved-degree negation beyond C32's exact one-leading-`not` pair grammar, non-exact or partially recognized reserved-degree sets beyond current fallback, non-exact boolean negation, contractions and broader negation NLP, natural-language degree/intensity interpretation, degree ordering/tolerance or cross-axis comparison, and other non-lexically-comparable values;
- richer durable logical memory identity/provenance behavior beyond the current governed `MemoryChunk.temporal_authority` carriage when #1260 work justifies it;
- persistent/segmented Event Journal indexing and retrieval-scaled targeted discovery beyond the current process-local validated snapshot reuse;
- redundancy reduction across State / Working Context / Continuity / Memory / Events beyond the current exact Working Context/Event Evidence Event-ID residency rule;
- embedding/index acceleration only after authority eligibility is preserved.

The realized #1387 total-budget/degradation mechanics are not deferred #1267 work. Evidence-backed numeric runtime/default profiles are separately owned by #1388.

The governing principle is:

> **Retrieve by relevance, assemble by authority.**
