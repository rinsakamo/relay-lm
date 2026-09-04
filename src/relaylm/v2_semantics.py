from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Iterable, Literal as TypingLiteral


Origin = TypingLiteral["observed", "endogenous"]
Verdict = TypingLiteral["accepted", "deferred", "rejected"]


@dataclass(frozen=True, slots=True)
class Literal:
    value: object


@dataclass(frozen=True, slots=True)
class Ref:
    anchor: str


@dataclass(frozen=True, slots=True)
class Var:
    name: str


@dataclass(frozen=True, slots=True)
class Apply:
    symbol: str
    args: tuple[Expr, ...] = ()


Expr = Literal | Ref | Var | Apply


@dataclass(frozen=True, slots=True)
class ProvenanceLink:
    relation: str
    target: str


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    id: str
    origin: Origin
    time: str
    source: str
    payload_ref: str | None
    links: tuple[ProvenanceLink, ...] = ()


@dataclass(frozen=True, slots=True)
class ObservationInput:
    slot: str
    time: str
    source: str
    payload: str


@dataclass(frozen=True, slots=True)
class Proposal:
    expr: Expr
    observed_support_slots: tuple[str, ...] = ()
    existing_provenance_support: tuple[str, ...] = ()
    revision_of: tuple[str, ...] = ()
    deactivate_roots: tuple[str, ...] = ()
    requested_anchors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionRequest:
    name: str
    payload: str


@dataclass(frozen=True, slots=True)
class TransactionRequest:
    base_generation: str
    observations: tuple[ObservationInput, ...] = ()
    proposals: tuple[Proposal, ...] = ()
    actions: tuple[ActionRequest, ...] = ()


@dataclass(frozen=True, slots=True)
class GovernancePolicy:
    allow_protected_roots: bool = False
    protected_root_symbols: frozenset[str] = frozenset({"identity", "values"})
    outcome_symbols: frozenset[str] = frozenset({"outcome"})


@dataclass(frozen=True, slots=True)
class ProposalDecision:
    status: Verdict
    reason: str
    semantic_id: str | None = None


@dataclass(frozen=True, slots=True)
class TransactionResult:
    generation_id: str
    decisions: tuple[ProposalDecision, ...]
    observation_records: tuple[str, ...]
    action_records: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Generation:
    generation_id: str
    parent_generation_id: str | None
    active_roots: tuple[str, ...]
    anchor_root: str
    provenance_head: str | None
    target_cognition: str | None
    horizon: str | None
    created_by_transaction: str


@dataclass(frozen=True, slots=True)
class MigrationCheck:
    ok: bool
    missing_symbols: tuple[str, ...] = ()
    missing_provenance: tuple[str, ...] = ()


class StaleGenerationError(RuntimeError):
    pass


class InvalidTransactionError(ValueError):
    pass


_BINDERS = frozenset({"forall", "exists", "lambda"})


def literal(value: object) -> Literal:
    return Literal(value)


def ref(anchor: str) -> Ref:
    return Ref(anchor)


def var(name: str) -> Var:
    return Var(name)


def apply(symbol: str, *args: Expr) -> Apply:
    return Apply(symbol, tuple(args))


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _literal_payload(value: object) -> object:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite float literal is not canonical")
        return value
    raise TypeError(f"unsupported literal type: {type(value).__name__}")


def canonical_form(expr: Expr) -> object:
    return _canonical_form(expr, {})


def _canonical_form(expr: Expr, env: dict[str, str]) -> object:
    if isinstance(expr, Literal):
        return ["lit", _literal_payload(expr.value)]
    if isinstance(expr, Ref):
        if not expr.anchor:
            raise ValueError("anchor must not be empty")
        return ["ref", expr.anchor]
    if isinstance(expr, Var):
        if not expr.name:
            raise ValueError("variable name must not be empty")
        return ["var", env.get(expr.name, expr.name)]
    if not isinstance(expr, Apply):
        raise TypeError(f"unsupported expression type: {type(expr).__name__}")
    if not expr.symbol:
        raise ValueError("symbol must not be empty")
    if expr.symbol in _BINDERS:
        if len(expr.args) != 2 or not isinstance(expr.args[0], Var):
            raise ValueError(f"{expr.symbol} requires (Var, body)")
        binder = expr.args[0]
        canonical_name = f"${len(env)}"
        inner = dict(env)
        inner[binder.name] = canonical_name
        return [
            "apply",
            expr.symbol,
            [["var", canonical_name], _canonical_form(expr.args[1], inner)],
        ]
    return [
        "apply",
        expr.symbol,
        [_canonical_form(arg, env) for arg in expr.args],
    ]


