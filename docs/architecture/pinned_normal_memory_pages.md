---
relaylm_doc_type: stable_architecture
relaylm_authority: pinned_normal_memory_page_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - memory_lifecycle_design.md
  - character_template_creation_flow.md
  - file_first_character_workspace_design.md
  - phase_i5b_pin_unpin_apply.md
---
# Pinned Normal Memory Pages

## Purpose

This note defines the target meaning of pinned normal memory pages in the file-first Character Workspace.

Pinned normal memory is ordinary memory for retrieval and context injection. It is also intentionally protected from ordinary RelaySLP maintenance.

## Core rule

```text
Pinned normal memory
  -> ordinary memory for RelayMEM retrieval
  -> eligible for RelayCTX injection when relevant
  -> intentionally fixed and important from the user's point of view
  -> not changed by ordinary RelaySLP maintenance
```

Pinning does not make a memory a character source file. It remains lower authority than `SOUL.md`, `STYLE.md`, `EMOTION.md`, `SCENE.md`, `RELATIONSHIP.md`, `MEMORY.md`, and `BOUNDARY.md`.

Pinning also does not mean always injected. It remains subject to relevance, scope, lifecycle eligibility, scene policy, token budget, and boundary rules.

## Recommended metadata

```markdown
status:: active
pin_state:: pinned
slp_update:: disabled
importance:: high
```

For template-scoped RelayLM onboarding knowledge:

```markdown
status:: template_knowledge
source:: template:relaylm_onboarding
scope:: product_help
pin_state:: pinned
slp_update:: disabled
update_policy:: bundled_template_update_only
```

## Component behavior

```text
RelayMEM
  Treats the page as ordinary retrieval memory.
  Compiles blocks and chunks the same way as other memory pages.
  May use pin_state as a retrieval or ranking hint when all scope and lifecycle gates pass.

RelayCTX
  Receives selected memory evidence from RelayMEM.
  Places relevant pinned memory in the selected memory tier or dynamic retrieval tier.
  Does not paste all pinned pages unconditionally.

RelaySLP
  Does not rewrite, merge, summarize away, or supersede the page during ordinary memory maintenance while slp_update:: disabled is present.
  May still create a review proposal when a user or operator explicitly asks for a change.

User / workspace editor
  May edit the Markdown file because the workspace is file-first.
  May remove slp_update:: disabled if normal RelaySLP maintenance is desired.
```

## RelayLM onboarding knowledge

Official starter and showcase characters may include `memory/topics/relaylm.md` as pinned normal memory.

That page explains RelayLM basics when relevant, without turning the character into a developer-review character.

Self-authored and imported characters should not receive this memory automatically. If the user copies the file into a custom workspace, it works as ordinary pinned memory under the same metadata rules.

## Summary

```text
Pin = user-visible fixed and important normal memory.
Pin does not mean always-in-prompt.
Pin does not mean source identity.
Pin does not prevent user file edits.
Pin protects the page from ordinary RelaySLP maintenance while slp_update:: disabled is present.
```
