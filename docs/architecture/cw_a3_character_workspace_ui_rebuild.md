---
relaylm_doc_type: implementation_handoff
relaylm_authority: cw_a3_character_workspace_ui_rebuild
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - Character Workspace top-level UI surfaces change
  - SOUL Lab route mapping changes
  - content-free UI projection rules change
  - Memory governance visibility moves between default surfaces and Advanced
relaylm_not_authoritative_for:
  - CW-A4 SLP-maintained workspace maintenance
  - CW-A5 character creation or template import
  - runtime prompt injection behavior
  - source write/save API contracts
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - file_first_character_workspace_design.md
  - cw_a1_file_first_source_tree_parser_contracts.md
  - cw_a2_workspace_compiler_projections.md
  - soul_lab_ui_mvp.md
  - project_execution_plan.md
---
# CW-A3 Character Workspace UI Rebuild

## Scope

CW-A3 rebuilds `apps/soul-lab` around the file-first Character Workspace user model. It changes the browser shell and read-only UI surfaces from an internal SOUL Lab/governance-first layout into these top-level surfaces:

```text
Home
Character
Scenes
Relationships
Memory Wiki
Runtime
Advanced
```

CW-A3 is a UI rebuild. It is not CW-A4 RelaySLP-maintained workspace maintenance and not CW-A5 character creation, templates, or showcase import.

## Top-level surfaces

### Home

Home keeps the existing RelayLM `/v1/chat/completions` authority path. The browser continues to send only the server-projected route model and ordinary user/assistant messages. It does not send raw SOUL, raw MEM, compiled context, namespaces, backend IDs, credentials, source paths, queue identities, or frontend-generated system/developer messages.

Real Runtime and Local Preview remain explicit modes. Local Preview is never selected automatically after a Real Runtime failure.

### Character

Character shows the required/optional source families as safe source-status cards:

```text
SOUL.md
STYLE.md
EMOTION.md
BOUNDARY.md
optional LORE.md
```

The surface is read-only / draft-oriented. Without an explicit save API, editing is preview-only and not saved. BOUNDARY.md remains visible as a high-priority source. The UI does not add RelaySOUL apply/rollback, source auto-writing, or LLM-generated source rewrites.

### Scenes

Scenes separates:

```text
SCENE.md
scenes/*.md
scenes/_inbox/*.md
```

SCENE.md is presented as scene policy, active scene pages as known scenes, and `_inbox` as candidate/staging. RelaySCN remains the scene policy owner. RelayEMO is not shown as the scene owner. ACG-6 structured classifier execution, scene auto-merge, and runtime-authoritative browser scene selection remain non-goals.

### Relationships

Relationships separates:

```text
RELATIONSHIP.md
relationships/<target>.md
relationships/_inbox/**
```

RelayREL is shown as a relationship policy layer separate from SOUL identity. Role assignment and important relationship parameters require proposal / explicit approval and are not auto-applied by the browser.

### Memory Wiki

Memory Wiki uses human-facing vocabulary and avoids reviving one-file-per-memory UI assumptions. It separates memory policy, pages, blocks, retrieval chunks, inbox/staging, forgotten items, and archive/hidden/held/blocked states.

Default Memory Wiki surfaces do not expose `memory_id`, revision, pin state, apply token, queue, worker, or audit internals. Those details are intentionally moved to Advanced.

### Runtime

Runtime displays content-free summaries for latest used scene, emotion, relationship projection, used-memory evidence, context projection, and CW-A2 tier summaries. Runtime does not display backend prompt text, raw traces, content-bearing source bodies, source paths, memory IDs, or queue records by default.

Used-memory evidence is the authority for whether memory entered backend-bound context. The UI must not infer backend-bound context from visible response text.

### Advanced

Advanced is the developer / diagnostics / internal governance surface. It can intentionally expose labels such as memory_id, revision, pin_state, lifecycle state, apply token, queue, worker, audit, and raw content-free projections when existing APIs expose them safely. It still must not expose content-bearing protected source, credentials, API keys, URL credentials, raw backend prompts, or raw traces.

Existing Correct / Forget / Pin / Unpin / Held Governance controls remain guarded by their existing loopback-only token/revision/security contracts. Moving them to Advanced does not increase browser authority.

## Old route mapping

CW-A3 absorbs old SOUL Lab routes as follows:

```text
#/home          -> Home
#/observation   -> Runtime
#/communication -> Advanced
#/pod           -> Advanced
#/adoption      -> Advanced
#/settings      -> Advanced
```

The canonical visible routes are:

```text
/lab/#/home
/lab/#/character
/lab/#/scenes
/lab/#/relationships
/lab/#/memory
/lab/#/runtime
/lab/#/advanced
```

## Default display rule

Default surfaces use content-free projection, source-status wording, counts, hashes, and status labels. Raw source content, full compiled prompts, queue payloads, credentials, absolute filesystem paths, and protected source bodies are not default browser UI content.

Browser state remains minimal. Conversation transcripts stay browser-process-local and are not saved to `localStorage`. Character Workspace UI state must not persist raw source or memory bodies to browser storage.

## Non-goals

CW-A3 does not implement:

- CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates or auto-apply;
- CW-A5 character creation, templates, or showcase import;
- source file auto-writing or LLM source rewrites;
- RelaySOUL apply/rollback;
- Communication peer transport;
- static bundle serving from RelayLM;
- TTS/audio/avatar/Live2D/ASR;
- O2/O3 supervised or always-on worker operation;
- browser-owned trusted Home admission;
- runtime prompt injection or prompt preview production apply;
- backend prompt/full compiled context display;
- raw trace display;
- credentials display;
- queue/worker mutation;
- memory mutation authority beyond existing explicit loopback contracts;
- one-file-per-memory model revival;
- ACG-6 scene classifier execution.

## Validation

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run smoke:home-conversation
npm run smoke:lifecycle-visibility
npm run smoke:forget-ui
npm run smoke:pin-unpin-ui
npm run smoke:held-governance-ui
npm run smoke:character-workspace
npm run build
```

Repository validation:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a1_file_first_workspace_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a2_workspace_compiler_smoke.py
```
