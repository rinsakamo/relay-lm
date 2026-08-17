# Release Runtime Configuration Contract

Status: RCFG1 contract for RelayLM v1 release runtime configuration. Owning Issue: #1446.

This contract defines the release-facing configuration boundary only. It does not choose cognitive semantics, retrieval relevance, Continuity lifecycle semantics, or calibrated numeric defaults.

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

## 2. Runtime configuration format

The runtime configuration file uses YAML and requires exact integer `format_version: 1`. Boolean, string-coerced, missing, or unsupported versions fail closed.

Version-1 top-level shape:

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

runtime:                   # optional; every child is explicit opt-in
  profile: profile-name    # reserved for #1388 canonical profile consumption

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

Every retrieval, Continuity, and cognitive number above is an **explicit example value only**, not a RelayLM default. #1388 remains the sole owner of canonical cognitive values and profile boundaries; #1371 remains the owner of Continuity lifecycle semantics and defines no release default here.

The serialized `policy` shape maps directly to the existing #1387 `BudgetDegradationPolicy`, `BudgetPlan`, envelope, and degradation-step types. RCFG2 may parse those types; it must not invent alternative degradation semantics.

`runtime.continuity.max_items` and `lifetime_revisions` are explicit lifecycle inputs already required by the Continuity owner. Their presence here does not establish default values.

`token_counter.capability` is an assembly capability identifier. RCFG1 does not claim that any arbitrary identifier is available. RCFG3/`doctor` must fail with `capability_unavailable` when the configured capability cannot construct the provider/model-specific serialized-input counter. `mode` carries the existing #1387 `TokenCountMode` values unchanged: `exact` or `conservative_estimate`.

## 3. Unknown fields and validation

Unknown keys fail with `unknown_field` at every mapping level. No version-1 key is silently ignored.

Validation is staged and fail-fast:

1. discover the explicitly selected configuration file;
2. read and parse YAML;
3. require a mapping and exact supported format version;
4. reject unknown keys and invalid field types/values;
5. resolve field precedence;
6. require complete Character/provider inputs;
7. validate cross-field combinations;
8. during assembly/preflight, validate Character Package, secret availability, provider compatibility, token-counter capability, and other machine requirements;
9. only after successful validation may `serve` begin accepting generation requests.

Configuration validation does not inspect SOUL, State, Event, MEMORY, Continuity payload, or user text to choose runtime policy. Character Package validity may be checked through its existing owner contract without reinterpreting semantic content.

## 4. Configuration discovery

Version 1 performs **no ambient filesystem search** for runtime configuration.

File selection is explicit:

```text
relaylm ... --config PATH
        > RELAYLM_CONFIG=PATH
        > no runtime config file
```

If an explicit path is supplied and cannot be read, RelayLM fails; it does not fall through to another file or silently start from a guessed working-directory config.

Absence of a config file is allowed only when all required values can be resolved from higher-precedence explicit inputs or future canonical defaults.

## 5. Leaf-level precedence

For every field that has the corresponding source binding, precedence is resolved per leaf:

```text
explicit CLI override
    > explicit environment override
    > runtime config file
    > canonical default/profile value
```

A higher-precedence source replaces only the leaf it explicitly supplies; it does not discard unrelated lower-source siblings. Missing and explicit false/zero are distinct values.

There is no generic arbitrary `--set key=value` override in the version-1 contract. RCFG4 may expose only named CLI arguments whose field mapping is fixed by this contract.

Initial named scalar bindings are:

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

Complex Retrieval, Continuity, and explicit Cognitive Budget structures have no generic environment/CLI expansion in format version 1. An explicit runtime-config leaf outranks any selected canonical profile value. Additional named overrides require a later contract change rather than implicit environment-variable synthesis.

Until #1388 publishes canonical profiles, a non-empty `runtime.profile` is only a schema-valid selector; resolution must fail closed rather than guess profile values.

## 6. Secret boundary

