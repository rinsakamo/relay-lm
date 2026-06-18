"""Cache fixture helper for Phase 5-C4a smoke."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phase5c4a_smoke_support import cache_entry, identity_for


def write_fixture(
    cache_root: Path,
    request_payload: dict[str, Any],
    opaque_value: str,
) -> Path:
    identity = identity_for(request_payload)
    path = cache_root / f"{identity.cache_key_sha256}.json"
    path.write_text(
        json.dumps(cache_entry(identity, opaque_value), sort_keys=True),
        encoding="utf-8",
    )
    return path
