from __future__ import annotations

from collections.abc import Sequence

from relaylm.v2_transfer_actual_model import ExperimentCompletion
from tools.v2_cognitive_work_structured_output_qualification import (
    OpenAICompatibleStructuredOutputClient,
    StructuredOutputClient,
)
from tools.v2_transfer_q1_target_range import (
    Q1Call,
    Q1TargetRangeError,
    target_response_format,
    transport_identity,
)


class Q1StructuredClientError(Q1TargetRangeError):
    pass


class Q1PlanStructuredClient:
    """Strict target-only JSON-schema transport bound to one frozen Q1 plan."""

    def __init__(
        self,
        *,
        call_plan: Sequence[Q1Call],
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
        structured_client: StructuredOutputClient | None = None,
    ) -> None:
        self._plan = tuple(call_plan)
        if not self._plan or tuple(x.call_index for x in self._plan) != tuple(range(len(self._plan))):
            raise Q1StructuredClientError("Q1 structured client requires a contiguous non-empty plan")
        if structured_client is not None:
            if any(value is not None for value in (base_url, model, api_key)):
                raise Q1StructuredClientError("structured_client cannot be combined with provider constructor arguments")
            self._client = structured_client
            self._owned = None
        else:
            if not isinstance(base_url, str) or not base_url.strip() or not isinstance(model, str) or not model.strip():
                raise Q1StructuredClientError("base_url and model must be non-empty")
            owned = OpenAICompatibleStructuredOutputClient(base_url=base_url, model=model, api_key=api_key, timeout=timeout)
            self._client = owned
            self._owned = owned
        self._cursor = 0

    @property
    def call_count(self) -> int:
        return self._cursor

    @property
    def next_plan_entry(self) -> Q1Call | None:
        return None if self._cursor >= len(self._plan) else self._plan[self._cursor]

    @property
    def identity(self) -> dict[str, object]:
        return transport_identity(self._plan)

    def close(self) -> None:
        if self._owned is not None:
            self._owned.close()

    def complete(self, entry: Q1Call, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self.next_plan_entry != entry:
            raise Q1StructuredClientError("Q1 structured client plan cursor disagrees with host")
        self._cursor += 1
        completion = self._client.complete(
            messages,
            response_format=target_response_format(entry.width, entry.modulus),
        )
        return ExperimentCompletion(
            content=completion.content,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            response_id=completion.response_id,
        )
