from __future__ import annotations

import tools.v1_stage_r_llama_cpp_continuity_label_invariance_wsl as wrapper


def test_diagnostic_wrapper_reuses_fresh_base_wrapper(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_main(argv, *, inner_transaction):
        observed["argv"] = argv
        observed["inner_transaction"] = inner_transaction
        return 23

    monkeypatch.setattr(wrapper._base_wrapper, "main", fake_main)

    assert wrapper.main(["--one-shot"]) == 23
    assert observed == {
        "argv": ["--one-shot"],
        "inner_transaction": wrapper.INNER_TRANSACTION,
    }
