from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from tools.v2_event_semantic_kernel import (
    ActionReceipt,
    EventSemanticKernel,
    Head,
    IngressResult,
    Occurrence,
    Proposal,
    Settlement,
)

ExternalMode = Literal["IDEMPOTENT", "NON_IDEMPOTENT"]
ExternalStatus = Literal["DISPATCHED", "SUCCEEDED", "OUTCOME_UNKNOWN"]


@dataclass(frozen=True, slots=True)
class KernelImage:
    """Durable canonical image for the deterministic fault reference.

    Delivery attempts are intentionally omitted: they are transaction debris.
    Logical ingress identity is retained because it is sufficient to recognize a
    trustworthy retry after restart.
    """

    heads: tuple[tuple[str, Head], ...]
    current_head: str
    occurrences: tuple[tuple[str, Occurrence], ...]
    logical_ingress: tuple[tuple[str, str], ...]
    actions: tuple[tuple[str, ActionReceipt], ...]

    @classmethod
    def capture(cls, kernel: EventSemanticKernel) -> KernelImage:
        return cls(
            heads=tuple(sorted(kernel.heads.items())),
            current_head=kernel.current_head,
            occurrences=tuple(sorted(kernel.occurrences.items())),
            logical_ingress=tuple(sorted(kernel._logical_ingress.items())),
            actions=tuple(sorted(kernel.actions.items())),
        )

    def restore(self) -> EventSemanticKernel:
        kernel = EventSemanticKernel()
        kernel.heads = dict(self.heads)
        kernel.current_head = self.current_head
        kernel.occurrences = dict(self.occurrences)
        kernel.deliveries = {}
        kernel.actions = dict(self.actions)
        kernel._logical_ingress = dict(self.logical_ingress)
        kernel._occurrence_counter = _max_numeric_suffix(kernel.occurrences, "o")
        kernel._delivery_counter = 0
        kernel._head_counter = _max_numeric_suffix(kernel.heads, "h")
        kernel._action_counter = _max_numeric_suffix(kernel.actions, "a")
        return kernel


@dataclass(frozen=True, slots=True)
class ExternalReceipt:
    action_id: str
    mode: ExternalMode
    status: ExternalStatus


@dataclass(slots=True)
class DurableStore:
    """Small durable surface: canonical image plus irreversible-effect receipts."""

    kernel_image: KernelImage
    external_receipts: dict[str, ExternalReceipt] = field(default_factory=dict)

    @classmethod
    def fresh(cls) -> DurableStore:
        return cls(kernel_image=KernelImage.capture(EventSemanticKernel()))


class FakeActionSink:
    """Deterministic external-effect stand-in; never performs a real action."""

    def __init__(self) -> None:
        self._calls: dict[str, int] = {}
        self._effects: dict[str, int] = {}

    def invoke(self, action_id: str, *, idempotent: bool) -> None:
        self._calls[action_id] = self._calls.get(action_id, 0) + 1
        if idempotent:
            self._effects.setdefault(action_id, 1)
        else:
            self._effects[action_id] = self._effects.get(action_id, 0) + 1

    def call_count(self, action_id: str) -> int:
        return self._calls.get(action_id, 0)

    def effect_count(self, action_id: str) -> int:
        return self._effects.get(action_id, 0)


class CrashSafeRuntime:
    """LLM-free crash/restart falsifier around the #2230 semantic kernel.

    This class deliberately has no persisted Transaction, phase FSM, proposal
    queue, model intermediate, or provider-resume state. The experiment asks
    whether canonical images plus irreversible-boundary receipts are enough.
    """

    def __init__(self, store: DurableStore) -> None:
        self.store = store
        self.kernel = store.kernel_image.restore()

    @classmethod
    def fresh(cls) -> CrashSafeRuntime:
        return cls(DurableStore.fresh())

    def crash_and_recover(self) -> CrashSafeRuntime:
        return type(self)(self.store)

    def _persist_kernel(self) -> None:
        self.store.kernel_image = KernelImage.capture(self.kernel)

    def ingest(self, content: str, **kwargs: object) -> IngressResult:
        result = self.kernel.ingest(content, **kwargs)
        self._persist_kernel()
        return result

    def propose_value(self, *args: object, **kwargs: object) -> Proposal:
        return self.kernel.propose_value(*args, **kwargs)

    def settle(self, proposal: Proposal, *, persist: bool = True) -> Settlement:
        result = self.kernel.settle(proposal)
        if persist and result.status == "COMMIT":
            self._persist_kernel()
        return result

    def emit_response(self, content: str, **kwargs: object) -> ActionReceipt:
        receipt = self.kernel.emit_action(content, **kwargs)
        self._persist_kernel()
        return receipt

    def complete_transport(
        self, action_id: str, *, marker: str | None = None
    ) -> ActionReceipt:
        receipt = self.kernel.complete_transport(action_id, marker=marker)
        self._persist_kernel()
        return receipt

    def privacy_delete_occurrence(self, occurrence_id: str) -> Settlement:
        result = self.kernel.privacy_delete_occurrence(occurrence_id)
        # The occurrence redaction itself is durable even when the canonical
        # semantic projection needed no further change.
        self._persist_kernel()
        return result

    def begin_external_dispatch(
        self, action_id: str, *, mode: ExternalMode
    ) -> ExternalReceipt:
        if action_id not in self.kernel.actions:
            raise KeyError(f"unknown action: {action_id}")
        if mode not in ("IDEMPOTENT", "NON_IDEMPOTENT"):
            raise ValueError(f"unsupported external mode: {mode}")
        existing = self.store.external_receipts.get(action_id)
        if existing is not None:
            if existing.mode != mode:
                raise ValueError("external dispatch mode changed")
            return existing
        receipt = ExternalReceipt(action_id=action_id, mode=mode, status="DISPATCHED")
        self.store.external_receipts[action_id] = receipt
        return receipt

    def record_external_success(self, action_id: str) -> ExternalReceipt:
        receipt = self.external_receipt(action_id)
        if receipt.status == "OUTCOME_UNKNOWN":
            raise ValueError("cannot retroactively assert success from unknown outcome")
        updated = replace(receipt, status="SUCCEEDED")
        self.store.external_receipts[action_id] = updated
        return updated

    def recover_external(
        self, action_id: str, sink: FakeActionSink
    ) -> ExternalReceipt:
        receipt = self.external_receipt(action_id)
        if receipt.status != "DISPATCHED":
            return receipt
        if receipt.mode == "IDEMPOTENT":
            sink.invoke(action_id, idempotent=True)
            updated = replace(receipt, status="SUCCEEDED")
        else:
            # Dispatch happened, but no trustworthy result receipt survived.
            # Repeating a non-idempotent action could duplicate reality.
            updated = replace(receipt, status="OUTCOME_UNKNOWN")
        self.store.external_receipts[action_id] = updated
        return updated

    def external_receipt(self, action_id: str) -> ExternalReceipt:
        return self.store.external_receipts[action_id]


def _max_numeric_suffix(mapping: object, prefix: str) -> int:
    keys = mapping.keys() if hasattr(mapping, "keys") else mapping
    values: list[int] = []
    for key in keys:
        text = str(key)
        if text.startswith(prefix) and text[len(prefix) :].isdigit():
            values.append(int(text[len(prefix) :]))
    return max(values, default=0)
