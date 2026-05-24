"""Memory adapter boundary dry-run helpers for RelayLM."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from relaylm.memory_selection import ConfiguredMemorySelection
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
    scope_isolation_status: str
    missing_scope_fields: list[str]
    scope_warning_count: int
    fallback_reason: str | None = None

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryAdapterDryRun:
    result: MemoryAdapterResult

    def to_log_dict(self) -> dict[str, object]:
        return self.result.to_log_dict()


def evaluate_memory_adapter_scope_isolation(
    scope: dict[str, str | None],
) -> tuple[str, list[str], int]:
    required_scope_fields = [
        "character_id",
        "memory_namespace",
        "user_id",
        "room_id",
        "scene_id",
        "session_id",
    ]
    missing_scope_fields = [field for field in required_scope_fields if not scope.get(field)]
    status = "ok" if not missing_scope_fields else "partial_scope"
    return status, missing_scope_fields, len(missing_scope_fields)


def build_local_seed_memory_adapter_dry_run_from_selection(
    *,
    route: ResolvedRoute,
    memory_selection: ConfiguredMemorySelection,
    memory_fallback_reason: str | None,
) -> MemoryAdapterDryRun:
    scope = {
        "character_id": route.character_id,
        "memory_namespace": route.memory_namespace,
        "cache_namespace": route.cache_namespace,
        "user_id": route.user_id,
        "user_type": route.user_type,
        "room_id": route.room_id,
        "scene_id": route.scene_id,
        "session_id": route.session_id,
    }
    scope_isolation_status, missing_scope_fields, scope_warning_count = (
        evaluate_memory_adapter_scope_isolation(scope)
    )

    if memory_fallback_reason:
        return MemoryAdapterDryRun(
            result=MemoryAdapterResult(
                adapter_name="local_seed",
                adapter_kind="seed_file",
                status="load_error",
                scope=scope,
                candidate_count=0,
                candidate_ids=[],
                selected_candidate_ids=[],
                scope_isolation_status=scope_isolation_status,
                missing_scope_fields=missing_scope_fields,
                scope_warning_count=scope_warning_count,
                fallback_reason=memory_fallback_reason,
            )
        )

    summary = memory_selection.summary
    if summary is None:
        return MemoryAdapterDryRun(
            result=MemoryAdapterResult(
                adapter_name="local_seed",
                adapter_kind="seed_file",
                status="not_configured",
                scope=scope,
                candidate_count=0,
                candidate_ids=[],
                selected_candidate_ids=[],
                scope_isolation_status=scope_isolation_status,
                missing_scope_fields=missing_scope_fields,
                scope_warning_count=scope_warning_count,
            )
        )

    selected_ids = list(summary.selected_memory_ids)
    candidate_ids = [*selected_ids, *summary.excluded_disabled_ids, *summary.excluded_character_ids]
    return MemoryAdapterDryRun(
        result=MemoryAdapterResult(
            adapter_name="local_seed",
            adapter_kind="seed_file",
            status="ok",
            scope=scope,
            candidate_count=summary.total_candidates,
            candidate_ids=candidate_ids,
            selected_candidate_ids=selected_ids,
            scope_isolation_status=scope_isolation_status,
            missing_scope_fields=missing_scope_fields,
            scope_warning_count=scope_warning_count,
        )
    )
