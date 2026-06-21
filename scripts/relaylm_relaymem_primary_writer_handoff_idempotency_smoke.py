from __future__ import annotations

import json
import tempfile
from hashlib import sha256
from pathlib import Path

from relaylm.relaymem_primary_writer_handoff import (
    build_relaymem_primary_writer_handoff_preflight,
)
from relaylm_relaymem_primary_writer_handoff_smoke import _artifact


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "memory/mem/primary/projects").mkdir(parents=True)

        artifact = _artifact()
        page = artifact["page_candidates"][0]
        forged_key = "f" * 64
        page["idempotency_key"] = forged_key
        page["target_relative_path"] = (
            f"memory/mem/primary/projects/{forged_key}.md"
        )
        page["page_markdown"] = page["page_markdown"].replace(
            next(
                line
                for line in page["page_markdown"].splitlines()
                if line.startswith("idempotency_key: ")
            ),
            f"idempotency_key: {json.dumps(forged_key)}",
        )
        encoded = page["page_markdown"].encode("utf-8")
        page["page_bytes"] = len(encoded)
        page["page_digest"] = sha256(encoded).hexdigest()

        result = build_relaymem_primary_writer_handoff_preflight(
            page_candidate_artifact=artifact,
            root_path=str(root),
            enabled=True,
        )
        assert result["handoff_count"] == 0
        assert result["page_candidate_valid"] is False
        assert result["blocked_reasons"] == [
            "primary_page_candidate_idempotency_key_mismatch"
        ]
        assert result["projection"]["blocked_reasons"] == [
            "primary_page_candidate_idempotency_key_mismatch"
        ]
        assert forged_key not in str(result["projection"])

    print("RelayMEM Primary writer handoff idempotency smoke passed")


if __name__ == "__main__":
    main()
