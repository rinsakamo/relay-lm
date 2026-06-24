"""Temporary exact-source hardening patch for Phase I-3."""
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one match in {path}, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/soul_lab_memory_correction.py",
    '''    schema: Literal["relaylm.lab.memory_correct_preflight_request.v0"] = PREFLIGHT_REQUEST_SCHEMA\n''',
    '''    schema: Literal["relaylm.lab.memory_correct_preflight_request.v0"]\n''',
)
replace_once(
    "relaylm/soul_lab_memory_correction.py",
    '''    schema: Literal["relaylm.lab.memory_correct_apply_request.v0"] = APPLY_REQUEST_SCHEMA\n''',
    '''    schema: Literal["relaylm.lab.memory_correct_apply_request.v0"]\n''',
)

replace_once(
    "relaylm/relaymem_primary_correction.py",
    '''        else:\n            state = load_primary_correction_state(root, namespace=namespace)\n''',
    '''        else:\n            _ensure_no_other_pending(root, memory_id, operation_key)\n            state = load_primary_correction_state(root, namespace=namespace)\n''',
)
replace_once(
    "relaylm/relaymem_primary_correction.py",
    '''                with _memory_lock(root, logical):\n                    result = _publish_prepared_successor(root, prepared, fault_at=None)\n''',
    '''                with _memory_lock(root, logical):\n                    current_state = load_primary_correction_state(\n                        root, namespace=namespace\n                    )\n                    current = current_state.current_by_logical.get(\n                        logical, (logical, 1)\n                    )\n                    if current != (\n                        str(prepared["prior_physical_id"]),\n                        int(prepared["prior_revision"]),\n                    ):\n                        failed += 1\n                        continue\n                    result = _publish_prepared_successor(root, prepared, fault_at=None)\n''',
)
replace_once(
    "relaylm/relaymem_primary_correction.py",
    '''def _operation_path(root: Path, memory_id: str, operation_key: str, state: str) -> Path:\n''',
    '''def _ensure_no_other_pending(\n    root: Path, memory_id: str, operation_key: str\n) -> None:\n    memory_dir = root / _CORRECTION_ROOT / memory_id\n    _ensure_private_dir(root, memory_dir)\n    for prepared_path in memory_dir.glob("*.prepared.json"):\n        other_key = prepared_path.name.removesuffix(".prepared.json")\n        if other_key == operation_key:\n            continue\n        applied_path = memory_dir / f"{other_key}.applied.json"\n        if not applied_path.exists():\n            raise PrimaryCorrectionError("operation_conflict")\n\n\ndef _operation_path(root: Path, memory_id: str, operation_key: str, state: str) -> Path:\n''',
)

replace_once(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    '''  pinned: boolean | null;\n  source_kind: string;\n}\n\nexport interface LabRecentMemoryProjection''',
    '''  pinned: boolean | null;\n  source_kind: string;\n  revision: number;\n  correction_count: number;\n  last_corrected_at: string | null;\n  has_prior_revision: boolean;\n}\n\nexport interface LabRecentMemoryProjection''',
)
replace_once(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    '''  "scope_label", "formed_at", "pinned", "source_kind",\n] as const;\n''',
    '''  "scope_label", "formed_at", "pinned", "source_kind", "revision",\n  "correction_count", "last_corrected_at", "has_prior_revision",\n] as const;\n''',
)
replace_once(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    '''    !isNullableString(value.formed_at) || !(value.pinned === null || typeof value.pinned === "boolean") ||\n    typeof value.source_kind !== "string"\n''',
    '''    !isNullableString(value.formed_at) || !(value.pinned === null || typeof value.pinned === "boolean") ||\n    typeof value.source_kind !== "string" || !isPositiveInteger(value.revision) ||\n    !isNonNegativeInteger(value.correction_count) || !isNullableString(value.last_corrected_at) ||\n    typeof value.has_prior_revision !== "boolean" ||\n    value.has_prior_revision !== (value.correction_count > 0)\n''',
)
replace_once(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    '''function isNonNegativeInteger(value: unknown): value is number {\n''',
    '''function isPositiveInteger(value: unknown): value is number {\n  return Number.isInteger(value) && Number(value) >= 1;\n}\n\nfunction isNonNegativeInteger(value: unknown): value is number {\n''',
)

replace_once(
    "apps/soul-lab/scripts/observationApiSmoke.mjs",
    '''          source_kind: "preference",\n        },\n''',
    '''          source_kind: "preference",\n          revision: 1,\n          correction_count: 0,\n          last_corrected_at: null,\n          has_prior_revision: false,\n        },\n''',
)
replace_once(
    "apps/soul-lab/src/features/lab/correctionApi.ts",
    '''    value.items.length !== value.correction_count\n''',
    '''    value.items.length > value.correction_count\n''',
)
replace_once(
    "apps/soul-lab/src/features/lab/PrimaryMemoryCorrectPanel.tsx",
    '''  const ready = state.kind === "preflight-ready" ? state.value : null;\n''',
    '''  const ready =\n    state.kind === "preflight-ready" || state.kind === "apply-loading"\n      ? state.value\n      : null;\n''',
)

print("Phase I-3 hardening patch applied")
