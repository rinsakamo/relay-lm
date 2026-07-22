from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/evidence_capture_attempt.py",
    '''        snapshot = RouteCaptureGrantSnapshot(
            schema=str(snapshot_payload["schema"]),
''',
    '''        expires_at_or_null = snapshot_payload["expires_at_or_null"]
        if expires_at_or_null is not None and type(expires_at_or_null) is not str:
            raise TypeError("expires_at_or_null must be null or string")
        snapshot = RouteCaptureGrantSnapshot(
            schema=str(snapshot_payload["schema"]),
''',
)
replace_once(
    "relaylm/evidence_capture_attempt.py",
    '''            expires_at_or_null=snapshot_payload["expires_at_or_null"],
''',
    '''            expires_at_or_null=expires_at_or_null,
''',
)
replace_once(
    "tests/test_evidence_final_review_regressions.py",
    '''import relaylm.evidence_response_capture as response_capture_module
''',
    '''import relaylm.evidence_response_capture as response_capture_module
from relaylm.evidence_capture_attempt import build_managed_conversation_route_snapshot
from relaylm.evidence_space import derive_evidence_space_id
''',
)
replace_once(
    "tests/test_evidence_final_review_regressions.py",
    '''def test_store_rejects_existing_symlink_root(tmp_path: Path) -> None:
''',
    '''def test_route_snapshot_rejects_non_string_expiry() -> None:
    payload = route_snapshot(capture_profile="managed_assistant_response")
    payload["expires_at_or_null"] = 123
    evidence_space_id = derive_evidence_space_id(
        workspace_or_tenant_ref="relaylm-local",
        character_id="char1",
        memory_namespace="ns1",
        session_id="sess1",
    )

    snapshot, reasons = build_managed_conversation_route_snapshot(
        snapshot_payload=payload,
        evidence_space_id=evidence_space_id,
        capture_profile="managed_assistant_response",
    )

    assert snapshot is None
    assert reasons == ("route_capture_grant_snapshot_shape_invalid",)


def test_store_rejects_existing_symlink_root(tmp_path: Path) -> None:
''',
)
