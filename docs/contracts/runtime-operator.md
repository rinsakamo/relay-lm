# Release Runtime Operator Contract

Status: current RelayLM v1 installed operator contract. Owning Issue: #1446.

The supported product entrypoint is `relaylm`. It resolves runtime configuration, runs non-generative preflight, assembles current owner objects, and starts the OpenAI-compatible service. It does not choose Character semantics or calibrated numeric defaults.

## Commands

```text
relaylm --version
relaylm doctor [runtime options] [--json]
relaylm serve [runtime options]
relaylm-eval
```

`init` remains deferred; the operator layer does not fabricate Character memory, Identity, or secrets.

## Runtime options

Current named CLI overrides remain bounded:

```text
--config PATH
--character PATH
--provider-adapter NAME
--provider-base-url URL
--provider-model MODEL
--provider-api-key-env ENV_NAME
--host HOST
--port PORT
--profile NAME
```

There is no generic `--set`. Complex cognition pass controls, Retrieval, Continuity, and Cognitive Budget objects are runtime-file inputs in format version 1.

Existing named leaves preserve:

```text
CLI > environment > runtime file > canonical default
```

`--profile` is reserved but every non-empty profile currently fails closed because #1388 has not published calibrated profile authority.

## `doctor`

`doctor` performs the same configuration, preflight, and assembly admission used by `serve`, without model generation or Character mutation.

It verifies, where applicable:

- runtime YAML/discovery/secret-reference validity;
- provider URL/model/backend configuration;
- selected cognition topology can be assembled for ordinary serving;
- Character Package readability;
- persistence writability without creating semantic files;
- selected token-counter capability when the existing single-pass Cognitive Budget is configured;
- safe server bind-target syntax.

It does not probe model output, append Events, save State, rewrite MEMORY, or claim provider reachability merely from a configured URL.

Human-readable diagnostics include safe runtime metadata only. Current summaries expose:

```text
provider adapter + backend + model + base URL
server bind
cognition=<resolved mode>
memory/event/continuity/cognitive-budget enabled flags
```

Non-printable characters are escaped before line-oriented output. Secret material and Character semantic payload are never printed.

`doctor --json` includes the content-free `effective_config` view, including `runtime.cognition.mode` and its provenance.

## `serve`

`serve` uses exactly the successfully prepared assembly:

```text
resolve runtime config
  -> doctor-equivalent preflight
  -> RuntimeAssembly
  -> server.create_app(**assembly.app_kwargs())
  -> /v1/chat/completions
```

For Core 1.0, the no-profile release topology default is `two_pass`. The assembled ordinary runtime therefore uses the existing response-first two-pass Turn path for both buffered and streaming requests.

Explicit `single_pass` remains a compatibility mode. Unresolved `auto` and evidence-only `shadow_two_pass` fail before serving.

Pass 1 and Pass 2 requests are carried independently. Omitted pass controls remain omitted; the operator layer does not manufacture reasoning/decoding/output values.

Streaming exposes Pass 1 text through the existing two-pass streaming owner and preserves the same Pass 2 semantics as buffered execution. The operator layer does not define a separate streaming cognition policy.

## Cognitive Budget

The current explicit `runtime.cognitive_budget` is single-pass #1387 authority. Until #1388 publishes two-pass per-pass budget/profile values, `two_pass + runtime.cognitive_budget` fails closed rather than copying one total into both passes.

## Provider backends

Backend names are provider-owned identities. Operator configuration does not silently downgrade a backend-specific selection to `generic`.

At this boundary:

- generic OpenAI-compatible serving is available;
- vLLM specialized assembly requires its explicit provider-owned capability attestation;
- LM Studio specialized assembly is a separate pending repository transaction and currently fails capability admission rather than masquerading as generic.

## Installed-artifact gate

The `package-smoke` CI gate continuously proves that wheel and sdist can be built reproducibly, installed non-editably outside the repository checkout, and execute installed `relaylm --version`, `relaylm doctor`, and `relaylm-eval` without repository-relative dependencies.

This is an operator/distribution smoke, not an actual-model quality run.

## Errors

Configuration, assembly, and preflight failures use the existing typed runtime taxonomy and return status `2`. Successful `doctor`, normal `serve` shutdown, and `--version` return status `0`.

Error rendering must not expose API keys, Character payload, arbitrary decoder exception text, or terminal-control injection.

## Ownership

The operator layer does not own:

- Pass 1 / Pass 2 semantics (#1533);
- #1388 numeric profile/default selection;
- provider-specific capability/wire truth;
- Retrieval/Context/Continuity/State semantics;
- Character Identity/Event/MEMORY authority;
- actual-model Stage R evidence (#1386);
- distribution/tag/publication mechanics (#1447).

## Remaining release-runtime work

After ordinary two-pass serving is wired, the remaining repository-side operator work is bounded:

1. connect additional provider backend-specific assembly such as LM Studio through provider-owned capability contracts;
2. add only named operator cognition overrides that are justified beyond the version-1 file contract;
3. consume #1388 calibrated two-pass profiles/defaults once that authority exists;
4. re-run installed release-candidate smoke when an authorized candidate exists.

Actual-model Stage R qualification is deliberately outside this operator transaction.

> The operator path carries the release cognition policy faithfully; it does not redefine it.