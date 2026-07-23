"""Canonical Markdown physical contract for Subjective MEM revisions.

ST-1 publishes the legacy revision-1 create block.  LC-1 appends immutable
lifecycle successor blocks to the same human-readable page; a page path,
heading, block order, and mtime are never logical identity.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Literal

from relaylm.character_workspace import parse_markdown_blocks
from relaylm.evidence_common import canonical_digest, utf8_text_digest
from relaylm.subjective_mem import (
    SubjectiveMemFormationSnapshot,
    SubjectiveMemRevision,
    SubjectiveMemScopeBinding,
    SubjectiveMemStrength,
)

PAGE_SCHEMA = "relaylm.subjective_mem_markdown_page.v1"
BLOCK_SCHEMA = "relaylm.subjective_mem_markdown_block.v1"
LIFECYCLE_BLOCK_SCHEMA = "relaylm.subjective_mem_markdown_block.v2"
RENDERER_REVISION = "relaylm.subjective_mem_markdown_renderer.v1"
PAGE_PARTITION_REVISION = "relaylm.subjective_mem_page_partition.v1"
MAX_CANONICAL_PAGE_BYTES = 512 * 1024
MAX_CANONICAL_PAGE_BLOCKS = 128
MISSING_PAGE_DIGEST = "sha256:" + sha256(
    b"relaylm.subjective_mem_canonical_page.missing.v1"
).hexdigest()

Partition = Literal["episodes", "topics"]

_PAGE_HEADER_RE = re.compile(
    r"\A# RelayLM Subjective MEM Page\n\n"
    r"relaylm_page_schema:: (?P<schema>[^\n]+)\n"
    r"relaylm_page_id:: (?P<page_id>[^\n]+)\n"
    r"relaylm_character_id:: (?P<character_id>[^\n]+)\n"
    r"relaylm_partition:: (?P<partition>episodes|topics)\n"
    r"relaylm_partition_revision:: (?P<partition_revision>[^\n]+)\n"
    r"relaylm_renderer_revision:: (?P<renderer_revision>[^\n]+)\n\n"
    r"(?P<body>.*)\Z",
    re.DOTALL,
)
_BLOCK_RE = re.compile(
    r"## Subjective MEM revision (?P<memory_revision>[1-9][0-9]*) \^(?P<anchor>[A-Za-z0-9][A-Za-z0-9_.:-]*)\n\n"
    r"relaylm_block_schema:: (?P<schema>[^\n]+)\n"
    r"relaylm_block_id:: (?P<block_id>[^\n]+)\n"
    r"relaylm_memory_id:: (?P<memory_id>[^\n]+)\n"
    r"relaylm_memory_revision:: (?P=memory_revision)\n"
    r"relaylm_revision_digest:: (?P<revision_digest>[0-9a-f]{64})\n"
    r"relaylm_grounded_content_digest:: (?P<grounded_digest>[0-9a-f]{64})\n"
    r"relaylm_subjective_meaning_digest:: (?P<subjective_digest>[0-9a-f]{64})\n"
    r"(?:relaylm_decision_id:: (?P<legacy_authorization_id>[^\n]+)\n|"
    r"relaylm_authorization_kind:: (?P<authorization_kind>[^\n]+)\n"
    r"relaylm_authorization_id:: (?P<authorization_id>[^\n]+)\n)"
    r"relaylm_created_at:: (?P<created_at>[^\n]+)\n\n"
    r"Canonical revision:\n~~~json\n(?P<revision_json>.*?)\n~~~\n\n"
    r"Grounded content:\n~~~json\n(?P<grounded_json>.*?)\n~~~\n\n"
    r"Subjective meaning:\n~~~json\n(?P<subjective_json>.*?)\n~~~\n",
    re.DOTALL,
)


@dataclass(frozen=True)
class SubjectiveMemMarkdownBlock:
    block_id: str
    anchor: str
    revision: SubjectiveMemRevision
    revision_digest: str
    block_digest: str


@dataclass(frozen=True)
class SubjectiveMemMarkdownPage:
    page_id: str
    character_id: str
    partition: Partition
    blocks: tuple[SubjectiveMemMarkdownBlock, ...]
    page_digest: str


@dataclass(frozen=True, repr=False)
class SubjectiveMemPagePlan:
    page_id: str
    relative_path: str
    partition: Partition
    block_id: str
    anchor: str
    pre_image_state: Literal["absent", "present"]
    pre_image_digest: str
    post_image_digest: str
    block_digest: str
    rendered_bytes: bytes
    existing_block_count: int

    @property
    def artifact_id(self) -> str:
        return "smartifact_" + self.post_image_digest.removeprefix("sha256:")


@dataclass(frozen=True)
class SubjectiveMemPagePlanResult:
    plan: SubjectiveMemPagePlan | None
    reasons: tuple[str, ...] = ()


def canonical_page_digest(data: bytes) -> str:
    return "sha256:" + sha256(data).hexdigest()


def subjective_mem_page_identity(
    *, character_id: str, memory_kind: str
) -> tuple[str, str, Partition]:
    partition: Partition
    if memory_kind == "episodic":
        partition = "episodes"
    elif memory_kind == "semantic":
        partition = "topics"
    else:
        raise ValueError("subjective_mem_markdown_memory_kind_unsupported")
    token = sha256(
        (PAGE_PARTITION_REVISION + "\0" + character_id + "\0" + partition).encode(
            "utf-8"
        )
    ).hexdigest()
    return (
        "smpage_" + token,
        PurePosixPath("memory", partition, "subjective-mem-v1.md").as_posix(),
        partition,
    )


def subjective_mem_block_identity(
    memory_id: str, memory_revision: int = 1
) -> tuple[str, str]:
    # Preserve the exact ST-1 revision-1 identity.  Successors include their
    # immutable revision number so each retained canonical block is stable.
    material = BLOCK_SCHEMA + "\0" + memory_id
    if memory_revision != 1:
        material = LIFECYCLE_BLOCK_SCHEMA + "\0" + memory_id + "\0" + str(memory_revision)
    token = sha256(material.encode("utf-8")).hexdigest()
    return "smblock_" + token, "smb-" + token


def plan_subjective_mem_page(
    *, revision: SubjectiveMemRevision, existing_bytes: bytes | None
) -> SubjectiveMemPagePlanResult:
    """Plan the ST-1 revision-1 create publication."""

    revision_reasons = _validate_create_revision(revision)
    if revision_reasons:
        return SubjectiveMemPagePlanResult(None, revision_reasons)
    page_id, relative_path, partition = subjective_mem_page_identity(
        character_id=revision.character_id, memory_kind=revision.memory_kind
    )
    block_id, anchor = subjective_mem_block_identity(revision.memory_id, 1)

    if existing_bytes is None:
        pre_state: Literal["absent", "present"] = "absent"
        pre_digest = MISSING_PAGE_DIGEST
        existing_blocks: tuple[SubjectiveMemMarkdownBlock, ...] = ()
        prefix = _render_page_header(
            page_id=page_id,
            character_id=revision.character_id,
            partition=partition,
        )
    else:
        pre_state = "present"
        pre_digest = canonical_page_digest(existing_bytes)
        parsed, reasons = parse_subjective_mem_page_bytes(
            existing_bytes,
            expected_page_id=page_id,
            expected_character_id=revision.character_id,
            expected_partition=partition,
        )
        if parsed is None:
            return SubjectiveMemPagePlanResult(None, reasons)
        existing_blocks = parsed.blocks
        if len(existing_blocks) >= MAX_CANONICAL_PAGE_BLOCKS:
            return SubjectiveMemPagePlanResult(
                None, ("subjective_mem_markdown_page_capacity_exceeded",)
            )
        if any(item.revision.memory_id == revision.memory_id for item in existing_blocks):
            return SubjectiveMemPagePlanResult(
                None, ("subjective_mem_markdown_duplicate_logical_memory",)
            )
        prefix = existing_bytes.decode("utf-8")

    return _finish_plan(
        revision=revision,
        page_id=page_id,
        relative_path=relative_path,
        partition=partition,
        pre_state=pre_state,
        pre_digest=pre_digest,
        existing_blocks=existing_blocks,
        prefix=prefix,
    )


def plan_subjective_mem_revision_successor(
    *,
    predecessor: SubjectiveMemRevision,
    successor: SubjectiveMemRevision,
    existing_bytes: bytes,
) -> SubjectiveMemPagePlanResult:
    """Append one exact immutable lifecycle successor to its canonical page."""

    reasons = list(_validate_revision(predecessor)) + list(_validate_revision(successor))
    if (
        successor.memory_id != predecessor.memory_id
        or successor.character_id != predecessor.character_id
        or successor.memory_kind != predecessor.memory_kind
        or successor.memory_revision != predecessor.memory_revision + 1
        or successor.predecessor_revision_or_null != predecessor.memory_revision
        or successor.authorization_kind != "lifecycle_transition"
    ):
        reasons.append("subjective_mem_markdown_successor_lineage_invalid")
    if type(existing_bytes) is not bytes:
        reasons.append("subjective_mem_markdown_pre_image_invalid")
    if reasons:
        return SubjectiveMemPagePlanResult(None, tuple(dict.fromkeys(reasons)))

    page_id, relative_path, partition = subjective_mem_page_identity(
        character_id=successor.character_id, memory_kind=successor.memory_kind
    )
    parsed, parse_reasons = parse_subjective_mem_page_bytes(
        existing_bytes,
        expected_page_id=page_id,
        expected_character_id=successor.character_id,
        expected_partition=partition,
    )
    if parsed is None:
        return SubjectiveMemPagePlanResult(None, parse_reasons)
    if len(parsed.blocks) >= MAX_CANONICAL_PAGE_BLOCKS:
        return SubjectiveMemPagePlanResult(
            None, ("subjective_mem_markdown_page_capacity_exceeded",)
        )
    current = [
        item
        for item in parsed.blocks
        if item.revision.memory_id == predecessor.memory_id
        and item.revision.memory_revision == predecessor.memory_revision
    ]
    if len(current) != 1 or current[0].revision.to_dict() != predecessor.to_dict():
        return SubjectiveMemPagePlanResult(
            None, ("subjective_mem_markdown_predecessor_not_exact",)
        )
    later = [
        item
        for item in parsed.blocks
        if item.revision.memory_id == predecessor.memory_id
        and item.revision.memory_revision > predecessor.memory_revision
    ]
    if later:
        exact = [item for item in later if item.revision.to_dict() == successor.to_dict()]
        if len(exact) == 1 and len(later) == 1:
            # Already post-image is classified by the durable intent/writer, not
            # re-planned from a changed current page.
            return SubjectiveMemPagePlanResult(
                None, ("subjective_mem_markdown_successor_already_present",)
            )
        return SubjectiveMemPagePlanResult(
            None, ("subjective_mem_markdown_stale_successor",)
        )
    return _finish_plan(
        revision=successor,
        page_id=page_id,
        relative_path=relative_path,
        partition=partition,
        pre_state="present",
        pre_digest=canonical_page_digest(existing_bytes),
        existing_blocks=parsed.blocks,
        prefix=existing_bytes.decode("utf-8"),
    )


def _finish_plan(
    *,
    revision: SubjectiveMemRevision,
    page_id: str,
    relative_path: str,
    partition: Partition,
    pre_state: Literal["absent", "present"],
    pre_digest: str,
    existing_blocks: tuple[SubjectiveMemMarkdownBlock, ...],
    prefix: str,
) -> SubjectiveMemPagePlanResult:
    block_id, anchor = subjective_mem_block_identity(
        revision.memory_id, revision.memory_revision
    )
    if any(item.block_id == block_id or item.anchor == anchor for item in existing_blocks):
        return SubjectiveMemPagePlanResult(
            None, ("subjective_mem_markdown_duplicate_block_identity",)
        )
    block_text = render_subjective_mem_block(
        revision=revision, block_id=block_id, anchor=anchor
    )
    post_bytes = (prefix + block_text).encode("utf-8")
    if len(post_bytes) > MAX_CANONICAL_PAGE_BYTES:
        return SubjectiveMemPagePlanResult(
            None, ("subjective_mem_markdown_page_size_exceeded",)
        )
    parsed_post, reasons = parse_subjective_mem_page_bytes(
        post_bytes,
        expected_page_id=page_id,
        expected_character_id=revision.character_id,
        expected_partition=partition,
    )
    if parsed_post is None:
        return SubjectiveMemPagePlanResult(None, reasons)
    matches = [
        item
        for item in parsed_post.blocks
        if item.block_id == block_id
        and item.revision.memory_id == revision.memory_id
        and item.revision.memory_revision == revision.memory_revision
    ]
    if len(matches) != 1 or matches[0].revision.to_dict() != revision.to_dict():
        return SubjectiveMemPagePlanResult(
            None, ("subjective_mem_markdown_post_image_lineage_invalid",)
        )
    return SubjectiveMemPagePlanResult(
        SubjectiveMemPagePlan(
            page_id=page_id,
            relative_path=relative_path,
            partition=partition,
            block_id=block_id,
            anchor=anchor,
            pre_image_state=pre_state,
            pre_image_digest=pre_digest,
            post_image_digest=canonical_page_digest(post_bytes),
            block_digest=matches[0].block_digest,
            rendered_bytes=post_bytes,
            existing_block_count=len(existing_blocks),
        )
    )


def render_subjective_mem_block(
    *, revision: SubjectiveMemRevision, block_id: str, anchor: str
) -> str:
    revision_dict = revision.to_dict()
    revision_digest = canonical_digest(revision_dict)
    subjective_digest = utf8_text_digest(revision.subjective_meaning)
    revision_json = json.dumps(
        revision_dict,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        separators=(",", ": "),
    )
    grounded_json = json.dumps(revision.grounded_content, ensure_ascii=False)
    subjective_json = json.dumps(revision.subjective_meaning, ensure_ascii=False)
    legacy = revision.memory_revision == 1 and revision.authorization_kind == "formation_decision"
    schema = BLOCK_SCHEMA if legacy else LIFECYCLE_BLOCK_SCHEMA
    authorization = (
        f"relaylm_decision_id:: {revision.authorization_id}\n"
        if legacy
        else (
            f"relaylm_authorization_kind:: {revision.authorization_kind}\n"
            f"relaylm_authorization_id:: {revision.authorization_id}\n"
        )
    )
    return (
        f"## Subjective MEM revision {revision.memory_revision} ^{anchor}\n\n"
        f"relaylm_block_schema:: {schema}\n"
        f"relaylm_block_id:: {block_id}\n"
        f"relaylm_memory_id:: {revision.memory_id}\n"
        f"relaylm_memory_revision:: {revision.memory_revision}\n"
        f"relaylm_revision_digest:: {revision_digest}\n"
        f"relaylm_grounded_content_digest:: {revision.grounded_content_digest}\n"
        f"relaylm_subjective_meaning_digest:: {subjective_digest}\n"
        f"{authorization}"
        f"relaylm_created_at:: {revision.created_at}\n\n"
        "Canonical revision:\n~~~json\n"
        f"{revision_json}\n"
        "~~~\n\n"
        "Grounded content:\n~~~json\n"
        f"{grounded_json}\n"
        "~~~\n\n"
        "Subjective meaning:\n~~~json\n"
        f"{subjective_json}\n"
        "~~~\n"
    )


def parse_subjective_mem_page_bytes(
    data: bytes,
    *,
    expected_page_id: str | None = None,
    expected_character_id: str | None = None,
    expected_partition: Partition | None = None,
) -> tuple[SubjectiveMemMarkdownPage | None, tuple[str, ...]]:
    if type(data) is not bytes or len(data) > MAX_CANONICAL_PAGE_BYTES:
        return None, ("subjective_mem_markdown_page_size_exceeded",)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, ("subjective_mem_markdown_page_not_utf8",)
    if not text.endswith("\n"):
        return None, ("subjective_mem_markdown_page_noncanonical_newline",)
    header = _PAGE_HEADER_RE.fullmatch(text)
    if header is None:
        return None, ("subjective_mem_markdown_page_header_invalid",)
    if (
        header.group("schema") != PAGE_SCHEMA
        or header.group("partition_revision") != PAGE_PARTITION_REVISION
        or header.group("renderer_revision") != RENDERER_REVISION
    ):
        return None, ("subjective_mem_markdown_page_schema_unsupported",)
    page_id = header.group("page_id")
    character_id = header.group("character_id")
    partition = header.group("partition")
    if expected_page_id is not None and page_id != expected_page_id:
        return None, ("subjective_mem_markdown_page_identity_mismatch",)
    if expected_character_id is not None and character_id != expected_character_id:
        return None, ("subjective_mem_markdown_character_mismatch",)
    if expected_partition is not None and partition != expected_partition:
        return None, ("subjective_mem_markdown_partition_mismatch",)

    body = header.group("body")
    if not body:
        return None, ("subjective_mem_markdown_page_empty",)
    matches = list(_BLOCK_RE.finditer(body))
    if not matches or "".join(match.group(0) for match in matches) != body:
        return None, ("subjective_mem_markdown_block_malformed",)
    if len(matches) > MAX_CANONICAL_PAGE_BLOCKS:
        return None, ("subjective_mem_markdown_page_capacity_exceeded",)

    cw_blocks = parse_markdown_blocks(text)
    memory_headings = [item for item in cw_blocks if item.heading_level == 2]
    anchors = [item.anchor for item in memory_headings]
    if len(memory_headings) != len(matches) or any(anchor is None for anchor in anchors):
        return None, ("subjective_mem_markdown_block_heading_invalid",)
    if len(set(anchors)) != len(anchors):
        return None, ("subjective_mem_markdown_duplicate_anchor",)

    parsed_blocks: list[SubjectiveMemMarkdownBlock] = []
    logical_revisions: set[tuple[str, int]] = set()
    block_ids: set[str] = set()
    for match in matches:
        parsed, reasons = _parse_block(match)
        if parsed is None:
            return None, reasons
        if parsed.revision.character_id != character_id:
            return None, ("subjective_mem_markdown_character_mismatch",)
        expected_page, _path, expected_block_partition = subjective_mem_page_identity(
            character_id=character_id,
            memory_kind=parsed.revision.memory_kind,
        )
        if expected_page != page_id or expected_block_partition != partition:
            return None, ("subjective_mem_markdown_partition_mismatch",)
        logical = (parsed.revision.memory_id, parsed.revision.memory_revision)
        if logical in logical_revisions:
            return None, ("subjective_mem_markdown_duplicate_logical_revision",)
        if parsed.block_id in block_ids:
            return None, ("subjective_mem_markdown_duplicate_block_identity",)
        logical_revisions.add(logical)
        block_ids.add(parsed.block_id)
        parsed_blocks.append(parsed)

    by_memory: dict[str, list[SubjectiveMemRevision]] = {}
    for item in parsed_blocks:
        by_memory.setdefault(item.revision.memory_id, []).append(item.revision)
    for revisions in by_memory.values():
        ordered = sorted(revisions, key=lambda item: item.memory_revision)
        if ordered[0].memory_revision != 1 or ordered[0].predecessor_revision_or_null is not None:
            return None, ("subjective_mem_markdown_revision_chain_invalid",)
        for previous, current in zip(ordered, ordered[1:]):
            if (
                current.memory_revision != previous.memory_revision + 1
                or current.predecessor_revision_or_null != previous.memory_revision
                or current.character_id != previous.character_id
                or current.memory_kind != previous.memory_kind
                or current.scope_binding.to_dict() != previous.scope_binding.to_dict()
            ):
                return None, ("subjective_mem_markdown_revision_chain_invalid",)

    return (
        SubjectiveMemMarkdownPage(
            page_id=page_id,
            character_id=character_id,
            partition=partition,  # type: ignore[arg-type]
            blocks=tuple(parsed_blocks),
            page_digest=canonical_page_digest(data),
        ),
        (),
    )


def _parse_block(
    match: re.Match[str],
) -> tuple[SubjectiveMemMarkdownBlock | None, tuple[str, ...]]:
    try:
        raw_revision = json.loads(match.group("revision_json"))
        grounded = json.loads(match.group("grounded_json"))
        subjective = json.loads(match.group("subjective_json"))
    except (TypeError, ValueError):
        return None, ("subjective_mem_markdown_block_json_invalid",)
    if not isinstance(raw_revision, dict) or not isinstance(grounded, str) or not isinstance(subjective, str):
        return None, ("subjective_mem_markdown_block_json_invalid",)
    revision = _revision_from_dict(raw_revision)
    if revision is None:
        return None, ("subjective_mem_markdown_revision_invalid",)
    legacy = revision.memory_revision == 1 and revision.authorization_kind == "formation_decision"
    if match.group("schema") != (BLOCK_SCHEMA if legacy else LIFECYCLE_BLOCK_SCHEMA):
        return None, ("subjective_mem_markdown_block_schema_unsupported",)
    block_id, anchor = subjective_mem_block_identity(
        revision.memory_id, revision.memory_revision
    )
    observed_authority = match.group("legacy_authorization_id") or match.group("authorization_id")
    if (
        match.group("block_id") != block_id
        or match.group("anchor") != anchor
        or match.group("memory_id") != revision.memory_id
        or int(match.group("memory_revision")) != revision.memory_revision
        or observed_authority != revision.authorization_id
        or (not legacy and match.group("authorization_kind") != revision.authorization_kind)
        or (legacy and match.group("authorization_kind") is not None)
        or match.group("created_at") != revision.created_at
        or match.group("revision_digest") != canonical_digest(revision.to_dict())
        or match.group("grounded_digest") != revision.grounded_content_digest
        or match.group("subjective_digest") != utf8_text_digest(revision.subjective_meaning)
        or grounded != revision.grounded_content
        or subjective != revision.subjective_meaning
    ):
        return None, ("subjective_mem_markdown_block_digest_or_lineage_mismatch",)
    canonical_block = render_subjective_mem_block(
        revision=revision, block_id=block_id, anchor=anchor
    )
    if match.group(0) != canonical_block:
        return None, ("subjective_mem_markdown_block_noncanonical",)
    return (
        SubjectiveMemMarkdownBlock(
            block_id=block_id,
            anchor=anchor,
            revision=revision,
            revision_digest=canonical_digest(revision.to_dict()),
            block_digest=canonical_page_digest(canonical_block.encode("utf-8")),
        ),
        (),
    )


def _revision_from_dict(raw: dict[str, object]) -> SubjectiveMemRevision | None:
    try:
        grounded = raw["grounded_assessment_ref"]
        authorization = raw["authorization_ref"]
        if not isinstance(grounded, dict) or not isinstance(authorization, dict):
            return None
        revision = SubjectiveMemRevision(
            memory_id=str(raw["memory_id"]),
            character_id=str(raw["character_id"]),
            assessment_id=str(grounded["assessment_id"]),
            assessment_revision=int(grounded["assessment_revision"]),
            grounded_content=raw["grounded_content"],  # type: ignore[arg-type]
            grounded_content_digest=str(raw["grounded_content_digest"]),
            subjective_meaning=raw["subjective_meaning"],  # type: ignore[arg-type]
            memory_kind=str(raw["memory_kind"]),
            scope_binding=SubjectiveMemScopeBinding(**raw["scope_binding"]),  # type: ignore[arg-type]
            formation_snapshot=SubjectiveMemFormationSnapshot(**raw["formation_snapshot"]),  # type: ignore[arg-type]
            strength=SubjectiveMemStrength(**raw["strength"]),  # type: ignore[arg-type]
            decision_id=str(authorization["authority_id"]),
            created_at=str(raw["created_at"]),
            memory_revision=int(raw["memory_revision"]),
            formation_stage=str(raw["formation_stage"]),
            lifecycle_state=str(raw["lifecycle_state"]),
            retrieval_visible=raw["retrieval_visible"],  # type: ignore[arg-type]
            predecessor_revision_or_null=raw["predecessor_revision_or_null"],  # type: ignore[arg-type]
            authorization_kind=str(authorization["authority_kind"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
    validation = (
        _validate_create_revision(revision)
        if revision.memory_revision == 1
        else _validate_revision(revision)
    )
    if revision.to_dict() != raw or validation:
        return None
    return revision


def _validate_revision(revision: object) -> tuple[str, ...]:
    if type(revision) is not SubjectiveMemRevision:
        return ("subjective_mem_markdown_revision_invalid",)
    if (
        type(revision.memory_revision) is not int
        or revision.memory_revision < 1
        or revision.formation_stage not in {"primary", "secondary"}
        or revision.lifecycle_state not in {"active", "pinned", "held", "hidden", "superseded", "purged"}
        or type(revision.retrieval_visible) is not bool
        or revision.retrieval_visible != (revision.lifecycle_state in {"active", "pinned"})
        or revision.memory_kind not in {"episodic", "semantic"}
        or revision.authorization_kind not in {"formation_decision", "lifecycle_transition"}
        or (revision.memory_revision == 1 and revision.authorization_kind != "formation_decision")
        or (revision.memory_revision > 1 and revision.authorization_kind != "lifecycle_transition")
        or not isinstance(revision.authorization_id, str)
        or not revision.authorization_id
        or not isinstance(revision.grounded_content, str)
        or not 1 <= len(revision.grounded_content) <= 8000
        or not isinstance(revision.subjective_meaning, str)
        or not 1 <= len(revision.subjective_meaning) <= 4000
        or utf8_text_digest(revision.grounded_content) != revision.grounded_content_digest
        or (revision.memory_revision == 1 and revision.predecessor_revision_or_null is not None)
        or (revision.memory_revision > 1 and revision.predecessor_revision_or_null != revision.memory_revision - 1)
    ):
        return ("subjective_mem_markdown_revision_invalid",)
    return ()


def _validate_create_revision(revision: object) -> tuple[str, ...]:
    if _validate_revision(revision):
        return ("subjective_mem_markdown_revision_invalid",)
    assert isinstance(revision, SubjectiveMemRevision)
    if (
        revision.memory_revision != 1
        or revision.formation_stage != "primary"
        or revision.lifecycle_state != "active"
        or revision.retrieval_visible is not True
        or revision.predecessor_revision_or_null is not None
        or revision.authorization_kind != "formation_decision"
        or revision.scope_binding.to_dict() != SubjectiveMemScopeBinding().to_dict()
    ):
        return ("subjective_mem_markdown_revision_invalid",)
    return ()


def _render_page_header(*, page_id: str, character_id: str, partition: Partition) -> str:
    return (
        "# RelayLM Subjective MEM Page\n\n"
        f"relaylm_page_schema:: {PAGE_SCHEMA}\n"
        f"relaylm_page_id:: {page_id}\n"
        f"relaylm_character_id:: {character_id}\n"
        f"relaylm_partition:: {partition}\n"
        f"relaylm_partition_revision:: {PAGE_PARTITION_REVISION}\n"
        f"relaylm_renderer_revision:: {RENDERER_REVISION}\n\n"
    )


__all__ = [
    "BLOCK_SCHEMA",
    "LIFECYCLE_BLOCK_SCHEMA",
    "MAX_CANONICAL_PAGE_BLOCKS",
    "MAX_CANONICAL_PAGE_BYTES",
    "MISSING_PAGE_DIGEST",
    "PAGE_PARTITION_REVISION",
    "PAGE_SCHEMA",
    "RENDERER_REVISION",
    "SubjectiveMemMarkdownBlock",
    "SubjectiveMemMarkdownPage",
    "SubjectiveMemPagePlan",
    "SubjectiveMemPagePlanResult",
    "canonical_page_digest",
    "parse_subjective_mem_page_bytes",
    "plan_subjective_mem_page",
    "plan_subjective_mem_revision_successor",
    "render_subjective_mem_block",
    "subjective_mem_block_identity",
    "subjective_mem_page_identity",
]
