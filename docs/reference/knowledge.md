# Package KNOWLEDGE

Core 1.0 treats package-authored reference material as a separate semantic layer:

```text
SOUL      who/what the package is and how it should behave
KNOWLEDGE what the package author supplied as reference material
MEMORY    what governed experience was later crystallized into lived synthesis
STATE     what RelayLM currently accepts as current understanding
EVENTS    what occurred and supplies occurrence provenance
```

The invariant is **Identity != Knowledge != Experience**. Reading a packaged fact does not mean the package experienced it, remembered it, observed it, or accepted it into Canonical State.

## Portable v0 format

A Cognitive Package may optionally contain:

```text
<CognitivePackage>/
└─ knowledge/
   └─ ... .md or .txt UTF-8 text assets ...
```

Packages that do not use KNOWLEDGE do not need an empty directory. v0 supports regular UTF-8 Markdown and text files only. The loader rejects symlinks, unsupported asset types, invalid UTF-8, NUL text, non-regular assets, more than 32 files, files larger than 64 KiB, or more than 256 KiB total package KNOWLEDGE. Paths exposed to cognition are deterministic package-relative locators under `knowledge/`.

Those byte bounds are package-format safety limits, not a substitute for the model context budget.

## Cognitive projection and authority

Model-facing KNOWLEDGE is carried as dedicated `KnowledgeItem` values and serialized as its own `knowledge` section. A Knowledge `location` is a document locator. It is **not an Event ID** and is never admitted as State/Continuity candidate source provenance.

The provider instruction labels KNOWLEDGE as package-authored reference material. It may be used to answer or reason according to the package role, but it must not be narrated as personal experience or memory unless separate governed evidence supports that claim.

Ordinary turns and Crystallization have no write operation for `knowledge/`. Crystallization continues to own lived `memory/MEMORY.md` and State proposals; it does not rewrite package KNOWLEDGE.

## Bounded selection

When total Cognitive Budget enforcement is configured, KNOWLEDGE has an independent Tier-3 `package_knowledge` `CountCharacterEnvelope`. Existing budget policies that omit it resolve to a zero item/character envelope, preserving their prior identity until an owner explicitly allocates KNOWLEDGE capacity.

Selection is deterministic and semantic-free: package-relative file order is preserved, whole files are included while item/character caps permit them, and a file that cannot fit the remaining character cap is skipped so a later smaller file may still fit. Files are never truncated, embedded, re-ranked, or summarized by a hidden model call. The final provider serialization still passes through the normal exact/conservative total-context counter and fail-before-generation enforcement.

A non-budgeted compatibility turn may carry the package catalog bounded by the strict package-format limits above; release/calibrated runtime capacity remains owned by Cognitive Budget and calibration policy.

## Deliberately deferred

KNOWLEDGE v0 does not add embeddings, vector databases, semantic RAG, crawlers, external URLs, autonomous refresh, binary/PDF/Office ingestion, mutable model-authored KNOWLEDGE, or a second truth database. Large-corpus retrieval and governed external knowledge import remain post-1.0 concerns unless separately promoted.
