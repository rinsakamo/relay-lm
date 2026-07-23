"""ST-1 canonical Markdown physical contract for Subjective MEM create.

The page is canonical semantic/lifecycle authority.  It is deliberately a
human editing unit that may contain several stable logical memory blocks; the
page path, heading text, and block order are never logical memory identity.
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
    r"## Subjective MEM revision 1 \^(?P<anchor>[A-Za-z0-9][A-Za-z0-9_.:-]*)\n\n"
    r"relaylm_block_schema:: (?P<schema>[^\n]+)\n"
    r"relaylm_block_id:: (?P<block_id>[^\n]+)\n"
    r"relaylm_memory_id:: (?P<memory_id>[^\n]+)\n"
    r"relaylm_memory_revision:: 1\n"
    r"relaylm_revision_digest:: (?P<revision_digest>[0-9a-f]{64})\n"
    r"relaylm_grounded_content_digest:: (?P<grounded_digest>[0-9a-f]{64})\n"
    r"relaylm_subjective_meaning_digest:: (?P<subjective_digest>[0-9a-f]{64})\n"
    r"relaylm_decision_id:: (?P<decision_id>[^\n]+)\n"
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
        (
            PAGE_PARTITION_REVISION
            + "\0"
            + character_id
            + "\0"
            + partition
        ).encode("utf-8")
    ).hexdigest()
    return (
        "smpage_" + token,
        PurePosixPath("memory", partition, "subjective-mem-v1.md").as_posix(),
        partition,
    )


def subjective_mem_block_identity(memory_id: str) -> tuple[str, str]:
    token = sha256((BLOCK_SCHEMA + "\0" + memory_id).encode("utf-8")).hexdigest()
    return "smblock_" + token, "smb-" + token


def plan_subjective_mem_page(
    *, revision: SubjectiveMemRevision, existing_bytes: bytes | None
) -> SubjectiveMemPagePlanResult:
    revision_reasons = _validate_create_revision(revision)
    if revision_reasons:
        return SubjectiveMemPagePlanResult(None, revision_reasons)
    page_id, relative_path, partition = subjective_mem_page_identity(
        character_id=revision.character_id, memory_kind=revision.memory_kind
    )
    block_id, anchor = subjective_mem_block_identity(revision.memory_id)

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
        if any(item.block_id == block_id or item.anchor == anchor for item in existing_blocks):
            return SubjectiveMemPagePlanResult(
                None, ("subjective_mem_markdown_duplicate_block_identity",)
            )
        prefix = existing_bytes.decode("utf-8")

    block_text = render_subjective_mem_block(
        revision=revision, block_id=block_id, anchor=anchor
    )
    post_text = prefix + block_text
    post_bytes = post_text.encode("utf-8")
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
        if item.block_id == block_id and item.revision.memory_id == revision.memory_id
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
    return (
        f"## Subjective MEM revision 1 ^{anchor}\n\n"
        f"relaylm_block_schema:: {BLOCK_SCHEMA}\n"
        f"relaylm_block_id:: {block_id}\n"
        f"relaylm_memory_id:: {revision.memory_id}\n"
        "relaylm_memory_revision:: 1\n"
        f"relaylm_revision_digest:: {revision_digest}\n"
        f"relaylm_grounded_content_digest:: {revision.grounded_content_digest}\n"
        f"relaylm_subjective_meaning_digest:: {subjective_digest}\n"
        f"relaylm_decision_id:: {revision.decision_id}\n"
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
    memory_ids: set[str] = set()
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
        if parsed.revision.memory_id in memory_ids:
            return None, ("subjective_mem_markdown_duplicate_logical_memory",)
        if parsed.block_id in block_ids:
            return None, ("subjective_mem_markdown_duplicate_block_identity",)
        memory_ids.add(parsed.revision.memory_id)
        block_ids.add(parsed.block_id)
        parsed_blocks.append(parsed)
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
    if match.group("schema") != BLOCK_SCHEMA:
        return None, ("subjective_mem_markdown_block_schema_unsupported",)
    try:
        raw_revision = json.loads(match.group("revision_json"))
        grounded = json.loads(match.group("grounded_json"))
        subjective = json.loads(match.group("subjective_json"))
    except (TypeError, ValueError):
        return None, ("subjective_mem_markdown_block_json_invalid",)
    if (
        not isinstance(raw_revision, dict)
        or not isinstance(grounded, str)
        or not isinstance(subjective, str)
    ):
        return None, ("subjective_mem_markdown_block_json_invalid",)
    revision = _revision_from_dict(raw_revision)
    if revision is None:
        return None, ("subjective_mem_markdown_revision_invalid",)
    block_id, anchor = subjective_mem_block_identity(revision.memory_id)
    if (
        match.group("block_id") != block_id
        or match.group("anchor") != anchor
        or match.group("memory_id") != revision.memory_id
        or match.group("decision_id") != revision.decision_id
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
    block_bytes = canonical_block.encode("utf-8")
    return (
        SubjectiveMemMarkdownBlock(
            block_id=block_id,
            anchor=anchor,
            revision=revision,
            revision_digest=canonical_digest(revision.to_dict()),
            block_digest=canonical_page_digest(block_bytes),
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
            formation_snapshot=SubjectiveMemFormationSnapshot(
                **raw["formation_snapshot"]  # type: ignore[arg-type]
            ),
            strength=SubjectiveMemStrength(**raw["strength"]),  # type: ignore[arg-type]
            decision_id=str(authorization["authority_id"]),
            created_at=str(raw["created_at"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if revision.to_dict() != raw:
        return None
    if _validate_create_revision(revision):
        return None
    return revision


def _validate_create_revision(revision: object) -> tuple[str, ...]:
    if type(revision) is not SubjectiveMemRevision:
        return ("subjective_mem_markdown_revision_invalid",)
    raw = revision.to_dict()
    if (
        raw.get("memory_revision") != 1
        or raw.get("formation_stage") != "primary"
        or raw.get("lifecycle_state") != "active"
        or raw.get("retrieval_visible") is not True
        or raw.get("predecessor_revision_or_null") is not None
        or revision.scope_binding.to_dict() != SubjectiveMemScopeBinding().to_dict()
        or revision.memory_kind not in {"episodic", "semantic"}
        or utf8_text_digest(revision.grounded_content)
        != revision.grounded_content_digest
    ):
        return ("subjective_mem_markdown_revision_invalid",)
    return ()


def _render_page_header(
    *, page_id: str, character_id: str, partition: Partition
) -> str:
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
    "render_subjective_mem_block",
    "subjective_mem_block_identity",
    "subjective_mem_page_identity",
]
