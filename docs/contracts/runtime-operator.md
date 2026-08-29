# Release Runtime Operator Contract

Status: current RelayLM v1 installed operator contract. Owning Issue: #1446.

The supported product entrypoint is `relaylm`. It resolves runtime configuration, runs non-generative preflight, assembles configured Cognitive Profiles, and starts the OpenAI-compatible service. It does not choose Cognitive Package semantics or invent calibrated numeric defaults; it carries an explicitly selected #1388 authority.

## Commands

```text
relaylm --version
relaylm doctor [runtime options] [--json]
relaylm serve [runtime options]
relaylm-eval
```

`init` remains deferred; the operator layer does not fabricate Cognitive Package memory, Identity, or secrets. First-party Starter Packages provide the shipped starting points for users who do not yet have a package root.

## Runtime options

Current named CLI overrides remain bounded:

```text
--config PATH
--profile-name NAME
--profile-root PATH
--provider-adapter NAME
--provider-base-url URL
--provider-model MODEL
--provider-api-key-env ENV_NAME
--host HOST
--port PORT
--calibration-profile NAME
--cognition-mode MODE
```

`--profile-name` plus `--profile-root` is the bounded single-Profile convenience surface. Multi-Profile registries and Profile-local physical-model overrides belong in `profiles[]` runtime YAML. There is no generic `--set`.

The matching environment convenience inputs are:

```text
RELAYLM_PROFILE_NAME
RELAYLM_PROFILE_ROOT
```

The removed Character-only `--character`, `RELAYLM_CHARACTER_DIR`, and top-level runtime `character:` schema are not compatibility aliases for Cognitive Profiles.

Existing named leaves preserve:

```text
CLI > environment > runtime file > canonical default
```

`--cognition-mode` selects only the existing #1533 execution-mode vocabulary and is paired with `RELAYLM_COGNITION_MODE` and `runtime.cognition.mode`. Omission resolves to the canonical `two_pass` topology default; `auto` and `shadow_two_pass` still fail ordinary serving admission later rather than being silently reinterpreted. Calibration selection does not rewrite this cognition mode.

`--calibration-profile` / `runtime.calibration_profile` selects the current named #1388 authority `fastcal-v1`. It carries desired `target_window=4096`, `output_allowance=512`, and authority `#1388 FastCal v1`; it is a different concept from a Cognitive Profile name and is never used to resolve the OpenAI request `model`. Unsupported names fail closed, and transient VRAM/admission observations are not part of the calibration identity.

## Cognitive Profile operator boundary

A configured Cognitive Profile has a public name and one Cognitive Package root. A Character Package is one valid specialization; machine-like roots use the same operator path.

The public request boundary is:

```text
OpenAI request model
  -> exact configured Cognitive Profile name
  -> Profile root + Profile runtime bundle
  -> physical provider/model
```

The public Profile ID and physical provider-model ID are separate. Multiple Profiles may use one physical model, and a supported Profile-local model override does not move host, backend, or secret configuration into the package.

`GET /v1/models` exposes configured public Profile IDs. It does not expose the global or Profile-local physical provider model as the selectable public identity.

## `doctor`

`doctor` performs the same configuration, preflight, and assembly admission used by `serve`, without model generation or semantic mutation.

It verifies, where applicable:

- runtime YAML/discovery/secret-reference validity;
- non-empty unique Cognitive Profile names and valid Profile roots;
- Character-like and machine-like Cognitive Package readability;
- persistence writability without creating semantic files;
- provider URL/model/backend configuration and supported Profile-local physical-model mappings;
- selected calibration profile, desired target window/output allowance, and #1388 provenance;
- selected cognition topology can be assembled for ordinary serving;
- selected token-counter capability and, for budgeted two-pass serving, explicit provider hard output limits compatible with the configured reserve;
- safe server bind-target syntax.

It does not probe model output, append Events, save State, rewrite MEMORY, or claim provider reachability merely from a configured URL.

Human-readable diagnostics include safe runtime metadata only. Current summaries expose each Profile's public name, root, and effective physical model, plus:

```text
provider adapter + backend + default physical model + base URL
server bind
cognition=<resolved mode>
memory/event/continuity/cognitive-budget enabled flags
```

Non-printable characters are escaped before line-oriented output. Secret material and Cognitive Package semantic payload are never printed.

`doctor --json` includes the content-free `effective_config` view and provenance for resolved runtime leaves. When selected, calibration identity, desired target window, output allowance, and authority are included as non-secret values. Profile routing metadata remains separate from SOUL, State, Event, MEMORY, Continuity, and conversation content.

## `serve`

`serve` uses exactly the successfully prepared assembly:

```text
resolve runtime config
  -> doctor-equivalent preflight
  -> RuntimeAssembly
  -> CognitiveProfileRegistry
  -> server.create_app(**assembly.app_kwargs())
  -> /v1/chat/completions
       request model -> one Profile
       -> selected cognition path
```

