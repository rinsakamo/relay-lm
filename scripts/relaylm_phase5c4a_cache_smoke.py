#!/usr/bin/env python3
"""Phase 5-C4a cache-disabled and cache-miss smoke."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase5c4a_smoke_support import build_context, payload, write_config
from relaylm.pipeline_context import consume_active_pipeline_context


def main() -> int:
    request = payload([("system", "cache-independent sentinel")])
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        root = Path(td)
        disabled_cfg = root / "disabled.yaml"
        write_config(disabled_cfg, dry_run_only=False, lookup_enabled=False)
        disabled, _ = build_context(disabled_cfg, request)
        result = disabled.client_history_exclusion_apply_result
        assert result is not None and result.status == "applied"
        assert disabled.client_instruction_cache_lookup_runtime_result is None
        assert disabled.client_instruction_identity_result is not None
        consume_active_pipeline_context()

        cache_root = root / "cache"
        cache_root.mkdir()
        miss_cfg = root / "miss.yaml"
        write_config(
            miss_cfg,
            dry_run_only=False,
            lookup_enabled=True,
            cache_root=str(cache_root),
        )
        before = list(cache_root.iterdir())
        miss, _ = build_context(miss_cfg, request)
        miss_result = miss.client_history_exclusion_apply_result
        assert miss_result is not None and miss_result.status == "applied"
        assert miss_result.instruction_resolution_mode == "cache_miss_first_pass"
        assert miss.client_instruction_cache_lookup_runtime_result is not None
        assert miss.client_instruction_cache_lookup_runtime_result.status == "miss"
        assert list(cache_root.iterdir()) == before
        consume_active_pipeline_context()

    print("relaylm_phase5c4a_cache_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
