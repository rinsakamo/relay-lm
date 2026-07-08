---
relaylm_doc_type: architecture
relaylm_authority: relayatn_reflex_layer_target_boundary
relaylm_status: target
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - reflex-layer component naming or charter decisions
  - continuous-input / multi-user admission design decisions
  - RelayRUN pre-request boundary decisions
  - O3 always-on operation scoping
relaylm_not_authoritative_for:
  - current implementation status
  - RelayRUN checkpoint/recovery contract
  - RelayINT intra-turn intent ownership
  - RelaySCN scene classification ownership
  - v0.1 release scope and committed sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - relayrun_runtime_checkpoint_design.md
  - relayint_mvp_design.md
  - relayscn_mvp_scene_policy.md
  - pipeline_responsibility_design.md
  - project_execution_plan.md
  - o3_always_on_local_scheduler.md
  - soul_lab_runtime_mvp.md
  - ../PROJECT_STATUS.md
---
# RelayATN Reflex Layer Design (Target)

Last reviewed: 2026-07-09 JST

## Status of this document

This is a **target design boundary** for a component that does not exist. It authorizes no implementation, changes no current contracts, and defers all current-state claims to [Project Status](../PROJECT_STATUS.md). Implementation is explicitly sequenced after voice-out (SOUL Lab Runtime MVP); see [Project Execution Plan](project_execution_plan.md).

`RelayATN` (Relay Attention) is a **provisional working name**. Registering it as canonical component vocabulary is a separate decision.

## Purpose

RelayATN is a resident pre-request reflex layer for continuous-input environments (streaming chat, group voice, always-listening contexts). It decides **whether and on what to start a turn** before any RelayRUN request shell exists.

## Motivating limits of the current single-call architecture

The current architecture is a single Main-LLM call per turn over a RelayCTX-compiled context, with the model's own structured self-report (working-state update) feeding the next turn's parameters. This is latency-optimal and should be preserved. It has two structural limits that continuous input exposes:

```text
L1  Self-report staleness
      Input-side judgment for turn N depends on the model's
      self-assessment produced at turn N-1. In turn-based 1:1
      conversation this one-turn lag is noise. Under continuous
      input, "the situation changed since the last report" is
      the steady state.

L2  Nobody watches between turns
      A single-call design has judgment only while the Main LLM
      is awake. Under continuous input, the decisions "should
      anything wake at all" and "which input deserves a turn"
      must exist outside the turn cycle.
```

## Dual-loop structure

```text
Reflex loop (RelayATN)              Deliberation loop (existing)
  resident, CPU-side                  turn-based, GPU-side
  content-light                       full pipeline + Main LLM
  continuous cadence                  single-call per admitted turn
  reject / hold / select only         full semantic authority
```

The reflex loop runs independently of the turn cycle. The deliberation loop is the existing canonical pipeline, unchanged, invoked only for inputs the reflex loop admits.

RelayATN is not a shortcut around the deliberation loop. It may reduce how often the deliberation loop is invoked, but once an input is admitted, all semantic, safety, scene, memory, and response decisions remain inside the existing pipeline.

## Position relative to existing components

### Why not inside RelayRUN (charter conflict)

The [RelayRUN Runtime Checkpoint Design](relayrun_runtime_checkpoint_design.md) contract states that RelayRUN owns orchestration, checkpoint, recovery, and idempotency state, and **must not make semantic decisions**. Attention scoring, interruption-value judgment, and wake decisions are semantic decisions. Additionally, the canonical flow begins at `User input -> RelayRUN request shell`: RelayRUN is per-request, while the reflex loop exists **before a request exists** — it decides whether to create one.

Therefore RelayATN is a **new component**, orchestrated by (not owned by) the runtime. RelayRUN's charter is unchanged: once RelayATN admits an input as a turn, RelayRUN owns that turn's orchestration exactly as today. RelayRUN may additionally record content-free admission summaries (counts, decision classes) as run-shell metadata.

### Relationship to RelayINT

RelayINT retains intra-turn ownership: intent, ambiguity, continue/confirm/stop **for an admitted input**. RelayATN owns pre-turn admission: whether an input becomes a turn at all, and which input when several compete. The boundary sentence:

```text
RelayATN decides IF and ON WHAT a turn starts.
RelayINT decides WHAT TO DO with the turn's input.
```

RelayATN must not resolve references, classify intent, or select response modes.

### Relationship to RelaySCN

