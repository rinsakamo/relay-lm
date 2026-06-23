from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.relaymem_primary_pipeline import (
    execute_relaymem_primary_pipeline,
    project_relaymem_primary_pipeline,
)
from relaylm_relaymem_primary_pipeline_smoke import (
    create_request,
    prepare_store,
    require,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        prepare_store(root)

        invalid_disabled, _ = create_request(
            root,
            enabled=False,
            dry_run_only=True,
            apply_enabled=False,
        )
        object.__setattr__(invalid_disabled, "dry_run_only", False)
        invalid = execute_relaymem_primary_pipeline(invalid_disabled)
        require(invalid.status == "invalid_input", invalid.to_log_dict())
        require(
            invalid.reason_ids == ("primary_pipeline_gate_mode_invalid",),
            invalid.to_log_dict(),
        )

        request, _ = create_request(
            root,
            dry_run_only=True,
            apply_enabled=False,
        )
        result = execute_relaymem_primary_pipeline(request)
        require(result.status == "dry_run_ready", result.to_log_dict())

        object.__setattr__(
            result,
            "stage_results",
            tuple(reversed(result.stage_results)),
        )
        try:
            project_relaymem_primary_pipeline(result)
        except ValueError as exc:
            require(str(exc) == "primary pipeline stage order invalid", str(exc))
        else:
            raise AssertionError("impossible stage order accepted")

    print("RelayMEM Primary pipeline result validation smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
