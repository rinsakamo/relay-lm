#!/usr/bin/env python3
"""Phase 5-C4a optional dependency smoke."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase5c4a_cache_fixture import write_fixture
from phase5c4a_smoke_support import build_context, payload, write_config
from relaylm.pipeline_context import consume_active_pipeline_context


def main() -> int:
    request = payload([("developer", "optional dependency sentinel")])
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        root = Path(td)
        store = root / "lookup"
        store.mkdir()
        cfg = root / "configured.yaml"
        write_config(
            cfg,
            dry_run_only=False,
            lookup_enabled=True,
            cache_root=str(store),
        )
        opaque = "optional opaque sentinel"
        path = write_fixture(store, request, opaque)
        original_bytes = path.read_bytes()
        context, _ = build_context(cfg, request)
        result = context.client_history_exclusion_apply_result
        lookup = context.client_instruction_cache_lookup_runtime_result
        assert result is not None and result.status == "applied"
        assert result.instruction_resolution_mode == "cache_hit"
        assert lookup is not None and lookup.status == "hit"
        prefix = context.forwarded_payload["messages"][0]["content"]
        assert opaque not in prefix
        assert prefix.count("optional dependency sentinel") == 1
        assert path.read_bytes() == original_bytes
        consume_active_pipeline_context()

    print("relaylm_phase5c4a_optional_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
