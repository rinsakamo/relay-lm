from __future__ import annotations

from pathlib import Path

from tools.v2_cognitive_ir_calibration_host import probe_calibration_git_repository
from tools.v2_cognitive_ir_calibration_v2_host import (
    CalibrationV2HostError,
    CalibrationV2HostResult,
    build_reasoning_off_lmstudio_calibration_v2_client,
    calibration_v2_call_plan,
    probe_lmstudio_native_calibration_binding,
    run_calibration_v2_host,
)


def run_lmstudio_calibration_v2_transaction(
    *,
    base_url: str,
    model: str,
    repository_root: str | Path,
    artifact_root: str | Path,
    api_key: str | None = None,
) -> CalibrationV2HostResult:
    """Run the canonical LM Studio calibration-v2 transaction from fresh observed authority."""

    repository = probe_calibration_git_repository(repository_root)
    if not repository.clean:
        raise CalibrationV2HostError("repository checkout is dirty")

    client = build_reasoning_off_lmstudio_calibration_v2_client(
        base_url=base_url,
        model=model,
        api_key=api_key,
    )
    try:
        binding = probe_lmstudio_native_calibration_binding(
            base_url=base_url,
            model=model,
            api_key=api_key,
        )
        transport = dict(client.transport_identity)
        if transport.get("model") != binding.get("model"):
            raise CalibrationV2HostError(
                "OpenAI-compatible transport model does not match native loaded-model binding"
            )

        identity: dict[str, object] = {
            "repository": {
                "commit": repository.commit,
                "tree": repository.tree,
                "clean_required": True,
            },
            **binding,
            "transport": transport,
            "retry_policy": {"automatic_retry": False, "semantic_retry": False},
            "live_binding_fields": ["model", "model_instance_id", "context_length", "runtime"],
            "call_plan": list(calibration_v2_call_plan()),
        }

        def live_binding_probe() -> dict[str, object]:
            return probe_lmstudio_native_calibration_binding(
                base_url=base_url,
                model=model,
                api_key=api_key,
            )

        return run_calibration_v2_host(
            artifact_root=artifact_root,
            identity=identity,
            repository_root=repository_root,
            live_binding_probe=live_binding_probe,
            client=client,
        )
    finally:
        client.close()


__all__ = ["run_lmstudio_calibration_v2_transaction"]
