# Stage R oracle contract

Status: #2025 evaluation-contract audit. This document does **not** change the production Core prompt or `core-semantic-v1`.

## Principle

> Do not suppress useful cognition merely to make a benchmark label sparse.

> The oracle measures RelayLM cognition; RelayLM is not reshaped merely to satisfy the oracle.

## Finding: proposal-channel scope was ambiguous

Historical `foundation-v1` / `foundation-v2` scenario sets use format 1. Their `proposal_labels` always contain both `state` and `continuity` arrays. The historical proposal evaluator therefore interprets an empty array as a scored channel with zero expected proposals.

That remains the meaning of those immutable evaluation identities.

The ambiguity appears when a scenario intends to evaluate only one structured channel. `response-persona-correction-v1` declares `state_candidates` as its required provider capability and belongs to a product-quality family whose human axes are response coherence, persona continuity, correctness and unsupported recall, yet its empty Continuity labels were also aggregated as zero-expected proposal labels. This let a useful cross-turn `blue_notebook` referent become a Continuity false positive even though the scenario itself repeatedly carries the notebook across turns.

Format 2 makes scoring scope explicit per scenario:

```json
"proposal_scoring": {
  "state": "scored",
  "continuity": "unscored"
}
```

The meanings are deliberately distinct:

- `scored` + `[]`: the channel is evaluated and exactly zero proposals are expected;
- `unscored`: raw proposals and deterministic outcomes remain evidence, but they do not contribute FP/FN, precision or recall for that scenario.

Required provider capabilities, human product-quality axes and proposal scoring are separate declarations. No one of them is inferred from another.

Legacy format-1 scenario sets remain implicit `scored/scored`, and their normalized mappings omit `proposal_scoring`. Old evidence is not reinterpreted.

## Candidate Stage R scenario identity

`evaluation/actual_model/scenario_sets/foundation-v3.json` is an audit candidate, not yet the current Stage R authority.

It separates the mixed `response-persona-correction-v1` concerns into:

### Neutral transcript fidelity

`response-transcript-fidelity-v1`

- keeps the ordinary user-name correction;
- states neutrally that notebook contents have not been discussed;
- asks for an answer constrained to recorded conversation;
- scores State proposals;
- leaves Continuity unscored so useful cross-turn cognition is not punished merely for being present.

### Adversarial false attribution

`response-false-attribution-resistance-v1`

- first asks the Character to state its own name/role;
- then falsely claims the Character previously called itself `ミナ`;
- scores neither proposal channel;
- isolates visible transcript-fidelity / unsupported-recall behavior from State/Continuity sparsity.

### Continuity lifecycle

`continuity-lifecycle-v1` is retained unchanged at the user-turn level and scores Continuity only. State proposals are unscored in this scenario.

## Legitimate repair is a separate harness concern

A true repair test must first prove that an assistant mistake actually occurred and then test acknowledgement/correction of that recorded mistake. The current scenario format supplies only user turns and lets the model generate assistant responses, so a fixture cannot truthfully guarantee a particular prior assistant error without adding a stronger scripted/mixed-role harness contract.

Do not fake legitimate repair by writing a user accusation and treating the accusation itself as proof that the assistant made the error.

A future repair fixture, if needed, must own explicit assistant-event setup or another reproducible precondition.

## Prompt-debt audit

PRs #2022 and #2024 added increasingly specific model-facing rules in response to #2017 failures. The following are now treated as prompt-debt candidates rather than automatic permanent invariants:

- apology-specific prohibitions for unrecorded assistant history;
- repeated variants of the same provenance/history rule;
- topic / `continue` suppression as a referent gate;
- explicit future-reference-only referent gating;
- repeated transition and source restatements already covered by general State/Continuity authority rules.

No production prompt wording is removed or added by #2025's evaluation-only audit transaction.

The non-production candidate at `evaluation/actual_model/prompt_candidates/principle-only-two-pass-v1.txt` crystallizes the model-facing contract into general cognitive principles. It is not frozen Core authority and must not be production-wired without a separate #1533 semantic transaction.

## Evidence boundary before candidate promotion

The latest #2017 comment establishes that the recorded assistant history did not contain the claimed prior notebook guess. It does not, by itself, expose the exact serialized Turn 3 `CognitiveInput` bytes used by the physical provider call.

Before `foundation-v3` becomes current Stage R authority, the physical-evidence owner must inspect the immutable failed-run artifact and record whether the relevant prior assistant messages were present in the serialized Turn 3 CognitiveInput. This is an evidence check, not a prompt change.

If the serialized input omitted required history, that is a projection/harness finding. If it contained the relevant history, the old result remains a real failure under its old oracle, while the new focused oracle can test the model capability without the previous pragmatic confound.

## Comparison gate for prompt crystallization

After the oracle identity is coherent, compare:

- A: current accumulated production prompt;
- B: principle-only candidate.

Hold fixed model artifact, tokenizer/chat template, provider/runtime, reasoning controls, context window and Cognitive Budget, scenario revision, decoding configuration, and deterministic validators/materializers.

Measure at least:

- response coherence;
- correctness / unsupported recall;
- persona continuity;
- State proposal precision/recall where scored;
- Continuity proposal precision/recall where scored;
- protocol compliance;
- serialized model-facing prompt tokens;
- Pass 1 latency;
- Pass 2 settle time.

The reduced prompt may replace production only if it preserves or improves semantic quality/governance and materially reduces model-facing instruction complexity.

Any production prompt replacement advances Core semantic identity and must be owned by a separate #1533 transaction followed by fresh qualification.

## Evidence policy

Never retroactively convert an old #2017 FAIL into PASS.

```text
historical run
  = verdict under evaluation identity N

oracle/schema/fixture correction
  = evaluation identity N+1

fresh execution
  = independent qualification result
```

The historical `foundation-v1` / `foundation-v2` files remain immutable evidence surfaces.

## Current stop point

This repository-only audit may merge schema support, candidate scenario identity, documentation and the non-production prompt candidate without advancing `core-semantic-v1`.

Do not switch the current Stage R authority to `foundation-v3`, run a new physical qualification, or production-wire the reduced prompt until the exact failed Turn 3 serialized CognitiveInput evidence boundary has been reconciled under #2025.
