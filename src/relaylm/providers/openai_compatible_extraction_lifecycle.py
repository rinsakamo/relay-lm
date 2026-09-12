from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from relaylm.cognitive import CognitiveInput, ContextItem
from relaylm.cognition_execution import CognitionExtractionInput
from relaylm.continuity import CONTINUITY_EPISTEMIC_ROLES, CONTINUITY_KINDS
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_extraction_projection import (
    ExtractionProjectionMode,
    continuity_extraction_component,
    continuity_only_extraction_intro,
    continuity_only_extraction_outro,
    extraction_response_component,
    production_extraction_intro,
    production_extraction_outro,
    state_extraction_component,
    unresolved_only_continuity_extraction_component,
    unresolved_only_extraction_intro,
    unresolved_only_extraction_outro,
)


_LIFECYCLE_KIND_ORDER = ("referent", "unresolved", "active_task")


@dataclass(frozen=True, slots=True)
class AcceptedContinuityLifecycleItem:
    kind: str
    key: str
    value: Any
    sources: tuple[str, ...]
    epistemic_role: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "key": self.key,
            "value": self.value,
            "sources": list(self.sources),
            "epistemic_role": self.epistemic_role,
        }


@dataclass(frozen=True, slots=True)
class ExtractionLifecycleProjection:
    cognitive_input: CognitiveInput
    accepted_items: tuple[AcceptedContinuityLifecycleItem, ...]

    def grouped_mapping(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {
            kind: [] for kind in _LIFECYCLE_KIND_ORDER
        }
        for item in self.accepted_items:
            grouped[item.kind].append(item.to_mapping())
        return grouped


def separate_accepted_continuity_for_extraction(
    cognitive_input: CognitiveInput,
) -> ExtractionLifecycleProjection:
    """Move only the canonical accepted-Continuity prefix out of generic context.

    The Context Compiler has already used accepted Continuity while selecting the
    State working set. This helper never recompiles the turn; it derives a Pass2
    view from the already-compiled object and fails closed if the current 1.0
    context boundary is not structurally exact.
    """

    context = cognitive_input.context
    accepted: list[AcceptedContinuityLifecycleItem] = []
    prefix_length = 0
    while prefix_length < len(context) and context[prefix_length].actor is None:
        accepted.append(_parse_projected_continuity_item(context[prefix_length]))
        prefix_length += 1

    remaining = context[prefix_length:]
    if any(item.actor not in {"user", "assistant"} for item in remaining):
        raise ProviderProtocolError(
            "Pass2 working-context boundary is not structurally exact"
        )

    extraction_view = replace(cognitive_input, context=remaining)
    _require_same_noncontext_cognitive_input(cognitive_input, extraction_view)
    return ExtractionLifecycleProjection(
        cognitive_input=extraction_view,
        accepted_items=tuple(accepted),
    )


def build_lifecycle_separated_extraction_pass_suffix(
    extraction_input: CognitionExtractionInput,
    *,
    mode: ExtractionProjectionMode,
    accepted_items: tuple[AcceptedContinuityLifecycleItem, ...],
) -> str:
    """Compose canonical extraction rules with a dedicated accepted-lifecycle channel."""

    source_id = extraction_input.originating_event_id
    common = extraction_response_component(extraction_input)
    lifecycle_contract = _lifecycle_channel_contract(accepted_items)

    if mode is ExtractionProjectionMode.PRODUCTION:
        return (
            common
            + production_extraction_intro()
            + state_extraction_component(source_id)
            + lifecycle_contract
            + continuity_extraction_component(source_id)
            + production_extraction_outro()
        )
    if mode is ExtractionProjectionMode.CONTINUITY_ONLY:
        return (
            common
            + continuity_only_extraction_intro()
            + lifecycle_contract
            + continuity_extraction_component(source_id)
            + continuity_only_extraction_outro()
        )
    if mode is ExtractionProjectionMode.UNRESOLVED_ONLY:
        return (
            common
            + unresolved_only_extraction_intro()
            + lifecycle_contract
            + unresolved_only_continuity_extraction_component(source_id)
            + unresolved_only_extraction_outro()
        )
    raise TypeError("unsupported extraction projection mode")


def _lifecycle_channel_contract(
    accepted_items: tuple[AcceptedContinuityLifecycleItem, ...],
) -> str:
    grouped = {kind: [] for kind in _LIFECYCLE_KIND_ORDER}
    for item in accepted_items:
        grouped[item.kind].append(item.to_mapping())
    lifecycle_json = json.dumps(
        grouped,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""- Pass 2 lifecycle channel: first discover current-turn Continuity meanings from the current Input plus non-lifecycle CognitiveInput. Do not let prior lifecycle items decide whether a distinct current-turn meaning exists.
- After discovering a current-turn Continuity meaning, consult only the same-kind bucket in `<ACCEPTED_CONTINUITY_LIFECYCLE_JSON>` for no-op, existing-key reuse, or resolve. Prior items of other kinds must not suppress discovery.
- `<ACCEPTED_CONTINUITY_LIFECYCLE_JSON>` is read-only accepted prior lifecycle state, not a new proposal and not current-turn evidence. New transitions still require the current Input Event ID in `sources`.
<ACCEPTED_CONTINUITY_LIFECYCLE_JSON>
{lifecycle_json}
</ACCEPTED_CONTINUITY_LIFECYCLE_JSON>
"""


def _parse_projected_continuity_item(
    item: ContextItem,
) -> AcceptedContinuityLifecycleItem:
    if item.actor is not None:
        raise ProviderProtocolError("accepted Continuity projection must have actor=None")
    if not item.sources:
        raise ProviderProtocolError(
            "accepted Continuity projection must preserve non-empty sources"
        )
    try:
        payload = json.loads(item.content)
    except json.JSONDecodeError as exc:
        raise ProviderProtocolError(
            "accepted Continuity projection is not canonical JSON"
        ) from exc
    if not isinstance(payload, dict) or set(payload) != {"continuity"}:
        raise ProviderProtocolError(
            "accepted Continuity projection must contain only continuity"
        )
    continuity = payload["continuity"]
    if not isinstance(continuity, dict) or set(continuity) != {
        "kind",
        "key",
        "value",
        "epistemic_role",
    }:
        raise ProviderProtocolError(
            "accepted Continuity projection has unexpected semantic fields"
        )
    kind = continuity["kind"]
    if kind not in CONTINUITY_KINDS:
        raise ProviderProtocolError(
            "accepted Continuity projection has unsupported kind"
        )
    key = continuity["key"]
    if not isinstance(key, str) or not key.strip():
        raise ProviderProtocolError(
            "accepted Continuity projection key must be non-empty"
        )
    epistemic_role = continuity["epistemic_role"]
    if epistemic_role not in CONTINUITY_EPISTEMIC_ROLES:
        raise ProviderProtocolError(
            "accepted Continuity projection has unsupported epistemic_role"
        )
    return AcceptedContinuityLifecycleItem(
        kind=kind,
        key=key,
        value=continuity["value"],
        sources=item.sources,
        epistemic_role=epistemic_role,
    )


def _require_same_noncontext_cognitive_input(
    baseline: CognitiveInput,
    treatment: CognitiveInput,
) -> None:
    for field_name in (
        "identity",
        "state_classes",
        "state",
        "input",
        "knowledge",
        "memory",
        "event_evidence",
    ):
        if getattr(baseline, field_name) != getattr(treatment, field_name):
            raise ProviderProtocolError(
                f"Pass2 lifecycle separation changed CognitiveInput.{field_name}"
            )
