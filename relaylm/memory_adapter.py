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


@dataclass(frozen=True)
class MemoryAdapterReadinessCheck:
    ready_for_adapter_evaluation: bool
    ready_for_future_enforcement: bool
    blocked_reason: str | None
    non_enforcing: bool
    adapter_status: str | None
    scope_isolation_status: str | None
    missing_scope_fields: list[str]

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryAdapterConflictDiagnostics:
    conflict_status: str
    conflict_count: int
    conflict_reasons: list[str]
    duplicate_candidate_ids: list[str]
    duplicate_selected_ids: list[str]
    selected_not_in_candidates: list[str]
    scope_conflict_reasons: list[str]

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryAdapterShadowDelta:
    delta_status: str
    scope_changed: bool
    scope_improved: bool
    scope_regressed: bool
    readiness_improved: bool
    readiness_regressed: bool
    conflicts_improved: bool
    conflicts_regressed: bool
    candidate_ids_changed: bool
    selected_candidate_ids_changed: bool
    before_scope_isolation_status: str | None
    after_scope_isolation_status: str | None
    before_readiness_blocked_reason: str | None
    after_readiness_blocked_reason: str | None
    before_conflict_status: str | None
    after_conflict_status: str | None
    changed_scope_fields: list[str]

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


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


def build_memory_adapter_readiness_check(
    memory_adapter_dry_run: dict[str, object] | None,
) -> MemoryAdapterReadinessCheck:
    if not isinstance(memory_adapter_dry_run, dict):
        return MemoryAdapterReadinessCheck(
            ready_for_adapter_evaluation=False,
            ready_for_future_enforcement=False,
            blocked_reason="missing_dry_run",
            non_enforcing=True,
            adapter_status=None,
            scope_isolation_status=None,
            missing_scope_fields=[],
        )

    adapter_status_obj = memory_adapter_dry_run.get("status")
    adapter_status = adapter_status_obj if isinstance(adapter_status_obj, str) else None
    scope_status_obj = memory_adapter_dry_run.get("scope_isolation_status")
    scope_isolation_status = scope_status_obj if isinstance(scope_status_obj, str) else None
    missing_obj = memory_adapter_dry_run.get("missing_scope_fields")
    missing_scope_fields = [item for item in missing_obj if isinstance(item, str)] if isinstance(missing_obj, list) else []

    if adapter_status == "load_error":
        return MemoryAdapterReadinessCheck(
            ready_for_adapter_evaluation=False,
            ready_for_future_enforcement=False,
            blocked_reason="load_error",
            non_enforcing=True,
            adapter_status=adapter_status,
            scope_isolation_status=scope_isolation_status,
            missing_scope_fields=missing_scope_fields,
        )
    if adapter_status == "not_configured":
        return MemoryAdapterReadinessCheck(
            ready_for_adapter_evaluation=False,
            ready_for_future_enforcement=False,
            blocked_reason="not_configured",
            non_enforcing=True,
            adapter_status=adapter_status,
            scope_isolation_status=scope_isolation_status,
            missing_scope_fields=missing_scope_fields,
        )
    if adapter_status == "ok" and scope_isolation_status == "ok":
        return MemoryAdapterReadinessCheck(
            ready_for_adapter_evaluation=True,
            ready_for_future_enforcement=False,
            blocked_reason=None,
            non_enforcing=True,
            adapter_status=adapter_status,
            scope_isolation_status=scope_isolation_status,
            missing_scope_fields=missing_scope_fields,
        )
    if scope_isolation_status == "partial_scope":
        return MemoryAdapterReadinessCheck(
            ready_for_adapter_evaluation=True,
            ready_for_future_enforcement=False,
            blocked_reason="partial_scope",
            non_enforcing=True,
            adapter_status=adapter_status,
            scope_isolation_status=scope_isolation_status,
            missing_scope_fields=missing_scope_fields,
        )
    return MemoryAdapterReadinessCheck(
        ready_for_adapter_evaluation=False,
        ready_for_future_enforcement=False,
        blocked_reason="missing_dry_run",
        non_enforcing=True,
        adapter_status=adapter_status,
        scope_isolation_status=scope_isolation_status,
        missing_scope_fields=missing_scope_fields,
    )


