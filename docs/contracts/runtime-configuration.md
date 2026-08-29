# Release Runtime Configuration Contract

Status: current RelayLM v1 release configuration contract. Owning Issue: #1446.

Runtime configuration carries machine/operator policy and public Cognitive Profile bindings into existing semantic owners. It does not become Cognitive Package authority, provider-wire authority, or #1388 calibration authority.

## Boundary

```text
portable Cognitive Package
        !=
Cognitive Profile binding
        !=
runtime / physical provider configuration
        !=
semantic authority
```

A Character Package is one valid Cognitive Package specialization. Runtime configuration may bind Character-like or machine-like roots without changing package semantics.

Canonical implementation:

- `src/relaylm/runtime_config.py`
- `src/relaylm/runtime_config_loader.py`
- `src/relaylm/runtime_assembly.py`
- `src/relaylm/cognitive_profile.py`

Cognitive Packages contain portable cognitive data. Public Profile names, provider endpoints, backend identity, secrets, server bind settings, cognition topology, pass controls, token counters, and other machine-specific policy belong to runtime configuration instead.

## Format

Runtime YAML uses exact integer `format_version: 1`. Unknown keys, duplicate YAML keys, wrong scalar types, unsupported closed-vocabulary values, and raw secret material fail closed.

Current shape:

```yaml
format_version: 1

profiles:
  - name: relm
    root: /path/to/characters/relm

  - name: medical-soap
    root: /path/to/machines/medical-soap
    provider:
      model: specialist-physical-model

provider:
  adapter: openai_compatible
  backend: lm_studio        # generic | vllm | lm_studio
  base_url: http://127.0.0.1:1234/v1
  model: default-physical-model
  api_key:                  # optional reference only
    env: OPENAI_API_KEY

server:
  host: 127.0.0.1
  port: 8090

runtime:
  # Core 1.0 topology default is two_pass when this block is omitted.
  cognition:
    mode: two_pass          # two_pass | single_pass | shadow_two_pass | auto
    pass1:                  # optional normally; hard limit required with two-pass budget
      reasoning_mode: "off" # off | bounded; quote "off" because YAML treats bare off as bool
      temperature: 0
      top_p: 1
      max_output_tokens: 512
    pass2:
      reasoning_mode: bounded
      reasoning_budget: 256
      max_output_tokens: 256
      structured_output_mode: native  # plain | native | auto

  # Explicit #1388 execution/calibration selection. This is not a Cognitive Profile.
  calibration_profile: fastcal-v1

  memory_retrieval:
    max_chunks: 4
    max_chars: 4096

  event_retrieval:
    max_events: 4
    max_chars: 4096

  continuity:
    max_items: 8
    lifetime_revisions: 4

  # #1387 total-budget semantics. In two_pass, this one explicit coarse total
  # is applied to both real passes while their serialized inputs are counted separately.
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

Numbers in the example are examples, not release defaults. The `fastcal-v1` selection below is the one current named #1388 calibration authority; it is not selected unless the operator configures it. The example uses a backend with declared hard output-limit carriage because a budgeted two-pass path requires that capability.

## Cognitive Profiles

`profiles[]` is the public request-routing registry for Core 1.0.

Each entry requires:

```text
name
  non-empty unique public Cognitive Profile ID
  exact value accepted in OpenAI request `model`

root
  one Cognitive Package root
  may be Character-like or machine-like

provider.model
  optional physical-model override for this Profile
```

The global `provider` block remains the machine/runtime default. A Profile may override only explicitly supported leaves; Core 1.0 currently supports the physical `model` leaf. Provider hosts, backend identity, API keys, server settings, and secrets do not move into Cognitive Packages.

Public Profile identity and physical provider-model identity are intentionally different concepts. Multiple Profiles may share the same physical model. A request selects exactly one Profile before semantic turn preparation; unknown Profile IDs fail before Event/State mutation.

Each Profile root owns its own State/Event/MEMORY persistence boundary. Runtime configuration must never use one Profile selection to read or mutate another Profile root.

### Environment and CLI binding

The bounded single-Profile CLI/environment convenience surface is:

```text
--profile-name NAME
--profile-root PATH
RELAYLM_PROFILE_NAME
RELAYLM_PROFILE_ROOT
```

These values construct one `profiles[]` entry when no runtime-file list supplies the registry. They are not aliases for the removed Character-only runtime schema.

## Cognition carriage

#1533 owns cognition semantics. Configuration only carries them.

For Core 1.0:

- `two_pass` is the release/reference topology and the canonical topology default;
- `single_pass` remains an explicit compatibility/experimental mode;
- `shadow_two_pass` is evidence-only and ordinary release assembly rejects it;
- `auto` remains reserved for a future cognition-profile resolution and ordinary release assembly rejects it while unresolved. Selecting a calibration profile does not rewrite the cognition topology.

The topology default does **not** imply numeric pass defaults. With no explicit pass controls, both `CognitionPassRequest` values contain omitted reasoning/decoding/output controls. Provider behavior must therefore remain truthful about what was requested, omitted, unsupported, or applied.

Pass 1 and Pass 2 controls are independently represented. The configuration layer does not infer stronger Pass 2 reasoning simply because a request is Pass 2.

When `two_pass` is combined with `runtime.cognitive_budget`, omission semantics become intentionally stricter for output limits: both `pass1.max_output_tokens` and `pass2.max_output_tokens` must be explicit because the configured reserve must dominate a real provider-side hard generation bound for each pass.

### Calibration-profile naming

`runtime.calibration_profile` belongs to #1388 execution/default policy and is distinct from `profiles[].name` Cognitive Profiles. The current supported selection is `fastcal-v1`, whose auditable values are `target_window: 4096`, `output_allowance: 512`, and authority `#1388 FastCal v1`. The target is a desired Cognitive Budget window, not a physical VRAM/KV guarantee; transient free VRAM, profiler admission, and one launch's effective KV capacity are runtime/operator observations. An old `runtime.profile` value is not silently reinterpreted as a Cognitive Profile or calibration profile. Unsupported calibration names fail closed.

