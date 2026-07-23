from pathlib import Path

path = Path("relaylm/subjective_mem_lifecycle_runtime.py")
text = path.read_text(encoding="utf-8")
original = text


def replace_region(source: str, start: str, end: str, replacement: str) -> str:
    left = source.index(start)
    right = source.index(end, left)
    return source[:left] + replacement + source[right:]


text = replace_region(
    text,
    "def _predecessor_from_artifact(\n",
    "def _artifact_exact_for_intent(\n",
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

text = replace_region(
    text,
    "def _artifact_exact_for_intent(\n",
    "def identity_transition(",
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

text = replace_region(
    text,
    "def _state_from_intent(\n",
    "def _mark_recovery_required(\n",
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
                intent["pre_image_digest"] if predecessor else intent["post_image_digest"]
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
                intent["current_receipt_id"] if predecessor else intent["receipt_id"]
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

text = replace_region(
    text,
    "def _current_state_from_dict(raw: object) -> SubjectiveMemCurrentState | None:\n",
    "def _derive_identity(",
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

if text == original:
    raise SystemExit("verified repair produced no change")
compile(text, str(path), "exec")
path.write_text(text, encoding="utf-8")
