from __future__ import annotations

import inspect
import json
from pathlib import Path

import relaylm.actual_model_stage_r_llama_cpp_production_unresolved_no_pass1_no_accepted_continuity as host
import relaylm.actual_model_stage_r_llama_cpp_production_unresolved_no_pass1_no_accepted_continuity_transaction as selector
import relaylm.actual_model_stage_r_llama_cpp_two_turn_diagnostic as carriage
import tools.v1_stage_r_llama_cpp_production_unresolved_no_pass1_no_accepted_continuity_wsl as wrapper


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_strategy_reuses_generic_two_turn_carriage() -> None:
    assert issubclass(
        host.ProductionUnresolvedNoPass1NoAcceptedContinuityLlamaProvider,
        carriage.TwoTurnDiagnosticLlamaProvider,
    )
    assert host.run_two_turn_diagnostic_host is carriage.run_two_turn_diagnostic_host

    source = inspect.getsource(
        host.ProductionUnresolvedNoPass1NoAcceptedContinuityLlamaProvider
    )
    assert (
        "build_unresolved_no_pass1_no_accepted_continuity_request_body("
        in source
    )
    assert "body=prepared.treatment_overlay_body" in source
    assert (
        "parse_unresolved_no_pass1_no_accepted_continuity_completion("
        in source
    )
    assert "prepared.baseline.no_pass1_body" in source
    assert "prepared.baseline.no_pass1_overlay_body" in source
    assert "prepared.treatment_body" in source
    assert "prepared.treatment_overlay_body" in source
    assert "prepared.diff_receipt" in source
    assert '"continuity_expectation_supplied": False' in source
    assert '"pass1_response_component_supplied": False' in source
    assert (
        '"accepted_continuity_context_supplied_to_treatment": False'
        in source
    )

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


def test_zero_counts_remain_unspent_before_host_execution() -> None:
    counts = host._zero_counts()
    assert counts["semantic_generation_count"] == 0
    assert counts["t1_pass1_generation_count"] == 0
    assert counts["t1_pass2_generation_count"] == 0
    assert counts["t2_pass1_generation_count"] == 0
    assert counts["t2_diagnostic_pass2_generation_count"] == 0
    assert (
        counts[
            "t2_unresolved_no_pass1_no_accepted_continuity_pass2_generation_count"
        ]
        == 0
    )
    assert counts["formation_generation_count"] == 0
    assert counts["t3_generation_count"] == 0
    assert counts["semantic_retry_count"] == 0
    assert counts["replay_count"] == 0
    assert counts["reseed_count"] == 0
    assert counts["fallback_count"] == 0
    assert counts["fastcal_count"] == 0
    assert counts["lm_studio_contact_count"] == 0
    assert counts["repository_mutation_count"] == 0


def test_selector_forwards_only_retained_artifact_to_named_host(
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


def test_wrapper_is_only_a_thin_v1_forwarder(tmp_path: Path, monkeypatch) -> None:
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


def test_shared_physical_registry_selects_the_thin_v1_adapter() -> None:
    registry = json.loads(
        (REPOSITORY_ROOT / ".ai" / "physical" / "llama_cpp_targets.json").read_text(
            encoding="utf-8"
        )
    )
    target = registry[
        "targets"
    ]["v1:unresolved-no-pass1-no-accepted-continuity"]
    assert target == {
        "branch": "v1",
        "module": (
            "tools.v1_stage_r_llama_cpp_production_unresolved_no_pass1_"
            "no_accepted_continuity_wsl"
        ),
        "description": (
            "Repository-owned v1 unresolved-only no-Pass1 no-accepted-Continuity "
            "discriminator wrapper from #2715."
        ),
        "required_distributions": ["httpx"],
    }


def test_v1_specialization_does_not_duplicate_shared_runner_logic() -> None:
    source = "\n".join(
        (
            inspect.getsource(host),
            inspect.getsource(selector),
            inspect.getsource(wrapper),
        )
    )
    for forbidden in (
        "QueueConfig(",
        "run_queued_command(",
        "reexec_into_environment(",
        "verify_current_environment(",
        "git ls-remote",
        "nvidia-smi",
        "subprocess.Popen(",
        "fcntl.flock(",
    ):
        assert forbidden not in source
