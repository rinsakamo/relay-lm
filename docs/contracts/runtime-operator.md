# Release Runtime Operator Contract

Status: RCFG4 implementation contract for RelayLM v1. Owning Issue: #1446.

RCFG4 exposes the RCFG1 configuration contract, RCFG2 resolver, and RCFG3 assembly through the installed `relaylm` console entrypoint. It adds operator ergonomics and preflight only; it does not choose cognitive semantics or calibrated numeric defaults.

## Commands

```text
relaylm --version
relaylm doctor [runtime options] [--json]
relaylm serve [runtime options]
```

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
2. provider configuration validation sufficient for the current HTTP OpenAI-compatible adapter;
3. Character Package readability/structural validation by reading current config, Identity, State, Event journal, and optional MEMORY markdown through `CharacterDirectory`;
4. non-mutating persistence writability checks using filesystem permissions only;
5. RCFG3 assembly, including explicit token-counter capability availability when Cognitive Budget is configured.

`doctor` does not call the provider, generate model output, append Events, save State, rewrite MEMORY, or create persistence directories/files.

A successful human-readable run prints only runtime metadata: selected Character path, provider adapter/model/base URL, server bind, and enabled runtime-layer flags. It never prints API-key material or Character semantic payload.

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

The current provider adapter requires an HTTP or HTTPS base URL with a host. RCFG4 does not issue network requests during `doctor`; provider reachability is intentionally not inferred from an adapter-specific discovery endpoint.

If explicit Cognitive Budget is configured, its token-counter capability must already be registered with RCFG3 and match the configured existing `TokenCountMode`. RCFG4 supplies no generic tokenizer heuristic and no implicit capability fallback.

## Persistence check

Ordinary turns may append the Event journal and save State, and crystallization may write MEMORY. Preflight therefore verifies the selected Character root or existing `memory/` directory is writable and that existing persistence files are writable. The check itself creates no file and changes no Character data.

## Errors and exit status

Configuration, assembly, and preflight failures use the existing RCFG1 taxonomy and exit with status `2`. Messages contain safe field/configuration metadata only.

Examples relevant to RCFG4:

```text
character_invalid
provider_invalid
capability_unavailable
invalid_combination
```

Successful `doctor`, `serve` shutdown, and `--version` return status `0`.

## Preserved ownership

RCFG4 does not own or alter:

- Retrieval ranking/selection semantics;
- Context Compiler authority;
- Continuity candidate acceptance/lifecycle;
- Cognitive Budget degradation semantics;
- provider wire/prompt/decoding semantics;
- Character Identity/State/Event/MEMORY authority;
- #1388 profile/default numbers.

## Remaining release work

- RCFG5: consume evidence-backed #1388 canonical profiles/defaults after that authority exists;
- RCFG6: installed-artifact execution smoke for `relaylm --version`, `doctor`, and supported startup outside editable-repository assumptions.
