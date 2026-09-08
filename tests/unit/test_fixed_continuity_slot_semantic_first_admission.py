from __future__ import annotations

import asyncio
from types import SimpleNamespace

from relaylm import actual_model_stage_r_lm_studio_fixed_continuity_slots as diagnostic
from relaylm.actual_model_stage_r_lm_studio_semantic_first import (
    _declared_reasoning_capability,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
)


def test_fixed_slot_runner_does_not_require_generic_structured_output_attestation(
    monkeypatch,
    tmp_path,
) -> None:
    reached_semantic_sequence = False

    class FakeProvider:
        def __init__(self, *args, **kwargs) -> None:
            self.decoding_capabilities = OpenAICompatibleDecodingCapabilities(
                supported_controls=frozenset({"temperature", "top_p"})
            )
            self.vllm_reasoning_capability = None
            self.lm_studio_reasoning_capability = kwargs[
                "lm_studio_reasoning_capability"
            ]
            self.completion_observation_artifacts = []
            self.slot_observation_artifacts = []

        async def aclose(self) -> None:
            return None

    async def fake_run_fail_fast_sequence(*, scenario_ids, execute):
        nonlocal reached_semantic_sequence
        reached_semantic_sequence = True
        assert scenario_ids == ("scenario",)
        return [], None

    monkeypatch.setattr(diagnostic, "FixedContinuitySlotDiagnosticProvider", FakeProvider)
    monkeypatch.setattr(
        diagnostic,
        "describe_openai_compatible_provider",
        lambda provider: SimpleNamespace(
            adapter_identity="fake-adapter",
            effective_decoding_configuration={},
            provider_capabilities=(),
        ),
    )
    monkeypatch.setattr(diagnostic, "_git_head", lambda repo_root: "head")
    monkeypatch.setattr(
        diagnostic,
        "character_fixture_revision",
        lambda fixture_root: "fixture-revision",
    )
    monkeypatch.setattr(
        diagnostic,
        "ActualModelRunManifest",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(
        diagnostic,
        "_run_fail_fast_sequence",
        fake_run_fail_fast_sequence,
    )

    authority = SimpleNamespace(
        temperature=0,
        top_p=1,
        seed=None,
        continuity_runtime=SimpleNamespace(),
        execution_path="buffered",
        cognition_execution=SimpleNamespace(),
        scenario_ids=("scenario",),
        authority_id="stage-r-current-v1",
        scenario_set_revision="scenario-revision",
        reasoning_preference="off",
        pass_requests=lambda reasoning_mode: (),
    )
    scenario_set = SimpleNamespace(
        character_fixture_id="fixture",
        scenario_set_version="foundation-v3",
    )
    reasoning_capability = _declared_reasoning_capability(
        request_model="gemma",
        loaded_instance_id="gemma",
        reasoning_options="off,on",
        reasoning_default="on",
    )

    summary = asyncio.run(
        diagnostic._run_stage_r(
            repo_root=tmp_path,
            provider_base_url="http://lm.test/v1",
            request_model="gemma",
            loaded_instance_id="gemma",
            model_artifact="model.gguf",
            tokenizer_identity="tokenizer",
            context_window=8192,
            workspace_root=tmp_path / "workspace",
            artifact_root=tmp_path / "artifacts",
            replicate_id="0",
            api_key_env=None,
            authority=authority,
            scenario_set=scenario_set,
            reasoning_capability=reasoning_capability,
            binding={},
        )
    )

    assert reached_semantic_sequence is True
    assert summary["executions"] == []
    assert summary["stop_reason"] is None
