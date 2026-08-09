---
relaylm_doc_type: concept_policy
relaylm_authority: conversation_content_and_executable_capability_authority_boundary
relaylm_status: current
relaylm_volatility: low
relaylm_owner: runtime
relaylm_update_trigger:
  - executable capability or side-effect authority changes
  - tool, filesystem, network, protected-data, credential, or mutation execution ownership changes
  - managed-route conversation/content handling begins to authorize a new capability class
  - an adapter starts interpreting model output as executable action
relaylm_not_authoritative_for:
  - current repository implementation completion or sequencing
  - exact tool-call, command, filesystem, network, credential, persistence, memory, or character-mutation schemas
  - exact authorization, authentication, sandbox, deployment, provider, or access-control implementation
  - open-ended semantic moderation policy for ordinary natural-language conversation
  - backend, frontend, or external adapter guarantees outside RelayLM-owned capability gates
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../system-overview.md
  - ../pipeline-responsibilities.md
  - request-response-pipeline.md
  - ../context/context-assembly.md
  - ../privacy/protected-source-and-disclosure.md
  - ../ai_character_product_principles.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - runtime, router, and integration maintainers
  - tool, filesystem, network, persistence, and protected-data adapter maintainers
  - privacy, safety, and character-expression reviewers
relaylm_authority_level: concept
---
# Conversation Content and Executable Capability Authority

## Authority summary

RelayLM keeps **what a character says** separate from **what the runtime is authorized to execute, access, or mutate**.

The stable boundary is:

```text
natural-language conversation content
  -> semantic output for the conversation
  -> no executable authority by itself

capability proposal or structured action request
  -> identify the owning capability boundary
  -> validate typed inputs and caller/context authority
  -> pass the owning gate
  -> only then may an external effect occur
```

A model may mention a command, tool, file, URL, memory operation, configuration change, or other action in ordinary text. That text is not an execution token.

Conversely, once RelayLM or an attached governed adapter would interpret an artifact as an executable action, that path is no longer ordinary conversation. It must use the owning capability authority.

This page owns that conceptual separation. It does not define the exact contract for any individual capability.

## Why the boundary exists

A character runtime combines two very different kinds of output:

1. language intended to be read, heard, or otherwise presented to a user; and
2. machine-interpreted artifacts that may cause an externally observable effect.

Collapsing those categories creates unsafe authority transfer.

Examples of invalid inference include:

```text
model wrote a shell command
  -> execute it

model mentioned a file path
  -> open or overwrite that file

model said "remember this"
  -> mutate durable memory

model emitted a URL
  -> fetch it

model proposed a SOUL change
  -> rewrite character source

model claimed a tool result was needed
  -> invent or perform the tool call outside its contract
```

The stable correction is:

```text
semantic suggestion != capability authorization
```

## Conversation content is not an execution envelope

Ordinary assistant text remains conversation content even when it includes material that resembles an action.

Examples include:

- source code;
- shell commands;
- SQL;
- file paths;
- URLs;
- API examples;
- configuration snippets;
- JSON shown for explanation;
- a natural-language request to save, delete, fetch, send, or change something.

The presence of such material does not allow RelayLM Core to reinterpret the visible response as a capability call.

If a frontend or integration intentionally supports executable actions, it must receive a separately governed action artifact under its own contract rather than scraping ordinary prose for authority.

## Capability authority begins at interpretation for effect

The boundary is crossed when a RelayLM-owned or governed external component intends to interpret input as a request for an effect rather than merely present it.

Capability classes may include, depending on current implementation:

- tool invocation;
- code or command execution;
- filesystem reads or writes;
- protected-data access;
- credential or secret access;
- network requests or external API actions;
- configuration mutation;
- durable memory mutation;
- relationship, scene, character-source, or other persistent-state mutation;
- externally visible message or notification delivery;
- other irreversible or privileged side effects.

These are conceptual examples, not a registered capability enum.

Each implemented class remains subject to its exact owning architecture and contract.

## Typed artifacts do not inherit authority from prose

A capability path should operate on an explicit, bounded machine artifact rather than infer execution authority from arbitrary text.

