# Release Runtime Configuration Contract

Status: RCFG1 contract + RCFG2 validated loader/resolver with provider backend selection follow-up for RelayLM v1. Owning Issue: #1446.

This contract defines the release-facing configuration boundary only. It does not choose cognitive semantics, Retrieval relevance, Continuity lifecycle semantics, provider-wire semantics, or calibrated cognitive numeric defaults.

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
- `src/relaylm/runtime_config_loader.py` — discovery, strict parse/validation, leaf resolution, process-local secret resolution, and content-free effective diagnostics;
- `src/relaylm/runtime_assembly.py` — assembly/preflight consumption of already-owned provider and runtime controls.

Provider backend machine IDs and backend-specific wire meaning remain owned by `provider_and_api`. Runtime configuration only selects and carries those owner-defined IDs.

## 2. Runtime configuration format

The runtime configuration file uses YAML and requires exact integer `format_version: 1`. Boolean, string-coerced, missing, or unsupported file versions fail closed.

Version-1 shape:

```yaml
format_version: 1

character:
  directory: /path/to/Character

provider:
  adapter: openai_compatible
  backend: vllm            # generic | vllm | lm_studio
  base_url: http://127.0.0.1:8000/v1
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

`provider.adapter` and `provider.backend` are distinct:

```text
adapter = API protocol family
backend = implementation/dialect serving that protocol
```

For the current adapter:

```text
adapter: openai_compatible
backend: generic | vllm | lm_studio
```

The backend vocabulary comes from the provider-owned `OpenAICompatibleBackendId`. Human spellings such as `vLLM`, `VLLM`, `LM Studio`, and `lm-studio` may be accepted only through the provider owner's bounded alias table; the resolved runtime value and diagnostics always carry the canonical machine ID. There is no fuzzy matching or backend auto-detection in configuration resolution.

Every Retrieval, Continuity, and Cognitive Budget number above is an **explicit schema example only**, not a RelayLM default. #1388 remains the sole owner of canonical cognitive numeric values and profile boundaries. #1371 remains the owner of Continuity lifecycle semantics and supplies no release default here.

The serialized Cognitive Budget policy maps directly into existing #1387 types: `TotalBudgetConfig`, `BudgetPlan`, `CountEnvelope`, `CountCharacterEnvelope`, `BudgetDegradationStep`, `BudgetDegradationPolicy`, and `TokenCountMode`. The configuration layer does not invent parallel budget semantics.

## 3. Strict file validation

A selected runtime file is validated before precedence resolution.

The loader requires:

1. YAML root is a mapping;
2. `format_version` exists and is exact integer `1`;
3. duplicate YAML mapping keys are rejected rather than using last-value-wins behavior;
4. unknown keys fail at every governed mapping level;
5. configured scalar types are exact — boolean is not accepted as integer;
6. configured strings that are required to be meaningful are non-empty;
7. `provider.backend` must resolve through the provider-owned backend vocabulary rather than a runtime-owned vendor table;
8. nested explicit owner-control objects contain exactly their required keys;
9. owner-defined value invariants such as non-negative budgets, floors, tier order, and valid `TokenCountMode` are validated by the existing owner types;
10. raw secret material is never a valid config-file field.

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

The resolver exposes the first input programmatically as `config_path`; the operator CLI binds it to its public spelling.

If an explicitly selected path cannot be read, resolution fails with `read_error`. It does not fall through to `RELAYLM_CONFIG` or a guessed current-working-directory file.

If there is no file, the v1 runtime schema version remains `1` and required runtime leaves may be supplied by explicit environment/CLI inputs. This preserves the existing env-only startup boundary without turning the Character Package into runtime config.

## 5. Leaf-level precedence

For every field with a named override binding:

```text
explicit CLI/programmatic override
    > explicit environment override
    > runtime config file
    > canonical default/profile value