def build_memory_adapter_conflict_diagnostics(
    memory_adapter_dry_run: dict[str, object] | None,
) -> MemoryAdapterConflictDiagnostics:
    if not isinstance(memory_adapter_dry_run, dict):
        return MemoryAdapterConflictDiagnostics(
            conflict_status="unknown",
            conflict_count=1,
            conflict_reasons=["missing_dry_run"],
            duplicate_candidate_ids=[],
            duplicate_selected_ids=[],
            selected_not_in_candidates=[],
            scope_conflict_reasons=[],
        )

    candidate_ids_raw = memory_adapter_dry_run.get("candidate_ids")
    selected_ids_raw = memory_adapter_dry_run.get("selected_candidate_ids")
    candidate_ids = [x for x in candidate_ids_raw if isinstance(x, str)] if isinstance(candidate_ids_raw, list) else []
    selected_ids = [x for x in selected_ids_raw if isinstance(x, str)] if isinstance(selected_ids_raw, list) else []
    candidate_set = set(candidate_ids)

    def duplicates(items: list[str]) -> list[str]:
        seen: set[str] = set()
        dup: list[str] = []
        for item in items:
            if item in seen and item not in dup:
                dup.append(item)
            seen.add(item)
        return dup

    duplicate_candidate_ids = duplicates(candidate_ids)
    duplicate_selected_ids = duplicates(selected_ids)
    selected_not_in_candidates = sorted({item for item in selected_ids if item not in candidate_set})

    conflict_reasons: list[str] = []
    scope_conflict_reasons: list[str] = []
    if duplicate_candidate_ids:
        conflict_reasons.append("duplicate_candidate_ids")
    if duplicate_selected_ids:
        conflict_reasons.append("duplicate_selected_ids")
    if selected_not_in_candidates:
        conflict_reasons.append("selected_not_in_candidates")
    if memory_adapter_dry_run.get("scope_isolation_status") == "partial_scope":
        scope_conflict_reasons.append("partial_scope")
        conflict_reasons.append("partial_scope")

    return MemoryAdapterConflictDiagnostics(
        conflict_status="ok" if not conflict_reasons else "warning",
        conflict_count=len(conflict_reasons),
        conflict_reasons=conflict_reasons,
        duplicate_candidate_ids=duplicate_candidate_ids,
        duplicate_selected_ids=duplicate_selected_ids,
        selected_not_in_candidates=selected_not_in_candidates,
        scope_conflict_reasons=scope_conflict_reasons,
    )


def build_memory_adapter_shadow_dry_run_with_scope(
    *,
    base_dry_run: dict[str, object] | None,
    merged_scope: dict[str, str | None],
) -> dict[str, object] | None:
    if not isinstance(base_dry_run, dict):
        return None
    scope = {
        "character_id": merged_scope.get("character_id"),
        "memory_namespace": merged_scope.get("memory_namespace"),
        "cache_namespace": merged_scope.get("cache_namespace"),
        "user_id": merged_scope.get("user_id"),
        "user_type": merged_scope.get("user_type"),
        "room_id": merged_scope.get("room_id"),
        "scene_id": merged_scope.get("scene_id"),
        "session_id": merged_scope.get("session_id"),
    }
    scope_isolation_status, missing_scope_fields, scope_warning_count = evaluate_memory_adapter_scope_isolation(scope)
    return {
        "adapter_name": base_dry_run.get("adapter_name"),
        "adapter_kind": base_dry_run.get("adapter_kind"),
        "status": base_dry_run.get("status"),
        "scope": scope,
        "candidate_count": base_dry_run.get("candidate_count"),
        "candidate_ids": base_dry_run.get("candidate_ids"),
        "selected_candidate_ids": base_dry_run.get("selected_candidate_ids"),
        "scope_isolation_status": scope_isolation_status,
        "missing_scope_fields": missing_scope_fields,
        "scope_warning_count": scope_warning_count,
        "fallback_reason": base_dry_run.get("fallback_reason"),
        "shadow_source": "scope_resolution_merged_scope",
    }


