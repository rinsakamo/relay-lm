---
relaylm_doc_type: strategic_vision
relaylm_authority: post_v01_strategic_direction_vision
relaylm_status: target
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - post-v0.1 strategic direction changes
  - ingestion contract introduction
  - multi-user or broadcast scene design decisions
  - full-duplex or attention-selection design decisions
  - two-layer persona design decisions
relaylm_not_authoritative_for:
  - current implementation status
  - v0.1 release readiness
  - MVP boundary
  - dependency-first sequencing of committed work
  - exact contracts vocabulary
  - exact schemas
  - implementation authorization
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - ../mvp/v0.1_release_readiness.md
  - project_execution_plan.md
  - soul_lab_runtime_mvp.md
  - ai_vtuber_pipeline_profile.md
  - relayemo_return_side_expression_design.md
  - file_first_character_workspace_design.md
  - relayrel_relationship_design.md
---
# Post-v0.1 Strategic Direction Vision

Last reviewed: 2026-07-09 JST

## Purpose

This document captures RelayLM's strategic direction beyond the v0.1 release boundary. It records long-horizon bets, design principles, and vocabulary recommendations so that near-term slices can be shaped without foreclosing future directions.

This is a vision document. It authorizes no implementation, changes no contracts, registers no scene classes, and defers current-state claims to [Project Status](../PROJECT_STATUS.md). v0.1 release-readiness evidence belongs to [v0.1 Release Readiness](../mvp/v0.1_release_readiness.md). Committed sequencing remains owned by [RelayLM Project Execution Plan](project_execution_plan.md).

## Near-term strategic sequence after v0.1

The following is strategic guidance only. It should be translated into concrete implementation slices through Project Execution Plan updates or dedicated contract documents before work begins.

```text
1. Final v0.1 main-HEAD smoke pass and tag boundary
     close the release boundary without reopening completed lanes
2. SOUL Lab Runtime MVP / voice-and-avatar adapter execution layer
     product-critical path; completes the text-in / voice-and-avatar-out hypothesis
     without moving TTS or avatar execution into RelayLM Core
3. Post-v0.1 decision debt triage
     PM-D1, PM-D2, PM-D4, and PM-D9 should be resolved or explicitly deferred
4. Ingestion contract design
     extract the shared candidate / provenance / approval-gate layer after twin
     extraction calibration; add adapters one source class at a time
5. Attention / full-duplex / broadcast design exploration
     design-only until the voice/avatar execution layer and disclosure gates are
     strong enough to carry public or multi-speaker scenes
```

Rationale: prior waves showed a recurring tendency to over-invest in diagnostic infrastructure and RelaySOUL elaboration ahead of the product-critical path. Voice/avatar execution completes the core product hypothesis; broader ingestion, broadcast, full-duplex, and multi-agent work compound on top of that boundary.

## Three-year strategic bets

### Bet 1: The durable asset is character data, not the model

Local LLMs will keep improving; the pipeline tracks that by backend swap. What cannot be swapped is years of accumulated MEM / SOUL / REL. The file-first Character Workspace direction is the foundation for a portable, user-owned character format independent of any specific model.

When large providers ship native companion features, the defensible axis is three properties: **local, private, user-owned**. The fail-closed / content-free boundary is simultaneously the safety mechanism and the proof of this differentiation.

This bet underwrites all others below.

### Bet 2: Full-duplex and interruption

Introducing ASR changes the problem class. Turn-based flow weakens, and the center of gravity shifts to interruption of in-progress speech, listening-while-speaking affect estimation, cancellation, and resume. RelayRUN's existing chunk-state tracking and idempotency design are the natural substrate. ASR remains out of current scope, but a full-duplex-aware RUN extension deserves early design-only exploration.

### Bet 3: RelaySLP as the entry point to proactivity

RelaySLP currently operates as an after-turn background path. Long-term, it is the entry point for the character initiating contact: surfacing sleep-consolidated observations in a later conversation. The existing approval-gate design directly serves as the runaway-prevention mechanism, so this direction is compatible with current governance philosophy.

### Bet 4: Longitudinal dogfooding as unique data

Almost no one holds first-party longitudinal data on an AI companion whose memory has grown over multiple years. Memory decay, identity drift, and forgetting design are open questions where this project can produce publication-grade insight. The twin evaluation infrastructure should be grown into the observation instrument for this.

## Generalized ingestion: Notion, email, recordings

