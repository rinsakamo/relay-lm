# AITuber SOUL Lab UI MVP

## Purpose

AITuber SOUL Lab is the browser-based local UI that turns RelayLM's runtime value into an understandable product experience.

It is not a generic settings panel. Its MVP must let a user see a character:

1. be initialized or adopted,
2. live in a Home space,
3. communicate with an external API or another RelayLM character,
4. bring that experience back as memory candidates,
5. inspect the result in Lab Observation,
6. enter Pod / SOUL Intervention only when the user intentionally changes the character core.

The product loop is:

```text
create or adopt
  -> live in Home
  -> communicate
  -> return with experience
  -> observe in Lab
  -> intervene in Pod only when needed
  -> live in Home again
```

The MVP should prove this product statement:

> A RelayLM character can have a stable SOUL, separate MEM, managed context, and relationship continuity that the user can experience without needing to understand the whole runtime first.

## Deployment shape

The UI MVP is a local browser app served by RelayLM.

```text
RelayLM Core
  localhost API server

AITuber SOUL Lab UI
  browser-based local web app

Backend
  LM Studio / OpenAI-compatible API
```

Recommended local routes:

```text
http://127.0.0.1:8090/v1/*
  OpenAI-compatible frontend/backend API

http://127.0.0.1:8090/lab
  AITuber SOUL Lab UI

http://127.0.0.1:8090/lab/api/*
  SOUL Lab management API
```

Development may use a separate frontend server such as Vite, but the distributable MVP should work as a local web app without requiring a native shell.

## Visual reference

The UI has both light and dark modes.

- Light mode keeps Home warm, domestic, and approachable; Lab is a bright engineering workspace; Pod is darker and ritualized.
- Dark mode keeps the same information architecture but uses blue lighting, blue status accents, and blue primary actions.
- Pod uses the strongest lighting contrast because it is the only UI area where SOUL-level intervention happens.

The following compressed WebP references capture the approved image direction. They are not pixel-perfect UI requirements.

![AITuber SOUL Lab light UI reference](../assets/soul_lab_ui_light_reference.webp)

![AITuber SOUL Lab dark UI reference](../assets/soul_lab_ui_dark_reference.webp)

## Conceptual layers

SOUL Lab has three intervention-depth layers plus one horizontal communication space.

```text
Home
  daily conversation and character presence

Lab Observation
  observe runtime state, memory candidates, communication results, SLP, and CTX status

Pod / SOUL Intervention
  propose, compare, apply, hold, discard, and rollback SOUL-level changes

Communication / PC Chat
  horizontal space from Home for external API or RelayLM peer communication
```

The layers are not only navigation. They express how close the user is to changing the character.

```text
Home
  live with the character

Lab Observation
  inspect the character's state and experiences without changing the core

Pod / SOUL Intervention
  intentionally modify or reject changes to the character core
```

## Required MVP screens

### 1. First Launch / No Character

On first launch, the user should not land in an empty configuration form.

A built-in `Lab Assistant` character should greet the user and guide them into either:

- creating a new character,
- adopting an existing `SOUL.md`,
- asking questions about SOUL Lab and RelayLM.

The Lab Assistant is a normal RelayLM character instance, not a privileged administrator.

It may know:

- public RelayLM help context,
- SOUL Lab screen concepts,
- tutorial progress,
- its own approved SOUL and retrieved MEM evidence through normal RelayLM context,
- user-provided conversation context.

It must not know or access:

- raw SOUL or MEM for other characters unless exposed through explicit inspection APIs,
- API keys,
- raw traces,
- unapproved configuration changes,
- filesystem contents outside allowed APIs.

No Character state remains valid and should be explicit:

```text
NO ACTIVE CHARACTER

[New character]
[Adopt existing SOUL]
[Talk to Lab Assistant]
```

### 2. Character Selector

The active character selector is always visible near the top-left.

```text
[ Rina v ]  SOUL v3 · Stable  RelayLM ●
```

The selector includes:

```text
Characters
  Rina
  Mica
  Lab Assistant
----------------
  New character...
  Adopt existing SOUL...
  No character
```

MVP requirements:

