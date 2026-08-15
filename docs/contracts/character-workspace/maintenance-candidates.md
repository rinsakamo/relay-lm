---
relaylm_doc_type: contract
relaylm_authority: character_workspace_maintenance_candidates_and_proposals_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - maintenance run, candidate, proposal, or projection schema changes
  - candidate/proposal identifier, field, status, risk, or reason vocabulary changes
  - source-evidence parsing, write-candidate, approval, or fail-closed gates change
  - public content-free projection or runtime-private boundary changes
relaylm_not_authoritative_for:
  - stable Character Workspace maintenance responsibility and lifecycle architecture
  - CW-A4 milestone completion or repository-wide implementation status
  - Character Workspace source-tree, Markdown validation, or compiler semantics
  - RelayMEM lifecycle/mutation, RelaySCN scene, RelayREL relationship, or RelaySOUL apply authority
  - queue, worker, scheduler, current-turn response, or runtime activation authority
  - source retirement, documentation migration, or Lane R repository classification
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/character-workspace/maintenance-candidates.md
  - ../../architecture/cw_a4_slp_workspace_maintenance_candidates.md
  - source-tree.md
  - parser-and-validation.md
  - compiled-projections.md
relaylm_verified_by:
  - ../../../scripts/relaylm_cw_a4_workspace_slp_candidates_smoke.py
  - ../../../scripts/relaylm_cw_a4_workspace_slp_review_fix_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace and RelaySLP maintenance maintainers
  - memory, scene, relationship, compiler, privacy, and approval reviewers
  - public-diagnostics and documentation maintainers
relaylm_authority_level: exact_contract
---
# Character Workspace Maintenance Candidates Contract

## Authority summary

This contract owns the exact current candidate/proposal planning boundary implemented by:

    relaylm/character_workspace/_slp_core.py
    relaylm/character_workspace/_slp.py
    scripts/relaylm_cw_a4_workspace_slp_candidates.py

It owns the current RelaySLP Character Workspace maintenance run, candidate, proposal, source-evidence, write-candidate, validation-gate, identifier, status, and content-free projection semantics.

The stable deferred-maintenance responsibility model remains in [Character Workspace Maintenance Candidates](../../architecture/character-workspace/maintenance-candidates.md). The live CW-A4 implementation handoff remains a current implementation source and is linked for provenance; it is not retired by this contract promotion.

The exact lifecycle remains:

    bounded governed source evidence
      -> read-only workspace validation
      -> deterministic candidate/proposal planning
      -> content-free public projection
      -> optional allowlisted candidate/proposal write
      -> separate owner approval/apply boundary
      -> source/compiler authority

Candidate or proposal creation is never approval, source application, activation, current-turn response mutation, queue publication, or worker execution.

## Implemented schema identifiers

The exact current schema identifiers are:

    relaylm.character_workspace_slp_run.v0
    relaylm.character_workspace_candidate.v0
    relaylm.character_workspace_proposal.v0
    relaylm.character_workspace_slp_projection.v0

CharacterWorkspaceSLPRun.schema_version uses the run identifier. Candidate and proposal private records use their respective identifiers. The public projection always uses relaylm.character_workspace_slp_projection.v0, including when the private run is invalid or has no candidates.

## Exact result shapes

The current private source-evidence value carries exactly these fields:

    relative_path
    stable_ref
    content_hash
    roles
    text_for_private_planning
    malformed
    reason_ids

Its public projection is content-free and carries:

    schema_version
    source_ref
    content_hash
    roles
    reason_ids
    content_free

The current candidate value carries exactly these fields:

    schema_version
    candidate_id
    candidate_kind
    target_domain
    target_path
    source_evidence_refs
    risk_level
    approval_required
    auto_apply_eligible
    apply_default
    reason_ids
    content_hash
    created_by

The current proposal value carries exactly these fields:

    schema_version
    proposal_id
    proposal_kind
    target_domain
    target_path
    approval_required
    blocked_reason_ids
    public_summary

The current private run value carries exactly these fields:

    schema_version
    generated_by
    status
    is_valid
    character_id
    dry_run
    write_candidates
    candidates
    proposals
    written_paths
    reason_ids
    blocked_reason_ids
    source_evidence_count
    source_evidence_refs
    content_free

## Exact vocabulary

The current candidate target domains are exactly:

    memory
    scene
    relationship

The current candidate kinds are exactly:

    memory_inbox_addition
    scene_inbox_addition
    relationship_note
    relationship_parameter_proposal

The current proposal kinds are exactly:

    append_inbox_page
    relationship_update
    uppercase_source_change_required

The current risk levels are exactly:

    low
    medium
    high

The current source roles exposed by source-evidence classification are exactly:

    user
    assistant
    unknown

The current created_by value is relaylm.character_workspace_slp.

The current candidate and proposal identity prefixes are:

    cw-a4-candidate:
    cw-a4-proposal:

Candidate IDs use the first 32 hexadecimal characters of their deterministic content hash. Proposal IDs use the first 32 hexadecimal characters of their deterministic candidate/proposal hash. Source-evidence references use the src: prefix and the first 24 hexadecimal characters of their deterministic path/content hash. None of these identities uses a timestamp, random UUID, file mtime, or absolute path.

