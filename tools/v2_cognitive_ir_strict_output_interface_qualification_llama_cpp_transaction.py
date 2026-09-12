from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
import sys

import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction as legacy
from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    freeze_consumer_identity,
)
from relaylm.v2_cognitive_ir_strict_output_interface_qualification import (
    ARCHITECTURE_CONSEQUENCE,
    CASE_COUNT,
    CITABLE_FOR_REPRESENTATION_CLAIM,
    INPUT_TOKEN_REQUESTS,
    SEMANTIC_COMPLETIONS,
    preregistered_case_seeds,
)
from relaylm.v2_cognitive_ir_strict_output_interface_qualification_physical import (
    CLAIM,
    validate_physical_adapter_binding,
)
from tools.v2_cognitive_ir_s2_host import probe_s2_git_repository
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    probe_llama_cpp_selected_s2_binding as selected_binding_probe,
)
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    run_llama_cpp_shared_floor_calibration as legacy_runner,
)
from tools.v2_cognitive_ir_strict_output_interface_qualification_llama_cpp import (
    StrictOutputInputCounterPreflight,
    StrictOutputInterfaceLlamaCppRun,
    preflight_strict_output_input_counter,
    run_llama_cpp_strict_output_interface_qualification,
)


class StrictOutputInterfaceTransactionError(RuntimeError):
    """The #2748 E4-IFQ1 transaction adapter cannot bind the frozen probe."""


def _argv_value(
    argv: Sequence[str],
    name: str,
    *,
    default: str | None,
) -> str | None:
    values = list(argv)
    prefix = f"{name}="
    for index, item in enumerate(values):
        if item.startswith(prefix):
            return item[len(prefix) :]
        if item == name:
            if index + 1 >= len(values):
                raise StrictOutputInterfaceTransactionError(
                    f"missing value for {name}"
                )
            return values[index + 1]
    return default


def _prepare_consumer_identity(
    *,
    repository_commit: str,
    repository_tree: str,
    model: str,
    runtime_attestation: Mapping[str, object],
    base_url: str,
):
    counter_preflight = preflight_strict_output_input_counter(
        base_url=base_url,
        model=model,
    )
    if (
        counter_preflight.request_attempts != 2
        or counter_preflight.request_completions != 2
    ):
        raise StrictOutputInterfaceTransactionError(
            "IFQ1 structured input-counter preflight did not complete 2/2 requests"
        )
    identity = freeze_consumer_identity(
        repository_commit=repository_commit,
        repository_tree=repository_tree,
        model=model,
        runtime_attestation=runtime_attestation,
    )
    return identity, counter_preflight


def _finalize_artifacts(
    *,
    artifact_root: Path,
    run: StrictOutputInterfaceLlamaCppRun,
    counter_preflight: StrictOutputInputCounterPreflight,
    end_binding_stable: bool,
    final_binding_error: str | None,
) -> None:
    result = asdict(run.result)
    if not end_binding_stable and run.provider_attempts > 0:
        result.update(
            {
                "classification": "QUALIFICATION_INCOMPLETE",
                "completed": False,
                "failure": final_binding_error
                or "final runtime/material binding drifted",
            }
        )
    legacy._write_json(
        artifact_root / "strict-output-interface-qualification-result.json",
        result,
    )
    legacy._write_json(
        artifact_root / "strict-output-interface-qualification-receipt.json",
        {
            "provider_attempts": run.provider_attempts,
            "provider_completions": run.provider_completions,
            "input_count_attempts": run.input_count_attempts,
            "input_count_completions": run.input_count_completions,
            "live_binding_checks": run.live_binding_checks,
            "preflight_input_token_requests": asdict(counter_preflight),
            "end_binding_stable": end_binding_stable,
            "final_binding_error": final_binding_error,
            "semantic_retry": 0,
            "replay": 0,
            "reseed": 0,
            "fallback": 0,
            "hidden_repair": 0,
            "judge": 0,
        },
    )