The twin extraction pipeline is not just an evaluation tool; it is prototype #1 of a generalized ingestion foundation. Its design elements — two-stream extraction, provenance labeling, and private-first defaults — are source-agnostic:

```text
style / values -> SOUL candidate path
facts / events -> MEM candidate path
source metadata -> provenance and disclosure policy
approval gate -> apply, hold, or discard
```

### Design direction

Extract an ingestion contract as a shared layer: candidate schema, provenance axes, approval gates, and disclosure defaults, with thin per-source adapters. The RelaySLP candidate-formation -> approval-gate path is reusable in principle. A registered doc type such as `ingestion_contract` should be considered when this work begins.

### Key design tensions

**Bulk bootstrap and continuous sync are different problems.** Twin extraction is the former. Making email or Notion genuinely valuable requires the latter, which centers contradiction resolution, freshness management, and memory staleness — the same problems longitudinal dogfooding was meant to observe, surfaced earlier.

**Understanding and creepiness are close together.** Facts absorbed from imported sources, surfaced casually in conversation, sit on a knife edge between useful and unsettling. Extend the E1-R4 grounding / unsupported-detail-suppression direction into provenance-differentiated disclosure policy: conversation-formed memories are more freely referenceable; import-derived memories lean toward known-but-not-volunteered. Email, dense with third-party information, may warrant source-class-specific disclosure behavior beyond `private_only`.

**Recordings are a separate monster.** Offline batch transcription plus extraction fits the pipeline shape, but passively captured conversation differs fundamentally from explicitly authored content in reliability, sensitivity, and third-party speech. Provenance needs an `author: self / other / mixed` axis from the start.

**Ingestion is the existence proof for local.** Users should not need to hand email or daily recordings to a cloud provider when the value can be produced locally. This is where local / private / user-owned becomes a functional difference rather than an abstract claim.

### Suggested order

Twin extraction PR review and calibration first; then document the ingestion contract informed by that experience; adapter #2 should be one of Notion or email, not both; recordings should remain deferred alongside the ASR decision.

## Multi-user, broadcast, and multi-agent

### What breaks: turn and single primary user

The current design assumes one speaker per turn. Streaming chat is a continuous input stream, and the central problem becomes attention allocation and scheduling: which comment to respond to, which speaker to prioritize, and when to interrupt or ignore.

This is not a RelayINT extension. It is a future Attention / Selection layer in front of RelayRUN, sharing roots with full-duplex interruption design. A future RelayATN Reflex Layer Design should define that boundary. If interruption, cancellation, and priority design lands first, multi-user becomes a special case of it.

### What carries over: RelayREL and RelaySCN

RelayREL's position as relationship-policy selection before scene resolution is groundwork for per-viewer relationship projections: casual with regulars, polite with first-timers. New design is required for per-viewer REL / MEM scale and for representing a collective relationship such as the audience. Expect a two-layer structure: individual REL plus collective REL.

### Broadcast is the maximum disclosure-accident surface

A character carrying deep import-derived understanding of its primary user, appearing on a public stream, makes provenance-differentiated disclosure a survival requirement rather than a refinement. RelaySCN already owns per-scene memory, expression, and persistence policy. A future `broadcast` scene class should block `private_only`, import-derived, and specific-individual-REL-derived memories wholesale. The fail-closed principle applies here at full strength.

A useful product guarantee is: an AI VTuber should be architecturally unable to recite its owner's email or private imported notes on stream.

### Multi-agent

Other agents' utterances are untrusted input: injection risk, style contamination, and possible SOUL drift. This is naturally captured as an extension of the `author: self / other / mixed` provenance axis. The twin infrastructure enables a cheap testbed: run the user's twin as a counterpart agent for unattended long-horizon multi-agent conversation, doubling as an identity-drift observation accelerator for the longitudinal program.

### Cheap documentation-only hedges

```text
H1  Document the single-primary-user assumption explicitly in contracts
      implicit assumptions will be broken by external contributors post-release
H2  Keep the RelayREL contract shape extensible to N-ary relationships
H3  Reserve a future broadcast scene class slot in RelaySCN scene taxonomy
```

All implementation remains deferred until after voice/avatar execution and disclosure gates are ready.

## Two-layer persona: engineered shadow / kayfabe

Character appeal often correlates with the perceived existence of an unseen private life. The design insight is that accident and performance have opposite information flow.

```text
Accident     = real data crossing a boundary        (fail-closed violation)
Performance  = the appearance of a private life,
               generated with zero reference to real data
```

