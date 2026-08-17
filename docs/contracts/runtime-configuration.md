# Release Runtime Configuration Contract

Status: RCFG1 contract + RCFG2 validated loader/resolver for RelayLM v1. Owning Issue: #1446.

This contract defines the release-facing configuration boundary only. It does not choose cognitive semantics, Retrieval relevance, Continuity lifecycle semantics, or calibrated cognitive numeric defaults.

## 1. Ownership boundary

RelayLM keeps portable character data separate from machine/runtime configuration.

```text
<Character>/
├─ SOUL.md
├─ config.yaml
└─ memory/...
```

Character `config.yaml` remains portable character-owned metadata. Provider endpoints, provider/model selection, secrets, server bind, runtime profiles, machine paths, token-counting capabilities, and operator overrides do not belong there.

```text
portable Character Package
        != runtime configuration
runtime configuration
        != semantic authority
configuration value
        != permission to reinterpret owner semantics
```

The runtime configuration layer may only carry values into already-owned runtime controls.

Canonical implementation surfaces are:

- `src/relaylm/runtime_config.py` — versioned non-secret configuration types, provenance vocabulary, secret-redacted process input boundary, and error taxonomy;
- `src/relaylm/runtime_config_loader.py` — RCFG2 discovery, strict parse/validation, leaf resolution, process-local secret resolution, and content-free effective diagnostics.

Runtime assembly into provider/Character/Retrieval/Continuity/Cognitive Budget owners remains RCFG3 and is intentionally absent from the loader.

## 2. Runtime configuration format

The runtime configuration file uses YAML and requires exact integer `format_version: 1`. Boolean, string-coerced, missing, or unsupported file versions fail closed.

Version-1 shape:

```yaml
format_version: 1

character:
  directory: /path/to/Character

provider:
  adapter: openai_compatible
  base_url: http://127.0.0.1:1234/v1
  model: model-id
  api_key:                 # optional secret reference, never a secret value
    env: OPENAI_API_KEY

server:                    # optional; release-owned defaults shown
  host: 127.0.0.1
  port: 8090

runtime:                   # optional; children are explicit opt-in
  profile: profile-name    # reserved for #1388; currently fails resolution

  memory_retrieval:
    max_chunks: 4
    max_chars: 4096

  event_retrieval:
    max_events: 4
    max_chars: 4096

  continuity:
    max_items: 8
    lifetime_revisions: 4

  cognitive_budget:
    total:
      model_context_window: 32768
      reserved_output_tokens: 2048
    policy:
      initial_plan:
        canonical_state:
          max_items: 32
          floor_items: 8
        working_context:
          max_items: 16
          floor_items: 2
          max_chars: 12000
          floor_chars: 1000
        retrieved_memory:
          max_items: 8
          floor_items: 0
          max_chars: 8000
          floor_chars: 0
        event_evidence:
          max_items: 8
          floor_items: 0
          max_chars: 8000
          floor_chars: 0
      steps:
        - layer: retrieved_memory
          target:
            max_items: 4
            floor_items: 0
            max_chars: 4000
            floor_chars: 0
    token_counter:
      capability: implementation-id
      mode: exact          # exact | conservative_estimate
```

Every Retrieval, Continuity, and Cognitive Budget number above is an **explicit schema example only**, not a RelayLM default. #1388 remains the sole owner of canonical cognitive numeric values and profile boundaries. #1371 remains the owner of Continuity lifecycle semantics and supplies no release default here.

The serialized Cognitive Budget policy maps directly into existing #1387 types: `TotalBudgetConfig`, `BudgetPlan`, `CountEnvelope`, `CountCharacterEnvelope`, `BudgetDegradationStep`, `BudgetDegradationPolicy`, and `TokenCountMode`. The configuration layer does not invent parallel budget semantics.

## 3. Strict file validation

A selected runtime file is validated before precedence resolution.

RCFG2 requires:

1. YAML root is a mapping;
2. `format_version` exists and is exact integer `1`;
3. duplicate YAML mapping keys are rejected rather than using last-value-wins behavior;
4. unknown keys fail at every governed mapping level;
5. configured scalar types are exact — boolean is not accepted as integer;
6. configured strings that are required to be meaningful are non-empty;
7. nested explicit owner-control objects contain exactly their required keys;
8. owner-defined value invariants such as non-negative budgets, floors, tier order, and valid `TokenCountMode` are validated by the existing owner types;
9. raw secret material is never a valid config-file field.

