# RelayLM Core Concepts

This Starter knowledge is a bounded projection of shipped documentation. When a question requires more detail than is stated here, treat the answer as unsupported rather than filling the gap from model prior knowledge.

## What RelayLM governs

Source: `docs/architecture/core.md`

RelayLM's Core thesis is to relay a persistent Identity plus governed current context into a replaceable language-model substrate, then accept only validated semantic change back. The model is not the Character. Identity is stable human-authored normative authority; the Event Journal records occurrence/provenance; Canonical State is accepted current understanding rather than history.

Assistant text does not become factual State merely because the assistant generated it. State and Continuity proposals gain authority only after RelayLM's deterministic validators accept them.

## Pass 1 and Pass 2

Source: `docs/architecture/cognitive-runtime.md`

RelayLM 1.0 is two-pass first on the Core release/reference path.

Pass 1 owns the user-visible conversation response. It produces visible text without a State/Continuity proposal wrapper.

Pass 2 owns semantic extraction for immediate `state_candidates` and `continuity_candidates`. The Pass 1 response is lower-authority interpretive context; it cannot self-certify a user or external fact. RelayLM still owns exact parsing, typed construction, provenance checks, deterministic validation, stale guards, and final commit authority.

A valid Pass 1 can remain a valid conversation even if Pass 2 later fails. Invalid or stale Pass 2 output cannot partially mutate State or Continuity.

## SOUL.md and Cognitive Packages

Sources: `docs/reference/character-directory.md`, `docs/reference/knowledge.md`

`SOUL.md` is the package's stable identity or role authority. A Character is one specialization of Cognitive Package; a package may instead be deliberately machine-like.

Optional `knowledge/` files are package-authored read-only reference material. KNOWLEDGE is distinct from SOUL, Canonical State, Event provenance, and lived MEMORY. A KNOWLEDGE location is a document locator, not an Event ID and not candidate provenance.

Ordinary turns and Crystallization do not rewrite package KNOWLEDGE.

## State, MEMORY, and Continuity

Sources: `docs/architecture/core.md`, `docs/reference/knowledge.md`

Canonical State is accepted current understanding, not history.

MEMORY is lived crystallized synthesis governed separately from package-authored KNOWLEDGE. Packaged reference text must not be presented as something the Character experienced or remembered merely because it was supplied as KNOWLEDGE.

Continuity Context is bounded temporary cross-turn semantic authority. It is not Canonical State, Event occurrence authority, crystallized MEMORY, or current-turn Working Context.
