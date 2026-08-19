# Serialized input fit evaluation

`src/relaylm/evaluation_serialized_input_fit.py` provides the isolated deterministic `serialized_input_fit` evaluation component for the merged #1387 Cognitive Budget B3 provider-neutral serialized-input accounting capability from PR #1402.

## Current component contract

`evaluate_serialized_input_fit_component()` consumes the real `SerializedInputTokenCount`, `TokenCountMode`, and `evaluate_serialized_input_fit(...)` APIs. It does not implement a tokenizer or reconstruct provider serialization.

The deterministic fixture verifies that:

- exact counts preserve explicit framing attribution and derived cognitive-input token accounting;
- conservative estimates remain an explicit counting mode rather than an implicit heuristic;
- the final serialized input count plus reserved output capacity is authoritative for hard total-context fit and exact overflow;
- an output reservation larger than the model context window cannot fit even an empty serialized input;
- negative or boolean token counts, framing larger than the final total, and untyped estimation modes fail closed.

## Non-goals

This component does not define provider-specific token counting, tokenizer guesses, character/token ratios, semantic degradation, runtime fail-before-generation orchestration, numeric calibration/defaults, or any provider call.

## Integration status

This component is intentionally not registered in the native deterministic evaluation registry by this transaction. Shared scenario count, `src/relaylm/evaluation.py`, shared navigation, and aggregate Issue status remain for serial integration after component merge.