Teasing or hinting can therefore be designed as performance. Under a future `broadcast` scene, real MEM — import-derived, private-conversation-derived, or specific-individual-REL-derived — should be blocked, while SOUL may carry an expression class that implies the existence of private time. The shadow is fictional, not the shadow of real data.

**Why real data must never feed this:** partial hints are the entry point for inference attacks; audience-scale collective OSINT defeats paraphrase-level abstraction. A single real bit is a time bomb. A fully fictional shadow is character design, not leakage, and is architecturally compatible with the content-free boundary. Ethical questions about audience deception remain separate from this architecture note.

**RelaySOUL implication:** a two-layer persona — public persona and private persona — where the public layer may reference only the existence of the private layer, never its content.

**Implementation order:** first harden the side where the shadow cannot leak; only then play on the side that makes it look like it leaks. Build the vault before spreading rumors about the vault.

## The primary user: authority versus relationship

In group scenes, the primary user is socially one participant among many and administratively the sole owner. These must not be conflated:

```text
Owner authority   (RUN / governance layer)
  approval gates, Forget / Pin, SOUL change approval
  invariant across all scenes

REL relationship  (character social knowledge)
  who the character calls "Master", intimacy level, address terms
  retained as relationship data; SCENE-GATED in expression
```

During a broadcast the character still knows who its primary user is. Knowledge is retained; expression is gated by RelaySCN. The scene decides the right to say it aloud, not the right to know it.

### Vocabulary recommendation

Contracts and architecture should prefer neutral terms such as `primary_user` or `owner` for the subject of approval-gate authority. Avoid `master` in public repository vocabulary. The H1 single-primary-user assumption documentation should use this neutral vocabulary.

Character-facing address terms are REL relationship data and SOUL voice, not hardcoded architecture vocabulary. Terms such as `マスター`, `ご主人様`, or `せんぱい` belong in Character Workspace data. Scene-dependent address switching — `Master` in private, `あの人` on stream — is itself an expressive tool for the engineered-shadow direction.

This section is a recommendation. A binding vocabulary decision should be made in a dedicated contract, ADR, or documentation-model update before schema work depends on it.

## Personal / group scene switching

### Scene classes

```text
private_home    primary user, private context
group_private   known small group, such as private Discord voice
broadcast       public stream, untrusted audience
```

Each scene class defines both:

1. referenceable memory scope by provenance and REL range, and
2. persistence destination for newly formed memories.

Item 2 is the commonly missed half. Memories formed in group conversation must not land in the same shelf as private-context memories, or reverse-flow accidents follow. Memories carry a formation-scene label, and disclosure is resolved by a matrix of formation scene × current scene.

### Transition fail-closed direction

```text
Escalation   private -> group     automatically allowed
             someone joined the call -> immediately stricter

Downgrade    group -> private     explicit primary_user confirmation required
             we're alone again -> never inferred

Ambiguity    always resolve to the stricter side
```

## Expression responsibility layering

Using address terms as the running example:

| Layer | Owns | Address-term example |
|---|---|---|
| RelaySOUL | durable voice, values, two-layer persona | personality that treasures the master-servant bond |
| RelayREL | per-relationship expression base | calls this person `マスター` |
| RelaySCN | scene expression gate / transform directives | broadcast: address must be obscured |
| RelayEMO | transient affect intensity modulation | embarrassed -> says it haltingly |
| Main LLM + OUTPUT_POLICY | actual wording generation | `あの人はね…` |
| RelayCTX / Segmenter / RelayREF | guard, not expression | final leak barrier |

Expressive capability is effectively the product REL × SCN, rendered by the Main LLM.

## Disclosure third mode: transform

Disclosure policy is not binary. Three modes are useful:

```text
block       memory not referenceable in this scene
allow       memory freely referenceable
transform   memory referenceable only in obscured or abstracted form
            マスター -> あの人
```

`transform` extends the E1-R4 unsupported-detail-suppression direction. The engineered-shadow performance is then the expressive use of `transform` as a first-class disclosure-policy feature. The rumor-about-the-vault mechanism arrives as a governed capability rather than a hack.

## Non-goals of this document

This document does not:

- change v0.1 release scope or readiness evidence;
- add or reorder committed execution-plan lanes;
- register ingestion adapters, scene classes, schema fields, or contract vocabulary;
- authorize broadcast scenes, multi-agent runtime, ASR, or two-layer persona implementation;
- make TTS, Live2D, avatar execution, or ASR part of RelayLM Core;
- carry current-status claims.
