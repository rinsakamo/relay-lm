from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.request_scope import extract_request_scope_identity


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    payload = {
        "model": "relaylm-default",
        "metadata": {
            "user_id": "meta-user",
            "user_type": "meta-type",
            "room_id": "meta-room",
            "scene_id": "meta-scene",
            "session_id": "meta-session",
        },
    }
    payload_before = copy.deepcopy(payload)

    headers_only = {
        "x-relaylm-user-id": "hdr-user",
        "x-relaylm-user-type": "hdr-type",
        "x-relaylm-room-id": "hdr-room",
        "x-relaylm-scene-id": "hdr-scene",
        "x-relaylm-session-id": "hdr-session",
    }
    scope_headers = extract_request_scope_identity(headers_only, {"model": "relaylm-default"})
    require(scope_headers.source == "headers", scope_headers)
    require(scope_headers.user_id == "hdr-user", scope_headers)
    require(scope_headers.room_id == "hdr-room", scope_headers)
    print("ok request scope identity headers only")

    scope_metadata = extract_request_scope_identity({}, payload)
    require(scope_metadata.source == "metadata", scope_metadata)
    require(scope_metadata.user_id == "meta-user", scope_metadata)
    require(scope_metadata.scene_id == "meta-scene", scope_metadata)
    print("ok request scope identity metadata only")

    mixed_headers = {
        "x-relaylm-user-id": "hdr-user",
        "x-relaylm-room-id": "hdr-room",
    }
    scope_mixed = extract_request_scope_identity(mixed_headers, payload)
    require(scope_mixed.source == "mixed", scope_mixed)
    require(scope_mixed.user_id == "hdr-user", scope_mixed)
    require(scope_mixed.room_id == "hdr-room", scope_mixed)
    require(scope_mixed.scene_id == "meta-scene", scope_mixed)
    require(scope_mixed.session_id == "meta-session", scope_mixed)
    print("ok request scope identity mixed precedence")

    scope_missing = extract_request_scope_identity(None, {"model": "relaylm-default"})
    require(scope_missing.source == "missing", scope_missing)
    require(scope_missing.user_id is None, scope_missing)
    require(scope_missing.room_id is None, scope_missing)
    for field in ("user_id", "room_id", "scene_id", "session_id"):
        require(field in scope_missing.missing_fields, scope_missing)
    print("ok request scope identity missing fields")

    require(payload == payload_before, (payload, payload_before))
    print("ok request scope identity payload non-mutation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

