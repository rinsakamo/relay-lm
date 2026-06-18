#!/usr/bin/env python3
"""Compatibility wrapper for the Phase 5-C4a cache smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import phase5c4a_smoke_support as support
from phase5c4a_explicit_smoke_support import payload
from relaylm.pipeline_context import consume_active_pipeline_context


def main() -> int:
    request = payload([("system", "cache-independent sentinel")])
    import tempfile
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        root = Path(td)
        disabled_cfg = root / "disabled.yaml"
        support.write_config(disabled_cfg, dry_run_only=False, lookup_enabled=False)
        disabled, _ = support.build_context(disabled_cfg, request)
        result = disabled.client_history_exclusion_apply_result
        assert result is not None and result.status == "applied"
        consume_active_pipeline_context()

        cache_root = root / "cache"
        cache_root.mkdir()
        miss_cfg = root / "miss.yaml"
        support.write_config(
            miss_cfg,
            dry_run_only=False,
            lookup_enabled=True,
            cache_root=str(cache_root),
        )
        before = list(cache_root.iterdir())
        miss, _ = support.build_context(miss_cfg, request)
        miss_result = miss.client_history_exclusion_apply_result
        assert miss_result is not None and miss_result.status == "applied"
        assert miss_result.instruction_resolution_mode == "cache_miss_first_pass"
        assert list(cache_root.iterdir()) == before
        consume_active_pipeline_context()

    print("relaylm_phase5c4a_cache_explicit_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
