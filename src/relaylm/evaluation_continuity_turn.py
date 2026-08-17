from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.continuity import ContinuityCandidate, ContinuityContext
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.storage.filesystem import CharacterDirectory
from relaylm.turn import ContinuityRuntime, run_user_turn, run_user_turn_streaming


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


class _BufferedProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(
            response="その案の続きを見よう。",
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="referent",
                    key="draft.current",
                    value="the current draft",
                    sources=(cognitive_input.input.id,),
                    epistemic_role="assistant_inference",
                ),
            ),
        )


class _EmptyProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(response="了解。")


class _StreamingProvider:
    def __init__(self, runtime: ContinuityRuntime) -> None:
        self.runtime = runtime
        self.stream_calls = 0
        self.revisions_during_stream: list[int] = []

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("streaming evaluation must not call buffered generate")

    async def stream_generate(self, cognitive_input: CognitiveInput, emit) -> CognitiveOutput:
        self.stream_calls += 1
        self.revisions_during_stream.append(self.runtime.context.revision)
        await emit("続きを")
        self.revisions_during_stream.append(self.runtime.context.revision)
        await emit("進めよう。")
        return CognitiveOutput(
            response="続きを進めよう。",
            continuity_candidates=(
                ContinuityCandidate.set(
                    kind="active_task",
                    key="task.current",
                    value="continue the draft",
                    sources=(cognitive_input.input.id,),
                    epistemic_role="assistant_commitment",
                ),
            ),
        )


async def evaluate_continuity_turn() -> EvaluationScenarioResult:
    with TemporaryDirectory(prefix="relaylm-eval-continuity-buffered-") as temp:
        root = Path(temp)
        character = _make_character(root)
        buffered_provider = _BufferedProvider()
        buffered_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=2),
            lifetime_revisions=3,
        )
        buffered_result = await run_user_turn(
            character=character,
            provider=buffered_provider,
            content="この案の続きを見よう",
            continuity_runtime=buffered_runtime,
        )
        buffered_actors = tuple(
            event.actor for event in CharacterDirectory(root).iter_events()
        )

    with TemporaryDirectory(prefix="relaylm-eval-continuity-stream-") as temp:
        root = Path(temp)
        character = _make_character(root)
        stream_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=2),
            lifetime_revisions=3,
        )
        stream_provider = _StreamingProvider(stream_runtime)
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        stream_result = await run_user_turn_streaming(
            character=character,
            provider=stream_provider,
            content="この作業を続けよう",
            emit_response_delta=emit,
            continuity_runtime=stream_runtime,
        )

    with TemporaryDirectory(prefix="relaylm-eval-continuity-empty-") as temp:
        root = Path(temp)
        character = _make_character(root)
        empty_provider = _EmptyProvider()
        empty_runtime = ContinuityRuntime(
            context=ContinuityContext(max_items=2),
            lifetime_revisions=3,
        )
        empty_result = await run_user_turn(
            character=character,
            provider=empty_provider,
            content="まだ考えている",
            continuity_runtime=empty_runtime,
        )

    with TemporaryDirectory(prefix="relaylm-eval-continuity-missing-") as temp:
        root = Path(temp)
        character = _make_character(root)
        missing_provider = _BufferedProvider()
        missing_runtime_error = False
        try:
            await run_user_turn(
                character=character,
                provider=missing_provider,
                content="この案を覚えて",
            )
        except RuntimeError as exc:
            missing_runtime_error = (
                "continuity candidates require an explicit runtime" in str(exc)
            )
        missing_actors = tuple(
            event.actor for event in CharacterDirectory(root).iter_events()
        )
        missing_state_count = len(CharacterDirectory(root).load_state().states)

    checks = (
        EvaluationCheck(
            check_id="buffered_single_generation_commits_continuity",
            boundary="provider",
            passed=(
                buffered_provider.calls == 1
                and buffered_runtime.context.revision == 1
                and len(buffered_runtime.context.items) == 1
                and buffered_runtime.context.items[0].key == "draft.current"
                and buffered_result.continuity is not None
                and buffered_result.continuity.context is buffered_runtime.context
                and buffered_actors == ("user", "assistant")
            ),
            expected=True,
            observed=buffered_provider.calls == 1,
        ),
        EvaluationCheck(
            check_id="streaming_commits_only_after_completion",
            boundary="turn_runtime",
            passed=(
                stream_provider.stream_calls == 1
                and stream_provider.revisions_during_stream == [0, 0]
                and "".join(emitted) == "続きを進めよう。"
                and stream_runtime.context.revision == 1
                and stream_runtime.context.items[0].key == "task.current"
                and stream_result.continuity is not None
            ),
            expected=True,
            observed=stream_provider.revisions_during_stream == [0, 0],
        ),
        EvaluationCheck(
            check_id="empty_candidates_advance_configured_runtime",
            boundary="turn_runtime",
            passed=(
                empty_provider.calls == 1
                and empty_runtime.context.revision == 1
                and empty_runtime.context.items == ()
                and empty_result.continuity is not None
                and empty_result.continuity.decisions == ()
            ),
            expected=True,
            observed=empty_runtime.context.revision == 1,
        ),
        EvaluationCheck(
            check_id="missing_runtime_rejects_before_assistant_commit",
            boundary="turn_runtime",
            passed=(
                missing_provider.calls == 1
                and missing_runtime_error
                and missing_actors == ("user",)
                and missing_state_count == 0
            ),
            expected=True,
            observed=missing_runtime_error,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="continuity_turn",
        checks=checks,
        metrics={
            "buffered_provider_calls": buffered_provider.calls,
            "stream_provider_calls": stream_provider.stream_calls,
            "empty_provider_calls": empty_provider.calls,
            "missing_runtime_provider_calls": missing_provider.calls,
            "stream_delta_count": len(emitted),
        },
    )
