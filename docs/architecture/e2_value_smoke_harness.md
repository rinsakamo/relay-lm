---
relaylm_doc_type: implementation_handoff
relaylm_authority: e2_value_smoke_harness_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_update_trigger:
  - E2 comparison artifact sections change
  - baseline run definition changes
  - value smoke output containment path changes
  - scenario file schema changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - conversation quality judgment or its result
  - RelayLM Core pipeline behavior
  - MEM/SOUL/SLP persistence authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - project_execution_plan.md
  - e1_evaluation_consolidation.md
  - audit_trace_content_free_contract.md
---
# E2 Value Smoke Harness

Last reviewed: 2026-07-04 JST

## Purpose

RelayLM's existing evidence is dominated by "nothing bad happens" proofs
(fail-closed gates, content-free diagnostics, dry-run-first apply). The E2
value smoke harness is the first artifact generator for the core value
hypothesis: a conversation through RelayLM feels like it *remembers better
and stays in character better* than the same model driven directly.

The harness builds only the stage for that comparison. It runs one fixed
scenario through two controlled paths and emits one human-readable
comparison transcript. It does not judge. Whether RelayLM produced a felt
difference is decided only by a human (Rin) reading the artifact and
filling in the judgment section by hand.

## Responsibilities

`scripts/relaylm_e2_value_smoke.py` is an HTTP-client-only CLI:

- **Run A (RelayLM)** sends the scenario's user turns to the RelayLM
  `/v1/chat/completions` endpoint on a character-bound managed route.
  Conversation history follows the current RelayLM default: the client
  stacks its own user/assistant history like an ordinary frontend.
- **Run B (direct baseline)** sends the same user turns to the same
  backend and the same model, simulating a naive frontend: full raw
  history stacked as-is, no system message, no RelayLM-derived persona or
  memory injection. This baseline definition is written verbatim into the
  artifact header.
- **Controls shared by both runs:** same model, same sampling parameters
  (temperature, max_tokens, and seed when given), same user turn
  sequence. Route, character, backend, and model resolve from the
  existing `config.yaml` loading path (`relaylm.config.load_config`,
  honoring `RELAYLM_CONFIG`); nothing is hardcoded.

Scenario files live under `examples/value_smoke/` and carry a `probe`
note per turn describing what the turn tests; probes are copied into the
artifact next to each turn for the human judge.

The artifact contains, in order: run metadata (timestamp, model, route,
character, sampling parameters, config path and SHA-256, baseline
definition), the turn-by-turn A/B comparison with probe notes, and a
human judgment section that is always generated blank, with a fixed note
directly above it stating that an artifact whose judgment section is
still blank is not valid E2 evidence.

## Boundary exception: conversation bodies, local-only

The comparison artifact intentionally contains conversation bodies. This
is a deliberate, contained exception to the content-free principle:

- artifacts are written only under `local/value_smoke/`;
- `local/` is gitignored, so a body-bearing artifact can never be
  committed;
- no body flows into `docs/`, traces, audit output, or any existing
  content-free diagnostic path — harness stdout reports only turn
  indices, character counts, and the artifact path;
- the harness never touches MEM/SOUL/SLP persistence and never bypasses
  any RelayLM-internal gate; it behaves exclusively as an HTTP client of
  the public chat completion endpoints.

Anything later published under `docs/mvp/` is a hand-written judgment
summary without body quotes; producing that summary is outside this
slice.

## Human-only judgment

The harness performs no quality assertion, no pass/fail decision, no
scoring, and no LLM-as-judge. The blank judgment section asks for:

- felt difference in memory recall (A / B / no difference, plus grounds);
- felt difference in persona stability (same shape);
- overall: did RelayLM produce a felt difference (yes / no / unclear).

## Usage

With RelayLM and its backend (for example LM Studio) running locally:

```bash
PYTHONPATH=. python scripts/relaylm_e2_value_smoke.py \
  --scenario examples/value_smoke/scenario_01_memory_recall.yaml
```

Useful flags: `--config`, `--route`, `--relaylm-base-url`,
`--backend-base-url`, `--temperature`, `--max-tokens`, `--seed`,
`--timeout-seconds`. Defaults resolve from the loaded config; `--route`
is only needed when more than one character-bound route exists.

## Non-goals

- no conversation-quality assertion, pass/fail, or scoring;
- no LLM-as-judge and no automatic evaluation of response bodies;
- no new RelayLM Core feature or pipeline change;
- no MEM/SOUL/SLP mutation and no new persistence path;
- no artifact output outside `local/value_smoke/`;
- no automated aggregation of judgments.

## Validation

Harness-health only (never conversation quality):

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_e2_value_smoke_harness_smoke.py
```

The harness smoke checks with stub endpoints that both runs complete,
turn counts match, sampling parameters are identical across runs, the
artifact contains every required section with a blank judgment section,
the artifact is confined to `local/value_smoke/` and gitignored, a
failing endpoint fails closed without writing an artifact, and the two
shipped scenarios parse with 8-12 probe-annotated turns.
