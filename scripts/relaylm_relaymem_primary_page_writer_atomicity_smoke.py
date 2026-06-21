from __future__ import annotations

import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from relaylm.relaymem_primary_page_writer import apply_relaymem_primary_page_write
from relaylm_relaymem_primary_page_writer_smoke import _artifact


def _apply(artifact: dict, root: Path) -> dict:
    return apply_relaymem_primary_page_write(
        writer_handoff_artifact=artifact,
        root_path=str(root),
        enabled=True,
        dry_run_only=False,
        apply_enabled=True,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        parent = root / "memory/mem/primary/projects"
        parent.mkdir(parents=True)
        artifact = _artifact()
        target = root / artifact["handoffs"][0]["target_relative_path"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: _apply(artifact, root), range(2)))
        statuses = sorted(item["status"] for item in results)
        assert statuses == ["already_applied", "applied"]
        assert target.read_bytes() == artifact["handoffs"][0]["page_markdown"].encode("utf-8")
        assert not list(parent.glob(".relaymem-*.tmp"))

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        parent = root / "memory/mem/primary/projects"
        parent.mkdir(parents=True)
        artifact = _artifact()
        target = root / artifact["handoffs"][0]["target_relative_path"]

        with patch(
            "relaylm._relaymem_primary_page_writer_io._supports_secure_dirfd",
            return_value=True,
        ), patch(
            "relaylm._relaymem_primary_page_writer_io.os.link",
            side_effect=OSError("simulated"),
        ):
            result = _apply(artifact, root)
        assert result["status"] == "blocked"
        assert result["blocked_reasons"] == ["primary_page_writer_apply_failed"]
        assert result["writes_memory"] is False
        assert not target.exists()
        assert not list(parent.glob(".relaymem-*.tmp"))

    print("RelayMEM Primary page writer atomicity smoke passed")


if __name__ == "__main__":
    main()
