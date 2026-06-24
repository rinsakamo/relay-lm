"""Temporary exact-source patch applicator for Phase I-3 integration."""
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected one match in {path}, found {text.count(old)}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/relaymem_primary_recall.py",
    '''        if control is not None:\n            for raw_candidate in candidates:\n''',
    '''        if control is not None:\n            # Correction metadata is an audit/revision selector only. M2 remains\n            # relevance owner and the canonical page/index/log validator remains\n            # unchanged. The local import avoids a module cycle because the\n            # correction apply boundary reuses these private validation helpers.\n            from .relaymem_primary_correction import (\n                load_primary_correction_state,\n                resolve_primary_correction_identity,\n            )\n\n            correction_state = load_primary_correction_state(\n                root, namespace=namespace\n            )\n            for raw_candidate in candidates:\n''',
)

replace_once(
    "relaylm/relaymem_primary_recall.py",
    '''                identity = loaded["idempotency_key"]\n                if identity in seen_identities:\n''',
    '''                physical_identity = loaded["idempotency_key"]\n                resolved_identity = resolve_primary_correction_identity(\n                    correction_state, physical_identity\n                )\n                if resolved_identity is None:\n                    reasons.append("primary_recall_correction_state_invalid")\n                    continue\n                identity, revision, is_current = resolved_identity\n                if not is_current:\n                    reasons.append("primary_recall_superseded_revision_excluded")\n                    continue\n                loaded["physical_idempotency_key"] = physical_identity\n                loaded["idempotency_key"] = identity\n                loaded["revision"] = revision\n                if identity in seen_identities:\n''',
)

replace_once(
    "relaylm/relaymem_primary_recall.py",
    '''        "summary": summary,\n        "memory_kind": memory_kind,\n    }, []\n''',
    '''        "summary": summary,\n        "title": title,\n        "memory_kind": memory_kind,\n        "namespace": expected_namespace,\n        "source_event_kind": metadata["source_event_kind"],\n    }, []\n''',
)

replace_once(
    "relaylm/soul_lab_observation_projection.py",
    '''    source_kind: str\n\n\nclass LabMemoryOutcomeItem''',
    '''    source_kind: str\n    revision: int = Field(ge=1)\n    correction_count: int = Field(ge=0)\n    last_corrected_at: str | None = None\n    has_prior_revision: bool\n\n\nclass LabMemoryOutcomeItem''',
)

replace_once(
    "relaylm/soul_lab_observation_projection.py",
    '''    items: list[LabRecentMemoryItem] = []\n    seen: set[str] = set()\n    projection_reasons: list[str] = list(reasons)\n    for entry in reversed(control["log"]):\n        if entry.get("namespace") != scope.namespace:\n            continue\n        identity = entry.get("idempotency_key")\n        if not isinstance(identity, str) or identity in seen:\n            continue\n        loaded, blocked = _load_validated_page(\n            root, {"path": entry.get("page_relative_path")},\n            expected_namespace=scope.namespace, control=control,\n        )\n        if loaded is None:\n            projection_reasons.extend(blocked)\n            continue\n        seen.add(identity)\n        summary = bounded_text(loaded.get("summary"), maximum=512)\n        items.append(LabRecentMemoryItem(\n            memory_id=identity, title="",\n            bounded_summary=summary, source_kind=str(loaded.get("memory_kind", "primary")),\n        ))\n        if len(items) >= bounded_limit:\n            break\n''',
    '''    from .relaymem_primary_correction import (\n        load_primary_correction_state,\n        resolve_primary_correction_identity,\n    )\n\n    correction_state = load_primary_correction_state(\n        root, namespace=scope.namespace\n    )\n    items: list[LabRecentMemoryItem] = []\n    seen: set[str] = set()\n    projection_reasons: list[str] = list(reasons)\n    for entry in reversed(control["log"]):\n        if entry.get("namespace") != scope.namespace:\n            continue\n        physical_identity = entry.get("idempotency_key")\n        if not isinstance(physical_identity, str):\n            continue\n        resolved = resolve_primary_correction_identity(\n            correction_state, physical_identity\n        )\n        if resolved is None:\n            projection_reasons.append("primary_correction_state_invalid")\n            continue\n        identity, revision, is_current = resolved\n        if not is_current or identity in seen:\n            continue\n        loaded, blocked = _load_validated_page(\n            root, {"path": entry.get("page_relative_path")},\n            expected_namespace=scope.namespace, control=control,\n        )\n        if loaded is None:\n            projection_reasons.extend(blocked)\n            continue\n        seen.add(identity)\n        receipts = correction_state.receipts_by_logical.get(identity, ())\n        summary = bounded_text(loaded.get("summary"), maximum=512)\n        items.append(LabRecentMemoryItem(\n            memory_id=identity,\n            title=bounded_text(loaded.get("title"), maximum=160),\n            bounded_summary=summary,\n            source_kind=str(loaded.get("memory_kind", "primary")),\n            revision=revision,\n            correction_count=len(receipts),\n            last_corrected_at=(\n                str(receipts[-1]["applied_at"]) if receipts else None\n            ),\n            has_prior_revision=bool(receipts),\n        ))\n        if len(items) >= bounded_limit:\n            break\n''',
)

replace_once(
    "relaylm/soul_lab_observation_projection.py",
    '''    summaries: dict[str, str] = {}\n    output_reasons = list(reasons)\n    for entry in control["index"]:\n        if entry.get("namespace") != namespace:\n            continue\n        identity = entry.get("idempotency_key")\n        if not isinstance(identity, str):\n            continue\n        loaded, blocked = _load_validated_page(\n            root, {"path": entry.get("page_relative_path")},\n            expected_namespace=namespace, control=control,\n        )\n        if loaded is None:\n            output_reasons.extend(blocked)\n            continue\n        summaries[identity] = bounded_text(loaded.get("summary"), maximum=512)\n''',
    '''    from .relaymem_primary_correction import (\n        load_primary_correction_state,\n        resolve_primary_correction_identity,\n    )\n\n    correction_state = load_primary_correction_state(root, namespace=namespace)\n    summaries: dict[str, str] = {}\n    output_reasons = list(reasons)\n    for entry in control["index"]:\n        if entry.get("namespace") != namespace:\n            continue\n        physical_identity = entry.get("idempotency_key")\n        if not isinstance(physical_identity, str):\n            continue\n        resolved = resolve_primary_correction_identity(\n            correction_state, physical_identity\n        )\n        if resolved is None:\n            output_reasons.append("primary_correction_state_invalid")\n            continue\n        identity, _revision, is_current = resolved\n        if not is_current:\n            continue\n        loaded, blocked = _load_validated_page(\n            root, {"path": entry.get("page_relative_path")},\n            expected_namespace=namespace, control=control,\n        )\n        if loaded is None:\n            output_reasons.extend(blocked)\n            continue\n        summaries[identity] = bounded_text(loaded.get("summary"), maximum=512)\n''',
)

print("Phase I-3 exact-source integration patch applied")