- multiple registered characters,
- one active character per UI instance,
- character switching,
- new SOUL Initialization,
- existing SOUL Adoption,
- per-character SOUL, MEM, relationship history, and rollback history separation,
- restored active character after restart.

MVP non-goals:

- character deletion UI,
- character cloning,
- shared MEM,
- simultaneous multi-character rendering,
- SOUL inheritance between characters.

Archive can replace deletion for the first UI version.

### 3. Home

Home is the daily living space.

Light mode should feel warm and domestic. Dark mode may keep the same layout with low light and blue controls.

Home MVP requirements:

- text chat,
- streaming response display,
- stop response,
- current character display,
- SOUL version and stability status,
- RelayLM connection status,
- backend connection status,
- current mode/status display,
- entry point to Contacts / Communication,
- entry point to Lab Observation,
- current visible session log.

Home states:

```text
Home
Thinking
Communicating
Lab
Intervention
Sleeping
Recovery
```

Home should not expose raw prompt internals by default. It shows the relationship surface, not the compiled context.

### 4. Contacts / Communication

Communication is a core MVP feature because it demonstrates that RelayLM memory is not just chat history.

The user controls:

```text
select peer
start communication
soft stop communication
emergency stop only when needed
```

The character controls:

```text
what to say
whether to reply
when to stop naturally
how to interpret the conversation afterward
```

MVP peers:

```text
External API peer
  OpenAI-compatible API endpoint

RelayLM peer
  another local RelayLM character or another RelayLM endpoint

Lab Assistant
  built-in local RelayLM peer for first-run demos
```

The UI should avoid per-message user approval in the normal communication loop. User editing makes the feature feel like the user is writing messages through an AI rather than allowing the character to form its own experience.

Communication stop defaults to Soft Stop:

```text
user requests stop
  -> RelayRUN marks closing intent
  -> no new topic should start
  -> character may close naturally
  -> session ends
  -> RelaySLP processes the experience
```

### 5. Lab Observation

Lab Observation is not a raw debugger. It is the place where the user sees how the latest experience was processed.

MVP panels:

- current scene,
- latest experience summary,
- communication session metadata,
- MEM used count,
- memory candidates,
- SLP status,
- RelayRUN status,
- observation note,
- CTX Repack / Unpack status,
- blocked or recovery reasons when present,
- timing summary.

The most important Lab value is showing actual memory candidates in user-readable form.

Example:

```text
Memory candidate

Mica seemed a little anxious after the second half of the previous stream.

Source: communication session
Confidence: medium
Scope: relationship memory
Status: candidate
```

For a RelayLM-to-RelayLM communication demo, the UI should let the user compare each side's memory candidate. The point is not shared logs. The point is different subjective memory formation from the same interaction.

```text
Rina's memory
  Mica seemed anxious after the stream.

Mica's memory
  Rina noticed my condition and asked if I had rested.
```

### 6. Pod / SOUL Intervention

Pod is the intentional SOUL intervention space. It should feel darker and more ritualized than Home and Lab.

The Pod exists because editing `SOUL.md` directly is technically possible but should not be treated as casual UI behavior.

MVP flow:

```text
enter intent
  -> generate candidate
  -> inspect diff
  -> run one comparison/simulation
  -> apply, hold, discard, or rollback
```

MVP Pod panels:

- current SOUL version,
- intervention target,
- intervention intent / reason,
- protected traits,
- candidate summary,
- SOUL diff preview,
- comparison / simulation status,
- rollback point,
- CTX Repack / Unpack status,
- final decision buttons.

Required actions:

- Generate candidate,
- Compare,
- Apply,
- Hold,
- Discard,
- Rollback.

MVP non-goals:

- automatic SOUL optimization,
- automatic SOUL promotion,
- personality sliders,
- benchmark tournament,
- long regression suite in the synchronous UI flow.

## CTX and EMO UI boundary

CTX Repack and CTX Unpack are core protocol-boundary operations, not content moderation.

```text
RelayCTX Repack
  attaches RelayLM-owned SOUL / MEM / RelaySCN / CTX context
  to the backend-bound payload on managed routes

RelayCTX Unpack
  separates explicit internal update blocks
  from user-visible text after backend generation
```