### Pass 2 structured-output transport

Only `runtime.cognition.pass2` may carry:

```yaml
structured_output_mode: plain  # plain | native | auto
```

The values mean:

```text
plain
  use ordinary OpenAI-compatible message content containing RelayLM-owned JSON IR

native
  send provider-native response_format=json_schema for the current Pass 2 extraction wire

auto
  use native only when affirmative structured-output capability evidence is available;
  otherwise use plain
```

Omitting the field preserves the previously qualified `plain` transport. This is a compatibility default, not a claim that `plain` is the eventual calibrated #1388 recommendation.

`structured_output_mode` is invalid under `pass1`. Pass 1 is visible conversation and must not acquire the Pass 2 extraction schema.

Explicit `native` is not silently downgraded. If the selected provider/backend rejects the native request, the provider boundary fails closed. `auto` is the conservative option when the operator wants capability-gated selection rather than a forced native request.

The switch affects only how Pass 2 structure is constrained on the external provider wire. It does not change the Pass 2 semantic prompt, RelayLM JSON parsing, typed State/Continuity construction, source validation, or commit authority.

## Cognitive Budget boundary

`runtime.cognitive_budget` carries the existing #1387 total-budget equation, deterministic degradation policy, and token-counter capability selection. When an explicit Cognitive Budget is present together with `calibration_profile: fastcal-v1`, omitted `total.model_context_window` and `total.reserved_output_tokens` resolve to the #1388 values `4096` and `512`. Explicit total leaves remain higher precedence and are not overwritten. The calibration selection alone never creates a Cognitive Budget; `policy` and `token_counter` remain required and are never synthesized.

For explicit `single_pass`, the structure maps to the existing single-pass `CognitiveBudgetRuntimeConfig`.

For `two_pass`, #1979 deliberately reuses the same configuration shape rather than adding a second budget schema. The one explicitly configured total is a coarse safety envelope applied to both real passes:

```text
runtime.cognitive_budget.total
        -> Pass 1 total equation
        -> Pass 2 total equation
```

Pass 1 and Pass 2 still count their distinct serialized request shapes independently. Reusing the coarse total does not assert that the two prompt sizes are equal and does not create a numeric default.

Budgeted two-pass release admission requires all of the following:

```text
pass1.max_output_tokens is explicit
pass2.max_output_tokens is explicit
selected backend truthfully supports provider hard output-limit carriage
pass1.max_output_tokens <= cognitive_budget.total.reserved_output_tokens
pass2.max_output_tokens <= cognitive_budget.total.reserved_output_tokens
token-counter capability implements both two-pass serialized request counters
```

Missing or unsupported prerequisites fail before generation. `generic` OpenAI compatibility alone is not affirmative hard-limit capability evidence.

A Cognitive Budget cannot currently be shared across Profile-specific physical-model overrides because its token-counter configuration is global. That combination fails closed rather than guessing cross-model accounting.

Direct `memory_retrieval` / `event_retrieval` budgets also remain mutually exclusive with Cognitive Budget because the Cognitive Budget policy already owns those layer envelopes.

## Discovery and precedence

Runtime-file discovery is deterministic:

```text
explicit --config path
  > RELAYLM_CONFIG
  > no file
```

Named scalar leaves use:

```text
CLI/programmatic override
  > environment
  > config file
  > canonical default
```

Current named bindings include single-Profile name/root convenience inputs, provider adapter/base URL/model/secret reference, server host/port, calibration-profile selection, and cognition execution mode. Cognition mode is exposed as:

```text
--cognition-mode MODE
RELAYLM_COGNITION_MODE
runtime.cognition.mode
```

