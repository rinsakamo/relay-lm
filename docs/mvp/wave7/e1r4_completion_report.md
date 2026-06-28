---
relaylm_doc_type: implementation_completion_report
relaylm_authority: historical_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: low
relaylm_owner: e1_quality_gates
relaylm_update_trigger:
  - source PR number or merge commit changes
  - validation evidence changes
---
# E1-R4 Completion Report

Last reviewed: 2026-06-28 JST.

## Source PR

- PR: #437
- URL: https://github.com/rinsakamo/relay-lm/pull/437
- Title: `feat: add E1-R4 grounded recall response`

## Implementation boundary

E1-R4 implements retrieval-response grounding and unsupported-detail suppression as a deterministic request-side helper:

- `relaylm/relaymem_grounded_recall_response.py`
- `scripts/relaylm_e1r4_grounded_recall_response_smoke.py`
- `scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py`
- `scripts/relaylm_e1r4_grounded_recall_security_smoke.py`
- `docs/architecture/e1r4_retrieval_response_grounding.md`

The helper builds `relaymem.grounded_recall_context.v0` from already retrieved Primary MEM projections. The private backend-bound context may include bounded `fact_text` evidence. Public projections are content-free.

## Response behavior boundary

The backend-bound instruction requires remembered facts to come from directly supported evidence, marks inference as inference, and tells the backend not to invent dates, names, preferences, quantities, relationships, or causes. If retrieved evidence is missing or does not support a requested detail, the context instructs suppression, omission, or uncertainty rather than a remembered-fact claim.

## Request-side vs response-side decision

E1-R4 is request-side only. It does not implement post-hoc visible response rewriting, SSE mutation, stream interception, or public display of private evidence. This preserves visible-output transport semantics and avoids leaking protected evidence through errors or diagnostics.

## Non-goals

- E1-R3 formation summary changes
- O2 supervised worker service
- O3 always-on local operation
- scheduler loop / polling / sleep / daemon
- new queue lifecycle authority
- new worker execution authority
- browser-owned trusted admission
- automatic character-store bootstrap
- Pin / Unpin runtime changes
- Held Apply / Discard runtime changes
- Forget / Correct behavior changes
- Merge / Supersession
- Secondary MEM consolidation
- RelaySOUL proposal/intervention/rollback
- TTS/audio/avatar/Live2D/ASR
- post-hoc visible response rewriting
- public display of protected source, raw transcript, raw memory body, queue payload, store root, source path, token digest

## Tests / smokes run

Connector-local validation against the new helper and slice smokes:

```bash
PYTHONPATH=/mnt/data/e1r4 python -m compileall -q /mnt/data/e1r4/relaylm /mnt/data/e1r4/scripts
PYTHONPATH=/mnt/data/e1r4 python /mnt/data/e1r4/scripts/relaylm_e1r4_grounded_recall_response_smoke.py
PYTHONPATH=/mnt/data/e1r4 python /mnt/data/e1r4/scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
PYTHONPATH=/mnt/data/e1r4 python /mnt/data/e1r4/scripts/relaylm_e1r4_grounded_recall_security_smoke.py
```

Output:

```text
relaylm_e1r4_grounded_recall_response_smoke: ok
relaylm_e1r4_unsupported_detail_suppression_smoke: ok
relaylm_e1r4_grounded_recall_security_smoke: ok
```

Full repository validation was not executable in this connector environment because local `git` access to GitHub failed DNS resolution. Reviewer/CI validation should run the full command set from the implementation prompt.

## Content leakage review

Public projection fields are diagnostic-only and explicitly report:

```text
evidence_content_included=false
runtime_private_evidence_omitted=true
raw_memory_text_included=false
raw_user_text_included=false
raw_assistant_text_included=false
protected_source_body_included=false
queue_payload_included=false
store_root_included=false
source_path_included=false
claim_token_included=false
lease_owner_included=false
token_digest_included=false
source_digest_included=false
```

The security smoke verifies raw user text, raw assistant text, protected source body, queue payload, store root, source path, claim token, lease owner, token digest, and source digest are absent from public diagnostics.

## Authority preservation

E1-R4 does not create a new retrieval authority, queue authority, worker authority, scheduler authority, or browser trust authority. It consumes already retrieved Primary MEM projections and applies lifecycle/scope/provenance support checks before constructing the backend-bound recall contract.

Hidden / prior / prepared / recovery_required / corrupt / cross-scope memories are excluded before grounding. Pin ranking only reorders eligible evidence and does not create support. Held Governance evidence is not treated as recalled fact unless a later explicit authority has made it eligible Primary MEM.

## Remaining MVP gates

After E1-R4, the remaining MVP-adjacent items are not E1 quality gates. O2/O3 remain planned/unimplemented unless an explicit MVP need pulls them forward, and static SOUL Lab bundle serving remains optional if local packaging requires it.
