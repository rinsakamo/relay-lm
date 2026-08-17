from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.continuity import ContinuityContext, ContinuityItem
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import (
    ContinuityRuntime,
    run_user_turn,
    run_user_turn_streaming,
    run_user_turn_streaming_with_retrieval_diagnostics,
    run_user_turn_with_retrieval_diagnostics,
)


def _make_character(root: Path) -> CharacterDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text("# ReLM\n\nBe kind and honest.\n", encoding="utf-8")
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: relm\n  name: ReLM\n",
        encoding="utf-8",
    )
    (root / "memory" / "events.jsonl").write_text("", encoding="utf-8")
    (root / "memory" / "state.json").write_text(
        '{"format_version":1,"states":[]}', encoding="utf-8"
    )
    return CharacterDirectory(root)


def _runtime() -> ContinuityRuntime:
    retained = ContinuityItem(
        item_id="continuity:1:1",
        kind="referent",
        key="draft.current",
        value={"entity": "the blue draft"},
        sources=("accepted-source",),
        epistemic_role="user_assertion",
        accepted_revision=1,
        expires_revision=5,
    )
    return ContinuityRuntime(
        context=ContinuityContext(max_items=3, revision=1, items=(retained,)),
        lifetime_revisions=4,
    )


def _projected_referent(cognitive_input: CognitiveInput) -> bool:
    if len(cognitive_input.context) != 1:
        return False
    item = cognitive_input.context[0]
    try:
        payload = json.loads(item.content)
    except json.JSONDecodeError:
        return False
    return (
        payload
        == {
            "continuity": {
                "epistemic_role": "user_assertion",
                "key": "draft.current",
                "kind": "referent",
                "value": {"entity": "the blue draft"},
            }
        }
        and item.sources == ("accepted-source",)
        and item.actor is None
    )


class _BufferedInspectProvider:
    def __init__(self, runtime: ContinuityRuntime) -> None:
        self.runtime = runtime
        self.calls = 0
        self.inputs: list[CognitiveInput] = []
        self.revisions_during_generation: list[int] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        self.revisions_during_generation.append(self.runtime.context.revision)
        return CognitiveOutput(response="了解。")


class _StreamingInspectProvider:
    def __init__(self, runtime: ContinuityRuntime) -> None:
        self.runtime = runtime
        self.stream_calls = 0
        self.inputs: list[CognitiveInput] = []
        self.revisions_during_stream: list[int] = []

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("streaming evaluation must not call buffered generate")

    async def stream_generate(self, cognitive_input: CognitiveInput, emit) -> CognitiveOutput:
        self.stream_calls += 1
        self.inputs.append(cognitive_input)
        self.revisions_during_stream.append(self.runtime.context.revision)
        await emit("了解")
        self.revisions_during_stream.append(self.runtime.context.revision)
        await emit("。")
        return CognitiveOutput(response="了解。")


