# Release Runtime Operator Contract

Status: current RelayLM v1 installed operator contract. Owning Issue: #1446.

The supported product entrypoint is `relaylm`. It resolves runtime configuration, runs non-generative preflight, assembles configured Cognitive Profiles, and starts the OpenAI-compatible service. It does not choose Cognitive Package semantics or calibrated numeric defaults.

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

`--cognition-mode` selects only the existing #1533 execution-mode vocabulary and is paired with `RELAYLM_COGNITION_MODE` and `runtime.cognition.mode`. Omission resolves to the canonical `two_pass` topology default; `auto` and `shadow_two_pass` still fail ordinary serving admission later rather than being silently reinterpreted.

`--calibration-profile` / `runtime.calibration_profile` is reserved for #1388 execution/default policy. It is a different concept from a Cognitive Profile name and is never used to resolve the OpenAI request `model`.

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
- selected cognition topology can be assembled for ordinary serving;
- selected token-counter capability when the existing single-pass Cognitive Budget is configured;
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

`doctor --json` includes the content-free `effective_config` view and provenance for resolved runtime leaves. Profile routing metadata remains separate from SOUL, State, Event, MEMORY, Continuity, and conversation content.

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

Pass 1 and Pass 2 requests are carried independently. Omitted pass controls remain omitted; the operator layer does not manufacture reasoning/decoding/output values.

Streaming resolves the same Cognitive Profile as buffered execution and exposes Pass 1 text through the existing two-pass streaming owner. The operator layer does not define a separate streaming routing or cognition policy.

Global turn serialization may remain in Core 1.0. Profile routing does not imply group-chat orchestration or concurrent multi-profile scheduling; the required property is deterministic one-request -> one-Profile execution with isolated Profile-root authority.

## Cognitive Budget

The current explicit `runtime.cognitive_budget` is single-pass #1387 authority. Until #1388 publishes two-pass per-pass budget/profile values, `two_pass + runtime.cognitive_budget` fails closed rather than copying one total into both passes.

The current global single-pass token-counter configuration also cannot safely cover a Profile-local physical-model override. That combination fails closed rather than assuming cross-model counting equivalence.

## Provider backends

Backend names are provider-owned identities. Operator configuration does not silently downgrade a backend-specific selection to `generic`.

At this boundary:

- generic OpenAI-compatible serving is available;
- vLLM specialized assembly requires its explicit provider-owned capability attestation;
- LM Studio is assembly-capable through the common OpenAI-compatible transport when no unsupported LM Studio-specific reasoning override is requested. Its resolved backend identity and diagnostics remain `lm_studio`.

Exact provider-specific reasoning realization remains provider-owned. Unsupported explicit reasoning controls fail during assembly/preflight before serving; the operator layer does not guess or silently drop them.

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
- #1388 numeric calibration/default selection;
- provider-specific capability/wire truth;
- Retrieval/Context/Continuity/State semantics;
- Identity/Event/MEMORY authority;
- actual-model Stage R evidence (#1386);
- distribution/tag/publication mechanics (#1447);
- group-chat or multi-agent scheduling.

## Remaining release-runtime work

After Cognitive Profile routing, ordinary two-pass serving, non-reasoning LM Studio assembly, and named cognition-mode selection are wired, the remaining repository-side operator work is bounded:

1. consume #1388 calibrated two-pass profile/default authority once published;
2. consume provider-specific reasoning capability only after its provider owner proves and implements the wire;
3. re-run installed release-candidate smoke when an authorized candidate exists.

Actual-model Stage R qualification is deliberately outside this operator transaction.

> The operator path binds public Cognitive Profiles to portable cognitive roots and carries release cognition policy faithfully; it does not redefine either.