def semantic_id(expr: Expr) -> str:
    return _digest(canonical_form(expr))


def _iter_expr(expr: Expr) -> Iterable[Expr]:
    yield expr
    if isinstance(expr, Apply):
        for arg in expr.args:
            yield from _iter_expr(arg)


def _anchors_in_expr(expr: Expr) -> frozenset[str]:
    return frozenset(
        node.anchor
        for node in _iter_expr(expr)
        if isinstance(node, Ref)
    )


def root_symbol(expr: Expr) -> str | None:
    return expr.symbol if isinstance(expr, Apply) else None


def _decode_serialized(value: object) -> Expr:
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("invalid serialized expression")
    tag = value[0]
    if tag == "lit" and len(value) == 2:
        return Literal(value[1])
    if tag == "ref" and len(value) == 2 and isinstance(value[1], str):
        return Ref(value[1])
    if tag == "var" and len(value) == 2 and isinstance(value[1], str):
        return Var(value[1])
    if tag == "apply" and len(value) == 3 and isinstance(value[1], str):
        args_raw = value[2]
        if not isinstance(args_raw, list):
            raise ValueError("invalid apply args")
        return Apply(value[1], tuple(_decode_serialized(arg) for arg in args_raw))
    raise ValueError("invalid serialized expression")


class SemanticTransactionStore:
    """Deterministic LLM-free proof store for RelayLM 2.0 semantic transactions."""

    def __init__(self) -> None:
        self.semantic_nodes: dict[str, bytes] = {}
        self.anchors: set[str] = set()
        self.provenance: dict[str, ProvenanceRecord] = {}
        self.payloads: dict[str, str] = {}
        self.generations: dict[str, Generation] = {}
        self.retired_generations: set[str] = set()
        self.current_generation = self._create_genesis()

    def _create_genesis(self) -> str:
        tx_id = _digest(["genesis"])
        generation = self._make_generation(
            parent=None,
            roots=(),
            anchors=(),
            provenance_head=None,
            target_cognition=None,
            horizon=None,
            tx_id=tx_id,
        )
        self.generations[generation.generation_id] = generation
        return generation.generation_id

    def _make_generation(
        self,
        *,
        parent: str | None,
        roots: Iterable[str],
        anchors: Iterable[str],
        provenance_head: str | None,
        target_cognition: str | None,
        horizon: str | None,
        tx_id: str,
    ) -> Generation:
        root_tuple = tuple(sorted(set(roots)))
        anchor_tuple = tuple(sorted(set(anchors)))
        anchor_root = _digest(["anchors", anchor_tuple])
        payload = [
            "generation",
            parent,
            root_tuple,
            anchor_root,
            provenance_head,
            target_cognition,
            horizon,
            tx_id,
        ]
        generation_id = _digest(payload)
        return Generation(
            generation_id=generation_id,
            parent_generation_id=parent,
            active_roots=root_tuple,
            anchor_root=anchor_root,
            provenance_head=provenance_head,
            target_cognition=target_cognition,
            horizon=horizon,
            created_by_transaction=tx_id,
        )

    def active_generation(self) -> Generation:
        return self.generations[self.current_generation]

    def active_exprs(self) -> tuple[Expr, ...]:
        return tuple(self.expr_for_id(root) for root in self.active_generation().active_roots)

    def expr_for_id(self, node_id: str) -> Expr:
        raw = self.semantic_nodes[node_id]
        return _decode_serialized(json.loads(raw.decode("utf-8")))

    def _intern_accepted(self, expr: Expr) -> str:
        form = canonical_form(expr)
        node_id = _digest(form)
        self.semantic_nodes.setdefault(node_id, _json_bytes(form))
        return node_id

    def _provenance_record_id(
        self,
        *,
        origin: Origin,
        time: str,
        source: str,
        payload_ref: str | None,
        links: tuple[ProvenanceLink, ...],
    ) -> str:
        return _digest(
            [
                "provenance",
                origin,
                time,
                source,
                payload_ref,
                [[link.relation, link.target] for link in links],
            ]
        )

    def _append_provenance(
        self,
        *,
        previous_head: str | None,
        origin: Origin,
        time: str,
        source: str,
        payload: str | None = None,
        payload_ref: str | None = None,
        links: tuple[ProvenanceLink, ...] = (),
    ) -> str:
        if payload is not None and payload_ref is not None:
            raise ValueError("payload and payload_ref are mutually exclusive")
        if payload is not None:
            payload_ref = _digest(["payload", payload])
            self.payloads[payload_ref] = payload

        effective_links = list(links)
        if previous_head is not None:
            effective_links.append(ProvenanceLink("previous", previous_head))
        canonical_links = tuple(
            sorted(effective_links, key=lambda link: (link.relation, link.target))
        )

        record_id = self._provenance_record_id(
            origin=origin,
            time=time,
            source=source,
            payload_ref=payload_ref,
            links=canonical_links,
        )
        self.provenance.setdefault(
            record_id,
            ProvenanceRecord(
                id=record_id,
                origin=origin,
                time=time,
                source=source,
                payload_ref=payload_ref,
                links=canonical_links,
            ),
        )
        return record_id

    def _provenance_lineage(
        self,
        head: str | None,
    ) -> tuple[set[str], set[str]]:
        present: set[str] = set()
        missing: set[str] = set()
        current = head
        while current is not None:
            if current in present:
                raise InvalidTransactionError("provenance chain has a cycle")
            record = self.provenance.get(current)
            if record is None:
                missing.add(current)
                break
            present.add(current)
            previous = [
                link.target
                for link in record.links
                if link.relation == "previous"
            ]
            if len(previous) > 1:
                raise InvalidTransactionError(
                    "provenance record has multiple previous links"
                )
            current = previous[0] if previous else None
        return present, missing

    def _transaction_id(
        self,
        request: TransactionRequest,
        policy: GovernancePolicy,
    ) -> str:
        return _digest(
            [
                "tx",
                request.base_generation,
                [
                    [obs.slot, obs.time, obs.source, obs.payload]
                    for obs in request.observations
                ],
                [
                    [
                        canonical_form(proposal.expr),
                        proposal.observed_support_slots,
                        proposal.existing_provenance_support,
                        proposal.revision_of,
                        proposal.deactivate_roots,
                        proposal.requested_anchors,
                    ]
                    for proposal in request.proposals
                ],
                [[action.name, action.payload] for action in request.actions],
                sorted(policy.protected_root_symbols),
                sorted(policy.outcome_symbols),
                policy.allow_protected_roots,
            ]
        )

    def transact(
        self,
        request: TransactionRequest,
        *,
        policy: GovernancePolicy = GovernancePolicy(),
    ) -> TransactionResult:
        if request.base_generation != self.current_generation:
            raise StaleGenerationError("base generation is stale")
        if request.base_generation in self.retired_generations:
            raise InvalidTransactionError("base generation is retired")

        slots = [obs.slot for obs in request.observations]
        if any(not slot for slot in slots):
            raise InvalidTransactionError("observation slot must not be empty")
        if len(slots) != len(set(slots)):
            raise InvalidTransactionError("duplicate observation slot")
        for proposal in request.proposals:
            if any(not anchor for anchor in proposal.requested_anchors):
                raise InvalidTransactionError("anchor must not be empty")

        tx_id = self._transaction_id(request, policy)
        parent_generation = self.active_generation()
        pending_head = parent_generation.provenance_head

        observation_records: dict[str, str] = {}
        for obs in request.observations:
            record_id = self._append_provenance(
                previous_head=pending_head,
                origin="observed",
                time=obs.time,
                source=obs.source,
                payload=obs.payload,
            )
            observation_records[obs.slot] = record_id
            pending_head = record_id

        staged: list[tuple[int, Proposal, ProposalDecision]] = []
        decisions: list[ProposalDecision] = []
        for proposal_index, proposal in enumerate(request.proposals):
            decision = self._govern_proposal(
                proposal,
                observation_records=observation_records,
                policy=policy,
            )
            if decision.status == "accepted":
                decision = ProposalDecision(
                    "accepted",
                    "accepted",
                    semantic_id=semantic_id(proposal.expr),
                )
            staged.append((proposal_index, proposal, decision))
            decisions.append(decision)

        active_roots = set(parent_generation.active_roots)
        accepted_anchors: set[str] = set()
        for _proposal_index, proposal, decision in staged:
            if decision.status != "accepted":
                continue
            assert decision.semantic_id is not None
            for deactivate in proposal.deactivate_roots:
                active_roots.discard(deactivate)
            active_roots.add(decision.semantic_id)
            accepted_anchors.update(_anchors_in_expr(proposal.expr))
            accepted_anchors.update(proposal.requested_anchors)

        for proposal_index, proposal, decision in staged:
            if decision.status != "accepted":
                continue
            root_id = self._intern_accepted(proposal.expr)
            assert root_id == decision.semantic_id

            links: list[ProvenanceLink] = []
            for slot in proposal.observed_support_slots:
                links.append(ProvenanceLink("supports", observation_records[slot]))
            for record_id in proposal.existing_provenance_support:
                links.append(ProvenanceLink("supports", record_id))
            for revised in proposal.revision_of:
                links.append(ProvenanceLink("revises", f"sem:{revised}"))
            links.append(ProvenanceLink("produces", f"sem:{root_id}"))
            record_id = self._append_provenance(
                previous_head=pending_head,
                origin="endogenous",
                time=self._proposal_time(request, proposal_index),
                source=f"semantic-transaction:{tx_id}",
                payload=None,
                links=tuple(links),
            )
            pending_head = record_id

        self.anchors.update(accepted_anchors)

        action_records: list[str] = []
        for action_index, action in enumerate(request.actions):
            record_id = self._append_provenance(
                previous_head=pending_head,
                origin="endogenous",
                time=self._action_time(request, action_index),
                source=f"action:{tx_id}",
                payload=action.payload,
                links=(ProvenanceLink("attempts", f"action:{action.name}"),),
            )
            action_records.append(record_id)
            pending_head = record_id

        generation = self._make_generation(
            parent=request.base_generation,
            roots=active_roots,
            anchors=self.anchors,
            provenance_head=pending_head,
            target_cognition=parent_generation.target_cognition,
            horizon=parent_generation.horizon,
            tx_id=tx_id,
        )
        self.generations[generation.generation_id] = generation
        self.current_generation = generation.generation_id

        return TransactionResult(
            generation_id=generation.generation_id,
            decisions=tuple(decisions),
            observation_records=tuple(observation_records.values()),
            action_records=tuple(action_records),
        )

    @staticmethod
    def _proposal_time(request: TransactionRequest, index: int) -> str:
        if request.observations:
            return request.observations[-1].time
        return f"proposal:{index:06d}"

    @staticmethod
    def _action_time(request: TransactionRequest, index: int) -> str:
        if request.observations:
            return request.observations[-1].time
        return f"action:{index:06d}"

    def _govern_proposal(
        self,
        proposal: Proposal,
        *,
        observation_records: dict[str, str],
        policy: GovernancePolicy,
    ) -> ProposalDecision:
        try:
            canonical_form(proposal.expr)
        except (TypeError, ValueError) as exc:
            return ProposalDecision("rejected", f"invalid_semantics:{exc}")

        for slot in proposal.observed_support_slots:
            if slot not in observation_records:
                return ProposalDecision("rejected", "missing_observed_support_slot")

        support_ids = list(proposal.existing_provenance_support)
        support_ids.extend(
            observation_records[slot] for slot in proposal.observed_support_slots
        )
        for record_id in support_ids:
            if record_id not in self.provenance:
                return ProposalDecision("rejected", "missing_provenance_support")

        symbol = root_symbol(proposal.expr)
        if (
            symbol in policy.protected_root_symbols
            and not policy.allow_protected_roots
        ):
            return ProposalDecision("rejected", "protected_root_requires_authority")

        if symbol in policy.outcome_symbols:
            if not support_ids:
                return ProposalDecision("rejected", "outcome_requires_observed_support")
            if not any(
                self.provenance[record_id].origin == "observed"
                for record_id in support_ids
            ):
                return ProposalDecision("rejected", "outcome_requires_observed_support")

        for root_id in proposal.deactivate_roots:
            if root_id not in self.active_generation().active_roots:
                return ProposalDecision("rejected", "deactivate_root_not_active")
        for revised in proposal.revision_of:
            if revised not in self.semantic_nodes:
                return ProposalDecision("rejected", "revision_target_missing")

        return ProposalDecision("accepted", "accepted")

    def query_status(self, expr: Expr) -> str:
        root_id = semantic_id(expr)
        negated_id = semantic_id(apply("not", expr))
        roots = set(self.active_generation().active_roots)
        positive = root_id in roots
        negative = negated_id in roots
        if positive and negative:
            return "CONFLICT"
        if positive:
            return "TRUE"
        if negative:
            return "FALSE"
        return "UNKNOWN"

    def derive_pressures(self, now: str) -> tuple[str, ...]:
        current = datetime.fromisoformat(now.replace("Z", "+00:00"))
        pressures: list[str] = []
        for expr in self.active_exprs():
            if (
                isinstance(expr, Apply)
                and expr.symbol == "deadline"
                and len(expr.args) == 2
                and isinstance(expr.args[1], Literal)
                and isinstance(expr.args[1].value, str)
            ):
                deadline = datetime.fromisoformat(
                    expr.args[1].value.replace("Z", "+00:00")
                )
                if current >= deadline:
                    pressures.append(f"deadline_due:{semantic_id(expr)}")
        return tuple(sorted(pressures))

    def migrate_generation(
        self,
        generation_id: str,
        *,
        native_symbols: frozenset[str],
    ) -> MigrationCheck:
        generation = self.generations[generation_id]
        definitions = self._active_symbol_definitions(generation)
        missing_symbols: set[str] = set()
        native = set(native_symbols) | {
            "defines",
            "believes",
            "hypothetical",
            "counterfactual",
            "not",
            "same_as",
            "different_from",
            "forall",
            "exists",
            "lambda",
        }
        for root in generation.active_roots:
            expr = self.expr_for_id(root)
            self._find_missing_symbols(
                expr,
                native,
                definitions,
                missing_symbols,
            )

        lineage_ids, missing_provenance = self._provenance_lineage(
            generation.provenance_head
        )
        for root in generation.active_roots:
            missing_provenance.update(
                self._missing_supports_for_root(root, lineage_ids)
            )

        return MigrationCheck(
            ok=not missing_symbols and not missing_provenance,
            missing_symbols=tuple(sorted(missing_symbols)),
            missing_provenance=tuple(sorted(missing_provenance)),
        )

    def _active_symbol_definitions(self, generation: Generation) -> set[str]:
        defined: set[str] = set()
        for root in generation.active_roots:
            expr = self.expr_for_id(root)
            if (
                isinstance(expr, Apply)
                and expr.symbol == "defines"
                and len(expr.args) == 2
                and isinstance(expr.args[0], Ref)
            ):
                defined.add(expr.args[0].anchor)
        return defined

    def _find_missing_symbols(
        self,
        expr: Expr,
        native: set[str],
        defined: set[str],
        missing: set[str],
    ) -> None:
        if not isinstance(expr, Apply):
            return
        if expr.symbol not in native and expr.symbol not in defined:
            missing.add(expr.symbol)
        for arg in expr.args:
            self._find_missing_symbols(arg, native, defined, missing)

    def _missing_supports_for_root(
        self,
        root_id: str,
        allowed_record_ids: set[str],
    ) -> set[str]:
        target = f"sem:{root_id}"
        producer_ids = [
            record.id
            for record in self.provenance.values()
            if record.id in allowed_record_ids
            and any(
                link.relation == "produces" and link.target == target
                for link in record.links
            )
        ]
        if not producer_ids:
            return {f"producer:{root_id}"}

        missing: set[str] = set()
        visited: set[str] = set()
        for producer_id in producer_ids:
            self._collect_missing_supports(
                producer_id,
                allowed_record_ids,
                visited,
                missing,
            )
        return missing

    def _collect_missing_supports(
        self,
        record_id: str,
        allowed_record_ids: set[str],
        visited: set[str],
        missing: set[str],
    ) -> None:
        if record_id in visited:
            return
        visited.add(record_id)
        if record_id not in allowed_record_ids:
            missing.add(record_id)
            return
        record = self.provenance.get(record_id)
        if record is None:
            missing.add(record_id)
            return
        for link in record.links:
            if link.relation != "supports":
                continue
            support_id = (
                link.target[5:]
                if link.target.startswith("prov:")
                else link.target
            )
            if (
                support_id not in allowed_record_ids
                or support_id not in self.provenance
            ):
                missing.add(support_id)
                continue
            self._collect_missing_supports(
                support_id,
                allowed_record_ids,
                visited,
                missing,
            )

    def retire_generation(self, generation_id: str) -> None:
        if generation_id == self.current_generation:
            raise InvalidTransactionError("current generation cannot be retired")
        if generation_id not in self.generations:
            raise KeyError(generation_id)
        self.retired_generations.add(generation_id)

    def garbage_collect_semantics(self) -> int:
        retained_generations = [
            generation
            for generation_id, generation in self.generations.items()
            if generation_id not in self.retired_generations
        ]
        reachable = {
            root
            for generation in retained_generations
            for root in generation.active_roots
        }
        before = len(self.semantic_nodes)
        self.semantic_nodes = {
            node_id: payload
            for node_id, payload in self.semantic_nodes.items()
            if node_id in reachable
        }
        return before - len(self.semantic_nodes)

    def delete_payload(
        self,
        record_id: str,
        *,
        time: str,
        full_erasure: bool = False,
    ) -> str:
        record = self.provenance.get(record_id)
        if record is None:
            raise KeyError(record_id)
        if record.origin != "observed":
            raise InvalidTransactionError("only observed payloads are erasable evidence")

        parent_id = self.current_generation
        parent = self.active_generation()
        pending_head = parent.provenance_head

        if record.payload_ref is not None:
            self.payloads.pop(record.payload_ref, None)

        if full_erasure:
            del self.provenance[record_id]
            for generation_id, generation in self.generations.items():
                lineage_ids, missing = self._provenance_lineage(
                    generation.provenance_head
                )
                affected = record_id in missing
                if not affected:
                    affected = any(
                        record_id
                        in self._missing_supports_for_root(root, lineage_ids)
                        for root in generation.active_roots
                    )
                if affected:
                    self.retired_generations.add(generation_id)
            relation = "erases"
        else:
            relation = "deletes_payload"

        tombstone = self._append_provenance(
            previous_head=pending_head,
            origin="endogenous",
            time=time,
            source="governance",
            payload=None,
            links=(ProvenanceLink(relation, f"prov:{record_id}"),),
        )

        tx_id = _digest(["evidence-governance", parent_id, tombstone])
        generation = self._make_generation(
            parent=parent_id,
            roots=parent.active_roots,
            anchors=self.anchors,
            provenance_head=tombstone,
            target_cognition=parent.target_cognition,
            horizon=parent.horizon,
            tx_id=tx_id,
        )
        self.generations[generation.generation_id] = generation
        self.current_generation = generation.generation_id
        return tombstone

    def canonical_snapshot(self) -> bytes:
        value = {
            "anchors": sorted(self.anchors),
            "semantic_nodes": {
                node_id: payload.decode("utf-8")
                for node_id, payload in sorted(self.semantic_nodes.items())
            },
            "provenance": {
                record_id: {
                    "origin": record.origin,
                    "time": record.time,
                    "source": record.source,
                    "payload_ref": record.payload_ref,
                    "links": [
                        [link.relation, link.target]
                        for link in record.links
                    ],
                }
                for record_id, record in sorted(self.provenance.items())
            },
            "payloads": dict(sorted(self.payloads.items())),
            "generations": {
                generation_id: {
                    "parent": generation.parent_generation_id,
                    "roots": generation.active_roots,
                    "anchor_root": generation.anchor_root,
                    "provenance_head": generation.provenance_head,
                    "target_cognition": generation.target_cognition,
                    "horizon": generation.horizon,
                    "created_by": generation.created_by_transaction,
                }
                for generation_id, generation in sorted(self.generations.items())
            },
            "retired_generations": sorted(self.retired_generations),
            "current_generation": self.current_generation,
        }
        return _json_bytes(value)

    @classmethod
    def from_snapshot(cls, snapshot: bytes) -> "SemanticTransactionStore":
        try:
            raw = json.loads(snapshot.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidTransactionError("invalid durable snapshot") from exc

        expected_keys = {
            "anchors",
            "semantic_nodes",
            "provenance",
            "payloads",
            "generations",
            "retired_generations",
            "current_generation",
        }
        if not isinstance(raw, dict) or set(raw) != expected_keys:
            raise InvalidTransactionError("invalid durable snapshot shape")
        if (
            not isinstance(raw["anchors"], list)
            or not all(isinstance(anchor, str) and anchor for anchor in raw["anchors"])
            or not isinstance(raw["semantic_nodes"], dict)
            or not isinstance(raw["provenance"], dict)
            or not isinstance(raw["payloads"], dict)
            or not isinstance(raw["generations"], dict)
            or not isinstance(raw["retired_generations"], list)
            or not all(
                isinstance(generation_id, str) and generation_id
                for generation_id in raw["retired_generations"]
            )
            or not isinstance(raw["current_generation"], str)
            or not raw["current_generation"]
        ):
            raise InvalidTransactionError("invalid durable snapshot shape")

        store = cls.__new__(cls)
        store.anchors = set(raw["anchors"])

        store.semantic_nodes = {}
        semantic_anchors: set[str] = set()
        for node_id, serialized in raw["semantic_nodes"].items():
            if not isinstance(node_id, str) or not isinstance(serialized, str):
                raise InvalidTransactionError("invalid semantic snapshot entry")
            try:
                form = json.loads(serialized)
                expr = _decode_serialized(form)
                canonical = canonical_form(expr)
                canonical_bytes = _json_bytes(canonical)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise InvalidTransactionError(
                    "invalid semantic snapshot payload"
                ) from exc
            if (
                _digest(canonical) != node_id
                or canonical_bytes.decode("utf-8") != serialized
            ):
                raise InvalidTransactionError("semantic snapshot hash mismatch")
            store.semantic_nodes[node_id] = canonical_bytes
            semantic_anchors.update(_anchors_in_expr(expr))

        if not semantic_anchors.issubset(store.anchors):
            raise InvalidTransactionError("semantic snapshot has unbound anchor")

        store.payloads = {}
        for payload_ref, payload in raw["payloads"].items():
            if not isinstance(payload_ref, str) or not isinstance(payload, str):
                raise InvalidTransactionError("invalid payload snapshot entry")
            if _digest(["payload", payload]) != payload_ref:
                raise InvalidTransactionError("payload snapshot hash mismatch")
            store.payloads[payload_ref] = payload

        store.provenance = {}
        for record_id, record_raw in raw["provenance"].items():
            if not isinstance(record_id, str) or not isinstance(record_raw, dict):
                raise InvalidTransactionError("invalid provenance snapshot entry")
            if set(record_raw) != {
                "origin",
                "time",
                "source",
                "payload_ref",
                "links",
            }:
                raise InvalidTransactionError("invalid provenance snapshot entry")
            try:
                links_raw = record_raw["links"]
                if not isinstance(links_raw, list):
                    raise TypeError
                links = tuple(
                    ProvenanceLink(relation, target)
                    for relation, target in links_raw
                    if isinstance(relation, str) and isinstance(target, str)
                )
                if len(links) != len(links_raw):
                    raise TypeError
                record = ProvenanceRecord(
                    id=record_id,
                    origin=record_raw["origin"],
                    time=record_raw["time"],
                    source=record_raw["source"],
                    payload_ref=record_raw["payload_ref"],
                    links=links,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise InvalidTransactionError(
                    "invalid provenance snapshot entry"
                ) from exc
            if (
                record.origin not in ("observed", "endogenous")
                or not isinstance(record.time, str)
                or not isinstance(record.source, str)
                or (
                    record.payload_ref is not None
                    and not isinstance(record.payload_ref, str)
                )
            ):
                raise InvalidTransactionError("invalid provenance snapshot entry")
            previous_links = [
                link for link in record.links if link.relation == "previous"
            ]
            if len(previous_links) > 1:
                raise InvalidTransactionError(
                    "provenance record has multiple previous links"
                )
            expected_id = store._provenance_record_id(
                origin=record.origin,
                time=record.time,
                source=record.source,
                payload_ref=record.payload_ref,
                links=record.links,
            )
            if expected_id != record_id:
                raise InvalidTransactionError("provenance snapshot hash mismatch")
            store.provenance[record_id] = record

        store.generations = {}
        for generation_id, generation_raw in raw["generations"].items():
            if not isinstance(generation_id, str) or not isinstance(generation_raw, dict):
                raise InvalidTransactionError("invalid generation snapshot entry")
            if set(generation_raw) != {
                "parent",
                "roots",
                "anchor_root",
                "provenance_head",
                "target_cognition",
                "horizon",
                "created_by",
            }:
                raise InvalidTransactionError("invalid generation snapshot entry")
            roots = generation_raw["roots"]
            if (
                not isinstance(roots, list)
                or not all(isinstance(root, str) and root for root in roots)
            ):
                raise InvalidTransactionError("invalid generation snapshot entry")
            generation = Generation(
                generation_id=generation_id,
                parent_generation_id=generation_raw["parent"],
                active_roots=tuple(roots),
                anchor_root=generation_raw["anchor_root"],
                provenance_head=generation_raw["provenance_head"],
                target_cognition=generation_raw["target_cognition"],
                horizon=generation_raw["horizon"],
                created_by_transaction=generation_raw["created_by"],
            )
            if (
                (
                    generation.parent_generation_id is not None
                    and not isinstance(generation.parent_generation_id, str)
                )
                or not isinstance(generation.anchor_root, str)
                or (
                    generation.provenance_head is not None
                    and not isinstance(generation.provenance_head, str)
                )
                or (
                    generation.target_cognition is not None
                    and not isinstance(generation.target_cognition, str)
                )
                or (
                    generation.horizon is not None
                    and not isinstance(generation.horizon, str)
                )
                or not isinstance(generation.created_by_transaction, str)
            ):
                raise InvalidTransactionError("invalid generation snapshot entry")
            expected_id = _digest(
                [
                    "generation",
                    generation.parent_generation_id,
                    generation.active_roots,
                    generation.anchor_root,
                    generation.provenance_head,
                    generation.target_cognition,
                    generation.horizon,
                    generation.created_by_transaction,
                ]
            )
            if expected_id != generation_id:
                raise InvalidTransactionError("generation snapshot hash mismatch")
            store.generations[generation_id] = generation

        store.retired_generations = set(raw["retired_generations"])
        store.current_generation = raw["current_generation"]
        if store.current_generation not in store.generations:
            raise InvalidTransactionError("current generation is missing")
        if store.current_generation in store.retired_generations:
            raise InvalidTransactionError("current generation is retired")

        current = store.active_generation()
        if current.anchor_root != _digest(["anchors", tuple(sorted(store.anchors))]):
            raise InvalidTransactionError("current anchor root mismatch")

        for generation_id, generation in store.generations.items():
            if generation_id in store.retired_generations:
                continue
            if any(root not in store.semantic_nodes for root in generation.active_roots):
                raise InvalidTransactionError(
                    "retained generation has missing semantics"
                )
            if (
                generation.provenance_head is not None
                and generation.provenance_head not in store.provenance
            ):
                raise InvalidTransactionError(
                    "retained generation has missing provenance"
                )
            present, missing = store._provenance_lineage(
                generation.provenance_head
            )
            lineage_erasures = {
                link.target[5:]
                for record_id in present
                for link in store.provenance[record_id].links
                if link.relation == "erases"
                and link.target.startswith("prov:")
            }
            if not missing.issubset(lineage_erasures):
                raise InvalidTransactionError(
                    "retained generation has unexplained provenance gap"
                )

        return store

    def derived_symbol_index(self) -> dict[str, tuple[str, ...]]:
        index: dict[str, list[str]] = {}
        for node_id, payload in self.semantic_nodes.items():
            expr = _decode_serialized(json.loads(payload.decode("utf-8")))
            if isinstance(expr, Apply):
                index.setdefault(expr.symbol, []).append(node_id)
        return {
            symbol: tuple(sorted(node_ids))
            for symbol, node_ids in sorted(index.items())
        }
