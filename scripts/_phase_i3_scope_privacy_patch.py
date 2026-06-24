"""Temporary exact-source patch for Phase I-3 scope privacy ordering."""
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    count = body.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one exact match, found {count}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/relaymem_primary_correction.py",
    '''    root = _safe_store_root(store_root)\n    if not is_sha256(memory_id):\n        raise PrimaryCorrectionError("not_found_or_wrong_scope")\n    state = load_primary_correction_state(root, namespace=namespace)\n''',
    '''    root = _safe_store_root(store_root)\n    _load_scoped_control_state(\n        root, namespace=namespace, logical_memory_id=memory_id\n    )\n    state = load_primary_correction_state(root, namespace=namespace)\n''',
)

replace_once(
    "relaylm/relaymem_primary_correction.py",
    '''def _load_current_target(\n''',
    '''def _load_scoped_control_state(\n    root: Path, *, namespace: str, logical_memory_id: str\n) -> dict[str, Any]:\n    """Confirm logical target membership before reading correction metadata.\n\n    This preserves the not-found/wrong-scope indistinguishability contract even\n    after the target has correction receipts in another namespace.\n    """\n\n    if not is_sha256(logical_memory_id):\n        raise PrimaryCorrectionError("not_found_or_wrong_scope")\n    control, reasons = _load_control_state(root)\n    if control is None or reasons:\n        raise PrimaryCorrectionError("target_corrupt")\n    index_matches = [\n        entry\n        for entry in control["index"]\n        if entry.get("idempotency_key") == logical_memory_id\n        and entry.get("namespace") == namespace\n    ]\n    log_matches = [\n        entry\n        for entry in control["log"]\n        if entry.get("idempotency_key") == logical_memory_id\n        and entry.get("namespace") == namespace\n    ]\n    if not index_matches and not log_matches:\n        raise PrimaryCorrectionError("not_found_or_wrong_scope")\n    if len(index_matches) != 1 or len(log_matches) != 1:\n        raise PrimaryCorrectionError("target_corrupt")\n    return control\n\n\ndef _load_current_target(\n''',
)

replace_once(
    "relaylm/relaymem_primary_correction.py",
    '''    if not is_sha256(logical_memory_id):\n        raise PrimaryCorrectionError("not_found_or_wrong_scope")\n    if "*" in state.invalid_logical or logical_memory_id in state.invalid_logical:\n        raise PrimaryCorrectionError("target_corrupt")\n    current_physical, current_revision = state.current_by_logical.get(logical_memory_id, (logical_memory_id, 1))\n    if current_revision != expected_revision:\n        raise PrimaryCorrectionError("stale_revision")\n    control, reasons = _load_control_state(root)\n    if control is None or reasons:\n        raise PrimaryCorrectionError("target_corrupt")\n''',
    '''    control = _load_scoped_control_state(\n        root, namespace=namespace, logical_memory_id=logical_memory_id\n    )\n    if "*" in state.invalid_logical or logical_memory_id in state.invalid_logical:\n        raise PrimaryCorrectionError("target_corrupt")\n    current_physical, current_revision = state.current_by_logical.get(logical_memory_id, (logical_memory_id, 1))\n    if current_revision != expected_revision:\n        raise PrimaryCorrectionError("stale_revision")\n''',
)

replace_once(
    "scripts/relaylm_phase_i3_primary_mem_correct_security_smoke.py",
    '''            require(applied.status_code == 200, applied.text)\n            require(applied.json()["result_revision"] == 2, applied.json())\n            replay = client.post(\n''',
    '''            require(applied.status_code == 200, applied.text)\n            require(applied.json()["result_revision"] == 2, applied.json())\n\n            wrong_namespace_after = client.post(\n                f"{base_a}/correct/preflight?namespace={OTHER_NAMESPACE}",\n                json=preflight_body(2, "wrong-namespace-after-correct"),\n            )\n            require(wrong_namespace_after.status_code == 404, wrong_namespace_after.text)\n            require(\n                wrong_namespace_after.json()\n                == {"detail": "not_found_or_wrong_scope"},\n                wrong_namespace_after.json(),\n            )\n            wrong_namespace_history = client.get(\n                f"{base_a}/corrections?namespace={OTHER_NAMESPACE}"\n            )\n            require(wrong_namespace_history.status_code == 404, wrong_namespace_history.text)\n            require(\n                wrong_namespace_history.json()\n                == {"detail": "not_found_or_wrong_scope"},\n                wrong_namespace_history.json(),\n            )\n\n            replay = client.post(\n''',
)

print("Phase I-3 scope privacy ordering patch applied")