```

Resolution is per leaf. A higher source replaces only the leaf it explicitly supplies; it does not erase unrelated lower-source siblings. Missing and explicit zero are distinct.

There is no generic arbitrary `--set key=value` contract in version 1.

Named scalar bindings are:

| Runtime field | Programmatic/CLI shape | Environment |
|---|---|---|
| config file | `--config` | `RELAYLM_CONFIG` |
| `character.directory` | `--character` | `RELAYLM_CHARACTER_DIR` |
| `provider.adapter` | `--provider-adapter` | `RELAYLM_PROVIDER_ADAPTER` |
| `provider.backend` | `provider_backend` override; CLI exposure may follow | `RELAYLM_PROVIDER_BACKEND` |
| `provider.base_url` | `--provider-base-url` | `RELAYLM_PROVIDER_BASE_URL` |
| `provider.model` | `--provider-model` | `RELAYLM_PROVIDER_MODEL` |
| provider secret reference | `--provider-api-key-env` | raw secret via `RELAYLM_PROVIDER_API_KEY` |
| `server.host` | `--host` | `RELAYLM_HOST` |
| `server.port` | `--port` | `RELAYLM_PORT` |
| `runtime.profile` | `--profile` | `RELAYLM_PROFILE` |

Complex Retrieval, Continuity, and explicit Cognitive Budget objects are file-only in format version 1. There is no implicit environment-variable synthesis for their nested fields.

## 6. Current non-cognitive release defaults

The resolver currently supplies only release/startup defaults, not cognitive calibration values:

```text
runtime format version = 1
provider adapter        = openai_compatible
provider backend        = generic
server host             = 127.0.0.1
server port             = 8090
```

`provider.backend = generic` preserves the pre-backend-selection behavior: use the canonical OpenAI-compatible adapter without claiming any backend-specific dialect. It is not a guess about the upstream implementation.

These values appear with `canonical_default` provenance because that is the common configuration source category. They are **not #1388 cognitive defaults**.

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

Until #1388 publishes calibrated profile authority, any non-empty `runtime.profile` selected from CLI, environment, or file fails closed with `invalid_combination`. The resolver never guesses profile values from a model name or context-window folklore.

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

## 8. Resolved result

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

Backend display spelling is never retained as effective identity. For example:

```json
{
  "values": {
    "provider.adapter": {
      "value": "openai_compatible",
      "source": "canonical_default"
    },
    "provider.backend": {
      "value": "vllm",
      "source": "config_file"
    }
  }
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

The loader parses explicit file controls into current owner types without changing their meaning:

- `provider.backend` -> provider-owned `OpenAICompatibleBackendId`;
- `runtime.memory_retrieval` -> release carriage for current MEMORY retrieval count/character controls;
- `runtime.event_retrieval` -> release carriage for current Event Evidence retrieval count/character controls;
- `runtime.continuity` -> explicit `ContinuityContext.max_items` / `ContinuityRuntime.lifetime_revisions` inputs;
- `runtime.cognitive_budget.total` -> `TotalBudgetConfig`;
- `runtime.cognitive_budget.policy` -> current deterministic #1387 Budget Plan/degradation types;
- `runtime.cognitive_budget.token_counter.mode` -> existing `TokenCountMode` unchanged;
- `runtime.cognitive_budget.token_counter.capability` -> assembly capability identifier only.

The token-counter capability name is not proof that such a capability exists. Capability availability and construction belong to assembly/doctor and must fail with `capability_unavailable` when unsupported.

Likewise, selecting a known backend ID is not proof that RelayLM currently has a realizer for that backend. Until a backend-specific assembly path merges, selecting `vllm` or `lm_studio` fails with `capability_unavailable` at `provider.backend` before generation instead of silently falling through to `generic` behavior.

Presence of any config value is not permission to alter Retrieval ranking, Context authority, Continuity acceptance/lifecycle, Cognitive Budget degradation semantics, or provider wire semantics.

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

Resolution produces discovery/read/parse/schema/value/missing/combination/secret failures. Assembly/preflight owns machine capability, Character validation, backend-realizer availability, and provider validation failures.

Errors include a safe field path and actionable message where practical, without secret material or character semantic payload.

## 12. Assembly and operator dependency shape

Current boundary:

```text
loader/resolver
  explicit file + env + named programmatic inputs
        -> strict parse / validation
        -> leaf merge / provenance
        -> canonical provider backend ID
        -> RuntimeConfig
        -> RuntimeSecretInputs
        -> redacted effective diagnostics

assembly
  RuntimeConfig + RuntimeSecretInputs
        -> provider adapter + selected backend dialect capability
        -> CharacterDirectory
        -> owner-defined Retrieval controls
        -> ContinuityRuntime
        -> CognitiveBudgetRuntimeConfig
        -> serialized-input counter capability

operator
  relaylm serve
  relaylm doctor
        -> same resolution
        -> same assembly/preflight boundary
```

`doctor` remains non-generative and non-mutating with respect to character semantic state where practical.

A later provider transaction may make `vllm` assembly-capable. That transaction must consume the canonical backend ID defined by `provider_and_api`; configuration must not duplicate the vLLM wire mapping.

RCFG5 may add canonical cognitive profile/default consumption only from current #1388 authority. It must not alter the semantic owner types above.

## 13. Preserved runtime invariants

Configuration loading and later assembly must preserve:

- adapter/protocol identity remains distinct from backend implementation identity;
- backend machine IDs are canonicalized before effective diagnostics/evidence consumption;
- unknown or unavailable backend selection fails closed rather than being guessed or silently ignored;
- buffered/streaming semantic equivalence;
- Character, State, MEMORY, Event, and Continuity authority separation;
- deterministic cognitive-budget degradation;
- protected-floor fail-before-generation;
- Retrieval semantic ownership;
- Continuity lifecycle ownership;
- no semantic-payload inspection for runtime policy selection.

> A release configuration can select and carry runtime policy; it cannot become a new semantic authority.