---
relaylm_doc_type: concept_policy
relaylm_authority: visible_output_speech_suitability_and_caption_fallback_policy
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: voice
relaylm_update_trigger:
  - speech-suitability or caption/substitution responsibility changes
  - structured visible content becomes eligible for concrete TTS execution
  - a downstream adapter adds governed speech/caption fallback behavior
  - expression or accessibility policy changes how approved visible content is rendered
relaylm_not_authoritative_for:
  - current implementation completion or sequencing
  - exact segment-kind, TTS-policy, caption, replacement, SSML, phoneme, or adapter schemas
  - exact TTS segmentation offsets, stream-suppression behavior, or transport-envelope fields
  - response semantic generation or permission to disclose protected content
  - concrete TTS provider, audio playback, avatar, caption renderer, or frontend implementation
  - automatic semantic rewriting of assistant output
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - streaming-and-tts.md
  - ../privacy/protected-source-and-disclosure.md
  - ../relationship/social-expression.md
  - ../character/public-private-persona.md
  - ../ai_vtuber_pipeline_profile.md
relaylm_related_contracts:
  - ../../contracts/runtime/stream-suppression.md
  - ../../contracts/runtime/tts-segmentation.md
  - ../../contracts/runtime/tts-transport.md
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - voice, caption, and realtime frontend maintainers
  - output-safety and accessibility reviewers
  - future external TTS and avatar adapter maintainers
relaylm_authority_level: concept
---
# Speech Suitability and Caption Fallback

## Authority summary

This page defines a target output policy for a boundary that is easy to miss:

```text
safe to show
  != necessarily useful or safe to speak verbatim
```

RelayLM's current voice architecture already separates safe visible output, TTS segmentation metadata, adapter handoff, and concrete synthesis. This concept adds only the durable **speech-suitability** distinction for a future concrete voice path.

It does not define an exact segment classifier, enum, adapter payload, or TTS engine behavior.

## Why speech suitability is separate from disclosure safety

A piece of response content can be fully authorized for the current audience and still be a poor speech unit.

Examples include:

- a long URL;
- a code block;
- a filesystem path;
- a shell command;
- a table;
- machine-readable JSON or YAML;
- a dense identifier;
- long inline code;
- a citation or technical token whose spoken form is ambiguous.

The problem is not necessarily privacy or semantic correctness. The problem is presentation quality and the risk that speech becomes misleading, noisy, excessively long, or hard to understand.

Therefore the stable separation is:

```text
disclosure / output safety
  -> may this content be visible at all?

speech suitability
  -> given that it is already approved visible content,
     should it be spoken verbatim, represented differently,
     or left to captions/text only?
```

Speech suitability may only narrow the voice channel. It must not widen disclosure authority.

## Upstream safety is mandatory

Speech-suitability policy consumes only content that has already passed the owning visible/internal and disclosure boundaries.

It must not inspect raw backend material as a shortcut around:

- RelayCTX stream suppression;
- protected-source disclosure policy;
- scene/audience restrictions;
- response safety gates;
- current visible-output authority.

The safe order is:

```text
response meaning
  -> disclosure / output approval
  -> safe visible content
  -> structural segmentation
  -> speech-suitability decision
  -> external caption / TTS / avatar presentation
```

A voice adapter's ability to synthesize arbitrary text is never evidence that the text was permitted for speech.

## Three conceptual outcomes

A future speech-suitability boundary needs at least three semantic outcomes even if exact names differ:

```text
speak
  -> approved content may be voiced substantially as written

caption_only
  -> preserve visible text/caption, but do not voice it verbatim

substitute
  -> preserve the approved visible text while using a separately governed,
     meaning-preserving spoken representation
```

These are conceptual classes, not a registered runtime enum.

A later exact contract may choose different names or add narrower states.

## Caption-only is a first-class success mode

Not speaking a visible segment is not automatically a failure.

For some content, the correct voice behavior is:

```text
visible content remains available
  + speech is intentionally omitted
  -> successful multimodal delivery
```

This prevents concrete TTS from becoming a requirement that every visible byte must be pronounced.

Caption-only behavior is especially important for content whose visual form carries meaning that speech would distort or burden.

## Substitution requires stronger governance than omission

A substitute spoken representation is more powerful than caption-only behavior because it introduces text or speech that differs from the visible source.

The stable rule is:

```text
omit from speech
  -> presentation narrowing

replace with different spoken wording
  -> potential semantic transformation
  -> requires explicit meaning-preservation authority
```

