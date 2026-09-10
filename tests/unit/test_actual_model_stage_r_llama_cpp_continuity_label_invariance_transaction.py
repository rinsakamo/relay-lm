from __future__ import annotations

import relaylm.actual_model_stage_r_llama_cpp_continuity_label_invariance_transaction as transaction


def test_diagnostic_transaction_selects_only_diagnostic_host(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_main(argv, *, host_module):
        observed["argv"] = argv
        observed["host_module"] = host_module
        return 17

    monkeypatch.setattr(transaction, "_main", fake_main)

    assert transaction.main(["--one-shot"]) == 17
    assert observed == {
        "argv": ["--one-shot"],
        "host_module": transaction.HOST_MODULE,
    }