RelaySCN retains scene classification and scene-policy ownership. RelayATN may perform cheap **scene-change detection** (e.g. "a new participant joined") as a signal, which it forwards as a candidate trigger; the resulting scene classification and policy decision remain RelaySCN's, executed inside the admitted turn. Scene-change detection in RelayATN follows the fail-closed transition rule: detected escalation (private -> group) may emit a conservative `scene_escalation_detected` flag. The runtime may treat the next admitted turn as requiring RelaySCN re-evaluation before any relaxed scene policy is applied. RelayATN itself does not classify the scene or select the policy. Downgrade is never inferred by RelayATN.

### Relationship to O3 and the bounded scheduler

The `O3 always-on local operation` lane in [Project Execution Plan](project_execution_plan.md) is the natural home for RelayATN's resident-process concerns (supervision, lifecycle). RelayATN's judgment charter is defined here; its process/operational model belongs to the O2/O3 decision when that lane opens. The O1D2 bounded scheduler pattern (bounded, preemptible background work) is the reference for GPU-yielding behavior: reflex-triggered deliberation must be able to preempt SLP/off-turn work.

## RelayATN responsibilities

RelayATN may own:

- attention scoring over continuous input (which comment/utterance candidates matter),
- wake decision (whether to invoke the deliberation loop at all),
- interruption-value judgment (whether an input justifies interrupting in-progress speech; RelayATN may only emit an interruption candidate or flag, while interruption *execution* remains RelayRUN/runtime-adapter territory),
- input aggregation (e.g. collapsing "five viewers asked the same question" into one turn candidate),
- coarse, transient affect/urgency estimation as an admission signal (not as RelayEMO's expression input),
- scene-change **detection** signals (not classification),
- **self-report freshness check**: cheaply judging whether the previous turn's structured self-report still holds given inputs seen since, and flagging divergence for input-side correction — closing limit L1 without additional Main-LLM calls.

## Authority constraints (fail-closed)

RelayATN's permitted verbs are exactly:

```text
reject   drop an input candidate
hold     defer an input candidate
select   admit an input candidate as a turn
flag     attach content-free signals (staleness, scene-change,
         aggregation grouping) to an admitted turn
```

RelayATN flags are advisory and content-free. A RelayATN flag may cause downstream components to re-check their own inputs or choose a more conservative default, but it never overrides RelaySCN, RelayINT, RelayMEM disclosure, RelayEMO expression, or safety decisions.

RelayATN must not:

- authorize disclosure of any memory, at any tier, ever,
- mutate MEM / SOUL / REL / SCN state or emit persistence candidates,
- generate user-visible text,
- bypass, reorder, or pre-empt any safety gate in the deliberation loop,
- treat its own scores as scene policy, disclosure policy, or expression policy,
- stop audio, cancel generation, truncate visible output, or commit any interruption side effect.

Error asymmetry is the design principle: a wrong `reject`/`hold` degrades experience (a missed reply); RelayATN structurally cannot make the accident-class error (wrong disclosure), because it holds no disclosure verbs. Cheap models are allowed to be wrong only in the direction that fails closed.

## Implementation tiers

The reflex loop is a three-tier cascade; most traffic should terminate in the first two tiers. The latency figures below are target-order guidance, not contractual guarantees:

```text
Tier 1  heuristics / regex / rate rules            (~µs, deterministic)
Tier 2  embedding model + light classifier         (CPU, ~ms–tens of ms)
Tier 3  small LLM fallback (0.5–2B Q4, CPU)        (ambiguous cases only)
```

Tier 3 inputs must be short (single candidate + minimal state) because CPU-side small-LLM prefill is the dominant cost. A generative model is expected to be *rarely* necessary; attention scoring and change detection are primarily embedding/classifier problems. Tier placement per job is an implementation decision, not contract.

GPU contention rule: RelayATN never runs on the Main-LLM GPU. Its entire value proposition is judgment that does not serialize behind (or steal prefill from) the deliberation loop.

## Self-report interaction

The existing structured self-report remains owned by the Main LLM / RelayCTX Unpack path. RelayATN interacts with it in two bounded ways:

1. **Freshness check** (above): read-only comparison of the last report against subsequent observed input; divergence produces a content-free `stale_report` flag consumed by input-side nodes of the next admitted turn.
2. **Thinning pressure**: state that becomes observable by the reflex layer (e.g. who was addressed, collective activity level) should migrate *out* of the self-report over time. The self-report trends toward "internal state only the Main LLM can know," keeping its decode cost from growing with multi-user scale. This document only records the architectural pressure; any actual migration out of the self-report requires a separate RelayCTX / self-report schema decision.

RelayATN never writes to the self-report.

## Content boundary

RelayATN observes raw incoming input (it must, to score it), but its **outputs** are content-free: decision classes, scores, candidate IDs, flags. Admission decisions, traces, and diagnostics carry no input bodies, consistent with the content-free trace principle. Retained reflex-loop state is bounded and transient; RelayATN is not a memory store and its buffers are not MEM/SLP evidence.

Raw input buffers used by RelayATN are transient, bounded, and non-durable. They must not be written to persistent traces, diagnostics, queue records, or MEM/SLP evidence. Candidate IDs must not be reversible encodings of the input body.

## Failure behavior

- RelayATN process failure must not break turn-based operation: the runtime falls back to "every input is admitted" degraded mode only in trusted 1:1 scenes, and to "no admission" (fail-closed) in `broadcast`-class scenes. The trusted 1:1 fallback is allowed only when the current scene classification was established by RelaySCN before the RelayATN failure and the input channel is not multi-source. Unknown, stale, or multi-source scenes fail closed.
- Tier 3 timeout resolves as `hold`, never `select`.
- Freshness-check failure resolves as `stale_report` unset (the deliberation loop trusts its own input-side nodes), never as blocking a turn.

## Non-goals

RelayATN does not:

- implement the multi-user Attention/Selection *policy content* (per-scene admission policy belongs with scene design),
- own ASR, audio capture, or full-duplex speech execution,
- own broadcast scene classes, disclosure matrices, or REL scaling,
- replace RelayINT, RelaySCN, or RelayRUN responsibilities,
- exist in v0.1 scope or in any currently committed lane.

## Implementation-plan placement

RelayATN should enter the project execution plan only as a **post-v0.1 / post-voice-out candidate lane**, not as committed v0.1 scope. The first execution-plan change should be planning-only: list the component as a gated future lane under the O3 always-on operation track, with this document as its target-boundary reference and with no implementation tasks enabled until the preconditions below are satisfied.

Recommended sequencing in the implementation plan:

```text
ATN-0  Planning registration only
       - register RelayATN as provisional vocabulary or decide to fold it elsewhere
       - link this target-boundary document from the O3 / post-v0.1 section
       - state explicitly that no runtime behavior changes are authorized

ATN-1  Measurement prerequisites
       - complete voice-out / SOUL Lab Runtime MVP
       - collect first-audio and per-node latency baselines via content-free trace
       - document single-primary-user vs multi-input assumptions

ATN-2  Contract-only slice
       - define content-free admission record schema
       - define failure fallback modes and trusted 1:1 preconditions
       - define advisory flag consumption rules for RelaySCN / RelayINT / RelayCTX

ATN-3  Disabled implementation skeleton
       - resident-process lifecycle behind a disabled-by-default feature flag
       - deterministic Tier 1 only, no model dependency
       - no persisted raw input and no user-visible behavior change

ATN-4  Experimental admission path
       - trusted local/dev scenes only
       - content-free traces only
       - compare every-input-admitted baseline vs reject/hold/select outcomes

ATN-5  Tier 2 / Tier 3 experiments
       - CPU-only classifier / small-LLM fallback behind explicit opt-in
       - benchmark latency and false-hold / false-reject behavior before any default enablement
```

The execution plan should avoid scheduling RelayATN before voice-out because RelayATN's value depends on continuous input, interruption timing, and first-audio latency measurements. Before those exist, implementation would mostly create resident-process scaffolding without measurable user value.

## Preconditions before implementation

```text
P1  voice-out (SOUL Lab Runtime MVP) functional
P2  latency baseline measured (per-node, first-audio distribution) via content-free trace
P3  component name registered in canonical vocabulary
    (or an explicit decision to fold the charter elsewhere)
P4  single-primary-user assumption documented in contracts (hedge H1),
    since RelayATN is the first component whose reason to exist is multi-input
P5  execution plan lists RelayATN only as a gated post-v0.1 / O3 candidate
    before any implementation PR is cut
```

## Design decision record

Four placements were considered for the reflex charter:

1. **Amend RelayRUN's charter** to own pre-request admission — rejected: violates RelayRUN's "no semantic decisions" principle and bloats the orchestration layer into a judgment layer.
2. **New component (RelayATN)** — adopted: preserves existing charters, expresses the reject/hold/select/flag authority constraint as a component boundary, and gives the O3 lane a concrete tenant.
3. **Extend RelayINT** to pre-turn — rejected: closest existing charter, but RelayINT is implemented as an in-turn node; residency would be a structural rewrite, and admission-vs-intent is a cleaner seam than a stretched INT.
4. **Extend RelaySCN** to own admission — rejected: scene classification and scene policy are not the same as continuous pre-request attention selection; merging them would make scene policy depend on resident input buffering and wake mechanics.