async def evaluate_continuity_cognition_wiring() -> EvaluationScenarioResult:
    projected_observations: list[bool] = []
    post_revisions: list[int] = []

    with TemporaryDirectory(prefix="relaylm-eval-continuity-cognition-buffered-") as temp:
        runtime = _runtime()
        provider = _BufferedInspectProvider(runtime)
        await run_user_turn(
            character=_make_character(Path(temp)),
            provider=provider,
            content="その続きはどうする？",
            continuity_runtime=runtime,
        )
        buffered_projected = _projected_referent(provider.inputs[0])
        projected_observations.append(buffered_projected)
        post_revisions.append(runtime.context.revision)
        buffered_generation_revision = provider.revisions_during_generation[0]
        buffered_calls = provider.calls

    with TemporaryDirectory(prefix="relaylm-eval-continuity-cognition-diag-") as temp:
        runtime = _runtime()
        provider = _BufferedInspectProvider(runtime)
        diagnostic_result = await run_user_turn_with_retrieval_diagnostics(
            character=_make_character(Path(temp)),
            provider=provider,
            content="その続きはどうする？",
            continuity_runtime=runtime,
        )
        diagnostic_projected = _projected_referent(provider.inputs[0])
        projected_observations.append(diagnostic_projected)
        post_revisions.append(runtime.context.revision)
        diagnostic_generation_revision = provider.revisions_during_generation[0]
        diagnostic_calls = provider.calls
        diagnostic_enabled_layers = diagnostic_result.retrieval.aggregate.enabled_layer_count

    with TemporaryDirectory(prefix="relaylm-eval-continuity-cognition-stream-") as temp:
        runtime = _runtime()
        provider = _StreamingInspectProvider(runtime)
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        await run_user_turn_streaming(
            character=_make_character(Path(temp)),
            provider=provider,
            content="その続きはどうする？",
            emit_response_delta=emit,
            continuity_runtime=runtime,
        )
        streaming_projected = _projected_referent(provider.inputs[0])
        projected_observations.append(streaming_projected)
        post_revisions.append(runtime.context.revision)
        streaming_revisions = tuple(provider.revisions_during_stream)
        streaming_calls = provider.stream_calls
        streaming_text = "".join(emitted)

    with TemporaryDirectory(prefix="relaylm-eval-continuity-cognition-stream-diag-") as temp:
        runtime = _runtime()
        provider = _StreamingInspectProvider(runtime)
        emitted = []

        async def emit_diagnostic(text: str) -> None:
            emitted.append(text)

        streaming_diagnostic_result = (
            await run_user_turn_streaming_with_retrieval_diagnostics(
                character=_make_character(Path(temp)),
                provider=provider,
                content="その続きはどうする？",
                emit_response_delta=emit_diagnostic,
                continuity_runtime=runtime,
            )
        )
        streaming_diagnostic_projected = _projected_referent(provider.inputs[0])
        projected_observations.append(streaming_diagnostic_projected)
        post_revisions.append(runtime.context.revision)
        streaming_diagnostic_revisions = tuple(provider.revisions_during_stream)
        streaming_diagnostic_calls = provider.stream_calls
        streaming_diagnostic_layers = (
            streaming_diagnostic_result.retrieval.aggregate.enabled_layer_count
        )

    checks = (
        EvaluationCheck(
            check_id="buffered_provider_sees_pre_generation_continuity",
            boundary="turn_runtime",
            passed=(
                buffered_calls == 1
                and buffered_projected
                and buffered_generation_revision == 1
                and post_revisions[0] == 2
            ),
            expected=True,
            observed=buffered_projected,
        ),
        EvaluationCheck(
            check_id="buffered_diagnostics_uses_same_continuity_snapshot",
            boundary="turn_runtime",
            passed=(
                diagnostic_calls == 1
                and diagnostic_projected
                and diagnostic_generation_revision == 1
                and post_revisions[1] == 2
                and diagnostic_enabled_layers == 0
            ),
            expected=True,
            observed=diagnostic_projected,
        ),
        EvaluationCheck(
            check_id="streaming_keeps_snapshot_stable_until_completion",
            boundary="turn_runtime",
            passed=(
                streaming_calls == 1
                and streaming_projected
                and streaming_revisions == (1, 1)
                and post_revisions[2] == 2
                and streaming_text == "了解。"
            ),
            expected=True,
            observed=streaming_revisions == (1, 1),
        ),
        EvaluationCheck(
            check_id="streaming_diagnostics_uses_same_continuity_snapshot",
            boundary="turn_runtime",
            passed=(
                streaming_diagnostic_calls == 1
                and streaming_diagnostic_projected
                and streaming_diagnostic_revisions == (1, 1)
                and post_revisions[3] == 2
                and streaming_diagnostic_layers == 0
            ),
            expected=True,
            observed=streaming_diagnostic_projected,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="continuity_cognition_wiring",
        checks=checks,
        metrics={
            "ordinary_turn_variant_count": 4,
            "buffered_provider_call_count": buffered_calls + diagnostic_calls,
            "stream_provider_call_count": streaming_calls + streaming_diagnostic_calls,
            "projected_continuity_observation_count": sum(projected_observations),
            "post_generation_revision_count": sum(revision == 2 for revision in post_revisions),
        },
    )