The conceptual shape is:

```text
conversation / model output
  -> bounded parser or producer under an accepted contract
  -> typed capability candidate
  -> policy and authority validation
  -> execution decision
  -> adapter or owner execution
```

Producing a typed candidate is still not equivalent to execution approval.

A candidate may be:

- malformed;
- incomplete;
- unsupported;
- unauthorized;
- out of scope;
- stale;
- inconsistent with the current scene or caller;
- valid but intentionally not approved.

The owning gate decides the result.

## Fail closed when capability interpretation is ambiguous

Ordinary conversation can tolerate semantic ambiguity that a privileged action cannot.

When a capability path cannot establish the required identity, scope, target, parameters, authority, or current state, it must not use natural-language plausibility as a substitute.

Conceptually:

```text
ambiguous conversation meaning
  -> may ask, explain, or continue conversationally

ambiguous executable authority
  -> no side effect
  -> clarification or explicit reauthorization when supported
```

A failed capability proposal may still leave the visible conversation response usable if the owning response contract permits that separation.

## Managed context construction is not capability execution

RelayCTX Repack and related managed-route context assembly are core protocol/context operations.

They may:

- normalize client authority;
- select RelayLM-owned character/context inputs;
- omit untrusted prior history;
- construct the backend-bound request;
- preserve required structured protocol state.

Those operations do not by themselves execute an external capability merely because the compiled context describes one.

Likewise, managed-route ownership of backend context does not grant RelayCTX authority to write memory, edit character sources, access credentials, or execute tools outside the respective owners.

## Visible/internal separation is not semantic censorship authority

RelayLM may separate user-visible response material from explicit internal artifacts required by its own runtime contracts.

That protocol boundary is distinct from an open-ended rule that RelayLM must rewrite ordinary conversation based on meaning.

The stable separation is:

```text
protocol/internal boundary
  -> may suppress material that is explicitly non-visible under an owning contract

ordinary semantic conversation
  -> remains the selected model + approved character/context result
  -> is not automatically rewritten by a hidden second persona or universal moderation stage
```

Product- or deployment-specific presentation policy may exist elsewhere. It does not become executable capability authority and does not alter the core distinction on this page.

## Presentation adapters remain downstream

TTS, avatar, caption, renderer, and frontend adapters consume approved presentation artifacts.

They must not infer a privileged capability from character expression.

For example:

- saying "I'll delete it" does not itself delete a file;
- an angry avatar motion does not authorize relationship or memory mutation;
- a spoken command does not become a local shell invocation;
- a displayed URL does not authorize navigation or fetch;
- a public/private persona flourish does not expose protected data through another channel.

If an adapter intentionally supports actions, that action surface must be separately governed.

## Tool protocols remain distinct from ordinary text

Where a backend or integration has structured tool calling, the structured protocol must remain distinguishable from visible natural-language output.

A tool request may be model-produced, but RelayLM or the owning tool runtime still needs to validate the exact action boundary before execution.

The stable rule is:

```text
model selected a tool-shaped artifact
  != runtime authorized the tool effect
```

Tool observations and results likewise do not become durable character truth or unrestricted context merely because a tool executed successfully.

They enter later semantic owners only through their accepted evidence/context boundaries.

## Protected data requires purpose-bounded authority

Access to protected source, memory, credentials, or other sensitive material is itself a capability boundary when the current component would not otherwise possess that content.

A conversational need for information does not grant broad access.

The owning privacy/data authority decides whether the content may be accessed for the specific purpose, and disclosure remains a separate decision after access.

```text
may access internally
  != may disclose
  != may persist elsewhere
  != may execute another action with the data
```

## Mutation is always a capability

Durable mutation remains capability-governed even when the requested change appears harmless or conversationally obvious.

Examples include:

- MEM Correct / Forget / Pin / Unpin / Held Apply or Discard;
- character source changes;
- relationship or other persistent-state updates;
- configuration changes;
- persistent ingestion/sync state;
- destructive cleanup.

A model's confidence, emotional framing, repeated wording, or user-like voice does not replace the owning mutation authority.