The current candidate defaults are strict:

    approval_required = true
    auto_apply_eligible = false
    apply_default = dry_run_only

Every current proposal is approval-required. A sensitive memory candidate is high risk; ordinary memory, scene, and relationship candidates use the current low or medium values selected by the implementation. No current candidate or proposal is an activation authority.

## Run status vocabulary

The planner emits these current run statuses:

    invalid_workspace
    path_escape_rejected
    missing_required_source
    invalid_character_id
    invalid_root
    reserved_path_conflict
    malformed_markdown
    malformed_source_evidence
    no_candidates
    planned
    write_blocked

The workspace validator owns delegated validation statuses and their precedence. A valid workspace with no accepted evidence or no candidate signal returns no_candidates; a valid workspace with candidates or proposals returns planned; a write-mode conflict or other write failure returns write_blocked and never overwrites a different existing artifact.

## Bounded source evidence

The planner reads only these workspace-relative source roots:

    .relaylm/sources/conversations
    .relaylm/sources/corrections
    .relaylm/sources/imports

The current default bounds are:

    max_source_files = 32
    max_candidates = 64
    max_read_bytes = 65536

Source files are bounded UTF-8 reads. Control characters other than newline, carriage return, and tab are rejected. Source roots and files must remain inside the workspace after resolution; symlink escapes fail closed. JSON source roles are normalized from user/human and assistant/model/ai to the public user and assistant role values. Plain-text User:, Assistant:, and Model: lines provide the corresponding bounded planning text. Missing user assertion text does not become a user-fact candidate. Assistant-only text is blocked from user-fact promotion.

The planner delegates workspace-root, source-path, Markdown, and required-source validation to the Character Workspace source-tree and parser/validation contracts. It does not weaken those contracts or repair an invalid workspace.

## Candidate and proposal planning

User-origin evidence may produce a deterministic memory inbox candidate. Scene hints may additionally produce a scene inbox candidate. Relationship hints may additionally produce a relationship note or, for important relationship parameters/roles, an approval-required relationship parameter proposal. Sensitive memory remains approval-required and is not auto-applied.

The current planning boundary preserves these distinctions:

    source evidence
      != candidate
      != proposal
      != approved source/wiki change
      != compiled projection
      != current runtime state

The planner never treats assistant-only speculation as a user fact, never turns a scene candidate into active scene state, never turns a relationship candidate into current relationship policy, and never replaces RelayMEM lifecycle or RelaySOUL source authority.

## Exact write-candidate boundary

When write_candidates is enabled, candidate Markdown and proposal JSON may be written only under these exact prefixes:

    memory/inbox/
    scenes/_inbox/
    relationships/_inbox/
    proposals/memory/
    proposals/scene/
    proposals/relationship/

Current generated candidate paths are deterministic memory/inbox/memory-<hash>.md, scenes/_inbox/scene-<hash>.md, or relationships/_inbox/relationship-<hash>.md paths. Proposal paths are deterministic JSON paths under the matching proposals/<domain>/ directory.

The exact write gate is:

- candidate Markdown must be a classified memory, scene, or relationship workspace path;
- proposal artifacts must be JSON under one of the three allowlisted proposal prefixes;
- absolute, traversal, backslash-variant, uppercase-source, and unrecognized paths are rejected;
- an existing identical artifact is idempotent;
- an existing different artifact is a conflict and is never overwritten;
- deletion is not supported;
- a candidate write failure prevents its dependent proposal write;
- successful writes are reported by relative written_paths only.

These workspace destinations are explicitly forbidden to this planner:

    .relaylm/build/
    .relaylm/state/
    .relaylm/queue/

The planner never directly writes the uppercase source files:

    SOUL.md
    STYLE.md
    EMOTION.md
    SCENE.md
    RELATIONSHIP.md
    MEMORY.md
    BOUNDARY.md
    LORE.md

An uppercase-source implication is proposal metadata only and requires the owning approval/apply boundary.

## CLI and mode gates

The current CLI is:

    python scripts/relaylm_cw_a4_workspace_slp_candidates.py --workspace-root <path>

--workspace-root is required. --dry-run and --write-candidates are mutually exclusive. Dry-run is the default, and --write-candidates is the only CLI mode that permits allowlisted candidate/proposal writes. --json-out <path> may write only the content-free public projection chosen by the operator. The CLI exposes the bounded --max-source-files, --max-candidates, and --max-read-bytes controls.

The public projection is diagnostic-only. It does not authorize approval, application, activation, queue publication, worker execution, or current-turn response effects.

## Public projection and privacy boundary

The public projection uses the exact relaylm.character_workspace_slp_projection.v0 schema and reports bounded counts, candidate/proposal summaries, relative target paths, risk/approval classes, reason IDs, and write-mode information. It sets content_free to true and explicitly reports false for raw source-body inclusion, raw memory/scene/relationship body inclusion, absolute-path inclusion, queue-payload inclusion, uppercase-source mutation, build mutation, state mutation, queue mutation, current-turn response effect, and worker start.

