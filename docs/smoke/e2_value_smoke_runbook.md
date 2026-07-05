# E2 value smoke runbook

This runbook explains how to run the local E2 value smoke harness for a human RelayLM-vs-direct-backend comparison.

## What this is

The E2 value smoke is an operator-facing comparison flow. It sends the same checked-in scenario through two paths:

- Run A: RelayLM `/v1/chat/completions` through a character-bound managed route.
- Run B: the same backend/model directly, as a naive frontend baseline with raw client history only.

The harness writes one Markdown comparison artifact under `local/value_smoke/`. That artifact intentionally contains conversation bodies so a human can judge whether RelayLM produced a felt difference.

## What this is not

The harness is not an automated quality evaluator. It does not score, assert, or choose a winner. It is also not a runtime bypass: it is an HTTP client only, does not touch MEM/SOUL/SLP persistence directly, and does not bypass RelayLM gates.

A generated artifact does not count as E2 evidence while its human judgment section is blank.

## Prerequisites

Before running a value smoke that is meant to demonstrate durable memory effects, confirm all of the following locally:

1. The backend is running and reachable.
2. RelayLM is running and reachable.
3. The target route is configured as a character-bound managed route.
4. O2/O3 or an equivalent local worker drain has already produced evidence that queued durable memory work was drained.
5. The RelayLM config path is known.

For scenarios that only check harness usability or persona/output-style comparison, the worker drain evidence is not the claim being tested, but the backend, RelayLM, route, and config prerequisites still apply.

## Example scenarios

Checked-in examples live under `examples/value_smoke/`:

- `scenario_01_memory_recall.yaml` — safe synthetic memory-recall comparison.
- `scenario_02_persona_stability.yaml` — safe synthetic persona/output-style stability comparison.

The scenario files are intentionally concise and contain no real patient, hospital, account, token, or private project secret content.

## Run command

From the repository root:

```bash
PYTHONPATH=. python scripts/relaylm_e2_value_smoke.py \
  --config config.yaml \
  --scenario examples/value_smoke/scenario_01_memory_recall.yaml \
  --route relaylm-work-assistant \
  --temperature 0.2 \
  --max-tokens 512 \
  --seed 7
```

Use the route ID that matches a character-bound managed route in your local config. If there is exactly one character-bound route, `--route` can be omitted; otherwise pass it explicitly.

To validate the checked-in scenario files without starting RelayLM or a backend:

```bash
PYTHONPATH=. python scripts/relaylm_e2_value_smoke_scenarios_smoke.py
```

That scenario validation smoke only loads the YAML files and checks their contract. It must not call RelayLM, call the backend, or write generated artifacts.

## Output location and handling

Generated comparison artifacts are written under:

```text
local/value_smoke/*.md
```

These artifacts are content-bearing. They may contain full user and assistant conversation text. Keep them local-only:

- Do not commit them.
- Do not copy them into `docs/`, traces, audit output, or current-status documentation.
- Do not paste private or production content into checked-in scenarios.

`local/` is gitignored so normal runs should not create tracked files.

## Human judgment

Open the generated Markdown artifact and read Run A and Run B turn by turn. Fill in the blank human judgment section manually:

- memory-recall felt difference,
- persona-stability felt difference,
- overall judgment,
- rationale.

The comparison should be interpreted qualitatively. Run A is expected to show the effect of RelayLM route behavior and any governed memory/persona/context injection available through that route. Run B is the naive direct-backend baseline with no RelayLM-derived persona or memory injection. The harness intentionally does not auto-score either run.

## Common failure modes

- `route not found in config`: pass a valid local route ID with `--route` or update `config.yaml`.
- `no character-bound route in config`: configure a managed route with a `character_id` before using the harness.
- Backend unavailable: start the backend or pass the correct `--backend-base-url`.
- RelayLM unavailable: start RelayLM or pass the correct `--relaylm-base-url`.
- Artifact path refusal: the harness refused to write outside `local/value_smoke/`; do not override this boundary.

## Validation checklist

For a documentation-only PR that adds or changes checked-in scenario examples or this runbook, run at minimum:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_e2_value_smoke_scenarios_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

Optional harness help check, without backend calls:

```bash
PYTHONPATH=. python scripts/relaylm_e2_value_smoke.py --help
```
