"""Manual memory seed loading for RelayLM MVP-3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from relaylm.compiler import BlockType, ContextBlock, StabilityClass


MemorySeedState = Literal["active", "promoted", "demoted", "disabled"]
VALID_MEMORY_SEED_STATES: set[str] = {"active", "promoted", "demoted", "disabled"}


@dataclass(frozen=True)
class MemorySeed:
    memory_id: str
    character_id: str | None
    content: str
    importance: int = 1
    source: str = "manual_seed"
    tags: tuple[str, ...] = ()
    state: MemorySeedState = "active"


@dataclass(frozen=True)
class MemorySeedFile:
    memories: list[MemorySeed]


def validate_memory_seed(memory: MemorySeed) -> None:
    if not isinstance(memory.memory_id, str) or not memory.memory_id:
        raise ValueError("memory seed entry is missing memory_id")
    if not isinstance(memory.content, str) or not memory.content.strip():
        raise ValueError(f"memory seed entry {memory.memory_id!r} is missing content")
    if not isinstance(memory.tags, tuple) or not all(isinstance(tag, str) for tag in memory.tags):
        raise ValueError(f"memory seed entry {memory.memory_id!r} tags must be a tuple of strings")
    if not isinstance(memory.state, str) or memory.state not in VALID_MEMORY_SEED_STATES:
        raise ValueError(
            f"memory seed entry {memory.memory_id!r} state must be one of "
            f"{sorted(VALID_MEMORY_SEED_STATES)}"
        )


def memory_seed_to_yaml_item(memory: MemorySeed) -> dict[str, Any]:
    validate_memory_seed(memory)
    return {
        "memory_id": memory.memory_id,
        "character_id": memory.character_id,
        "importance": memory.importance,
        "state": memory.state,
        "source": memory.source,
        "tags": list(memory.tags),
        "content": memory.content.strip(),
    }


def append_memory_seed(path: str | Path, memory: MemorySeed) -> None:
    validate_memory_seed(memory)
    seed_path = Path(path)
    if seed_path.exists():
        with seed_path.open("r", encoding="utf-8") as f:
            raw: Any = yaml.safe_load(f) or {}
    else:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("memory seed file must be a mapping")
    memories = raw.get("memories", [])
    if memories is None:
        memories = []
    if not isinstance(memories, list):
        raise ValueError("memory seed file memories must be a list")
    existing_ids = {
        item.get("memory_id")
        for item in memories
        if isinstance(item, dict) and isinstance(item.get("memory_id"), str)
    }
    if memory.memory_id in existing_ids:
        raise ValueError(f"memory seed entry already exists: {memory.memory_id}")
    memories.append(memory_seed_to_yaml_item(memory))
    raw["memories"] = memories
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    with seed_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(raw, f, allow_unicode=True, sort_keys=False)


def load_memory_seed_file(path: str | Path) -> MemorySeedFile:
    seed_path = Path(path)
    with seed_path.open("r", encoding="utf-8") as f:
        raw: Any = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError("memory seed file must be a mapping")

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
        state = item.get("state", "active")
        if not isinstance(state, str) or state not in VALID_MEMORY_SEED_STATES:
            raise ValueError(
                f"memory seed entry {memory_id!r} state must be one of "
                f"{sorted(VALID_MEMORY_SEED_STATES)}"
            )
        memory = MemorySeed(
            memory_id=memory_id,
            character_id=item.get("character_id") if isinstance(item.get("character_id"), str) else None,
            content=content.strip(),
            importance=int(item.get("importance", 1)),
            source=str(item.get("source", "manual_seed")),
            tags=tuple(tags),
            state=state,
        )
        validate_memory_seed(memory)
        memories.append(memory)
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
