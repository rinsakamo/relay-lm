# OpenAI-compatible serialized counter evaluation

`src/relaylm/evaluation_openai_serialized_counter.py` provides the isolated deterministic `openai_serialized_counter` evaluation component for the merged #1387 OpenAI-compatible B3 serialized-input counter from PR #1405.

## Current component contract

`evaluate_openai_serialized_counter()` consumes the real `OpenAICompatibleSerializedInputCounter` and the real buffered `OpenAICompatibleProvider.generate(...)` path. It compares the model-input mapping delivered to the caller-supplied count function with the actual buffered request body after removing only the transport-only `stream` field.

The deterministic fixture verifies that:

- counting itself performs no provider HTTP request;
- the counted model-input mapping is byte-structure equivalent to the buffered generation request body modulo `stream`;
- the counter satisfies the provider-neutral `SerializedCognitiveInputTokenCounter` protocol;
- caller-supplied exact and conservative-estimate token counts are preserved unchanged;
- blank model configuration, non-callable count functions, and untyped count results fail closed.

## Non-goals

This component does not change provider prompts or wire schema, define a tokenizer heuristic or character/token ratio, choose numeric defaults, perform runtime total-budget enforcement, or change semantic selection/degradation.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, `docs/authority-map.yaml`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