All three select only the existing #1533 closed vocabulary. They do not create a new mode or numeric policy. CLI beats environment, environment beats runtime YAML, and omission falls back to canonical `two_pass`.

Complex multi-Profile registries, Profile-local provider mappings, Pass 1/Pass 2 controls, including `pass2.structured_output_mode`, Retrieval, Continuity, and Cognitive Budget structures remain file-owned in format version 1. There is no generic `--set key=value` surface.

## Current defaults

Only owner-approved startup/topology defaults exist here, plus the explicitly selectable named calibration authority:

```text
format_version            = 1
provider.adapter          = openai_compatible
provider.backend          = generic
server.host               = 127.0.0.1
server.port               = 8090
runtime.cognition.mode    = two_pass
```

There is no default public Cognitive Profile name or root: at least one Profile binding is required.

`runtime.calibration_profile` has no default selection. If explicitly selected, `fastcal-v1` exposes `target_window = 4096`, `output_allowance = 512`, and `authority = #1388 FastCal v1` through effective configuration diagnostics. It does not provide reasoning/decoding values, retrieval or Continuity controls, a BudgetPlan/degradation policy, a token-counter implementation, provider capability, or a physical memory guarantee.

`runtime.cognition.mode = two_pass` comes from #1533 architecture authority. It is not a #1388 numeric calibration value.

For Pass 2 structured-output transport, omission preserves the established `plain` path. This compatibility behavior is represented by omission in the resolved request rather than by inventing a calibration/default value.

There are no calibrated defaults here for reasoning effort, decoding values, retrieval counts, Continuity lifetime/capacity, Cognitive Budget envelopes, token-counter capability, or an eventual preferred Pass 2 structured-output transport. The only current calibration-owned numeric carriage is the explicitly selected `fastcal-v1` total-window/output-reserve pair described above.

## Provider identity

`provider.adapter` and `provider.backend` are separate identities:

```text
adapter = API protocol family
backend = selected implementation/dialect
```

The backend vocabulary is provider-owned. Runtime configuration resolves only the canonical machine IDs `generic`, `vllm`, and `lm_studio`; it does not perform backend detection or duplicate provider wire mappings.

A known backend name does not by itself prove that every specialized capability is available. Assembly/preflight may reuse the common OpenAI-compatible transport while preserving the selected backend identity, but any requested backend-specific control still requires a proven provider-owned realizer and otherwise fails closed.

The same rule applies to hard output limits and `structured_output_mode=auto`: backend naming or generic OpenAI compatibility is not sufficient affirmative capability evidence by itself. Assembly consumes provider-owned capability truth; it does not infer support from field spelling.

## Secrets

The file may persist only an environment-variable reference. Raw provider secret material may enter through the dedicated process environment but lives only in `RuntimeSecretInputs` and is excluded from representations and effective diagnostics.

Secret selection remains deterministic and an explicitly selected missing/empty reference does not fall through to a lower source.

## Effective diagnostics

`ResolvedRuntimeConfig.effective_diagnostics()` exposes non-secret effective values plus provenance. Profile names, roots, and effective physical-model mappings are content-free runtime metadata and may be reported; semantic package payload is not.

Current diagnostics include file-owned pass controls and Cognitive Budget leaves through collected provenance, plus selected calibration identity, desired target window, output allowance, and `#1388 FastCal v1` authority. Operator evidence can distinguish calibrated defaults from explicit total/reserve settings without reading Cognitive Package semantic payload.

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

`character_invalid` is the retained release error-code spelling for invalid portable package data; it does not mean runtime roots are restricted to Character Packages.

Errors expose safe configuration metadata only.

## Invariants

Runtime configuration must preserve:

- one request selects exactly one configured Cognitive Profile before semantic turn preparation;
- Profile names are unique public IDs and Profile roots keep State/Event/MEMORY authority isolated;
- public Profile identity remains distinct from physical provider/model identity;
- Character remains one Cognitive Package specialization rather than the runtime root type;
- two-pass topology ownership in #1533 and stale-extraction scheduling ownership in #1978;
- Pass 2 structured-output semantics ownership in #1533 and external wire realization in the provider lane;
- Cognitive Budget arithmetic/degradation ownership in #1387;
- numeric/calibration-profile ownership in #1388;
- provider capability/wire ownership in the provider lane;
- budgeted two-pass hard output limits never exceed the configured output reservation;
- State/Event/MEMORY/Continuity semantic authority separation;
- buffered/streaming cognition, Profile-selection, and two-pass budget equivalence;
- no semantic-payload inspection for runtime-policy selection;
- fail-closed unsupported capability behavior;
- no silent fallback from explicit Pass 2 `native` to `plain`.

> Configuration binds public Cognitive Profiles to portable roots and carries selected runtime policy. It does not manufacture semantics or calibrated defaults.