On managed routes, Repack and Unpack are target default-on. `pass_through` remains the compatibility exemption.

The UI may show:

```text
CTX Repack: applied
CTX Unpack: applied
Internal update candidate: present
Visible text changed by semantic filter: no
```

RelayEMO markers are optional presentation decoration. They should not be shown as required safety, censorship, or protocol separation.

MVP default recommendation:

```text
EMO marker: off
or
EMO marker: preview only
```

## Settings MVP

Settings should be minimal.

Backend settings:

```text
Backend name
Base URL
API key
Default backend model
Test connection
```

Model profile:

```text
RelayLM Recommended
  tested compatibility and default behavior

Custom / Experimental
  behavior and compatibility are not guaranteed
```

Required boundary text:

> RelayLM does not censor, rewrite, or guarantee ordinary model-generated conversation content. Output depends on the selected model, SOUL, context, and configuration. RelayLM governs tool execution, code execution, protected data access, persistence, and other side effects through runtime boundaries.

Security defaults:

- bind UI to `127.0.0.1` by default,
- remote access off by default,
- CORS deny except local UI origin,
- API keys stay server-side,
- browser does not directly read or write SOUL/MEM files,
- raw SOUL/MEM inspection is explicit and gated.

## Suggested management API surface

The UI should use dedicated management APIs instead of overloading `/v1/chat/completions`.

```text
GET  /lab/api/characters
POST /lab/api/characters
POST /lab/api/characters/{id}/activate

POST /lab/api/chat
POST /lab/api/communication/start
POST /lab/api/communication/stop

GET  /lab/api/lab/last-run
GET  /lab/api/memory/candidates
POST /lab/api/memory/candidates/{id}/adopt
POST /lab/api/memory/candidates/{id}/hold

POST /lab/api/soul/propose
POST /lab/api/soul/apply
POST /lab/api/soul/rollback

GET  /lab/api/settings
POST /lab/api/settings/backend/test
```

These APIs should enforce RelayLM authority boundaries server-side. The browser is presentation and interaction, not the owner of SOUL, MEM, RUN, SLP, or backend credentials.

## Research milestones

MVP gamification is a Lab Notebook, not a score system.

Milestones:

- First Boot,
- First Conversation,
- First Memory,
- First External Communication,
- First Mutual Memory,
- First SOUL Intervention.

Avoid:

- affection points,
- levels,
- login rewards,
- streaks,
- communication quotas,
- neglect penalties,
- paid personality upgrades.

The desired feeling is:

> Something accumulated because we spent time together.

## Deferred from MVP

Explicitly deferred:

- VRM / Live2D,
- TTS / ASR,
- OBS / streaming integration,
- image recognition,
- WebGPU inference,
- 3D room customization,
- furniture and clothing systems,
- real-time voice calls,
- simultaneous multi-avatar rendering,
- public RelayLM network,
- internet peer discovery,
- cloud sync,
- mobile app,
- always-on background communication,
- automatic SOUL updates,
- shared MEM.

These are future layers after the text-first product loop proves the core value.

## MVP completion criteria

The UI MVP is complete when:

1. first launch is guided by Lab Assistant,
2. a new character can be initialized,
3. an existing `SOUL.md` can be adopted,
4. multiple characters can be selected and switched,
5. Home supports normal text conversation,
6. an external OpenAI-compatible API peer can be contacted,
7. a RelayLM peer can be contacted,
8. communication runs with user start/stop rather than per-message approval,
9. communication creates memory candidates after SLP,
10. RelayLM-to-RelayLM communication can show different memories on both sides,
11. Lab Observation can inspect the latest experience and memory candidates,
12. Pod can propose, compare, apply, hold, discard, and rollback a SOUL candidate,
13. CTX Repack / Unpack status is observable and treated as protocol separation, not censorship,
14. EMO markers remain optional presentation decoration,
15. character, SOUL, MEM, relationship history, and rollback state survive restart.

## Summary

AITuber SOUL Lab UI MVP is a small local research room for artificial character continuity.

It should not try to be a full VTuber studio yet. It should prove that a character can be created, live in Home, communicate, return with experience, form memory candidates, and be safely observed or intentionally changed.