A malformed lower-precedence config file is not silently ignored merely because a higher-precedence override could replace the bad leaf. Selecting a file means the file itself must be a valid version-1 runtime configuration document.

Generic parse errors do not echo arbitrary YAML text. Typed errors expose safe field paths where practical.

## 4. Configuration discovery

Version 1 performs **no ambient filesystem search** for runtime configuration.

File selection is deterministic:

```text
explicit --config-equivalent path input
        > RELAYLM_CONFIG
        > no runtime config file
```

RCFG2 exposes the first input programmatically as `config_path`; RCFG4 will bind it to the CLI spelling.

If an explicitly selected path cannot be read, resolution fails with `read_error`. It does not fall through to `RELAYLM_CONFIG` or a guessed current-working-directory file.

If there is no file, the v1 runtime schema version remains `1` and required runtime leaves may be supplied by explicit environment/CLI inputs. This preserves the existing env-only startup boundary without turning the Character Package into runtime config.

## 5. Leaf-level precedence

For every field with a named override binding:

```text
explicit CLI override
    > explicit environment override
    > runtime config file
    > canonical default/profile value
```

Resolution is per leaf. A higher source replaces only the leaf it explicitly supplies; it does not erase unrelated lower-source siblings. Missing and explicit zero are distinct.

There is no generic arbitrary `--set key=value` contract in version 1.

Named scalar bindings are:

| Runtime field | CLI shape reserved for RCFG4 | Environment |
|---|---|---|
| config file | `--config` | `RELAYLM_CONFIG` |
| `character.directory` | `--character` | `RELAYLM_CHARACTER_DIR` |
| `provider.adapter` | `--provider-adapter` | `RELAYLM_PROVIDER_ADAPTER` |
| `provider.base_url` | `--provider-base-url` | `RELAYLM_PROVIDER_BASE_URL` |
| `provider.model` | `--provider-model` | `RELAYLM_PROVIDER_MODEL` |
| provider secret reference | `--provider-api-key-env` | raw secret via `RELAYLM_PROVIDER_API_KEY` |
| `server.host` | `--host` | `RELAYLM_HOST` |
| `server.port` | `--port` | `RELAYLM_PORT` |
| `runtime.profile` | `--profile` | `RELAYLM_PROFILE` |

Complex Retrieval, Continuity, and explicit Cognitive Budget objects are file-only in format version 1. There is no implicit environment-variable synthesis for their nested fields.

## 6. Current non-cognitive release defaults

RCFG2 currently supplies only defaults that already belonged to the release/startup boundary before calibration:

```text
runtime format version = 1
provider adapter        = openai_compatible
server host             = 127.0.0.1
server port             = 8090
```

These values appear with `canonical_default` provenance because that is the common RCFG1 source category. They are **not #1388 cognitive defaults**.

There is currently no default for:

- MEMORY retrieval counts/characters;
- Event Evidence retrieval counts/characters;
- Continuity capacity or lifetime;
- model context window;
- output reserve;
- State/Working Context/MEMORY/Event Evidence budget envelopes/floors;
- degradation step values;
- token-counter capability;
- cognitive runtime profile.

Until #1388 publishes calibrated profile authority, any non-empty `runtime.profile` selected from CLI, environment, or file fails closed with `invalid_combination`. RCFG2 never guesses profile values from a model name or context-window folklore.

## 7. Secret boundary and precedence

The config file may persist only an environment-variable reference:

```yaml
provider:
  api_key:
    env: OPENAI_API_KEY
```

A raw provider secret may enter the process through the existing dedicated environment input `RELAYLM_PROVIDER_API_KEY`. There is no raw CLI secret value contract.

Secret selection is deterministic:

```text
CLI env-name reference
    > raw RELAYLM_PROVIDER_API_KEY material
    > config-file env-name reference
    > no provider secret
```

An explicitly selected reference must resolve to a present, non-empty environment value. Failure is `secret_unavailable`; the resolver does not fall through to a lower source.

Resolved raw material lives only in `RuntimeSecretInputs`. Its field is excluded from representation. The non-secret `RuntimeConfig` may retain an env reference when the winning selector is CLI/file, but raw environment material is never copied into it.

Effective diagnostics report only:

```json
{
  "configured": true,
  "source": "cli|env|config_file",
  "material_source": "env"
}
```

They never emit the secret value or the referenced environment variable name.

## 8. RCFG2 resolved result

`resolve_runtime_config(...)` returns one `ResolvedRuntimeConfig` containing:

