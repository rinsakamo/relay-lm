# Free-form temporal State-shadow evaluation

`src/relaylm/evaluation_freeform_current_state_shadow.py` provides the isolated deterministic `freeform_current_state_shadow` regression component for the Context Compiler State-vs-MEMORY boundary.

## Current component contract

`evaluate_freeform_current_state_shadow()` calls the real `compile_cognitive_input(...)` API and observes only resulting MEMORY residency. It does not reproduce or invent temporal parsing rules.

The component now verifies the post-#1409 authority boundary:

- line-leading `Current <canonical key> is <value>` prose does not itself establish typed currentness;
- `<canonical key> is currently <value>` prose does not itself establish typed currentness;
- `<canonical key> is now <value>` prose does not itself establish typed currentness;
- prefixed `Previous current ...`, year-bearing historical prose, omitted-key prose, and free-form boolean prose likewise remain non-authoritative;
- all of those ordinary unannotated MEMORY chunks remain resident unless a separate accepted structural State-addressing rule applies.

The scenario ID is retained for compatibility with already-merged isolated-component references, but its oracle is corrective: lexical temporal wording is evidence text, not temporal authority. Typed MEMORY temporal/currentness metadata is owned by #1260/#1409 and future C5 may consume that metadata directly.

## Non-goals

This component does not implement C5, parse years/dates/tense, infer aliases or synonyms, interpret negation, add free-form boolean/degree semantics, change retrieval ranking, mutate State or MEMORY, or add an LLM contradiction classifier.

## Integration status

This isolated component does not modify the native deterministic evaluation registry, aggregate scenario count, shared navigation, or aggregate implementation status. Any shared registration/reconciliation remains Serial Integration work after the corrected component is merged.