Runtime-private planning may read bounded source text for candidate formation. That text is not copied into the public projection, candidate public summaries, proposal public summaries, or generic diagnostics. Content-bearing candidate/proposal workspace artifacts remain protected workspace material and are not runtime authority merely because they were written.

The exact public candidate summary keys are:

    schema_version
    candidate_id
    candidate_kind
    target_domain
    target_path
    source_evidence_ref_count
    risk_level
    approval_required
    auto_apply_eligible
    apply_default
    reason_ids
    content_hash
    created_by
    content_free

The exact public proposal summary contains the private proposal fields plus content_free. The exact public run projection keys are:

    schema_version
    generated_by
    status
    is_valid
    character_id
    dry_run
    write_candidates
    candidate_count
    proposal_count
    source_evidence_count
    source_evidence_ref_count
    memory_candidates_count
    memory_inbox_additions_count
    memory_consolidation_candidates_count
    scene_candidates_count
    scene_inbox_additions_count
    relationship_candidates_count
    relationship_note_count
    sensitive_candidates_count
    approval_required_count
    auto_apply_eligible_count
    written_path_count
    written_paths
    reason_ids
    blocked_reason_ids
    candidate_summaries
    proposal_summaries
    content_free
    raw_source_body_included
    raw_memory_body_included
    raw_scene_body_included
    raw_relationship_body_included
    absolute_paths_included
    queue_payload_included
    uppercase_source_mutated
    build_artifacts_mutated
    state_mutated
    queue_mutated
    current_turn_response_effect
    worker_started

## Fail-closed behavior and reason boundary

The planner fails closed toward no source/runtime mutation for:

    invalid workspace root
    invalid character ID or required source set
    malformed Markdown or source evidence
    source-file limit/read/encoding/control-character failure
    symlink or path escape
    candidate/proposal path validation failure
    conflicting existing artifact bytes

Current planner-owned reason identifiers include:

    path_traversal_rejected
    workspace_root_missing_or_not_directory
    symlink_escape_rejected
    workspace_root_resolve_failed
    source_root_resolve_failed
    source_root_invalid
    source_file_resolve_failed
    source_file_read_failed
    source_file_limit_reached
    source_read_limit_reached
    source_limit_invalid
    source_file_not_utf8
    source_file_control_character
    malformed_source_evidence
    source_evidence_missing
    source_user_assertion_evidence_missing
    assistant_only_speculation
    blocked_from_user_fact_candidate
    user_assertion_evidence_present
    sensitive_memory_candidate
    scene_candidate_signal
    relayscn_authority_preserved
    relationship_candidate_signal
    relayrel_authority_preserved
    important_relationship_parameter_requires_approval
    candidate_limit_reached
    candidate_artifact_conflict
    candidate_artifact_conflict_not_utf8
    candidate_artifact_write_failed
    proposal_write_skipped_after_candidate_write_failure
    proposal_write_limited_to_successful_candidates_after_candidate_write_failure
    write_path_escape_rejected
    write_path_symlink_rejected
    write_path_resolve_failed
    write_path_conflict
    write_path_not_allowlisted
    uppercase_source_write_rejected
    forbidden_workspace_mutation

The delegated source-tree and parser/validation contracts remain the owners of their validation reason vocabulary, including empty_path, path_escape_rejected, unrecognized_workspace_path, invalid_character_id, invalid_root, missing_required_source, reserved_path_conflict, malformed_markdown, and manifest_entry_limit_reached. This contract does not duplicate or reinterpret those delegated rules.

## Approval, application, and runtime non-authority

The exact non-authority boundary is:

    dry-run candidate/proposal
      -> diagnostic only

    write-candidate artifact
      -> persisted review material only

    approval/apply
      -> separately governed by the owning source/domain authority

    approved source change
      -> Source Compiler rebuild when required

This contract does not grant authority to:

- answer or alter the current turn;
- inject prompts or change RelayCTX state;
- select active scene, relationship, or memory;
- run RelayMEM lifecycle or RelaySOUL apply/rollback;
- write uppercase sources, build projections, runtime state, or queue records;
- enqueue jobs, start workers, poll, sleep, or supervise O2/O3;
- activate a character or publish a runtime projection.

## Verification

The exact current implementation is verified by the focused CW-A4 candidate and review/fix smokes. Related Character Workspace source-tree, parser/validation, and compiler smokes remain independently owned by their contracts. Documentation link, semantic, current-boundary, and governance validators verify the contract's current metadata and authority edges.

## Related authority

- [Character Workspace Maintenance Candidates architecture](../../architecture/character-workspace/maintenance-candidates.md)
- [CW-A4 SLP Workspace Maintenance Candidates implementation handoff](../../architecture/cw_a4_slp_workspace_maintenance_candidates.md)
- [Character Workspace Source Tree Contract](source-tree.md)
- [Character Workspace Parser and Validation Contract](parser-and-validation.md)
- [Character Workspace Compiled Projections Contract](compiled-projections.md)
