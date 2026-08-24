# Release Runtime Configuration Contract

Status: current RelayLM v1 release configuration contract. Owning Issue: #1446.

Runtime configuration carries machine/operator policy into existing semantic owners. It does not become Character authority, provider-wire authority, or #1388 calibration authority.

## Boundary

```text
portable Character Package
        !=
runtime configuration
        !=
semantic authority
```

Canonical implementation:

- `src/relaylm/runtime_config.py`
- `src/relaylm/runtime_config_loader.py`
- `src/relaylm/runtime_assembly.py`

The Character Package contains portable character data. Provider endpoints, backend identity, secrets, server bind settings, cognition topology, pass controls, token counters, and machine-specific paths belong to runtime configuration instead.

## Format

Runtime YAML uses exact integer `format_version: 1`. Unknown keys, duplicate YAML keys, wrong scalar types, unsupported closed-vocabulary values, and raw secret material fail closed.

Current shape:

```yaml
format_version: 1

character:
  directory: /path/to/Character

provider:
  adapter: openai_compatible
  backend: generic          # generic | vllm | lm_studio
  base_url: http://127.0.0.1:1234/v1
  model: model-id
  api_key:                  # optional reference only
    env: OPENAI_API_KEY

server:
  host: 127.0.0.1
  port: 8090

runtime:
  # Core 1.0 topology default is two_pass when this block is omitted.
  cognition:
    mode: two_pass          # two_pass | single_pass | shadow_two_pass | auto
    pass1:                  # optional; omitted values stay omitted
      reasoning_mode: off   # off | bounded; no hidden default
      temperature: 0
      top_p: 1
      max_output_tokens: 512
    pass2:
      reasoning_mode: bounded
      reasoning_budget: 256
      max_output_tokens: 256

  # Reserved for #1388. Any non-empty value currently fails closed.
  profile: profile-name

  memory_retrieval:
    max_chunks: 4
    max_chars: 4096

  event_retrieval:
    max_events: 4
    max_chars: 4096

  continuity:
    max_items: 8
    lifetime_revisions: 4

  # Existing #1387 single-pass Cognitive Budget carriage. Until #1388
  # publishes per-pass release budget authority, this is valid only with
  # explicit cognition.mode: single_pass.
  cognitive_budget:
    total:
      model_context_window: 32768
      reserved_output_tokens: 2048
    policy:
      initial_plan:
        canonical_state: {max_items: 32, floor_items: 8}
        working_context: {max_items: 16, floor_items: 2, max_chars: 12000, floor_chars: 1000}
        retrieved_memory: {max_items: 8, floor_items: 0, max_chars: 8000, floor_chars: 0}
        event_evidence: {max_items: 8, floor_items: 0, max_chars: 8000, floor_chars: 0}
      steps: []
    token_counter:
      capability: implementation-id
      mode: exact
```

Numbers in the example are examples, not release defaults.

## Cognition carriage

#1533 owns cognition semantics. Configuration only carries them.

For Core 1.0:

- `two_pass` is the release/reference topology and the canonical topology default;
- `single_pass` remains an explicit compatibility/experimental mode;
- `shadow_two_pass` is evidence-only and ordinary release assembly rejects it;
- `auto` requires future #1388 profile resolution and ordinary release assembly rejects it while unresolved.

The topology default does **not** imply numeric pass defaults. With no explicit pass controls, both `CognitionPassRequest` values contain omitted reasoning/decoding/output controls. Provider behavior must therefore remain truthful about what was requested, omitted, unsupported, or applied.

Pass 1 and Pass 2 controls are independently represented. The configuration layer does not infer stronger Pass 2 reasoning simply because a request is Pass 2.

## Cognitive Budget boundary

The existing `runtime.cognitive_budget` is the #1387 single-pass budget contract. RelayLM does not duplicate that one total into Pass 1 and Pass 2 by assumption.

Until #1388 publishes calibrated two-pass budget/profile authority:

```text
two_pass + runtime.cognitive_budget -> invalid_combination
single_pass + runtime.cognitive_budget -> existing #1387 behavior
```

This is deliberate fail-closed behavior, not a missing hidden default.

## Discovery and precedence

Runtime-file discovery is deterministic:

```text
explicit --config path
  > RELAYLM_CONFIG
  > no file
```

Existing named scalar overrides keep leaf precedence:

```text
CLI/programmatic override
  > environment
  > config file
  > canonical default
```

Current named bindings include Character, provider adapter/base URL/model/secret reference, server host/port, and reserved profile selection. Complex cognition pass controls, Retrieval, Continuity, and Cognitive Budget structures are file-owned in format version 1 unless a later bounded operator transaction adds a named override.

There is no generic `--set key=value` surface.

## Current defaults

Only owner-approved startup/topology defaults exist here:

```text
format_version            = 1
provider.adapter          = openai_compatible
provider.backend          = generic
server.host               = 127.0.0.1
server.port               = 8090
runtime.cognition.mode    = two_pass
```

`runtime.cognition.mode = two_pass` comes from #1533 architecture authority. It is not a #1388 numeric calibration value.

There are no defaults here for reasoning effort, decoding values, output budgets, context window, retrieval counts, Continuity lifetime/capacity, Cognitive Budget envelopes, token-counter capability, or runtime profile.

## Provider identity

`provider.adapter` and `provider.backend` are separate identities:

```text
adapter = API protocol family
backend = selected implementation/dialect
```

The backend vocabulary is provider-owned. Runtime configuration resolves only the canonical machine IDs `generic`, `vllm`, and `lm_studio`; it does not perform backend detection or duplicate provider wire mappings.

A known backend name does not by itself prove that its specialized runtime capability is available. Assembly/preflight owns that check and must fail rather than silently masquerading as `generic`.

## Secrets

The file may persist only an environment-variable reference. Raw provider secret material may enter through the dedicated process environment but lives only in `RuntimeSecretInputs` and is excluded from representations and effective diagnostics.

Secret selection remains deterministic and an explicitly selected missing/empty reference does not fall through to a lower source.

## Effective diagnostics

`ResolvedRuntimeConfig.effective_diagnostics()` exposes non-secret effective values plus provenance. Current diagnostics include `runtime.cognition.mode`, so `doctor --json` can distinguish the product topology without reading Character semantic payload.

Diagnostics never include API keys, secret environment-variable names, SOUL text, State values, Event/MEMORY content, Continuity semantic payload, or conversation text.

## Errors

Release configuration/preflight uses the stable typed categories including:

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

Errors expose safe configuration metadata only.

## Invariants

Runtime configuration must preserve:

- two-pass topology ownership in #1533;
- numeric/profile ownership in #1388;
- provider capability/wire ownership in the provider lane;
- Character/State/Event/MEMORY/Continuity semantic authority separation;
- buffered/streaming cognition-policy equivalence;
- no semantic-payload inspection for runtime-policy selection;
- fail-closed unsupported capability behavior.

> Configuration carries selected policy. It does not manufacture semantics or defaults.