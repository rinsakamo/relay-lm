# Context Compiler

The Context Compiler constructs the smallest sufficient cognitive context for the current turn **as the character**.

## Inputs

- Identity Core;
- relevant Canonical State;
- Event Journal and runtime observations as evidence sources;
- the current governed Event;
- minimum protocol/tool state;
- applicable audience/privacy/capability narrowing.

## Output

A bounded `CognitiveInput` object.

## Rules

- Raw transcript replay is not the default context mechanism.
- Raw assistant history is not trusted as factual support.
- Unsupported prior assistant assertions must not become accepted truth through prompt placement.
- Relevant accepted State may influence the response without being recited.
- Optional history/memory is evicted before protected Identity.
- The current valid request kernel remains protected.

> **Conversation history != Cognitive Context.**

## MVP implementation

M2 begins with a deliberately small projection: Identity + all active Canonical State + the current Event, with `context=[]`. It does not replay prior Events. This is sufficient to prove session continuity without introducing a retrieval subsystem before it is needed.

Large-State relevance selection, Event-derived trusted Context, and bounded budgeting are deferred to #1267 without changing this authority model.