Where normal chat may propose a future change, proposal and application remain distinct lifecycle states.

## Character identity is not autonomously rewritten by output

Ordinary conversation can reveal preferences, tensions, growth, or self-interpretation.

That output is evidence or candidate material only where another accepted owner says so.

It is not a shortcut for autonomous SOUL or canonical character-source mutation.

The durable character authority and personality architecture remain upstream of this concept.

## Pass-through does not create RelayLM-owned execution authority

An explicit pass-through route delegates more request authority to the configured upstream/backend path than a managed route.

That does not mean RelayLM Core silently acquires responsibility for external effects performed by an independent frontend, backend, or agent framework.

The integration boundary must still distinguish:

- what RelayLM itself executes;
- what another system executes under its own authority;
- what RelayLM merely forwards;
- what RelayLM observes or projects for diagnostics.

A delegated external capability cannot be represented as a RelayLM guarantee unless RelayLM actually owns and validates that capability path.

## Agent integrations preserve internal protocol authority

Agent planning, tool selection, tool observations, and structured intermediate artifacts may have their own protocol semantics.

Persona/context conditioning must not convert those artifacts into ordinary prose and then recover machine authority by reparsing the prose.

A safe integration keeps:

```text
agent protocol / capability artifacts
  -> machine-governed path

final natural-language response
  -> character/context presentation path
```

The exact division depends on the current integration contract, but authority must not move merely because both channels originate from the same model call.

## Capability success does not authorize unrelated persistence

A valid capability effect proves only that the owning action succeeded under its contract.

It does not automatically authorize:

- durable memory formation from every tool result;
- SOUL or SELF updates;
- relationship updates;
- scene persistence;
- broad diagnostic logging of protected payloads;
- reuse of credentials for a different action;
- disclosure of all returned data.

Later uses require their own authority.

## Capability failure does not invite prose fallback execution

If a structured action fails validation or execution, the runtime must not recover by extracting a command from visible text and running it through an ungoverned path.

Likewise, failure of one capability implementation does not authorize a more privileged fallback unless the current contract explicitly defines that fallback.

A conversational explanation of the failure may be appropriate, but it remains conversation content.

## No hidden authority from confidence or intent classification

Intent, reference, scene, relationship, affect, or analyzer confidence can help route a request.

None of them independently authorizes a side effect.

```text
high confidence that user wants action X
  != authority to execute action X
```

The final action boundary still validates the exact capability requirements.

This preserves the distinction between understanding a request and possessing permission to perform it.

## Diagnostics remain content-free by default

Generic capability diagnostics should report bounded state rather than protected action payloads.

Useful classes may include:

- capability family;
- candidate present/absent;
- validation outcome;
- execution attempted/not attempted;
- result class;
- reason IDs;
- bounded counts or timing.

They should not expose by default:

- credentials;
- protected file bodies;
- memory content;
- raw tool payloads containing protected information;
- full external API responses;
- user-visible conversation bodies merely to explain a gate decision.

Exact diagnostic schemas belong to owning contracts.

## Relationship to character experience

A character can remain expressive, opinionated, playful, confrontational, or emotionally distinctive without acquiring hidden execution authority.

The capability boundary is deliberately orthogonal to personality.

That allows RelayLM to preserve a recognizably characterful conversation while keeping privileged actions typed, explicit, reviewable, and fail-closed.

The character-experience quality model is a separate responsibility and should not be inferred from this page.

## Non-goals

This concept does not:

- define every capability RelayLM may ever support;
- register tool or action schemas;
- authorize shell, filesystem, network, credential, or protected-data access;
- define current tool execution support;
- define open-ended content moderation policy;
- guarantee the behavior of external frontends, backends, models, or adapters;
- replace exact mutation, privacy, route, or integration contracts;
- authorize automatic character-source updates.

## Durable invariants

```text
conversation content != executable authority
proposal != approval
candidate != execution permission
model confidence != permission
access != disclosure
capability success != unrelated persistence authority
capability failure != ungoverned fallback
character expression != side-effect authority
```

These invariants survive provider, model, frontend, and adapter changes.
