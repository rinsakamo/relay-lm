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
# Mobile Dogfood Daily Note Template

Copy this template into a local, gitignored path (e.g. `local/dogfood/`) before
filling it in. Do not commit filled-in copies to this repository — see the
[Mobile Dogfood Observation Runbook](../mobile_dogfood_observation_runbook.md)
local-only artifact policy. This template intentionally contains no actual
conversation content.

```markdown
# Mobile Dogfood Daily Note

Date:
Character:
Device:
Location context: home / outside / work / other

## Usage
- Morning:
- Daytime:
- Evening:

## Quality
- Best response:
- Worst response:
- Did I want to continue? yes/no/unclear

## Memory
- Helpful recall:
- Missing recall:
- Over-recall / creepy recall:
- Wrong source mixing:

## Latency
- Perceived speed:
- retrieval_ms if available:
- backend_forward_ms if available:
- pipeline_overhead_ms if available:
- time_to_first_token_ms: not measured / null (streaming TTFT is not implemented yet)

## Follow-up
- Memory to correct/forget:
- Prompt/config suspicion:
- Next hypothesis:
```
