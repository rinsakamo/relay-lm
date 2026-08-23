# Actual-model Character authoring boundary

This reference records the authoring boundary for Character fixtures used by
actual-model evaluation. Owning Issue: #1823. Parent evidence owner: #1386.

## Principle

Character authoring is not ordinary-turn runtime cognition.

A Character may be designed, refined, and reviewed with help from a strong
external model such as ChatGPT or Codex. The resulting SOUL/STYLE/package must
then be human-reviewed and frozen with explicit revision identity before it is
used as citable evaluation evidence.

The authoring model is a tool. It is not a persistent semantic authority inside
RelayLM.

## Core 1.0 boundary

Core 1.0 does not require a rebuilt SOUL Lab UI. A conversational authoring
workflow is sufficient if it can produce an explicit, reviewable Character
package.

A future UI may productize the same workflow after the authoring method is
stable.

## Aoi

The existing Aoi foundation fixture remains frozen and valid. It is not replaced
or rewritten as part of #1823.

## ReLM

ReLM must be deliberately re-authored before a new evaluation fixture is
frozen. Do not infer a final personality from stale prompts or construct a
minimal test persona merely to satisfy coverage.

The authoring session should make cognition as well as expression explicit:
what ReLM tends to notice, trust, doubt, prioritize, remember, reinterpret, and
how relationship or emotional context changes its response.

## Rin

Rin is based on the user, so the user is the final authority for the frozen
Character description. Repository history, assistant memory, or automated
profile inference must not substitute for deliberate authoring and user review.

The goal is not an objective psychological profile. The goal is an explicit
Character cognition/style specification the user recognizes as a useful
realization of Rin.

## Freeze requirements

Before ReLM or Rin becomes citable Stage R evidence, record at least:

- Character fixture ID;
- explicit revision/hash identity;
- SOUL/STYLE/package files included in the revision;
- authoring/review completion state;
- human authority that approved the frozen revision;
- scenario-set revision that consumes it.

Do not mutate a frozen Character fixture in place and continue citing old
evidence as if its identity were unchanged.

## Evaluation relationship

Shared scenarios may be reused across Characters, but expected behavior is not
one exact response. Hard authority requirements remain shared; interpretation
and expression are reviewed relative to each frozen Character.

Character-specific stress scenarios may be added only after the corresponding
Character revision exists.
