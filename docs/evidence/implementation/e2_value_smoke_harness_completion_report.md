---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e2_value_smoke_harness_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: evaluation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - durable-memory E2 human judgment or quality conclusion
  - current harness behavior or scenario inventory
  - repeatable evaluation method authority
relaylm_source_commit: 51d678dfb0a10899db424e59c08af70865b8333f
relaylm_source_pr: 481
relaylm_recorded_on: 2026-07-04
relaylm_source_blob: 333ba34007a38b794572683c41e947ae1d0ad8cf
relaylm_source_content_sha256: ffc09e20a41f7202c05682aa9e50a8c859107a64bacdc33ff5e9a81723b13358
relaylm_exact_source_snapshot: e2_value_smoke_harness_completion_report-source.txt
---
# E2 Value Smoke Harness Completion Report

## Status and authority

This document is frozen implementation evidence for the E2 comparison-transcript harness introduced by PR #481 and merged as `51d678dfb0a10899db424e59c08af70865b8333f`. Current repository status belongs to [Project Status](../../PROJECT_STATUS.md). The later durable-memory E2 human review and release-readiness conclusion belong to [v0.1 Release Readiness Assessment](../../release/v0.1-release-readiness.md), not this harness implementation record.

The exact pre-cutover report is retained byte-for-byte as [e2_value_smoke_harness_completion_report-source.txt](e2_value_smoke_harness_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified.

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open the next wave or release/evaluation gate.

## Scope

E2 value smoke harness: a comparison-transcript generator for the core value hypothesis that a RelayLM-mediated conversation feels like it remembers better and stays in character better than the same model driven directly. The slice builds only the stage; judgment stays human-only. Developed on branch `claude/e2-value-smoke-harness-e9pdlk` from main at `cd0d9804da41f4990c6ba84049baf375ec5819be`.

## Implemented production boundary

- `scripts/relaylm_e2_value_smoke.py`: HTTP-client-only CLI that runs one fixed scenario twice — Run A through RelayLM `/v1/chat/completions` on a character-bound managed route with the current RelayLM history default, Run B directly against the same backend and model as a naive frontend baseline (full raw history stacked as-is, no system message, no RelayLM-derived persona/memory injection) — under the same model, the same sampling parameters (temperature, max_tokens, seed when given), and the same user turn sequence, resolving route/character/backend/model from the existing `relaylm.config.load_config` path.
- One comparison artifact per run at `local/value_smoke/e2_<scenario>_<timestamp>.md` containing run metadata (model, route, character, sampling parameters, config path and SHA-256), the verbatim baseline definition, the turn-by-turn A/B comparison with per-turn probe notes, and an always-blank human judgment section with a fixed note that a blank-judgment artifact is invalid as E2 evidence.
- `examples/value_smoke/scenario_01_memory_recall.yaml` (10 turns: facts early, unrelated topics mid, indirect recall late) and `examples/value_smoke/scenario_02_persona_stability.yaml` (10 turns: baseline tone, destabilizing pressure, recovery), each turn carrying a `probe` note copied into the artifact.
- `.gitignore` gains `local/` so body-bearing artifacts can never be committed.

## Preserved authorities and non-goals

Preserved authorities:

- content-free trace/audit/diagnostic paths are untouched; conversation bodies exist only under gitignored `local/value_smoke/`;
- MEM/SOUL/SLP persistence and every RelayLM-internal gate keep their existing authority; the harness is an HTTP client of public endpoints only;
- RelayLM Core request pipeline is unchanged.

Non-goals:

- no conversation-quality assertion, pass/fail, or scoring;
- no LLM-as-judge and no automatic evaluation of response bodies;
- no new RelayLM Core feature or pipeline change;
- no artifact output outside `local/value_smoke/`;
- no shared status/plan document integration in the source slice.

## Changed files

- `scripts/relaylm_e2_value_smoke.py`
- `scripts/relaylm_e2_value_smoke_harness_smoke.py`
- `examples/value_smoke/scenario_01_memory_recall.yaml`
- `examples/value_smoke/scenario_02_persona_stability.yaml`
- `.gitignore`
- `docs/architecture/e2_value_smoke_harness.md`
- `docs/evidence/implementation/e2_value_smoke_harness_completion_report.md`

## Validation evidence

Commands run locally at the source boundary:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_e2_value_smoke_harness_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e2_value_smoke_harness_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
PYTHONPATH=.:scripts python scripts/relaylm_documentation_current_boundary_smoke.py
```

The harness smoke validates harness health only, with stub OpenAI-compatible endpoints: both runs complete; run A / run B turn counts match the scenario; both runs send identical sampling parameters and user turns; the baseline run sends no system message; the artifact contains every required section with per-turn probes and a blank judgment section; the artifact lands under `local/value_smoke/`, is gitignored, and adds nothing to the git-visible tree; a failing endpoint fails closed without writing an artifact; both shipped scenarios parse with 8-12 probe-annotated turns. A CLI end-to-end run against a stub backend produced a blank-judgment artifact and exit 0.

## Known limitations

- The harness proves nothing by itself: an artifact is E2 evidence only after a human fills in the judgment section, and the artifact says so.
- Run quality depends on the operator's live RelayLM + backend setup; the harness smoke uses stubs and does not exercise a live model.
- Backend seed support varies; when the backend ignores `seed`, sampling is controlled but not bit-reproducible.
- Run B approximates a naive frontend as defined in the artifact header; it does not replicate any specific frontend product.

## Shared documentation update inputs

At source PR #481:

- E2 value smoke harness was complete as a local-only comparison-transcript generator; judgment remained human-only and no automated quality gate existed.
- Handoff path was `docs/architecture/e2_value_smoke_harness.md`.
- `local/` was gitignored as the containment path for body-bearing artifacts; content-free boundaries elsewhere were unchanged.
- Any later committed publication was required to be a hand-written judgment summary without body quotes and was outside this slice.
- No config schema field was added or changed.

The later human review is recorded separately by the release-readiness authority and does not retroactively turn this harness implementation report into a quality-evaluation record.

## Source pull request

- PR: #481
- URL: https://github.com/rinsakamo/relay-lm/pull/481
