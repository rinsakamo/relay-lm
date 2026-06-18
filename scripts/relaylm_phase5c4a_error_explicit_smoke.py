#!/usr/bin/env python3
"""Phase 5-C4a explicit-provenance bounded error smoke."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase5c4a_explicit_smoke_support import build_context, payload, write_config
import relaylm.client_history_exclusion_apply_v1_prepare as prepare_module
from relaylm.client_history_exclusion_apply_runtime import (
    client_history_exclusion_apply_failure_reason,
)
from relaylm.pipeline_context import consume_active_pipeline_context


def main() -> int:
    private_detail = "private preparation detail"
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        cfg = Path(td) / "cfg.yaml"
        write_config(cfg, dry_run_only=False)
        original = prepare_module.prepare_client_history_exclusion_apply_v1
        prepare_module.prepare_client_history_exclusion_apply_v1 = (
            lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError(private_detail)
            )
        )
        try:
            context, _ = build_context(
                cfg,
                payload([("system", "error case sentinel")]),
            )
        finally:
            prepare_module.prepare_client_history_exclusion_apply_v1 = original

        result = context.client_history_exclusion_apply_result
        assert result is not None and result.status == "blocked"
        assert "client_history_exclusion_apply_preparation_failed" in (
            result.blocked_reasons
        )
        assert client_history_exclusion_apply_failure_reason(result) == (
            "client_history_exclusion_apply_preparation_failed"
        )
        encoded = json.dumps(
            context.node_results_to_log_dicts(),
            ensure_ascii=False,
            sort_keys=True,
        )
        assert private_detail not in encoded
        assert "message_indices" not in encoded
        consume_active_pipeline_context()

    print("relaylm_phase5c4a_error_explicit_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
