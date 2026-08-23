import math

import pytest

from relaylm.continuity import ContinuityCandidate, ContinuityContext, ContinuityItem
from relaylm.continuity_validation import apply_continuity_candidates
from relaylm.events import Event


def _item(value: object) -> ContinuityItem:
    return ContinuityItem(
        item_id="continuity-1",
        kind="referent",
        key="referent.current",
        value=value,
        sources=("event-user-1",),
        epistemic_role="user_assertion",
        accepted_revision=1,
        expires_revision=4,
    )


def _event() -> Event:
    return Event.create(
        type="message",
        actor="user",
        payload={"content": "source"},
        event_id="event-user-1",
        timestamp="2026-08-23T07:00:00+00:00",
    )


@pytest.mark.parametrize(
    "value",
    (
        {"tags": {"alpha"}},
        {"score": float("nan")},
        {1: "one"},
    ),
)
def test_continuity_item_rejects_values_outside_json_semantic_domain(value: object) -> None:
    with pytest.raises(ValueError, match="JSON semantic value"):
        _item(value)


def test_continuity_k2_rejects_non_string_object_keys_as_non_json_value() -> None:
    event = _event()
    candidate = ContinuityCandidate.set(
        kind="referent",
        key="referent.current",
        value={1: "one", "label": "first"},
        sources=(event.id,),
        epistemic_role="user_assertion",
    )

    result = apply_continuity_candidates(
        current_context=ContinuityContext(max_items=2),
        candidates=(candidate,),
        events={event.id: event},
        lifetime_revisions=3,
    )

    assert result.context.items == ()
    assert result.decisions[0].status == "rejected"
    assert result.decisions[0].reason == "non_json_value"


def test_existing_json_nested_value_and_tuple_array_normalization_remain_valid() -> None:
    item = _item(
        {
            "steps": [1, True, None],
            "coords": (1.0, 2),
        }
    )

    assert item.value["steps"] == (1, True, None)
    assert item.value["coords"] == (1.0, 2)
    assert math.isfinite(item.value["coords"][0])