Examples of potentially safe future substitution include:

- speaking only a domain name while keeping the complete URL visible;
- saying “code block shown on screen” instead of reading a long code block;
- saying “table shown in captions” instead of serializing every cell aloud.

These are conceptual examples, not implemented behavior.

A substitute must not:

- add facts;
- soften or strengthen a refusal;
- change commitments;
- hide a safety warning;
- convert uncertain content into confident content;
- disclose information absent from the approved visible output;
- alter protected-source or relationship boundaries.

## Structural content does not create a permanent exact kind list here

The historical AI VTuber profile proposed categories such as code, URLs, tables, commands, paths, quoted text, and normal sentences.

Those examples remain useful design evidence, but this concept deliberately does not freeze a permanent exact classifier vocabulary.

A future implementation may classify speech suitability using deterministic parsing, an allowlist, presentation metadata, or another bounded method.

Exact categories belong to a contract only after an implementation boundary requires them.

## Visible text remains canonical for meaning

Speech adaptation is downstream presentation.

When both caption/text and speech are emitted, the visible approved response remains the canonical semantic reference unless a later contract explicitly defines an equivalent multimodal representation.

The voice layer must not create a second answer whose meaning diverges from the visible response.

If safe meaning-preserving speech cannot be produced, fallback should move toward caption-only rather than inventing a different answer.

## Segmentation and suitability are different responsibilities

TTS segmentation answers:

```text
where can approved visible text be divided into bounded delivery units?
```

Speech suitability answers:

```text
which of those approved units should be voiced, omitted from speech,
or represented by an explicitly governed substitute?
```

The exact current segmentation contract is owned by:

```text
docs/contracts/runtime/tts-segmentation.md
```

This concept does not alter its offsets, statuses, punctuation rules, or safe-output admission.

A segment being structurally ready does not imply it is suitable for concrete speech.

## Transport readiness is not speech approval

The existing TTS handoff/transport boundary prepares runtime-private metadata and explicitly stops before concrete synthesis.

A future concrete adapter must not interpret transport readiness as universal permission to voice every referenced character range.

Conceptually:

```text
transport-ready metadata
  + speech-suitability approval
  + downstream execution authority
  -> eligible concrete synthesis request
```

This concept does not change the existing transport contract.

## Long machine-readable content should fail toward visual delivery

For large structured material, speech can become both unpleasant and misleading.

A conservative future policy should be able to keep material visible while avoiding verbatim voice when the segment is dominated by:

- serialized structures;
- source code;
- tabular layouts;
- dense identifiers;
- machine paths;
- command syntax;
- raw URLs.

This is a presentation principle, not a prohibition on ever speaking technical content.

A short command or identifier may be useful to speak in context. Exact thresholds belong to a later implementation contract.

## Quoted and parenthetical material requires context, not blanket suppression

Quoted text and parenthetical material are not inherently unsuitable for speech.

A future policy may consider:

- length;
- conversational relevance;
- whether punctuation conveys important structure;
- whether the quote is the answer itself;
- whether omission would change meaning;
- whether a caption-only choice would make the spoken response misleading.

The stable rule is conservative contextual handling rather than a universal “never speak quotes” rule.

## URLs and paths should not be normalized into false content

A speech adapter may be tempted to simplify a URL or path into something more pronounceable.

That simplification must not pretend to preserve exact identity when it does not.

For example:

```text
visible exact URL/path
  -> caption remains exact
  -> optional spoken abstraction may be allowed only as presentation
```

The spoken abstraction must not replace the exact visible artifact for copy/use workflows.

## Safety-critical text resists decorative substitution

Some approved visible output carries exact safety meaning even when awkward to speak.

A speech-suitability layer must not use convenience as authority to remove or materially alter:

- warnings;
- refusal boundaries;
- uncertainty qualifiers;
- dosage or other high-stakes numeric detail;
- confirmation requirements;
- destructive-action cautions;
- privacy or consent notices.

If exact speech is unsuitable, caption-only or a separately governed concise summary is safer than an improvised paraphrase.

## Numeric and identifier fidelity

Numbers, identifiers, dates, versions, hashes, addresses, and other exact tokens can be misheard.

A future adapter may combine visible exact presentation with a spoken-friendly form, but the voice channel must not silently change exact values.

Where fidelity matters, the system should prefer:

```text
exact caption/text
  + optional clearly subordinate speech
```

over speech-only delivery of ambiguous values.

## RelayEMO may style approved speech, not reopen suitability

Return-side affect may influence engine-neutral presentation hints such as intensity, pacing, or expression class under its own authority.