def build_memory_adapter_shadow_delta(
    *,
    base_dry_run: dict[str, object] | None,
    shadow_dry_run: dict[str, object] | None,
    base_readiness: dict[str, object] | None,
    shadow_readiness: dict[str, object] | None,
    base_conflicts: dict[str, object] | None,
    shadow_conflicts: dict[str, object] | None,
) -> MemoryAdapterShadowDelta:
    if not isinstance(base_dry_run, dict) or not isinstance(shadow_dry_run, dict):
        return MemoryAdapterShadowDelta(
            delta_status="missing",
            scope_changed=False,
            scope_improved=False,
            scope_regressed=False,
            readiness_improved=False,
            readiness_regressed=False,
            conflicts_improved=False,
            conflicts_regressed=False,
            candidate_ids_changed=False,
            selected_candidate_ids_changed=False,
            before_scope_isolation_status=None,
            after_scope_isolation_status=None,
            before_readiness_blocked_reason=None,
            after_readiness_blocked_reason=None,
            before_conflict_status=None,
            after_conflict_status=None,
            changed_scope_fields=[],
        )

    base_scope = base_dry_run.get("scope") if isinstance(base_dry_run.get("scope"), dict) else {}
    shadow_scope = shadow_dry_run.get("scope") if isinstance(shadow_dry_run.get("scope"), dict) else {}
    scope_keys = ("user_id", "user_type", "room_id", "scene_id", "session_id")
    changed_scope_fields = [k for k in scope_keys if base_scope.get(k) != shadow_scope.get(k)]
    scope_changed = bool(changed_scope_fields)

    base_candidate_ids = base_dry_run.get("candidate_ids")
    shadow_candidate_ids = shadow_dry_run.get("candidate_ids")
    base_selected_ids = base_dry_run.get("selected_candidate_ids")
    shadow_selected_ids = shadow_dry_run.get("selected_candidate_ids")
    candidate_ids_changed = base_candidate_ids != shadow_candidate_ids
    selected_candidate_ids_changed = base_selected_ids != shadow_selected_ids

    before_scope_isolation_status = (
        base_dry_run.get("scope_isolation_status")
        if isinstance(base_dry_run.get("scope_isolation_status"), str)
        else None
    )
    after_scope_isolation_status = (
        shadow_dry_run.get("scope_isolation_status")
        if isinstance(shadow_dry_run.get("scope_isolation_status"), str)
        else None
    )
    scope_improved = before_scope_isolation_status == "partial_scope" and after_scope_isolation_status == "ok"
    scope_regressed = before_scope_isolation_status == "ok" and after_scope_isolation_status == "partial_scope"

    before_readiness_blocked_reason = (
        base_readiness.get("blocked_reason")
        if isinstance(base_readiness, dict) and isinstance(base_readiness.get("blocked_reason"), str)
        else None
    )
    after_readiness_blocked_reason = (
        shadow_readiness.get("blocked_reason")
        if isinstance(shadow_readiness, dict) and isinstance(shadow_readiness.get("blocked_reason"), str)
        else None
    )
    readiness_improved = before_readiness_blocked_reason is not None and after_readiness_blocked_reason is None
    readiness_regressed = before_readiness_blocked_reason is None and after_readiness_blocked_reason is not None

    before_conflict_status = (
        base_conflicts.get("conflict_status")
        if isinstance(base_conflicts, dict) and isinstance(base_conflicts.get("conflict_status"), str)
        else None
    )
    after_conflict_status = (
        shadow_conflicts.get("conflict_status")
        if isinstance(shadow_conflicts, dict) and isinstance(shadow_conflicts.get("conflict_status"), str)
        else None
    )
    conflicts_improved = before_conflict_status == "warning" and after_conflict_status == "ok"
    conflicts_regressed = before_conflict_status == "ok" and after_conflict_status == "warning"

    if candidate_ids_changed or selected_candidate_ids_changed:
        delta_status = "changed_candidates"
    elif scope_improved or readiness_improved or conflicts_improved:
        delta_status = "improved" if not (scope_regressed or readiness_regressed or conflicts_regressed) else "regressed"
    elif scope_regressed or readiness_regressed or conflicts_regressed:
        delta_status = "regressed"
    elif scope_changed:
        delta_status = "changed"
    else:
        delta_status = "same"

    return MemoryAdapterShadowDelta(
        delta_status=delta_status,
        scope_changed=scope_changed,
        scope_improved=scope_improved,
        scope_regressed=scope_regressed,
        readiness_improved=readiness_improved,
        readiness_regressed=readiness_regressed,
        conflicts_improved=conflicts_improved,
        conflicts_regressed=conflicts_regressed,
        candidate_ids_changed=candidate_ids_changed,
        selected_candidate_ids_changed=selected_candidate_ids_changed,
        before_scope_isolation_status=before_scope_isolation_status,
        after_scope_isolation_status=after_scope_isolation_status,
        before_readiness_blocked_reason=before_readiness_blocked_reason,
        after_readiness_blocked_reason=after_readiness_blocked_reason,
        before_conflict_status=before_conflict_status,
        after_conflict_status=after_conflict_status,
        changed_scope_fields=changed_scope_fields,
    )


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
