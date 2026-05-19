# RelayLM

RelayLM is a Lineage Manager for local LLMs.

It controls and traces the flow from memory to context, token spans,
runtime cache / KV cache, and budget decisions.

RelayLM is not a language model. It is a memory-context-token-runtime-cache
lineage manager for local LLM applications, agents, and local inference runtimes.

## Architecture

RelayLM uses the RelayStack architecture:

- RelayMEM
- RelayCTX
- RelayKV
- RelayPLC
- RelayTRC
- Relay Adapter

The current implementation research continues in `rinsakamo/relay-kv`.
