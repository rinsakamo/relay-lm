from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"missing replacement anchor: {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: str, old: str, new: str, expected: int) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        if text.count(new) == expected:
            return
        raise RuntimeError(f"missing replacement anchors: {path}")
    if text.count(old) != expected:
        raise RuntimeError(f"unexpected replacement count: {path}")
    target.write_text(text.replace(old, new), encoding="utf-8")


replace_once(
    "relaylm/soul_lab_observation_store.py",
    '''def read_used_receipts(store_root: object) -> tuple[list[dict[str, Any]], list[str]]:
    return _read_receipts(store_root, "used", USED_RECEIPT_SCHEMA, _validate_used_payload)


def _validate_run_payload''',
    '''def read_used_receipts(store_root: object) -> tuple[list[dict[str, Any]], list[str]]:
    return _read_receipts(store_root, "used", USED_RECEIPT_SCHEMA, _validate_used_payload)


def read_outcome_receipts_for_run(
    store_root: object, run_id: str
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(run_id, str) or _TOKEN_RE.fullmatch(run_id) is None:
        return [], ["observation_run_id_invalid"]
    return _read_receipts(
        store_root,
        "outcomes",
        OUTCOME_RECEIPT_SCHEMA,
        _validate_outcome_payload,
        predicate=lambda item: item.get("run_id") == run_id,
    )


def read_used_receipt_for_run(
    store_root: object, run_id: str
) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(run_id, str) or _TOKEN_RE.fullmatch(run_id) is None:
        return None, ["observation_run_id_invalid"]
    try:
        root = _safe_store_root(store_root, create_observation=False)
    except ObservationStoreError as exc:
        return None, [str(exc)]
    kind_dir = root / "used"
    if not kind_dir.exists():
        return None, []
    if kind_dir.is_symlink() or not kind_dir.is_dir():
        return None, ["observation_kind_directory_unsafe"]
    path = kind_dir / f"{stable_correlation(run_id)}.json"
    if not path.exists():
        return None, []
    try:
        envelope = _read_one(path, kind_dir)
        payload = _validate_envelope(envelope, USED_RECEIPT_SCHEMA)
        validated = _validate_used_payload(payload)
        if validated.get("run_id") != run_id:
            raise ObservationStoreError("observation_receipt_identity_mismatch")
        return validated, []
    except (OSError, UnicodeError, json.JSONDecodeError, ObservationStoreError):
        return None, ["observation_receipt_corrupt_ignored"]


def _validate_run_payload''',
)
replace_once(
    "relaylm/soul_lab_observation_store.py",
    '''def _read_receipts(store_root: object, kind: str, expected_schema: str, validator: Any) -> tuple[list[dict[str, Any]], list[str]]:
''',
    '''def _read_receipts(
    store_root: object,
    kind: str,
    expected_schema: str,
    validator: Any,
    *,
    predicate: Any | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
''',
)
replace_once(
    "relaylm/soul_lab_observation_store.py",
    '''                validated = validator(payload)
                timestamp, identity = _receipt_order_key(validated, expected_schema)
''',
    '''                validated = validator(payload)
                if predicate is not None and not predicate(validated):
                    continue
                timestamp, identity = _receipt_order_key(validated, expected_schema)
''',
)
replace_once(
    "relaylm/soul_lab_observation_store.py",
    '''    "read_outcome_receipts", "read_run_receipts", "read_used_receipts",
''',
    '''    "read_outcome_receipts", "read_outcome_receipts_for_run", "read_run_receipts",
    "read_used_receipt_for_run", "read_used_receipts",
''',
)
replace_once(
    "relaylm/soul_lab_observation_projection.py",
    '''    read_outcome_receipts,
    read_run_receipts,
    read_used_receipts,
''',
    '''    read_outcome_receipts,
    read_outcome_receipts_for_run,
    read_run_receipts,
    read_used_receipt_for_run,
    read_used_receipts,
''',
)
replace_once(
    "relaylm/soul_lab_observation_projection.py",
    '''    outcomes, outcome_reasons = read_outcome_receipts(scope.store_root)
    matched_outcomes = [item for item in outcomes if item.get("run_id") == run_id and item.get("namespace") == scope.namespace]
''',
    '''    outcomes, outcome_reasons = read_outcome_receipts_for_run(scope.store_root, run_id)
    matched_outcomes = [item for item in outcomes if item.get("namespace") == scope.namespace]
''',
)
replace_once(
    "relaylm/soul_lab_observation_projection.py",
    '''    used, used_reasons = read_used_receipts(scope.store_root)
    used_match = next((item for item in used if item.get("run_id") == run_id and item.get("character_id") == scope.character_id and item.get("namespace") == scope.namespace), None)
''',
    '''    used_match, used_reasons = read_used_receipt_for_run(scope.store_root, run_id)
    if used_match is not None and (
        used_match.get("character_id") != scope.character_id
        or used_match.get("namespace") != scope.namespace
    ):
        used_match = None
        used_reasons = normalize_reason_ids([*used_reasons, "observation_receipt_scope_mismatch"])
''',
)
replace_once(
    "relaylm/soul_lab_observation_projection.py",
    '''    receipts, used_reasons = read_used_receipts(scope.store_root)
    receipt = next((item for item in receipts if item.get("run_id") == run_id and item.get("character_id") == scope.character_id and item.get("namespace") == scope.namespace), None)
''',
    '''    receipt, used_reasons = read_used_receipt_for_run(scope.store_root, run_id)
    if receipt is not None and (
        receipt.get("character_id") != scope.character_id
        or receipt.get("namespace") != scope.namespace
    ):
        receipt = None
        used_reasons = normalize_reason_ids([*used_reasons, "observation_receipt_scope_mismatch"])
''',
)
replace_all(
    "relaylm/soul_lab_observation_projection.py",
    "response_generation_completed=True,",
    'response_generation_completed=latest["relayrun_status"] == "completed",',
    2,
)
replace_once(
    "scripts/relaylm_phase_i2_lab_observation_security_smoke.py",
    '''        write_used_receipt(str(scoped), used_receipt("run-z-incomplete", 1))
''',
    '''        write_used_receipt(str(scoped), used_receipt("run-z-incomplete", 1))
        write_used_receipt(str(scoped), used_receipt("run-y-incomplete", 1))
''',
)
replace_once(
    "scripts/relaylm_phase_i2_lab_observation_security_smoke.py",
    '''        try:
            latest = build_lab_last_run_projection(scope)
        finally:
            observation_store._MAX_RECEIPTS_PER_KIND = original_receipt_limit
        require(latest.run_id == "run-b", latest.model_dump())
        require(latest.status == "completed", latest.model_dump())
        require("observation_receipt_count_exceeded" in latest.bounded_reason_ids, latest.model_dump())
        used = build_lab_memory_used_projection(scope)
''',
    '''        try:
            latest = build_lab_last_run_projection(scope)
            used = build_lab_memory_used_projection(scope)
        finally:
            observation_store._MAX_RECEIPTS_PER_KIND = original_receipt_limit
        require(latest.run_id == "run-b", latest.model_dump())
        require(latest.status == "completed", latest.model_dump())
        require("observation_receipt_count_exceeded" in latest.bounded_reason_ids, latest.model_dump())
''',
)
