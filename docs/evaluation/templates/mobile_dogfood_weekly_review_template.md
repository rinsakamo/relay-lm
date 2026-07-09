---
relaylm_doc_type: template
relaylm_authority: mobile_dogfood_observation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_not_authoritative_for:
  - runtime behavior
  - MEM/SOUL mutation authority
  - production benchmark claims
  - content-bearing local artifacts
---
# Mobile Dogfood Weekly Review Template

Copy this template into a local, gitignored path (e.g. `local/dogfood/`) before
filling it in. Do not commit filled-in copies to this repository — see the
[Mobile Dogfood Observation Runbook](../mobile_dogfood_observation_runbook.md)
local-only artifact policy. This template intentionally contains no actual
conversation content.

```markdown
# Mobile Dogfood Weekly Review

Week of:
Character(s):

## Continuation
- Do I want to keep using this daily? yes/no/unclear:
- Why / why not:

## Memory growth
- Has MEM growth slowed things down?
- Any noticeable retrieval degradation over the week?

## P1/P2 recall value
- Did P1/P2-sourced memory add value this week?
- Any P1/P2 recall that felt wrong or mixed-up?

## SOUL/REL/SCN/EMO complexity
- Did added complexity (relationship/scene/emotion state) show clear value?
- Any case where it felt unnecessary or noisy?

## Pruning candidates
- Memories to correct/forget:
- Settings/config to revisit:
- Characters/prompts to simplify:

## Notes for next week
- Hypotheses to test:
- Things to watch for:
```
