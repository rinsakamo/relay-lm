"""Memory adapter boundary dry-run helpers for RelayLM."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from relaylm.config import RelayLMConfig
from relaylm.memory_candidate import load_seed_memory_candidates, select_memory_candidates
from relaylm.memory_context import MemoryConfigurationError
from relaylm.routing import ResolvedRoute


@dataclass(frozen=True)
class MemoryAdapterCandidate:
    memory_id: str


@dataclass(frozen=True)
class MemoryAdapterResult:
    adapter_name: str
    adapter_kind: str
    status: str
    scope: dict[str, str | None]
    candidate_count: int
    candidate_ids: list[str]
    selected_candidate_ids: list[str]
    fallback_reason: str | None = None

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryAdapterDryRun:
    result: MemoryAdapterResult

    def to_log_dict(self) -> dict[str, object]:
        return self.result.to_log_dict()


def build_local_seed_memory_adapter_dry_run(
    *,
    config: RelayLMConfig,
    route: ResolvedRoute,
) -> MemoryAdapterDryRun:
    scope = {
        "character_id": route.character_id,
        "memory_namespace": route.memory_namespace,
        "cache_namespace": route.cache_namespace,
    }

    if not route.character_id:
        return MemoryAdapterDryRun(
            result=MemoryAdapterResult(
                adapter_name="local_seed",
                adapter_kind="seed_file",
                status="not_configured",
                scope=scope,
                candidate_count=0,
                candidate_ids=[],
                selected_candidate_ids=[],
            )
        )

    character = config.characters.get(route.character_id)
    if character is None:
        raise MemoryConfigurationError(
            f"RelayLM route {route.route_model} references missing character: {route.character_id}"
        )
    if character.memory_seed_path is None:
        return MemoryAdapterDryRun(
            result=MemoryAdapterResult(
                adapter_name="local_seed",
                adapter_kind="seed_file",
                status="not_configured",
                scope=scope,
                candidate_count=0,
                candidate_ids=[],
                selected_candidate_ids=[],
            )
        )

    candidates = load_seed_memory_candidates(character.memory_seed_path)
    selected = select_memory_candidates(
        candidates,
        character_id=route.character_id,
        limit=config.memory.candidate_limit,
    )
    candidate_ids = [c.memory_id for c in candidates]
    selected_ids = [c.memory_id for c in selected]
    return MemoryAdapterDryRun(
        result=MemoryAdapterResult(
            adapter_name="local_seed",
            adapter_kind="seed_file",
            status="ok",
            scope=scope,
            candidate_count=len(candidates),
            candidate_ids=candidate_ids,
            selected_candidate_ids=selected_ids,
        )
    )
