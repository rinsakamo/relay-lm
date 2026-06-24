#!/usr/bin/env python3
from pathlib import Path

path = Path("relaylm/relaymem_primary_recall.py")
body = path.read_text(encoding="utf-8")
old = '        "fallback_reason": _token(artifact.get("fallback_reason")),\n'
if body.count(old) != 2:
    raise SystemExit(f"expected two fallback projection anchors, got {body.count(old)}")
body = body.replace(
    old,
    '        "fallback_reason": _projection_fallback_reason(artifact),\n',
)
anchor = '''def _token(value: object) -> str | None:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None or bad_text(value):
        return None
    return value


'''
replacement = '''def _token(value: object) -> str | None:
    if not isinstance(value, str) or _TOKEN_RE.fullmatch(value) is None or bad_text(value):
        return None
    return value


def _projection_fallback_reason(artifact: Mapping[str, Any]) -> str | None:
    artifact_reason = _token(artifact.get("fallback_reason"))
    store_diagnostics = artifact.get("store_diagnostics")
    if isinstance(store_diagnostics, Mapping):
        store_reason = _token(store_diagnostics.get("fallback_reason"))
        if store_reason == "memory_store_disabled":
            return store_reason
    return artifact_reason


'''
if anchor not in body:
    raise SystemExit("token helper anchor missing")
path.write_text(body.replace(anchor, replacement, 1), encoding="utf-8")

smoke_path = Path("scripts/relaylm_relaymem_retrieval_dry_run_smoke.py")
smoke = smoke_path.read_text(encoding="utf-8")
expected = 'design["fallback_reason"] == "memory_store_not_configured"'
if smoke.count(expected) != 1:
    raise SystemExit(f"expected one disabled-store smoke anchor, got {smoke.count(expected)}")
smoke_path.write_text(
    smoke.replace(
        expected,
        'design["fallback_reason"] == "memory_store_disabled"',
        1,
    ),
    encoding="utf-8",
)
