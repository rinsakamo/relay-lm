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
