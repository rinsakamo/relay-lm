from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"missing replacement anchor: {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/soul_lab_observation_store.py",
    "import json\n",
    "import heapq\nimport json\n",
)
replace_once(
    "relaylm/soul_lab_observation_store.py",
    '''def _read_receipts(store_root: object, kind: str, expected_schema: str, validator: Any) -> tuple[list[dict[str, Any]], list[str]]:
    reasons: list[str] = []
    try:
        root = _safe_store_root(store_root, create_observation=False)
    except ObservationStoreError as exc:
        return [], [str(exc)]
    kind_dir = root / kind
    if not kind_dir.exists():
        return [], []
    if kind_dir.is_symlink() or not kind_dir.is_dir():
        return [], ["observation_kind_directory_unsafe"]
    try:
        paths = sorted(kind_dir.iterdir(), key=lambda item: item.name)
    except OSError:
        return [], ["observation_kind_directory_unreadable"]
    if len(paths) > _MAX_RECEIPTS_PER_KIND:
        reasons.append("observation_receipt_count_exceeded")
        paths = paths[-_MAX_RECEIPTS_PER_KIND:]
    receipts: list[dict[str, Any]] = []
    for path in paths:
        if path.name.startswith(".tmp-"):
            continue
        try:
            envelope = _read_one(path, kind_dir)
            payload = _validate_envelope(envelope, expected_schema)
            receipts.append(validator(payload))
        except (OSError, UnicodeError, json.JSONDecodeError, ObservationStoreError):
            reasons.append("observation_receipt_corrupt_ignored")
    return receipts, normalize_reason_ids(reasons)
''',
    '''def _read_receipts(store_root: object, kind: str, expected_schema: str, validator: Any) -> tuple[list[dict[str, Any]], list[str]]:
    reasons: set[str] = set()
    try:
        root = _safe_store_root(store_root, create_observation=False)
    except ObservationStoreError as exc:
        return [], [str(exc)]
    kind_dir = root / kind
    if not kind_dir.exists():
        return [], []
    if kind_dir.is_symlink() or not kind_dir.is_dir():
        return [], ["observation_kind_directory_unsafe"]

    retained: list[tuple[datetime, str, str, dict[str, Any]]] = []
    valid_count = 0
    try:
        for path in kind_dir.iterdir():
            if path.name.startswith(".tmp-"):
                continue
            try:
                envelope = _read_one(path, kind_dir)
                payload = _validate_envelope(envelope, expected_schema)
                validated = validator(payload)
                timestamp, identity = _receipt_order_key(validated, expected_schema)
                entry = (timestamp, identity, path.name, validated)
                valid_count += 1
                if len(retained) < _MAX_RECEIPTS_PER_KIND:
                    heapq.heappush(retained, entry)
                elif entry[:3] > retained[0][:3]:
                    heapq.heapreplace(retained, entry)
            except (OSError, UnicodeError, json.JSONDecodeError, ObservationStoreError):
                reasons.add("observation_receipt_corrupt_ignored")
    except OSError:
        return [], ["observation_kind_directory_unreadable"]

    if valid_count > _MAX_RECEIPTS_PER_KIND:
        reasons.add("observation_receipt_count_exceeded")
    receipts = [entry[3] for entry in sorted(retained)]
    return receipts, normalize_reason_ids(sorted(reasons))


def _receipt_order_key(payload: Mapping[str, Any], schema: str) -> tuple[datetime, str]:
    if schema == RUN_RECEIPT_SCHEMA:
        timestamp_key = "completed_at"
        identity = str(payload["run_id"])
    elif schema == OUTCOME_RECEIPT_SCHEMA:
        timestamp_key = "observed_at"
        identity = f"{payload['run_id']}:{payload['job_correlation_id']}"
    elif schema == USED_RECEIPT_SCHEMA:
        timestamp_key = "captured_at"
        identity = str(payload["run_id"])
    else:
        raise ObservationStoreError("observation_receipt_schema_unsupported")
    timestamp = datetime.fromisoformat(str(payload[timestamp_key]).replace("Z", "+00:00"))
    return timestamp.astimezone(timezone.utc), identity
''',
)
replace_once(
    "scripts/relaylm_phase_i2_lab_observation_security_smoke.py",
    "from relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root\n",
    "from relaylm import soul_lab_observation_store as observation_store\nfrom relaylm.relaymem_primary_recall import resolve_relaymem_character_store_root\n",
)
replace_once(
    "scripts/relaylm_phase_i2_lab_observation_security_smoke.py",
    '''        latest = build_lab_last_run_projection(scope)
        require(latest.run_id == "run-b", latest.model_dump())
        require(latest.status == "completed", latest.model_dump())
        used = build_lab_memory_used_projection(scope)
''',
    '''        original_receipt_limit = observation_store._MAX_RECEIPTS_PER_KIND
        observation_store._MAX_RECEIPTS_PER_KIND = 2
        try:
            latest = build_lab_last_run_projection(scope)
        finally:
            observation_store._MAX_RECEIPTS_PER_KIND = original_receipt_limit
        require(latest.run_id == "run-b", latest.model_dump())
        require(latest.status == "completed", latest.model_dump())
        require("observation_receipt_count_exceeded" in latest.bounded_reason_ids, latest.model_dump())
        used = build_lab_memory_used_projection(scope)
''',
)
