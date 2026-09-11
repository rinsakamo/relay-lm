from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import v2_cognitive_ir_p2_boundedness_qual_v2_entry as entry
from tools import v2_cognitive_ir_p2_boundedness_qual_v2_wsl as wsl


def _argv(summary_path: Path) -> list[str]:
    return ["--summary-path", str(summary_path)]


def test_entry_returns_zero_only_for_qualified_zero_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary_path = tmp_path / "summary.json"

    def fake_main(argv: list[str]) -> int:
        summary_path.write_text(
            json.dumps({"classification": "P2_BOUNDEDNESS_QUALIFIED_V2", "transaction_exit_code": 0}),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(entry.transaction, "main", fake_main)
    assert entry.main(_argv(summary_path)) == 0


def test_entry_fails_closed_for_incomplete_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary_path = tmp_path / "summary.json"

    def fake_main(argv: list[str]) -> int:
        summary_path.write_text(
            json.dumps({"classification": "P2_BOUNDEDNESS_QUALIFICATION_V2_INCOMPLETE", "transaction_exit_code": 2}),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(entry.transaction, "main", fake_main)
    assert entry.main(_argv(summary_path)) == 2


def test_wsl_launcher_routes_to_new_fail_closed_entrypoint() -> None:
    assert wsl.INNER_TRANSACTION_MODULE == "tools.v2_cognitive_ir_p2_boundedness_qual_v2_entry"