```text
RuntimeConfig
    non-secret validated effective config

RuntimeSecretInputs
    process-local provider secret material, redacted from repr

provenance
    immutable mapping of non-secret effective leaf -> EffectiveConfigValue

secret_effective
    EffectiveConfigSecret without material

config_path / config_path_source
    selected file identity and discovery provenance, if any
```

The resolver is deterministic for the same explicit inputs, file bytes, and environment mapping. It performs no network call, Character semantic read, persistence mutation, provider construction, or LLM generation.

## 9. Effective-config diagnostics

`ResolvedRuntimeConfig.effective_diagnostics()` is a content-free/secret-free machine-readable view.

Its shape is bounded to:

```json
{
  "format_version": 1,
  "config_path": {
    "value": "/selected/runtime.yaml",
    "source": "cli"
  },
  "values": {
    "provider.model": {
      "value": "model-id",
      "source": "config_file"
    }
  },
  "secrets": {
    "provider.api_key": {
      "configured": true,
      "source": "config_file",
      "material_source": "env"
    }
  },
  "validation_status": "valid"
}
```

The flattened `values` map may contain runtime configuration metadata and explicit numeric owner controls, but never:

- API-key values;
- secret-reference environment names;
- SOUL/Identity text;
- State keys or values;
- Event content;
- MEMORY content;
- Continuity semantic payload;
- conversation content.

## 10. Existing owner controls carried by configuration

RCFG2 parses explicit file controls into current owner types without changing their meaning:

- `runtime.memory_retrieval` -> release carriage for current MEMORY retrieval count/character controls;
- `runtime.event_retrieval` -> release carriage for current Event Evidence retrieval count/character controls;
- `runtime.continuity` -> explicit `ContinuityContext.max_items` / `ContinuityRuntime.lifetime_revisions` inputs;
- `runtime.cognitive_budget.total` -> `TotalBudgetConfig`;
- `runtime.cognitive_budget.policy` -> current deterministic #1387 Budget Plan/degradation types;
- `runtime.cognitive_budget.token_counter.mode` -> existing `TokenCountMode` unchanged;
- `runtime.cognitive_budget.token_counter.capability` -> assembly capability identifier only.

The token-counter capability name is not proof that such a capability exists. Capability availability and construction belong to RCFG3/doctor and must fail with `capability_unavailable` when unsupported.

Presence of any config value is not permission to alter Retrieval ranking, Context authority, Continuity acceptance/lifecycle, or Cognitive Budget degradation semantics.

## 11. Error taxonomy

Version-1 release configuration/preflight uses the RCFG1 categories:

```text
discovery_error
read_error
parse_error
unsupported_format_version
unknown_field
invalid_type
invalid_value
missing_required
invalid_combination
secret_unavailable
capability_unavailable
character_invalid
provider_invalid
```

RCFG2 produces discovery/read/parse/schema/value/missing/combination/secret failures. The later assembly/preflight layer owns machine capability, Character validation, and provider validation failures.

Errors include a safe field path and actionable message where practical, without secret material or character semantic payload.

## 12. Assembly and operator dependency shape

Current boundary after RCFG2:

```text
RCFG2 loader/resolver
  explicit file + env + named CLI inputs
        -> strict parse / validation
        -> leaf merge / provenance
        -> RuntimeConfig
        -> RuntimeSecretInputs
        -> redacted effective diagnostics

RCFG3 assembly
  RuntimeConfig + RuntimeSecretInputs
        -> CharacterDirectory
        -> OpenAICompatibleProvider
        -> owner-defined Retrieval controls
        -> ContinuityRuntime
        -> CognitiveBudgetRuntimeConfig
        -> serialized-input counter capability

RCFG4 operator CLI
  relaylm serve
  relaylm doctor
        -> same RCFG2 resolution
        -> same RCFG3 assembly/preflight boundary
```

`doctor` should remain non-generative and non-mutating with respect to character semantic state where practical.

RCFG5 may add canonical cognitive profile/default consumption only from current #1388 authority. It must not alter the semantic owner types above.

## 13. Preserved runtime invariants

Configuration loading and later assembly must preserve:

- exactly one ordinary semantic generation;
- buffered/streaming semantic equivalence;
- Character, State, MEMORY, Event, and Continuity authority separation;
- deterministic cognitive-budget degradation;
- protected-floor fail-before-generation;
- Retrieval semantic ownership;
- Continuity lifecycle ownership;
- no semantic-payload inspection for runtime policy selection.

> A release configuration can select and carry runtime policy; it cannot become a new semantic authority.