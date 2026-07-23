from pathlib import Path


def replace_between(
    text: str,
    start: str,
    end: str,
    replacement: str,
    *,
    after: int = 0,
) -> str:
    start_index = text.index(start, after)
    end_index = text.index(end, start_index)
    return text[:start_index] + replacement.rstrip() + text[end_index:]


subjective_path = Path("relaylm/subjective_mem.py")
subjective = subjective_path.read_text(encoding="utf-8")
class_index = subjective.index("class SubjectiveMemCurrentState:")
subjective = replace_between(
    subjective,
    "    def to_dict(self) -> dict[str, object]:\n",
    "\n@dataclass(frozen=True)\nclass SubjectiveMemPreparedManifest:",
    '''    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": (
                SUBJECTIVE_MEM_CURRENT_STATE_V2_SCHEMA
                if self.authority_bound
                else SUBJECTIVE_MEM_CURRENT_STATE_SCHEMA
            ),
            "memory_state_id": self.memory_state_id,
            "memory_id": self.memory_id,
            "character_id": self.character_id,
            "current_revision": self.current_revision,
            "lifecycle_state": self.lifecycle_state,
            "mutation_state": self.mutation_state,
            "retrieval_eligible": self.retrieval_eligible,
            "updated_at": self.updated_at,
        }
        if self.authority_bound:
            body["authority_binding"] = {
                "workspace_authority_digest": self.workspace_authority_digest,
                "scope_binding_digest": self.scope_binding_digest,
                "page_id": self.page_id,
                "block_id": self.block_id,
                "canonical_page_digest": self.canonical_page_digest,
                "authorization_ref": {
                    "authority_kind": self.authorization_kind,
                    "authority_id": self.authorization_id,
                },
                "current_receipt_id": self.current_receipt_id,
            }
        return body
''',
    after=class_index,
)
subjective_path.write_text(subjective, encoding="utf-8")