It must not convert a caption-only or blocked segment into speakable content merely because the current affect is expressive.

The ordering is:

```text
speech suitability
  -> eligible voice material
  -> bounded expression/prosody hints
  -> adapter execution
```

Affect changes presentation inside the allowed channel; it does not create a channel permission.

## Public/private persona does not bypass suitability

A public or private persona projection may change style, but it cannot make an otherwise unsuitable machine-readable block appropriate to read verbatim just for character flavor.

Likewise, speech adaptation must not use hidden private information to create a more personalized spoken substitute.

The same protected-source and public/private persona boundaries apply across text, caption, voice, and avatar channels.

## Failure behavior

Speech-suitability failure should degrade without losing the already-approved visible answer.

The stable direction is:

```text
classification or adaptation uncertain
  -> preserve approved visible/caption output
  -> omit or conservatively limit speech
  -> do not regenerate a new semantic answer
```

A TTS failure similarly should not invalidate or replay an already delivered caption/text response unless a separate runtime recovery contract requires it.

## Cancellation and duplicate prevention remain runtime concerns

Concrete audio queues may later require cancellation, interruption, retry, and duplicate suppression.

Those are downstream execution/runtime responsibilities.

This concept contributes only the rule that retries must not cause content previously deemed caption-only or blocked from speech to become spoken.

## Accessibility boundary

Caption-only fallback is not merely an error path; it is part of a multimodal output design.

Future frontends should preserve a readable representation when speech is omitted or adapted.

Conversely, accessibility requirements may motivate better governed spoken alternatives for content that is visually dense.

Exact accessibility behavior belongs to frontend and adapter implementation, not this concept.

## Diagnostics remain content-free

Generic speech-suitability diagnostics should expose bounded decision metadata rather than response bodies.

Potential future diagnostic classes include:

- speak / caption-only / substitute decision class;
- structural-content class;
- exact-token sensitivity flag;
- substitution requested/allowed/denied;
- reason IDs;
- counts.

They should not include:

- visible response text;
- substitute text;
- URL/path values;
- code bodies;
- protected source;
- TTS credentials;
- audio bytes.

Exact projection fields require a later contract.

## Evaluation boundary

Future evaluation should test both understandability and semantic preservation.

Useful questions include:

- does speech preserve the meaning of the approved visible answer?
- does caption-only fallback avoid noisy code/URL/table reading?
- are safety-critical qualifiers retained?
- can exact values still be copied from the visible channel?
- does a substitute introduce unsupported facts or hide important detail?
- does affect or persona styling ever reopen blocked/caption-only material?
- do retries or adapter failures change the suitability decision?

A more natural voice is not an improvement if it changes meaning.

## Stable invariants

1. safe visible content is the only input to speech suitability;
2. visible-safe does not imply speak-verbatim;
3. speech suitability may narrow presentation but not widen disclosure;
4. caption-only is a valid successful multimodal outcome;
5. substitution requires explicit meaning-preservation authority;
6. segmentation readiness and speech suitability remain distinct;
7. transport readiness does not imply synthesis permission;
8. exact visible values remain authoritative where speech is ambiguous;
9. RelayEMO/persona styling cannot reopen unsuitable material;
10. uncertainty degrades toward visible/caption output, not invented speech;
11. generic diagnostics remain content-free;
12. concrete TTS/audio/avatar execution remains downstream.

## Relationship to canonical voice architecture

`streaming-and-tts.md` owns the overall safe-output -> segmentation -> handoff -> external-execution responsibility chain.

`stream-suppression.md` owns exact visible/internal stream safety.

`tts-segmentation.md` owns exact current safe-visible offset segmentation.

`tts-transport.md` owns exact current handoff and transport-preparation metadata.

This concept begins only after safe visible content exists and remains non-executable until a later concrete voice adapter boundary exists.

## Source synthesis boundary

This page extracts the durable speech-suitability / caption-fallback principle from:

```text
docs/architecture/ai_vtuber_pipeline_profile.md
```

It deliberately does not preserve the source's illustrative exact segment-kind table, content-bearing sample payloads, historical pipeline ordering, or proposed adapter payload schemas as current exact authority.

Those details remain source history unless separately accepted by a later contract.

## Source-retirement boundary

This transaction does not retire `docs/architecture/ai_vtuber_pipeline_profile.md`.

The source remains transitional until its remaining responsibilities are absorbed/classified and a separate bounded retirement transaction repairs all consumers and records provenance/disposition.
