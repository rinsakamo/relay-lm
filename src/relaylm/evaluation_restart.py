from __future__ import annotations

import tempfile
from pathlib import Path

import httpx

from relaylm.cognitive import CognitiveInput, CognitiveOutput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.evaluation import EvaluationCheck, EvaluationScenarioResult
from relaylm.server import create_app
from relaylm.state import CanonicalState, StateCandidate
from relaylm.storage.cognitive_package import CognitivePackageDirectory


class _InitialContinuityProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        return CognitiveOutput(
            response="紅茶が好きって覚えておくね。",
            state_candidates=(
                StateCandidate.set(
                    state_class="user.preference",
                    key="tea",
                    value="likes",
                    sources=(cognitive_input.input.id,),
                ),
            ),
        )


class _RestartedContinuityProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[CognitiveInput] = []

    async def generate(self, cognitive_input: CognitiveInput) -> CognitiveOutput:
        self.calls += 1
        self.inputs.append(cognitive_input)
        return CognitiveOutput(response="うん。紅茶が好きって覚えてるよ。")


async def evaluate_restart_continuity() -> EvaluationScenarioResult:
    followup_content = "前に話した好きな飲み物、覚えてる？"
    with tempfile.TemporaryDirectory(prefix="relaylm-eval-restart-") as temporary:
        root = Path(temporary)
        _make_package(root)

        first_provider = _InitialContinuityProvider()
        first_app = create_app(profiles=_profiles(root, first_provider))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=first_app),
            base_url="http://relaylm.test",
        ) as client:
            first_response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "relaylm",
                    "messages": [
                        {"role": "user", "content": "紅茶が好き。覚えておいて"}
                    ],
                },
            )

        persisted = CognitivePackageDirectory(root)
        pre_restart_state = persisted.load_state()
        pre_restart_events = list(persisted.iter_events())

        restarted_provider = _RestartedContinuityProvider()
        restarted_app = create_app(profiles=_profiles(root, restarted_provider))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restarted_app),
            base_url="http://relaylm.test",
        ) as client:
            followup_response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "relaylm",
                    "messages": [{"role": "user", "content": followup_content}],
                },
            )

        restart_input = (
            restarted_provider.inputs[0] if restarted_provider.inputs else None
        )

    expected_state = [("user.preference", "tea", "likes")]
    observed_pre_state = [
        (record.state_class, record.key, record.value)
        for record in pre_restart_state.states
    ]
    observed_restart_state = (
        [
            (record.state_class, record.key, record.value)
            for record in restart_input.state
        ]
        if restart_input is not None
        else []
    )
    pre_restart_actors = [event.actor for event in pre_restart_events]
    restart_context = (
        [(item.actor, item.content) for item in restart_input.context]
        if restart_input is not None
        else []
    )
    restart_context_sources = (
        {source for item in restart_input.context for source in item.sources}
        if restart_input is not None
        else set()
    )
    pre_restart_event_ids = {event.id for event in pre_restart_events}
    current_input = (
        restart_input.input.payload.get("content")
        if restart_input is not None
        else None
    )

    checks = (
        EvaluationCheck(
            check_id="first_session_api_succeeded",
            boundary="client_api",
            passed=first_response.status_code == 200,
            expected=200,
            observed=first_response.status_code,
        ),
        EvaluationCheck(
            check_id="first_provider_called_once",
            boundary="provider",
            passed=first_provider.calls == 1,
            expected=1,
            observed=first_provider.calls,
        ),
        EvaluationCheck(
            check_id="pre_restart_state_persisted",
            boundary="canonical_state",
            passed=observed_pre_state == expected_state,
            expected="user.preference/tea=likes",
            observed=(
                "user.preference/tea=likes"
                if observed_pre_state == expected_state
                else str(observed_pre_state)
            ),
        ),
        EvaluationCheck(
            check_id="pre_restart_events_persisted",
            boundary="event_journal",
            passed=pre_restart_actors == ["user", "assistant"],
            expected="user,assistant",
            observed=",".join(pre_restart_actors) if pre_restart_actors else "none",
        ),
        EvaluationCheck(
            check_id="restarted_provider_called_once",
            boundary="provider",
            passed=restarted_provider.calls == 1,
            expected=1,
            observed=restarted_provider.calls,
        ),
        EvaluationCheck(
            check_id="restart_state_loaded",
            boundary="canonical_state",
            passed=observed_restart_state == expected_state,
            expected="user.preference/tea=likes",
            observed=(
                "user.preference/tea=likes"
                if observed_restart_state == expected_state
                else str(observed_restart_state)
            ),
        ),
        EvaluationCheck(
            check_id="restart_working_context_preserves_exchange",
            boundary="context_compiler",
            passed=restart_context
            == [
                ("user", "紅茶が好き。覚えておいて"),
                ("assistant", "紅茶が好きって覚えておくね。"),
            ],
            expected="user,assistant persisted exchange",
            observed=",".join(str(actor) for actor, _ in restart_context) or "none",
        ),
        EvaluationCheck(
            check_id="restart_context_sources_are_pre_restart_events",
            boundary="context_compiler",
            passed=restart_context_sources == pre_restart_event_ids,
            expected=True,
            observed=restart_context_sources == pre_restart_event_ids,
        ),
        EvaluationCheck(
            check_id="restart_current_input_is_followup_only",
            boundary="client_api",
            passed=current_input == followup_content,
            expected=followup_content,
            observed=str(current_input),
        ),
        EvaluationCheck(
            check_id="followup_api_succeeded",
            boundary="client_api",
            passed=followup_response.status_code == 200,
            expected=200,
            observed=followup_response.status_code,
        ),
    )
    return EvaluationScenarioResult(
        scenario_id="restart_continuity",
        checks=checks,
        metrics={
            "provider_calls": first_provider.calls + restarted_provider.calls,
            "pre_restart_event_count": len(pre_restart_events),
            "restart_context_count": len(restart_context),
        },
    )


def _profiles(root: Path, provider: object) -> CognitiveProfileRegistry:
    return CognitiveProfileRegistry(
        (
            CognitiveProfileRuntime(
                name="relaylm",
                package=CognitivePackageDirectory(root),
                provider=provider,
                physical_model="evaluation-model",
            ),
        )
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
