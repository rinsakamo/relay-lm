"""Manual memory seed loading for RelayLM MVP-3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from relaylm.compiler import BlockType, ContextBlock, StabilityClass


@dataclass(frozen=True)
class MemorySeed:
    memory_id: str
    character_id: str | None
    content: str
    importance: int = 1
    source: str = "manual_seed"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemorySeedFile:
    memories: list[MemorySeed]


def load_memory_seed_file(path: str | Path) -> MemorySeedFile:
    seed_path = Path(path)
    with seed_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    memories: list[MemorySeed] = []
    for index, item in enumerate(raw.get("memories", [])):
        if not isinstance(item, dict):
            raise ValueError(f"memory seed entry {index} must be a mapping")
        memory_id = item.get("memory_id")
        content = item.get("content")
        if not isinstance(memory_id, str) or not memory_id:
            raise ValueError(f"memory seed entry {index} is missing memory_id")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"memory seed entry {memory_id!r} is missing content")
        tags = item.get("tags", [])
        if tags is None:
            tags = []
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"memory seed entry {memory_id!r} tags must be a list of strings")
        memories.append(
            MemorySeed(
                memory_id=memory_id,
                character_id=item.get("character_id") if isinstance(item.get("character_id"), str) else None,
                content=content.strip(),
                importance=int(item.get("importance", 1)),
                source=str(item.get("source", "manual_seed")),
                tags=tuple(tags),
            )
        )
    return MemorySeedFile(memories=memories)


def filter_memory_seeds(
    seed_file: MemorySeedFile,
    *,
    character_id: str | None,
) -> list[MemorySeed]:
    return [
        memory
        for memory in seed_file.memories
        if memory.character_id is None or memory.character_id == character_id
    ]


def build_memory_context_block(
    memories: list[MemorySeed],
    *,
    block_id: str = "manual_memory_seed",
) -> ContextBlock | None:
    if not memories:
        return None

    sorted_memories = sorted(memories, key=lambda memory: (-memory.importance, memory.memory_id))
    lines: list[str] = []
    for memory in sorted_memories:
        tag_text = f" tags={','.join(memory.tags)}" if memory.tags else ""
        lines.append(f"- [{memory.memory_id} importance={memory.importance}{tag_text}] {memory.content}")

    return ContextBlock(
        block_id=block_id,
        block_type=BlockType.RETRIEVED_MEMORY,
        stability_class=StabilityClass.SLOW_PREFIX,
        source="manual_memory_seed",
        content="\n".join(lines),
        token_budget_hint=800,
        include_in_prefix_cache_target=False,
    )
