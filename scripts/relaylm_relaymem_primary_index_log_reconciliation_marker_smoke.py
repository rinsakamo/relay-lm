from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.relaylm_relaymem_primary_index_log_reconciliation_smoke import (
    fixture,
    preflight,
    require,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        receipt, _, index_path, _ = fixture(root)
        first = preflight(root, receipt)
        require(first["status"] == "index_and_log_update_required", first)
        proposed = first["plan"]["index_plan"]["proposed_next_content"]
        exact_line = next(
            line
            for line in proposed.splitlines()
            if "relaymem-primary-index-entry-v0" in line
        )
        prefix = "<!-- relaymem-primary-index-entry-v0 "
        exact_entry = json.loads(exact_line[len(prefix) : -4])

        unrelated = copy.deepcopy(exact_entry)
        unrelated["idempotency_key"] = "2" * 64
        unrelated["page_digest"] = "3" * 64
        unrelated["page_relative_path"] = (
            f"memory/mem/primary/projects/{'2' * 64}.md"
        )
        unrelated["entry_id"] = "4" * 64
        unrelated_payload = json.dumps(
            unrelated,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        index_path.write_text(
            f"# Index\n<!-- relaymem-primary-index-entry-v0 {unrelated_payload} -->\n",
            encoding="utf-8",
        )
        unrelated_result = preflight(root, receipt)
        require(unrelated_result["status"] == "index_conflict", unrelated_result)
        print("ok unrelated marker with forged deterministic identity fails closed")

        noncanonical_payload = json.dumps(exact_entry, ensure_ascii=False)
        index_path.write_text(
            f"# Index\n<!-- relaymem-primary-index-entry-v0 {noncanonical_payload} -->\n",
            encoding="utf-8",
        )
        noncanonical_result = preflight(root, receipt)
        require(noncanonical_result["status"] == "index_conflict", noncanonical_result)
        print("ok noncanonical marker JSON fails closed")

    print("all RelayMEM M3f marker hardening smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