def main(argv: Sequence[str] | None = None) -> int:
    validate_physical_adapter_binding()
    if legacy.run_llama_cpp_shared_floor_calibration is not legacy_runner:
        raise StrictOutputInterfaceTransactionError(
            "legacy shared-floor transaction runner binding drifted"
        )
    if legacy.probe_llama_cpp_selected_s2_binding is not selected_binding_probe:
        raise StrictOutputInterfaceTransactionError(
            "legacy runtime-binding probe drifted"
        )

    effective_argv = list(sys.argv[1:] if argv is None else argv)
    repo_root = Path(
        _argv_value(effective_argv, "--repo-root", default=".") or "."
    ).resolve()

    captured: dict[str, object] = {}
    original_fresh_root = legacy._fresh_artifact_root
    original_probe = legacy.probe_llama_cpp_selected_s2_binding

    def capture_artifact_root(value: str | None) -> Path:
        root = original_fresh_root(value)
        captured["artifact_root"] = root
        return root

    def finalize_from_end_binding(
        *,
        binding: Mapping[str, object] | None,
        error: str | None,
    ) -> None:
        run = captured.get("run")
        artifact_root = captured.get("artifact_root")
        counter_preflight = captured.get("counter_preflight")
        start = captured.get("start_binding")
        if (
            not isinstance(run, StrictOutputInterfaceLlamaCppRun)
            or not isinstance(artifact_root, Path)
            or not isinstance(counter_preflight, StrictOutputInputCounterPreflight)
            or not isinstance(start, Mapping)
        ):
            return
        stable = (
            binding is not None
            and legacy._canonical(binding) == legacy._canonical(start)
        )
        _finalize_artifacts(
            artifact_root=artifact_root,
            run=run,
            counter_preflight=counter_preflight,
            end_binding_stable=stable,
            final_binding_error=error,
        )

    def capture_binding(**kwargs):
        if "start_binding" not in captured:
            binding = original_probe(**kwargs)
            captured["start_binding"] = binding
            return binding
        try:
            binding = original_probe(**kwargs)
        except Exception as exc:
            finalize_from_end_binding(
                binding=None,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        captured["end_binding"] = binding
        finalize_from_end_binding(binding=binding, error=None)
        return binding

    def strict_output_runner(
        *,
        base_url: str,
        model: str,
        before_call=None,
    ):
        binding = captured.get("start_binding")
        if not isinstance(binding, Mapping):
            raise StrictOutputInterfaceTransactionError(
                "runtime identity was not frozen before IFQ1 runner entry"
            )
        runtime_attestation = binding.get("runtime_attestation")
        if not isinstance(runtime_attestation, Mapping):
            raise StrictOutputInterfaceTransactionError(
                "runtime attestation is missing before IFQ1 material boundary"
            )

        repository = probe_s2_git_repository(repo_root)
        if not repository.clean:
            raise StrictOutputInterfaceTransactionError(
                "IFQ1 requires a clean repository checkout"
            )

        identity, counter_preflight = _prepare_consumer_identity(
            repository_commit=repository.commit,
            repository_tree=repository.tree,
            model=model,
            runtime_attestation=runtime_attestation,
            base_url=base_url,
        )
        captured["frozen_consumer_identity"] = identity
        captured["counter_preflight"] = counter_preflight

        artifact_root = captured.get("artifact_root")
        if not isinstance(artifact_root, Path):
            raise StrictOutputInterfaceTransactionError(
                "fresh IFQ1 artifact root was not captured"
            )
        legacy._write_json(
            artifact_root / "strict-output-interface-qualification-manifest.json",
            {
                "claim": CLAIM,
                "citable_for_representation_claim": (
                    CITABLE_FOR_REPRESENTATION_CLAIM
                ),
                "architecture_consequence": ARCHITECTURE_CONSEQUENCE,
                "frozen_consumer_identity": asdict(identity),
                "case_count": CASE_COUNT,
                "semantic_completions": SEMANTIC_COMPLETIONS,
                "scientific_input_token_requests": INPUT_TOKEN_REQUESTS,
                "preregistered_seed_identities": list(preregistered_case_seeds()),
                "material_generation_boundary": (
                    "after_live_runtime_and_structured_counter_preflight_freeze"
                ),
            },
        )

        run = run_llama_cpp_strict_output_interface_qualification(
            base_url=base_url,
            model=model,
            frozen_identity=identity,
            before_call=before_call,
        )
        captured["run"] = run
        return run

    saved = {
        "runner": legacy.run_llama_cpp_shared_floor_calibration,
        "claim": legacy.SHARED_FLOOR_CLAIM,
        "citable": legacy.SHARED_FLOOR_CITABLE,
        "architecture": legacy.SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE,
        "incomplete": legacy.CALIBRATION_INCOMPLETE,
        "max_semantic": legacy.SHARED_FLOOR_MAX_SEMANTIC_CALLS,
        "max_input": legacy.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
        "per_candidate_input": (
            legacy.SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY
        ),
        "fresh_root": legacy._fresh_artifact_root,
        "probe": legacy.probe_llama_cpp_selected_s2_binding,
    }
    legacy.run_llama_cpp_shared_floor_calibration = strict_output_runner
    legacy.SHARED_FLOOR_CLAIM = CLAIM
    legacy.SHARED_FLOOR_CITABLE = CITABLE_FOR_REPRESENTATION_CLAIM
    legacy.SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE = ARCHITECTURE_CONSEQUENCE
    legacy.CALIBRATION_INCOMPLETE = "QUALIFICATION_INCOMPLETE"
    legacy.SHARED_FLOOR_MAX_SEMANTIC_CALLS = SEMANTIC_COMPLETIONS
    legacy.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS = INPUT_TOKEN_REQUESTS
    legacy.SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY = INPUT_TOKEN_REQUESTS
    legacy._fresh_artifact_root = capture_artifact_root
    legacy.probe_llama_cpp_selected_s2_binding = capture_binding
    try:
        return legacy.main(effective_argv)
    finally:
        legacy.run_llama_cpp_shared_floor_calibration = saved["runner"]
        legacy.SHARED_FLOOR_CLAIM = saved["claim"]
        legacy.SHARED_FLOOR_CITABLE = saved["citable"]
        legacy.SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE = saved["architecture"]
        legacy.CALIBRATION_INCOMPLETE = saved["incomplete"]
        legacy.SHARED_FLOOR_MAX_SEMANTIC_CALLS = saved["max_semantic"]
        legacy.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS = saved["max_input"]
        legacy.SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY = saved[
            "per_candidate_input"
        ]
        legacy._fresh_artifact_root = saved["fresh_root"]
        legacy.probe_llama_cpp_selected_s2_binding = saved["probe"]


if __name__ == "__main__":
    raise SystemExit(main())
