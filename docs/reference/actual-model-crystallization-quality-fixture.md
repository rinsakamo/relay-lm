# Actual-model crystallization consolidation-quality fixture

RelayLM freezes one canonical Character Package fixture for the first real-model off-turn crystallization quality review.

The fixture is:

```text
evaluation/actual_model/characters/crystallization-quality-v1/
```

Its exact byte revision is recorded separately as:

```text
evaluation/actual_model/characters/crystallization-quality-v1.revision.txt
```

Current frozen revision:

```text
sha256:531dcde63da312572ff6161e74d0bd72665c96dc6725023ed5e340e3d8c15d6a
```

The canonical semantic case is:

```text
case_id: crystallization-consolidation-quality-v1
case_version: 1
recommended max_events: 7
```

This fixture is not an exact-output benchmark. It creates one reproducible pre-crystallization situation in which the Event Journal contains better evidence than the currently accepted/organized durable understanding. A real crystallizer can therefore demonstrate whether off-turn consolidation repairs bounded representation-quality problems without widening authority.

## Seven-Event story

The complete Event Journal contains exactly seven Events, all of which are included when the crystallization condition uses `max_events = 7`.

1. `cry4-user-name-yuu` — the user initially says `私の名前はユウ。`.
2. `cry4-user-beverage-comparison` — the user says they like both coffee and tea, prefer tea, and explicitly does not revoke the coffee liking.
3. `cry4-user-blue-box-task` — the user asks for a temporary blue-box contents check.
4. `cry4-assistant-hokkaido-claim` — the assistant, without user evidence, says that Yuu lives in Hokkaido.
5. `cry4-user-name-correction` — the user explicitly corrects the name to `ユウト`.
6. `cry4-user-residence-correction` — the user distinguishes historical Kyoto from current Osaka.
7. `cry4-user-blue-box-complete` — the user explicitly closes the blue-box task and says it should not remain a future goal.

Event actor authority is intentional. The Hokkaido statement is assistant-authored; every persisted user State record is sourced only from user-authored Events.

## Pre-crystallization Canonical State

The fixture deliberately contains **plausible accepted one-pass interpretations that are now stale or incomplete**. This models the qualitative structured-output failures observed in real ordinary-turn evaluation without corrupting deterministic provenance rules.

Current State before crystallization is:

| Class | Key | Value | Purpose |
|---|---|---|---|
| `user.identity` | `name` | `ユウ` | stale after the later explicit `ユウト` correction |
| `user.preference` | `coffee` | `likes` | valid weaker-item liking that should not be revoked merely because tea is preferred |
| `user.preference` | `tea` | `likes` | valid positive tea preference |
| `user.preference` | `preferred_beverage` | `coffee` | stale/wrong interpretation of the comparative Event |
| `user.fact` | `residence_location` | `京都` | stale currentness interpretation of the Event that actually says historical Kyoto / current Osaka |
| `user.goal` | `current_task` | `check_blue_box_contents` | stale transient task after explicit completion |

These records are intentionally loaded as Canonical State because the question under evaluation is whether **later off-turn semantic consolidation can improve accepted current understanding using preserved evidence**. The deterministic Validator remains unchanged; any corrective write-back from a real crystallizer must still use the existing `StateCandidate -> Validator` path.

The fixture does not include Hokkaido in Canonical State. The unsupported claim exists only in the Event Journal and prior MEMORY.

## Prior MEMORY.md

The prior readable synthesis is valid under the current governed MEMORY metadata contract but intentionally poor as long-horizon organization.

It contains seven governed units:

- stale current name `ユウ`, sourced from the stale name State;
- a beverage-preference unit saying coffee and tea are liked but coffee is preferred;
- a second duplicate/alias preferred-drink unit also saying coffee is preferred;
- stale current residence Kyoto, sourced from current State;
- historical Kyoto, sourced directly from the user's residence-correction Event;
- a current Hokkaido note sourced **only** from the assistant-authored Event;
- a current blue-box task sourced from the stale current-task State.

All `relaylm-memory:v1` source references are real fixture Event or State IDs. CRY4 therefore does not test malformed metadata recovery. It tests whether semantic consolidation respects the difference between provenance existence and authority/meaning.

In particular:

> A syntactically valid MEMORY unit with assistant-only Event provenance still does not certify a user fact.

## Product-review intent

The CRY2 review contract remains the quality authority. CRY4 supplies concrete opportunities for each axis.

### `durable_information_selection`

A strong crystallization should preserve durable identity, preferences, and residence history while avoiding transcript-like retention of temporary task mechanics or unsupported incidental statements.

### `state_taxonomy_key_normalization`

Corrective State proposals should reuse the existing exact State identities when correcting the same concepts:

- `user.identity/name` for the name correction;
- `user.preference/preferred_beverage` for the comparative-preference correction;
- `user.fact/residence_location` for the current residence correction;
- `user.goal/current_task` for retirement/removal of the completed temporary goal.

The review should penalize unnecessary alias/key proliferation. It should **not** require the crystallizer to reclassify the already-correct positive `coffee` and `tea` preference keys.

### `transient_durable_discipline`

The completed blue-box task should not survive as an ongoing durable goal or long-term memory merely because it appeared recently.

### `correction_supersession_preservation`

Current identity should reflect `ユウト`; the earlier `ユウ` occurrence remains valid Event history rather than being rewritten or deleted.

### `temporal_provenance_fidelity`

Current residence should reflect Osaka while historical Kyoto remains meaningful. The assistant-authored Hokkaido claim must not become a user fact solely because prior MEMORY carried syntactically valid metadata for it.

### `memory_organization_readability`

The duplicate/stale prior beverage and residence organization should be consolidated into coherent readable long-horizon MEMORY rather than copied chronologically or retained as redundant aliases.

### `semantic_stability`

A single CRY4 run cannot establish stability. The frozen fixture/revision and CRY2 run identity allow a later controlled repeated-pass or replicate transaction to measure semantic churn without changing this case definition.

## What is deliberately not an oracle

CRY4 does **not** freeze:

- exact Markdown wording;
- exact Markdown heading names/order;
- exact number of MEMORY sections;
- exact StateCandidate ordering;
- a requirement that every review opportunity produce a StateCandidate rather than only better MEMORY;
- an exact human-readable explanation;
- a weighted score or pass threshold.

For example, a crystallizer may represent Kyoto history and Osaka currentness in one coherent MEMORY section or multiple well-organized sections. Product review evaluates semantic fidelity and usability, not a reference string.

## Host execution

Use the existing CRY3 module:

```bash
python -m relaylm.actual_model_crystallization_host_runner \
  --condition /path/to/condition.json \
  --repo-root /path/to/relay-lm \
  --model-artifact /path/to/frozen-model.gguf \
  --serving-proof /path/to/lm-studio-serving-proof.json \
  --workspace-root /path/to/workspaces \
  --artifact-root /path/to/evidence \
  --lmstudio-node /path/to/node \
  --lmstudio-sdk-root /path/to/sdk-project
```

The host condition for this case must use:

```json
{
  "character_fixture": {
    "id": "actual-model-crystallization-quality-v1",
    "path": "evaluation/actual_model/characters/crystallization-quality-v1",
    "revision": "sha256:531dcde63da312572ff6161e74d0bd72665c96dc6725023ed5e340e3d8c15d6a"
  },
  "case": {
    "id": "crystallization-consolidation-quality-v1",
    "version": "1"
  },
  "max_events": 7
}
```

Those fields are only the fixture/case fragment, not a complete CRY3 condition. The complete condition must additionally provide the exact **current clean repository commit at execution time**, frozen target identity, observed LM Studio environment, explicit request model/endpoint, decoding controls/capabilities, condition ID, and replicate ID.

Do not commit a supposedly canonical complete condition with a moving `relaylm_commit`. The serving proof is commit-bound by the existing #1508/CRY3 contract, so regenerate/re-attest it for the exact clean commit that will produce the citable run.

## Evidence interpretation

A successful host invocation proves only that one citable CRY2 evidence artifact was produced under the declared runtime/model/fixture identity. It is not itself a quality PASS.

Review the raw crystallizer output separately from deterministic RelayLM State decisions. Then apply the seven CRY2 quality axes and cite the resulting evidence run ID(s). Any later crystallizer prompt/schema tuning should be justified by those observed failures or strengths rather than by this fixture's intended answer.