For Core 1.0, the release topology default is `two_pass`. Profile selection occurs before the ordinary turn is prepared; unknown Profile IDs therefore fail before Event/State mutation.

Explicit `single_pass` remains a compatibility/experimental cognition mode. Unresolved `auto` and evidence-only `shadow_two_pass` fail before serving.

Pass 1 and Pass 2 requests are carried independently. Omitted pass controls remain omitted unless the operator also enables a two-pass Cognitive Budget, in which case each pass must explicitly provide a hard `max_output_tokens` bound that the selected backend can realize and that does not exceed the configured reserve.

Streaming resolves the same Cognitive Profile as buffered execution and exposes Pass 1 text through the existing two-pass streaming owner. The same assembled two-pass Cognitive Budget is passed to buffered and streaming execution; the operator layer does not define a separate streaming budget policy.

Global turn serialization may remain in Core 1.0. In addition, #1978 makes obsolete response-first Pass 2 work single-flight at RelayLM's local request boundary: a newly admitted turn cancels and joins an older pending extraction before its new provider generation begins. This is not a claim about stronger remote scheduler behavior than the selected backend actually guarantees.

## Cognitive Budget

`runtime.cognitive_budget` carries #1387 total-budget semantics. With an explicit `fastcal-v1` selection, omitted total-window/reserved-output leaves use the selected #1388 values, while explicit total leaves win. In explicit `single_pass`, it constructs the existing single-pass budget runtime.

In `two_pass`, #1979 uses the one explicitly configured coarse total as the safety envelope for both real generation passes while preserving separate serialized-input counting for Pass 1 and Pass 2. The operator is not claiming that both prompts consume the same number of tokens; both must independently fit the same configured envelope.

Budgeted two-pass serving additionally requires:

```text
Pass 1 max_output_tokens is explicit
Pass 2 max_output_tokens is explicit
selected backend can truthfully carry the hard output limit
both hard limits <= cognitive_budget.total.reserved_output_tokens
registered token counter supports both two-pass serialized request shapes
```

Any missing or unsupported prerequisite fails before serving. In particular, calibration selection does not synthesize #1387 policy, degradation steps, token-counter capability, or pass output limits. The numerical recommendation remains auditable #1388 authority.

The current global token-counter configuration also cannot safely cover a Profile-local physical-model override. That combination fails closed rather than assuming cross-model counting equivalence.

## Provider backends

Backend names are provider-owned identities. Operator configuration does not silently downgrade a backend-specific selection to `generic`.

At this boundary:

- generic OpenAI-compatible serving is available, but generic compatibility alone does not attest specialized controls such as hard output-limit carriage;
- vLLM specialized assembly requires its explicit provider-owned reasoning capability attestation where reasoning controls are used;
- LM Studio is assembly-capable through the common OpenAI-compatible transport when no unsupported LM Studio-specific reasoning override is requested. Its resolved backend identity and diagnostics remain `lm_studio`.

Exact provider-specific reasoning and output-limit realization remain provider-owned. Unsupported explicit controls fail during assembly/preflight before serving; the operator layer does not guess or silently drop them.

## Installed-artifact gate

The `package-smoke` CI gate continuously proves that wheel and sdist can be built reproducibly, installed non-editably outside the repository checkout, and execute installed `relaylm --version`, `relaylm doctor`, and `relaylm-eval` without repository-relative dependencies.

The Starter artifact smoke additionally proves installed Character-like and machine-like Starter roots through the same Profile/runtime path. These are operator/distribution smokes, not actual-model quality runs.

## Errors

Configuration, assembly, and preflight failures use the existing typed runtime taxonomy and return status `2`. Successful `doctor`, normal `serve` shutdown, and `--version` return status `0`.

Unknown OpenAI request Profile IDs are API request-routing failures rather than operator-startup errors; the API rejects them before semantic turn preparation.

Error rendering must not expose API keys, Cognitive Package payload, arbitrary decoder exception text, or terminal-control injection.

## Ownership

The operator layer does not own:

- Cognitive Package semantics or Character specialization semantics;
- Pass 1 / Pass 2 semantics (#1533);
- stale extraction scheduling semantics (#1978);
- #1388 numeric calibration/default selection;
- #1387 Cognitive Budget arithmetic/degradation semantics;
- provider-specific capability/wire truth;
- Retrieval/Context/Continuity/State semantics;
- Identity/Event/MEMORY authority;
- actual-model Stage R evidence (#1386);
- distribution/tag/publication mechanics (#1447);
- group-chat or multi-agent scheduling.

## Remaining release-runtime work

The current `fastcal-v1` #1388 recommendation/default authority is carried through runtime configuration with explicit selection and provenance. Remaining repository-side operator work is limited to provider-specific capabilities and later owner-qualified changes; this contract does not add physical VRAM/KV guarantees or new cognition semantics.

Actual-model Stage R qualification is deliberately outside this operator transaction.

> The operator path binds public Cognitive Profiles to portable cognitive roots and carries release cognition/safety policy faithfully; it does not redefine either.
