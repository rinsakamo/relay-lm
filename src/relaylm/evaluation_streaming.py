from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from relaylm.api.openai import _stream_chat_completion
from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRuntime
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.cognitive_package import CognitivePackageDirectory


class _SuccessfulProvider:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_during_stream = CanonicalState()
        self.actors_during_stream: list[str] = []

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("streaming evaluation must not use buffered generate")

    async def stream_generate(self, cognitive_input: CognitiveInput, emit) -> CognitiveOutput:
        await emit("紅茶")
        snapshot = CognitivePackageDirectory(self.root)
        self.state_during_stream = snapshot.load_state()
        self.actors_during_stream = [event.actor for event in snapshot.iter_events()]
        await emit("が好きって覚えてるよ。")
        return CognitiveOutput(
            response="紅茶が好きって覚えてるよ。",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(cognitive_input.input.id,),
                ),
            ),
        )


class _TruncatedProvider:
    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("streaming evaluation must not use buffered generate")

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        await emit("途中まで")
        raise ProviderProtocolError("truncated structured stream")


class _CancelledProvider:
    def __init__(self) -> None:
        self.cancelled = False

    async def generate(self, _: CognitiveInput) -> CognitiveOutput:
        raise AssertionError("streaming evaluation must not use buffered generate")

    async def stream_generate(self, _: CognitiveInput, emit) -> CognitiveOutput:
        try:
            await emit("見えている途中")
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        raise AssertionError("unreachable")


async def evaluate_streaming_safety() -> EvaluationScenarioResult:
    with tempfile.TemporaryDirectory(prefix="relaylm-eval-stream-ok-") as temporary:
        root = Path(temporary)
        _make_package(root)
        successful_provider = _SuccessfulProvider(root)
        successful_chunks = [
            chunk
            async for chunk in _stream_chat_completion(
                profile=_profile(root, successful_provider),
                turn_lock=asyncio.Lock(),
                content="前に話した好み、覚えてる？",
                completion_id="chatcmpl-eval-success",
                created=0,
            )
        ]
        successful_persisted = CognitivePackageDirectory(root)
        successful_actors = [event.actor for event in successful_persisted.iter_events()]
        successful_state = successful_persisted.load_state()

    with tempfile.TemporaryDirectory(prefix="relaylm-eval-stream-truncated-") as temporary:
        root = Path(temporary)
        _make_package(root)
        truncated_chunks = [
            chunk
            async for chunk in _stream_chat_completion(
                profile=_profile(root, _TruncatedProvider()),
                turn_lock=asyncio.Lock(),
                content="この話を覚えて",
                completion_id="chatcmpl-eval-truncated",
                created=0,
            )
        ]
        truncated_persisted = CognitivePackageDirectory(root)
        truncated_actors = [event.actor for event in truncated_persisted.iter_events()]
        truncated_state = truncated_persisted.load_state()

    with tempfile.TemporaryDirectory(prefix="relaylm-eval-stream-cancel-") as temporary:
        root = Path(temporary)
        _make_package(root)
        cancelled_provider = _CancelledProvider()
        cancelled_stream = _stream_chat_completion(
            profile=_profile(root, cancelled_provider),
            turn_lock=asyncio.Lock(),
            content="途中で切断する",
            completion_id="chatcmpl-eval-cancel",
            created=0,
        )
        first_cancelled_chunk = await anext(cancelled_stream)
        await cancelled_stream.aclose()
        cancelled_persisted = CognitivePackageDirectory(root)
        cancelled_actors = [event.actor for event in cancelled_persisted.iter_events()]
        cancelled_state = cancelled_persisted.load_state()

    successful_text = b"".join(successful_chunks).decode("utf-8")
    truncated_text = b"".join(truncated_chunks).decode("utf-8")
    cancelled_text = first_cancelled_chunk.decode("utf-8")

    checks = (
        EvaluationCheck(
            check_id="successful_stream_exposes_text_before_state_commit",
            boundary="stream_delivery",
            passed="紅茶" in successful_text
            and successful_provider.state_during_stream.states == ()
            and successful_provider.actors_during_stream == ["user"],
            expected=True,
            observed=successful_provider.state_during_stream.states == (),
        ),
        EvaluationCheck(
            check_id="successful_stream_commits_only_after_complete_result",
            boundary="canonical_state",
            passed=successful_actors == ["user", "assistant"]
            and [(record.state_class, record.key, record.value) for record in successful_state.states]
            == [("user.preference", "tea", "likes")]
            and "data: [DONE]" in successful_text,
            expected=True,
            observed=len(successful_state.states) == 1,
        ),
        EvaluationCheck(
            check_id="truncated_stream_keeps_visible_text_but_no_done_marker",
            boundary="stream_delivery",
            passed="途中まで" in truncated_text and "data: [DONE]" not in truncated_text,
            expected=True,
            observed="途中まで" in truncated_text,
        ),
        EvaluationCheck(
            check_id="truncated_stream_leaves_only_user_event_and_no_state",
            boundary="event_journal",
            passed=truncated_actors == ["user"] and truncated_state.states == (),
            expected="user-only/no-state",
            observed=f"{','.join(truncated_actors) or 'none'}/{len(truncated_state.states)}",
        ),
        EvaluationCheck(
            check_id="downstream_close_cancels_inflight_stream",
            boundary="cancellation",
            passed="見えている途中" in cancelled_text and cancelled_provider.cancelled is True,
            expected=True,
            observed=cancelled_provider.cancelled,
        ),
        EvaluationCheck(
            check_id="cancelled_stream_leaves_only_user_event_and_no_state",
            boundary="canonical_state",
            passed=cancelled_actors == ["user"] and cancelled_state.states == (),
            expected="user-only/no-state",
            observed=f"{','.join(cancelled_actors) or 'none'}/{len(cancelled_state.states)}",
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="streaming_safety",
        checks=checks,
        metrics={
            "successful_event_count": len(successful_actors),
            "successful_state_count": len(successful_state.states),
            "truncated_event_count": len(truncated_actors),
            "cancelled_event_count": len(cancelled_actors),
        },
    )


def _profile(root: Path, provider: object) -> CognitiveProfileRuntime:
    return CognitiveProfileRuntime(
        name="relaylm",
        package=CognitivePackageDirectory(root),
        provider=provider,
        physical_model="evaluation-model",
    )


def _make_package(root: Path) -> CognitivePackageDirectory:
    (root / "memory").mkdir(parents=True)
    (root / "SOUL.md").write_text(
        "# Evaluation Character\n\nBe honest and grounded.\n",
        encoding="utf-8",
    )
    (root / "config.yaml").write_text(
        "format_version: 1\ncharacter:\n  id: evaluation\n  name: Evaluation\n",
        encoding="utf-8",
    )
    package = CognitivePackageDirectory(root)
    package.save_state(CanonicalState())
    return package