runtime_path = Path("relaylm/subjective_mem_lifecycle_runtime.py")
runtime = runtime_path.read_text(encoding="utf-8")
runtime = replace_between(
    runtime,
    "def _validate_pre_image_authority_current(\n",
    "\ndef _predecessor_from_artifact(\n",
    '''def _validate_pre_image_authority_current(
    *,
    store: EvidenceRecordStore,
    evidence_space_id: str,
    character_authority: SubjectiveMemCharacterAuthority,
    proposal: SubjectiveMemCorrectProposal,
    identity: _Identity,
    intent: dict[str, object],
    artifact_bytes: bytes,
) -> bool:
    try:
        with store.transaction(evidence_space_id) as tx:
            if _validate_evidence_space_locked(
                tx=tx,
                evidence_space_id=evidence_space_id,
                character_authority=character_authority,
            ):
                return False
            expected_prepared = _state_from_intent(intent, prepared=True)
            if expected_prepared is None:
                return False
            selector, _ = _load_exact_selector_locked_raw(
                tx=tx,
                selector_id=expected_prepared.memory_state_id,
                expected=expected_prepared.to_dict(),
            )
            if selector is None or _validate_assessment_locked(
                tx=tx, proposal=proposal
            ):
                return False
            claim = tx.read_record(
                record_kind="subjective_mem_lifecycle_claim",
                record_id=identity.operation_slot_id,
            )
            stored_intent = tx.read_record(
                record_kind="subjective_mem_lifecycle_intent",
                record_id=identity.intent_id,
            )
            if (
                claim != _claim_from_intent(identity=identity, intent=intent)
                or stored_intent != intent
            ):
                return False
            predecessor = _predecessor_from_artifact(
                artifact_bytes,
                intent=intent,
                proposal=proposal,
                character_authority=character_authority,
            )
            return predecessor is not None and not _validate_predecessor_authority_locked(
                tx=tx,
                proposal=proposal,
                predecessor=predecessor,
                character_id=character_authority.character_id,
                evidence_space_id=evidence_space_id,
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
''',
)
runtime = replace_between(
    runtime,
    "def _predecessor_from_artifact(\n",
    "\ndef _artifact_exact_for_intent(\n",
    '''def _predecessor_from_artifact(
    artifact: bytes,
    *,
    intent: dict[str, object],
    proposal: SubjectiveMemCorrectProposal,
    character_authority: SubjectiveMemCharacterAuthority,
) -> SubjectiveMemRevision | None:
    try:
        _page_id, _relative, partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind=proposal.expected_memory_kind,
        )
        page, reasons = parse_subjective_mem_page_bytes(
            artifact,
            expected_page_id=proposal.expected_page_id,
            expected_character_id=character_authority.character_id,
            expected_partition=partition,
        )
        if page is None or reasons:
            return None
        matches = [
            item.revision
            for item in page.blocks
            if item.revision.memory_id == proposal.expected_memory_id
            and item.revision.memory_revision == proposal.expected_current_revision
            and canonical_digest(item.revision.to_dict())
            == intent.get("predecessor_revision_digest")
        ]
        return matches[0] if len(matches) == 1 else None
    except (TypeError, ValueError):
        return None
''',
)
runtime = replace_between(
    runtime,
    "def _artifact_exact_for_intent(\n",
    "\ndef identity_transition(\n",
    '''def _artifact_exact_for_intent(
    artifact: bytes,
    *,
    intent: dict[str, object],
    proposal: SubjectiveMemCorrectProposal,
    character_authority: SubjectiveMemCharacterAuthority,
) -> bool:
    try:
        _page_id, _relative, partition = subjective_mem_page_identity(
            character_id=character_authority.character_id,
            memory_kind=proposal.expected_memory_kind,
        )
        page, reasons = parse_subjective_mem_page_bytes(
            artifact,
            expected_page_id=proposal.expected_page_id,
            expected_character_id=character_authority.character_id,
            expected_partition=partition,
        )
        if page is None or reasons:
            return False
        predecessor = next(
            item
            for item in page.blocks
            if item.revision.memory_id == proposal.expected_memory_id
            and item.revision.memory_revision == proposal.expected_current_revision
        )
        successor = next(
            item
            for item in page.blocks
            if item.revision.memory_id == proposal.expected_memory_id
            and item.revision.memory_revision == proposal.expected_current_revision + 1
        )
    except (StopIteration, TypeError, ValueError):
        return False
    predecessor_revision = predecessor.revision
    successor_revision = successor.revision
    return (
        predecessor.block_id == proposal.expected_block_id
        and canonical_digest(predecessor_revision.to_dict())
        == intent.get("predecessor_revision_digest")
        and predecessor_revision.authorization_kind
        == intent.get("predecessor_authorization_kind")
        and predecessor_revision.authorization_id
        == intent.get("predecessor_authorization_id")
        and successor.block_id == intent.get("successor_block_id")
        and successor.block_digest == intent.get("successor_block_digest")
        and canonical_digest(successor_revision.to_dict())
        == intent.get("successor_revision_digest")
        and successor_revision.predecessor_revision_or_null
        == proposal.expected_current_revision
        and successor_revision.grounded_content == proposal.corrected_grounded_content
        and successor_revision.subjective_meaning == proposal.corrected_subjective_meaning
        and successor_revision.strength.to_dict() == proposal.corrected_strength.to_dict()
        and successor_revision.assessment_id == proposal.assessment_revision.assessment_id
        and successor_revision.assessment_revision
        == proposal.assessment_revision.assessment_revision
        and successor_revision.authorization_kind == "lifecycle_transition"
        and successor_revision.authorization_id == identity_transition(intent)
        and canonical_page_digest(artifact) == intent.get("post_image_digest")
    )
''',
)
runtime = replace_between(
    runtime,
    "def _state_from_intent(\n",
    "\ndef _mark_recovery_required(\n",
    '''def _state_from_intent(
    intent: dict[str, object], *, prepared: bool, recovery: bool = False
) -> SubjectiveMemCurrentState | None:
    try:
        mutation = "recovery_required" if recovery else "prepared" if prepared else "none"
        predecessor = prepared or recovery
        state = SubjectiveMemCurrentState(
            memory_state_id=str(intent["current_selector_id"]),
            memory_id=str(intent["memory_id"]),
            character_id=str(intent["character_id"]),
            current_revision=int(
                intent["from_revision"] if predecessor else intent["to_revision"]
            ),
            lifecycle_state="active",
            mutation_state=mutation,
            retrieval_eligible=not predecessor,
            updated_at=str(intent["prepared_at"]),
            workspace_authority_digest=str(intent["workspace_authority_digest"]),
            scope_binding_digest=str(intent["scope_binding_digest"]),
            page_id=str(intent["page_id"]),
            block_id=str(
                intent["predecessor_block_id"]
                if predecessor
                else intent["successor_block_id"]
            ),
            canonical_page_digest=str(
                intent["pre_image_digest"]
                if predecessor
                else intent["post_image_digest"]
            ),
            authorization_kind=str(
                intent["predecessor_authorization_kind"]
                if predecessor
                else "lifecycle_transition"
            ),
            authorization_id=str(
                intent["predecessor_authorization_id"]
                if predecessor
                else intent["transition_id"]
            ),
            current_receipt_id=str(
                intent["current_receipt_id"]
                if predecessor
                else intent["receipt_id"]
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if prepared and canonical_digest(state.to_dict()) != intent.get(
        "prepared_current_state_digest"
    ):
        return None
    return state
''',
)
runtime = replace_between(
    runtime,
    "def _current_state_from_dict(raw: object) -> SubjectiveMemCurrentState | None:\n",
    "\ndef _derive_identity(\n",
    '''def _current_state_from_dict(raw: object) -> SubjectiveMemCurrentState | None:
    if not isinstance(raw, dict):
        return None
    binding = raw.get("authority_binding")
    if binding is not None and not isinstance(binding, dict):
        return None
    authorization = (
        binding.get("authorization_ref") if isinstance(binding, dict) else None
    )
    if authorization is not None and not isinstance(authorization, dict):
        return None
    try:
        state = SubjectiveMemCurrentState(
            memory_state_id=raw["memory_state_id"],
            memory_id=raw["memory_id"],
            character_id=raw["character_id"],
            current_revision=raw["current_revision"],
            lifecycle_state=raw["lifecycle_state"],
            mutation_state=raw["mutation_state"],
            retrieval_eligible=raw["retrieval_eligible"],
            updated_at=raw["updated_at"],
            workspace_authority_digest=(
                binding.get("workspace_authority_digest")
                if isinstance(binding, dict)
                else None
            ),
            scope_binding_digest=(
                binding.get("scope_binding_digest")
                if isinstance(binding, dict)
                else None
            ),
            page_id=(binding.get("page_id") if isinstance(binding, dict) else None),
            block_id=(binding.get("block_id") if isinstance(binding, dict) else None),
            canonical_page_digest=(
                binding.get("canonical_page_digest")
                if isinstance(binding, dict)
                else None
            ),
            authorization_kind=(
                authorization.get("authority_kind")
                if isinstance(authorization, dict)
                else None
            ),
            authorization_id=(
                authorization.get("authority_id")
                if isinstance(authorization, dict)
                else None
            ),
            current_receipt_id=(
                binding.get("current_receipt_id")
                if isinstance(binding, dict)
                else None
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None
    return state if state.to_dict() == raw else None
''',
)
runtime_path.write_text(runtime, encoding="utf-8")
