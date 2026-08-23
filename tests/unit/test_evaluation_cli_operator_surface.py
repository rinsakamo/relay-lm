from __future__ import annotations

import sys

from relaylm import evaluation


class _PassingReport:
    status = "pass"

    def to_json(self) -> str:
        return '{"status":"pass"}'


def test_relaylm_eval_rejects_unsupported_arguments_before_running_suite(
    monkeypatch,
    capsys,
) -> None:
    suite_called = False

    async def fake_run_native_evaluation() -> _PassingReport:
        nonlocal suite_called
        suite_called = True
        return _PassingReport()

    unsafe_argument = "--unknown\nforged-status: pass\x1b[2J"
    monkeypatch.setattr(evaluation, "run_native_evaluation", fake_run_native_evaluation)
    monkeypatch.setattr(sys, "argv", ["relaylm-eval", unsafe_argument])

    code = evaluation.main()

    captured = capsys.readouterr()
    assert code == 2
    assert suite_called is False
    assert captured.out == ""
    assert "\x1b" not in captured.err
    assert "\nforged-status: pass" not in captured.err
    assert r"--unknown\nforged-status: pass\x1b[2J" in captured.err
