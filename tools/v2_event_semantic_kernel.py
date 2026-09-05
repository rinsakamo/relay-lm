from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

SettlementStatus = Literal["COMMIT", "NOOP", "REJECT"]
WorldOrder = Literal["BEFORE", "AFTER", "SAME", "UNKNOWN"]


class InvalidSemanticInput(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Occurrence:
    id: str
    source: str
    content: str | None
    receipt_index: int
    world_rank: int | None = None
    logical_ingress_id: str | None = None
    redacted: bool = False


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    id: str
    occurrence_id: str
    logical_ingress_id: str | None
    replay: bool


@dataclass(frozen=True, slots=True)
class IngressResult:
    occurrence_id: str
    delivery_id: str
    new_occurrence: bool


@dataclass(frozen=True, slots=True)
class Cell:
    value: str | int | bool | None
    supports: frozenset[str] = frozenset()
    derived_from: frozenset[str] = frozenset()
    hot: bool = True
    supported: bool = True


@dataclass(frozen=True, slots=True)
class Head:
    id: str
    parent: str | None
    cells: tuple[tuple[str, Cell], ...]


@dataclass(frozen=True, slots=True)
class Proposal:
    parent_head: str
    writes: tuple[tuple[str, Cell | None], ...]
    admissible: bool = True
    require_observed_support: bool = False


@dataclass(frozen=True, slots=True)
class Settlement:
    status: SettlementStatus
    head_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class ActionReceipt:
    id: str
    parent_head: str
    content: str
    transport_complete: bool = False
    completion_marker: str | None = None


@dataclass(frozen=True, slots=True)
class WorkOption:
    name: str
    expected_gain: float
    cost: float


class EventSemanticKernel:
    """Small LLM-free falsifier for the post-Turn-elimination semantics."""

    def __init__(self) -> None:
        genesis = Head(id="h0", parent=None, cells=())
        self.heads: dict[str, Head] = {genesis.id: genesis}
        self.current_head = genesis.id
        self.occurrences: dict[str, Occurrence] = {}
        self.deliveries: dict[str, DeliveryAttempt] = {}
        self.actions: dict[str, ActionReceipt] = {}
        self._logical_ingress: dict[str, str] = {}
        self._occurrence_counter = 0
        self._delivery_counter = 0
        self._head_counter = 0
        self._action_counter = 0

    def ingest(
        self,
        content: str,
        *,
        source: str = "user",
        logical_ingress_id: str | None = None,
        world_rank: int | None = None,
    ) -> IngressResult:
        self._delivery_counter += 1
        delivery_id = f"d{self._delivery_counter}"

        if logical_ingress_id is not None and logical_ingress_id in self._logical_ingress:
            occurrence_id = self._logical_ingress[logical_ingress_id]
            existing = self.occurrences[occurrence_id]
            if existing.content is not None and existing.content != content:
                raise InvalidSemanticInput("logical ingress replay changed content")
            self.deliveries[delivery_id] = DeliveryAttempt(
                id=delivery_id,
                occurrence_id=occurrence_id,
                logical_ingress_id=logical_ingress_id,
                replay=True,
            )
            return IngressResult(occurrence_id, delivery_id, False)

        self._occurrence_counter += 1
        occurrence_id = f"o{self._occurrence_counter}"
        occurrence = Occurrence(
            id=occurrence_id,
            source=source,
            content=content,
            receipt_index=self._occurrence_counter,
            world_rank=world_rank,
            logical_ingress_id=logical_ingress_id,
        )
        self.occurrences[occurrence_id] = occurrence
        if logical_ingress_id is not None:
            self._logical_ingress[logical_ingress_id] = occurrence_id
        self.deliveries[delivery_id] = DeliveryAttempt(
            id=delivery_id,
            occurrence_id=occurrence_id,
            logical_ingress_id=logical_ingress_id,
            replay=False,
        )
        return IngressResult(occurrence_id, delivery_id, True)

    def receipt_relation(self, left: str, right: str) -> WorldOrder:
        a = self.occurrences[left].receipt_index
        b = self.occurrences[right].receipt_index
        if a < b:
            return "BEFORE"
        if a > b:
            return "AFTER"
        return "SAME"

    def world_relation(self, left: str, right: str) -> WorldOrder:
        a = self.occurrences[left].world_rank
        b = self.occurrences[right].world_rank
        if a is None or b is None:
            return "UNKNOWN"
        if a < b:
            return "BEFORE"
        if a > b:
            return "AFTER"
        return "SAME"

    def cells(self, head_id: str | None = None) -> dict[str, Cell]:
        head = self.heads[head_id or self.current_head]
        return dict(head.cells)

    def cell(self, key: str, head_id: str | None = None) -> Cell | None:
        return self.cells(head_id).get(key)

    def proposal(
        self,
        writes: dict[str, Cell | None],
        *,
        parent_head: str | None = None,
        admissible: bool = True,
        require_observed_support: bool = False,
    ) -> Proposal:
        return Proposal(
            parent_head=parent_head or self.current_head,
            writes=tuple(sorted(writes.items())),
            admissible=admissible,
            require_observed_support=require_observed_support,
        )

    def propose_value(
        self,
        key: str,
        value: str | int | bool | None,
        *,
        supports: tuple[str, ...] = (),
        derived_from: tuple[str, ...] = (),
        hot: bool = True,
        supported: bool = True,
        parent_head: str | None = None,
        admissible: bool = True,
        require_observed_support: bool = False,
    ) -> Proposal:
        return self.proposal(
            {
                key: Cell(
                    value=value,
                    supports=frozenset(supports),
                    derived_from=frozenset(derived_from),
                    hot=hot,
                    supported=supported,
                )
            },
            parent_head=parent_head,
            admissible=admissible,
            require_observed_support=require_observed_support,
        )

    def settle(self, proposal: Proposal) -> Settlement:
        if proposal.parent_head != self.current_head:
            return Settlement("REJECT", self.current_head, "stale_parent")
        if not proposal.admissible:
            return Settlement("REJECT", self.current_head, "inadmissible")

        current = self.cells()
        observed_support = False
        for _key, cell in proposal.writes:
            if cell is None:
                continue
            for support_id in cell.supports | cell.derived_from:
                occurrence = self.occurrences.get(support_id)
                if occurrence is None:
                    return Settlement("REJECT", self.current_head, "missing_support")
                if occurrence.source != "endogenous":
                    observed_support = True
        if proposal.require_observed_support and not observed_support:
            return Settlement("REJECT", self.current_head, "observed_support_required")

        updated = dict(current)
        for key, cell in proposal.writes:
            if cell is None:
                updated.pop(key, None)
            else:
                updated[key] = cell

        canonical = tuple(sorted(updated.items()))
        if canonical == self.heads[self.current_head].cells:
            return Settlement("NOOP", self.current_head, "no_canonical_difference")

        self._head_counter += 1
        new_head_id = f"h{self._head_counter}"
        self.heads[new_head_id] = Head(
            id=new_head_id,
            parent=self.current_head,
            cells=canonical,
        )
        self.current_head = new_head_id
        return Settlement("COMMIT", new_head_id, "committed")

    def proposal_after_support_invalidation(self, support_id: str) -> Proposal:
        writes: dict[str, Cell | None] = {}
        for key, cell in self.cells().items():
            if support_id not in cell.supports:
                continue
            remaining = frozenset(s for s in cell.supports if s != support_id)
            if remaining:
                writes[key] = replace(cell, supports=remaining)
            else:
                writes[key] = replace(
                    cell,
                    value=None,
                    supports=frozenset(),
                    supported=False,
                )
        return self.proposal(writes)

    def proposal_demote(self, key: str) -> Proposal:
        cell = self.cell(key)
        if cell is None:
            return self.proposal({})
        return self.proposal({key: replace(cell, hot=False)})

    def proposal_restore(
        self,
        source_head: str,
        *,
        keys: tuple[str, ...] | None = None,
    ) -> Proposal:
        source = self.cells(source_head)
        current = self.cells()
        selected = set(keys) if keys is not None else set(source) | set(current)
        writes: dict[str, Cell | None] = {}
        for key in selected:
            writes[key] = source.get(key)
        return self.proposal(writes)

    def privacy_delete_occurrence(self, occurrence_id: str) -> Settlement:
        occurrence = self.occurrences[occurrence_id]
        self.occurrences[occurrence_id] = replace(
            occurrence,
            content=None,
            redacted=True,
        )
        writes: dict[str, Cell | None] = {}
        for key, cell in self.cells().items():
            if occurrence_id in cell.derived_from:
                writes[key] = None
            elif occurrence_id in cell.supports:
                remaining = frozenset(s for s in cell.supports if s != occurrence_id)
                if remaining:
                    writes[key] = replace(cell, supports=remaining)
                else:
                    writes[key] = replace(
                        cell,
                        value=None,
                        supports=frozenset(),
                        supported=False,
                    )
        return self.settle(self.proposal(writes))

    def hot_projection(self) -> dict[str, object]:
        return {
            key: cell.value
            for key, cell in self.cells().items()
            if cell.hot and cell.supported and cell.value is not None
        }

    def emit_action(
        self,
        content: str,
        *,
        parent_head: str | None = None,
    ) -> ActionReceipt:
        self._action_counter += 1
        action_id = f"a{self._action_counter}"
        receipt = ActionReceipt(
            id=action_id,
            parent_head=parent_head or self.current_head,
            content=content,
        )
        self.actions[action_id] = receipt
        return receipt

    def complete_transport(
        self,
        action_id: str,
        *,
        marker: str | None = None,
    ) -> ActionReceipt:
        receipt = replace(
            self.actions[action_id],
            transport_complete=True,
            completion_marker=marker,
        )
        self.actions[action_id] = receipt
        return receipt

    @staticmethod
    def choose_work(options: tuple[WorkOption, ...]) -> WorkOption | None:
        profitable = [option for option in options if option.expected_gain > option.cost]
        if not profitable:
            return None
        return max(
            profitable,
            key=lambda option: (option.expected_gain - option.cost, option.name),
        )