---
relaylm_doc_type: evaluation_record
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
- time_to_first_chunk_ms if LAT-2 stream_timing is available:
- stream_drain_ms if LAT-2 stream_timing is available:
- stream_chunk_count if LAT-2 stream_timing is available:
- time_to_first_token_ms: null / not used for streaming; see LAT-2 stream_timing

## Follow-up
- Memory to correct/forget:
- Prompt/config suspicion:
- Next hypothesis:
```
