---
relaylm_doc_type: architecture_handoff
relaylm_status: current
relaylm_volatility: bounded
relaylm_owner: evaluation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - e1_evaluation_consolidation.md
  - e1_local_runtime_evaluation_2026_06_25.md
  - soul_lab_ui_b0_real_home_conversation.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
---
# E1-R1 Trusted Home Scene Admission

## Purpose

E1-R1 adds the smallest server-owned trusted scene-admission path that can let a SOUL Lab Home-origin ordinary conversation enter the existing Primary MEM formation pipeline.

The boundary is intentionally narrow:

```text
SOUL Lab Home ordinary conversation
  -> route-owned trusted Home admission decision
  -> existing finalized-turn source builder
  -> existing C1-5 protected source persistence
  -> existing B2 durable queue admission
  -> existing O0/O1/C2 worker drain
  -> Primary MEM formation
```

E1-R1 does not create a new queue format, new worker, scheduler loop, polling loop, daemon, timer, or browser-owned trust authority.

## Server-owned authority

The browser may send ordinary OpenAI-compatible Chat Completions payloads, including Home conversation text and ordinary metadata used by existing routes. It may not self-assert trusted persistence policy.

The admission authority is route-owned server configuration:

```yaml
model_routes:
  relaylm-home:
    scene_id: home
    trusted_home_scene_admission_mode: disabled  # disabled | dry_run | apply
    trusted_home_scene_admission_scene_id: home
```

The route-owned mode defaults to `disabled`. When any route is configured for `dry_run` or `apply`, RelayLM enables only the minimal post-response runtime trigger needed to call the existing finalization/enqueue authority. The per-request gate then decides whether this specific route may actually build a source and enqueue.

Browser-provided trust claims in top-level payload fields, `metadata`, or trust-specific headers are rejected by the E1-R1 decision. They are not interpreted as authority and cannot upgrade a disabled or unsupported route into an admitted one. Request-local header capture keeps only the trust-relevant header names, never full header values or unrelated headers.

## Admission statuses

E1-R1 exposes deterministic content-free decision statuses:

```text
disabled
  No route-owned trusted Home admission is configured.

dry_run_ready
  The route is trusted Home and prerequisites are available, but only dry-run source/queue preview is allowed.

accepted
  The route is trusted Home and apply prerequisites are available. Existing source/queue authority may be invoked.

rejected_browser_owned_trust
  The request attempted to self-assert persistence trust through browser-owned fields or headers.

invalid_scene
  The configured/active route scene is not the server-owned Home scene.

unsupported_scope
  The route is pass-through or lacks a valid character/namespace scope.

missing_character_store
  The configured character store partition is absent.

downstream_existing_admission_failure
  Apply mode was requested, but existing downstream source/queue prerequisites are not available.
```

Public projections are content-free. They do not include user text, assistant text, memory summaries, raw source, queue/protected-source paths, job IDs, dispatch IDs, lease tokens, private namespace values, raw exceptions, request header values, unrelated request headers, or exact private timestamps.

## Existing authority reuse

E1-R1 does not publish protected source or queue records by itself. After a request is admitted, the existing `run_relaymem_slp_runtime_enqueue_after_response` path remains the authority for:

- finalized-turn source capture;
- durable protected source persistence;
- B2 durable queue publication;
- exact dispatch/job identity derivation;
- downstream O0/O1/C2 worker compatibility.

When E1-R1 is disabled, rejected, or blocked, the runtime gate passes `(enabled=False, dry_run_only=True, apply_enabled=False)` to the existing durable enqueue authority. Ordinary Home conversation still reaches the backend and returns normally, but no Home-origin source or queue evidence is created.

When an explicit pre-existing trusted formation lane already enables runtime enqueue globally, E1-R1 does not replace it. The route-owned Home gate only narrows the new Home-origin trigger that E1-R1 introduces.

## Non-goals preserved

E1-R1 does not implement:

- E1-R2 idempotent character-store bootstrap command;
- E1-R3 provenance-preserving Primary MEM summary quality;
- E1-R4 evidence-grounded recall response behavior;
- O2 supervised service or O3 always-on operation;
- TTS/audio/avatar/Live2D/ASR/peer transport;
- new browser-owned trust authority;
- scheduler loops, polling loops, timers, background workers, service supervision, or daemon operation;
- new queue schema or worker record format.
