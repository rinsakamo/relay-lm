# Release Runtime Operator Contract

Status: RCFG4 operator implementation + RCFG6 installed-artifact evidence reconciliation for RelayLM v1. Owning Issue: #1446.

RCFG4 exposes the RCFG1 configuration contract, RCFG2 resolver, and RCFG3 assembly through the installed `relaylm` console entrypoint. It adds operator ergonomics and preflight only; it does not choose cognitive semantics or calibrated numeric defaults.

## Commands

```text
relaylm --version
relaylm doctor [runtime options] [--json]
relaylm serve [runtime options]
relaylm-eval
```

The installed `relaylm-eval` auxiliary entrypoint currently accepts no command arguments. Supplying any argv token fails with status `2` before the native evaluation suite runs, and non-printable token content is rendered safely in the diagnostic rather than emitted as terminal controls. Native scenario/check/report semantics remain owned by #1247; this contract owns only the installed operator admission boundary.

`init` is intentionally deferred because a bounded release need has not been demonstrated. RCFG4 does not fabricate Character memory, Identity, or secrets.

## Runtime options

Version 1 binds only the named overrides frozen by RCFG1:

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

There is no generic `--set` or arbitrary nested CLI mutation. Complex Retrieval, Continuity, and Cognitive Budget structures remain runtime-config-file inputs.

The resolver keeps the frozen precedence:

```text
CLI > environment > runtime config file > canonical default/profile
```

`--profile` remains accepted as the reserved RCFG1 spelling, but current RCFG2 resolution still fails closed for every non-empty profile because #1388 has not yet published canonical profile authority.

## `doctor`

`doctor` is non-generative and does not persist semantic Character state. It performs, in order:

1. RCFG2 discovery, strict parsing, precedence, secret-reference resolution, and validation;
2. deterministic server bind-target syntax validation for an obvious bare hostname/IP shape before server startup;
3. provider configuration validation sufficient for the current HTTP OpenAI-compatible adapter;
4. Character Package readability/structural validation by reading current config, Identity, State, Event journal, and optional MEMORY markdown through `CharacterDirectory`;
5. non-mutating persistence writability checks using filesystem permissions only;
6. RCFG3 assembly, including explicit token-counter capability availability when Cognitive Budget is configured.

Server bind-target validation rejects obvious malformed values such as ASCII control characters, whitespace, or URL path/query/fragment syntax. Because `server.host` and `server.port` are separate runtime fields, a colon-bearing host is accepted only when it is a valid IPv6 address literal; embedded `host:port` values fail closed. It does not perform DNS reachability checks, reserve a socket, or prove that the address is currently bindable; those environment-dependent conditions remain server-startup concerns.

`doctor` does not call the provider, generate model output, append Events, save State, rewrite MEMORY, or create persistence directories/files.

A successful human-readable run prints only runtime metadata: selected Character path, provider adapter/model/base URL, server bind, and enabled runtime-layer flags. Before metadata is inserted into this line-oriented output, non-printable characters are rendered as visible `\x..`, `\u....`, or `\U........` escapes so resolved values cannot inject new diagnostic lines or terminal controls. This escaping is presentation-only and does not normalize or mutate the resolved runtime/provider value. Human-readable output never prints API-key material or Character semantic payload.

`doctor --json` returns a bounded object:

```json
{
  "status": "ok",
  "checks": {
    "configuration": "ok",
    "character": "ok",
    "persistence": "ok",
    "provider": "ok",
    "runtime_assembly": "ok"
  },
  "effective_config": {"...": "RCFG2 content-free diagnostics"}
}
```

The `effective_config` object is exactly the existing RCFG2 safe diagnostics boundary. Secret values and secret environment-variable names are excluded.

## `serve`

`serve` performs the same resolution and preflight as `doctor`. Only a successful `PreparedRuntime` is handed to `server.create_app`, and its configured host/port are passed to uvicorn.

The startup summary is emitted only after preflight succeeds. The same RCFG3 assembly objects feed buffered and streaming ordinary-turn paths; RCFG4 does not add a generation, semantic transformation, or separate streaming policy.

The previous `server.create_app_from_env()` helper may remain as an internal compatibility surface, but the supported release console entrypoint is `relaylm.cli:main` and therefore uses RCFG2 + RCFG3 + RCFG4.

## Provider and capability checks

The current provider adapter requires an HTTP or HTTPS base endpoint with a host and no query or fragment delimiter. If the URL explicitly names a port, preflight requires it to be in the usable TCP range `1..65535`; omitting the port leaves the HTTP/HTTPS scheme default in effect. Preflight rejects obvious malformed provider hostname syntax containing whitespace or a backslash and rejects literal whitespace or ASCII control characters anywhere in the configured base-URL string before startup succeeds. Provider model identifiers remain otherwise opaque owner-carried strings, but an identifier containing ASCII C0 or DEL control characters fails closed as `provider_invalid: provider.model` before `doctor` or `serve` can report success. Percent-encoded URL data is not decoded or reinterpreted by this lexical check. RCFG4 does not issue network requests during `doctor`; hostname resolution and provider reachability are intentionally not inferred from an adapter-specific discovery endpoint.

