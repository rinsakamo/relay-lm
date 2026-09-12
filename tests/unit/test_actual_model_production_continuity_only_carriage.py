from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

import pytest

import relaylm.actual_model_stage_r_llama_cpp_production_continuity_only as host
import relaylm.actual_model_stage_r_llama_cpp_production_continuity_only_transaction as selector
import relaylm.actual_model_stage_r_llama_cpp_production_continuity_overlay as legacy_host
import relaylm.actual_model_stage_r_llama_cpp_two_turn_diagnostic as carriage
import tools.v1_llama_cpp_controller_preflight as controller_preflight
import tools.v1_stage_r_llama_cpp_production_continuity_only_wsl as wrapper

from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.events import Event
from relaylm.identity import Identity


def test_zero_counts_bound_the_continuity_only_transaction() -> None:
    counts = host._zero_counts()
    assert counts["semantic_generation_count"] == 0
    assert counts["t1_pass1_generation_count"] == 0
    assert counts["t1_pass2_generation_count"] == 0
    assert counts["t2_pass1_generation_count"] == 0
    assert counts["t2_diagnostic_pass2_generation_count"] == 0
    assert counts["t2_continuity_only_pass2_generation_count"] == 0
    assert counts["formation_generation_count"] == 0
    assert counts["t3_generation_count"] == 0
    assert counts["semantic_retry_count"] == 0
    assert counts["replay_count"] == 0
    assert counts["reseed_count"] == 0
    assert counts["fallback_count"] == 0
    assert counts["fastcal_count"] == 0
    assert counts["lm_studio_contact_count"] == 0
    assert counts["repository_mutation_count"] == 0


def test_continuity_only_and_legacy_overlay_share_one_carriage_core() -> None:
    assert issubclass(
        host.ProductionContinuityOnlyLlamaProvider,
        carriage.TwoTurnDiagnosticLlamaProvider,
    )
    assert issubclass(
        legacy_host.ProductionContinuityOverlayLlamaProvider,
        carriage.TwoTurnDiagnosticLlamaProvider,
    )
    assert host.run_two_turn_diagnostic_host is carriage.run_two_turn_diagnostic_host
    assert (
        legacy_host.run_two_turn_diagnostic_host
        is carriage.run_two_turn_diagnostic_host
    )


def test_continuity_only_strategy_uses_merged_builder_body_and_parser() -> None:
    source = inspect.getsource(host.ProductionContinuityOnlyLlamaProvider)
    assert "build_continuity_only_extraction_request_body(" in source
    assert "body=prepared.continuity_only_overlay_body" in source
    assert "parse_continuity_only_completion(" in source
    assert "prepared.production_body" in source
    assert "prepared.production_overlay_body" in source
    assert "prepared.continuity_only_body" in source
    assert "prepared.diff_receipt" in source

    for forbidden in (
        ".replace(",
        "re.sub(",
        "setattr(",
        "sys.modules",
        "sys.meta_path",
        "blue_box",
        "box_contents_question",
    ):
        assert forbidden not in source


def test_continuity_only_provider_rejects_a_third_extraction_without_generation() -> None:
    provider = object.__new__(host.ProductionContinuityOnlyLlamaProvider)
    provider.extraction_call_count = 2
    cognitive_input = CognitiveInput(
        identity=Identity("Synthetic."),
        state_classes={},
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "x"},
            event_id="evt",
            timestamp="2026-01-01T00:00:00+00:00",
        ),
    )
    extraction = CognitionExtractionInput(
        cognitive_input=cognitive_input,
        assistant_response="y",
    )

    with pytest.raises(Exception, match="exactly two extraction calls"):
        asyncio.run(provider.generate_extraction(extraction))


def test_selector_forwards_retained_artifact_to_named_host(
    tmp_path: Path,
    monkeypatch,
) -> None:
    retained = tmp_path / "retained.json"
    retained.write_text("{}", encoding="utf-8")
    observed: dict[str, object] = {}

    def fake_run_transaction(
        argv,
        *,
        host_module,
        host_summary_filename,
        host_args,
    ) -> int:
        observed.update(
            argv=list(argv),
            host_module=host_module,
            host_summary_filename=host_summary_filename,
            host_args=tuple(host_args),
        )
        return 17

    monkeypatch.setattr(selector, "run_transaction", fake_run_transaction)
    rc = selector.main(
        [
            "--retained-formation-artifact",
            str(retained),
            "--origin",
            "http://127.0.0.1:1234",
        ]
    )

    assert rc == 17
    assert observed["host_module"] == selector.HOST_MODULE
    assert observed["host_summary_filename"] == selector.HOST_SUMMARY_FILENAME
    assert observed["host_args"] == (
        "--retained-formation-artifact",
        str(retained.resolve()),
    )
    assert observed["argv"] == ["--origin", "http://127.0.0.1:1234"]


def test_wrapper_forwards_only_explicit_retained_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    retained = tmp_path / "retained.json"
    observed: dict[str, object] = {}

    def fake_run_wsl_transaction(argv, *, inner_transaction, inner_args) -> int:
        observed.update(
            argv=list(argv),
            inner_transaction=inner_transaction,
            inner_args=tuple(inner_args),
        )
        return 23

    monkeypatch.setattr(wrapper, "run_wsl_transaction", fake_run_wsl_transaction)
    rc = wrapper.main(["--retained-formation-artifact", str(retained)])

    assert rc == 23
    assert observed["argv"] == []
    assert observed["inner_transaction"] == wrapper.INNER_TRANSACTION
    assert observed["inner_args"] == (
        "--retained-formation-artifact",
        str(retained.resolve()),
    )


def test_controller_preflight_can_emit_exact_continuity_only_command() -> None:
    command = controller_preflight.one_shot_command(
        "tools.v1_stage_r_llama_cpp_production_continuity_only_wsl",
        executable="/venv/bin/python",
        wrapper_args=("--retained-formation-artifact", "/tmp/retained.json"),
    )
    assert command == [
        "/venv/bin/python",
        "-m",
        "tools.v1_stage_r_llama_cpp_production_continuity_only_wsl",
        "--retained-formation-artifact",
        "/tmp/retained.json",
    ]


def test_host_source_has_no_model_answer_or_runtime_substitution() -> None:
    source = inspect.getsource(host) + inspect.getsource(carriage)
    forbidden = (
        "blue_box",
        "box_contents_question",
        "setattr(",
        "sys.modules",
        "sys.meta_path",
        "importlib",
    )
    for value in forbidden:
        assert value not in source

    assert json.loads('{"continuity_candidates":[]}') == {
        "continuity_candidates": []
    }