The runtime config file may persist only a secret reference:

```yaml
provider:
  api_key:
    env: OPENAI_API_KEY
```

It must not persist an API-key value. A raw provider secret may enter the process through the existing dedicated environment input `RELAYLM_PROVIDER_API_KEY`. RCFG4 must not add a raw `--api-key VALUE` argument because process argv and shell history are not an acceptable secret transport.

A CLI `--provider-api-key-env NAME` is a reference override, not a secret value. If selected, the named variable must exist at preflight/assembly time or resolution fails with `secret_unavailable`.

Resolved raw secret material is process-local `RuntimeSecretInputs`, separate from non-secret `RuntimeConfig` and from diagnostics. Its representation must redact secret values.

Generic diagnostics never emit the secret value. Effective secret diagnostics expose whether a secret is configured, the source that selected the secret/reference, and—when distinct—the material source category. For a config-file or CLI env reference, the selector source can therefore be `config_file` or `cli` while the material source is `env`.

## 7. Existing runtime controls carried by this contract

The contract mirrors current owner inputs without changing their meaning:

- `memory_retrieval` -> current MEMORY retrieval count/character controls;
- `event_retrieval` -> current Event Evidence retrieval count/character controls;
- `continuity` -> current process-local `ContinuityContext.max_items` and `ContinuityRuntime.lifetime_revisions` inputs;
- `cognitive_budget.total` -> current `TotalBudgetConfig`;
- `cognitive_budget.policy` -> current deterministic `BudgetDegradationPolicy` and owner envelopes;
- `cognitive_budget.token_counter.mode` -> existing `TokenCountMode` from #1387;
- `cognitive_budget.token_counter.capability` -> capability required to construct the current provider/model serialized-input counter.

Presence of a config value is not authority to alter selection/ranking/lifecycle/degradation semantics.

The release-owned server default remains loopback `127.0.0.1:8090`, matching the pre-RCFG startup path. External exposure requires an explicit override and remains observable in effective config.

## 8. Effective configuration

RCFG2 must resolve one effective non-secret configuration plus source provenance and separate process-local secret inputs. Non-secret leaves are representable as:

```json
{"value": "...", "source": "cli|env|config_file|canonical_default"}
```

A secret leaf is represented without material, for example:

```json
{"configured": true, "source": "config_file", "material_source": "env"}
```

The effective diagnostic surface may report only configuration metadata such as:

- runtime config format version and config-file source/path;
- Character directory selection, never Character semantic content;
- provider adapter/base URL/model identity;
- server host/port;
- enabled runtime layers;
- profile/default/explicit-override identity and provenance once available;
- cognitive capacity/reserve/envelopes when configured or canonically resolved;
- token-accounting capability identity and `TokenCountMode`;
- validation status.

It must never emit API-key values, SOUL/Identity text, State keys/values, Event content, MEMORY content, Continuity semantic payload, or conversation content.

## 9. Error taxonomy

Version-1 release configuration/preflight uses these stable categories:

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

Errors should include a safe field path and actionable message where possible, but never echo a secret value or semantic character payload.

## 10. CLI and assembly dependency shape

RCFG1 does not wire production runtime behavior. The next slices consume this contract as follows:

```text
RCFG2 loader/resolver
  explicit file + env + CLI inputs
        -> strict parse / leaf merge / provenance
        -> RuntimeConfig + RuntimeSecretInputs + redacted effective config

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

RCFG5 may add canonical profile/default consumption only from current #1388 authority. It must not change the semantic owner types above.

## 11. Preserved runtime invariants

Configuration assembly must preserve:

- exactly one ordinary semantic generation;
- buffered/streaming semantic equivalence;
- Character, State, MEMORY, Event, and Continuity authority separation;
- deterministic cognitive-budget degradation;
- protected-floor fail-before-generation;
- Retrieval semantic ownership;
- Continuity lifecycle ownership.

The configuration layer never inspects semantic payload to choose a policy.