If explicit Cognitive Budget is configured, its token-counter capability must already be registered with RCFG3 and match the configured existing `TokenCountMode`. RCFG4 supplies no generic tokenizer heuristic and no implicit capability fallback.

## Persistence check

Ordinary turns may append the Event journal and save State, and crystallization may write MEMORY. Preflight therefore verifies the selected Character root or existing `memory/` directory is writable and that existing persistence files are writable. The check itself creates no file and changes no Character data.

## Errors and exit status

Configuration, assembly, and preflight failures use the existing RCFG1 taxonomy and exit with status `2`. Messages contain safe field/configuration metadata only. Before a typed runtime failure is written to the human operator stderr stream, non-printable characters in the rendered message are converted to the same visible escape form used by successful human-readable summaries. This is presentation-only: the typed exception, field, taxonomy, and underlying runtime/config value are unchanged.

If a selected `--config` or `RELAYLM_CONFIG` path uses `~` / `~user` syntax whose home directory cannot be resolved, discovery fails closed as `discovery_error: config_path` before file access or startup; the selected path and underlying home-resolution exception text are not emitted.

Selected runtime configuration files are decoded strictly as UTF-8. A selected file that cannot be decoded as UTF-8 fails as `parse_error: config_path` before assembly or startup; decoder exception text and file bytes are not emitted.

Character Package text read during release preflight is likewise decoded as UTF-8. A Character text file that cannot be decoded fails as `character_invalid: character.directory` before `doctor` or `serve` can report success; decoder exception text, Character file paths, and invalid bytes are not emitted.

Argument-parser failures also exit with status `2`. If an argparse diagnostic carries non-printable characters from an operator-supplied argv token, those characters use the same visible escape form before stderr output; normal usage text, option admission, and parser semantics are unchanged.

Successful `--version` output is emitted only after the complete argv has passed argument parsing and only when no subcommand is selected. An unsupported trailing argv token or a recognized `doctor` / `serve` subcommand combined with `--version` therefore fails through the argument-parser boundary with status `2` and no version stdout instead of being ignored after a successful version report.

Examples relevant to RCFG4:

```text
invalid_value
character_invalid
provider_invalid
capability_unavailable
invalid_combination
```

Successful `doctor`, `serve` shutdown, and `--version` return status `0`.

## RCFG6 installed-artifact evidence

RCFG6 does not introduce a second packaging or distribution implementation inside #1446. The mechanical artifact owner is #1447, and its merged REL1/REL2A work supplies the installed-product evidence consumed by this operator contract.

The required `v1` `package-smoke` gate now builds both supported artifact forms from the exact transaction head and validates them outside editable-development assumptions. In particular, it:

1. builds wheel and sdist twice and requires byte-identical repeat builds in the same build environment;
2. inspects artifact metadata, required package files, and console entrypoints;
3. installs the built wheel into a fresh virtual environment without editable mode;
4. changes the working directory outside the repository checkout;
5. runs installed `relaylm --version` and requires agreement with the single package-version authority;
6. runs installed `relaylm doctor --config ... --json` against a scratch Character/runtime config created outside the checkout and requires `status: ok`;
7. runs installed `relaylm-eval` and requires its native evaluation report to pass;
8. installs the built sdist into a second fresh environment without editable mode;
9. again runs installed `relaylm --version` and `relaylm doctor` outside the checkout;
10. runs `pip check` in both installed environments.

This satisfies the #1446 RCFG6 requirement that the supported operator path execute from built artifacts without repository-relative imports, editable installation, or bundled Character fixtures. The package/version/build mechanics themselves remain owned by #1447 and `docs/contracts/release-distribution.md`; #1446 consumes that evidence rather than redefining it.

RCFG6 does not claim that a public 1.0 release is ready. Exact tag/commit/release-candidate identity and publication remain #1447 work, while the final integrated readiness decision remains #1449.

## Preserved ownership

RCFG4/RCFG6 do not own or alter:

- Retrieval ranking/selection semantics;
- Context Compiler authority;
- Continuity candidate acceptance/lifecycle;
- Cognitive Budget degradation semantics;
- provider wire/prompt/decoding semantics;
- Character Identity/State/Event/MEMORY authority;
- #1388 profile/default numbers;
- #1447 distribution/version/tag/publication mechanics.

## Remaining release-runtime work

The current installed `relaylm serve` path still drives the historical single-pass ordinary-turn API path. It is therefore not yet the #1533 qualified two-pass Core 1.0 release/reference runtime.

Current #1446 authority still requires the operator layer to:

- carry the owner-defined #1533 cognition mode/profile and independent Pass 1 / Pass 2 controls through release configuration and deterministic resolution;
- assemble the qualified two-pass ordinary runtime instead of the historical single-pass API path;
- preserve equivalent resolved per-pass semantics across buffered and streaming execution;
- expose safe cognition capability/profile state and provenance through effective configuration and `doctor` diagnostics;
- RCFG5: consume evidence-backed #1388 canonical profiles/defaults after that authority exists;
- consume the exact release-candidate operator smoke owned mechanically by #1447 when an authorized candidate exists.

RCFG6 installed-artifact execution smoke is satisfied by the current #1447 REL1/REL2A package-smoke authority and remains continuously rechecked by `v1` CI on relevant transaction heads.
