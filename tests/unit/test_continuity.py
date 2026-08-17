from dataclasses import FrozenInstanceError

import pytest

from relaylm.continuity import ContinuityCandidate, ContinuityContext, ContinuityItem


INITIAL_KINDS = ("referent", "unresolved", "active_task")


def test_continuity_candidate_freezes_bounded_kind_provenance_and_epistemic_role() -> None:
    for kind in INITIAL_KINDS:
        candidate = ContinuityCandidate.set(
            kind=kind,
            key=f"example.{kind}",
            value={"text": kind},
            sources=("event-user-1",),
            epistemic_role="user_assertion",
        )
        assert candidate.kind == kind
        assert candidate.sources == ("event-user-1",)
        assert candidate.epistemic_role == "user_assertion"
        assert candidate.has_value is True

    with pytest.raises(ValueError, match="unsupported continuity kind"):
        ContinuityCandidate.set(
            kind="future_kind",  # type: ignore[arg-type]
            key="example.future",
            value="value",
            sources=("event-user-1",),
            epistemic_role="assistant_inference",
        )

    with pytest.raises(ValueError, match="sources must not be empty"):
        ContinuityCandidate.set(
            kind="referent",
            key="example.referent",
            value="value",
            sources=(),
            epistemic_role="assistant_inference",
        )

    with pytest.raises(ValueError, match="unsupported epistemic role"):
        ContinuityCandidate.set(
            kind="referent",
            key="example.referent",
            value="value",
            sources=("event-user-1",),
            epistemic_role="external_truth",  # type: ignore[arg-type]
        )


def test_continuity_candidate_resolve_is_explicit_and_carries_no_value() -> None:
    candidate = ContinuityCandidate.resolve(
        kind="active_task",
        key="task.current",
        sources=("event-user-2",),
        epistemic_role="assistant_inference",
    )

    assert candidate.op == "resolve"
    assert candidate.has_value is False

    with pytest.raises(ValueError, match="resolve candidate must not carry a semantic value"):
        ContinuityCandidate(
            kind="active_task",
            key="task.current",
            op="resolve",
            value="done",
            sources=("event-user-2",),
            epistemic_role="assistant_inference",
        )


def test_continuity_item_and_context_are_immutable_explicitly_bounded_boundaries() -> None:
    item = ContinuityItem(
        item_id="continuity-1",
        kind="unresolved",
        key="question.location",
        value={"question": "Which location?"},
        sources=("event-user-3",),
        epistemic_role="assistant_inference",
        accepted_revision=2,
        expires_revision=5,
    )
    context = ContinuityContext(max_items=2, revision=2, items=(item,))

    assert context.items == (item,)
    assert context.max_items == 2

    with pytest.raises(FrozenInstanceError):
        context.revision = 3  # type: ignore[misc]

    with pytest.raises(ValueError, match="max_items must be positive"):
        ContinuityContext(max_items=0)

    with pytest.raises(ValueError, match="exceeds max_items"):
        ContinuityContext(max_items=1, revision=2, items=(item, item))

    with pytest.raises(ValueError, match="item lifetime must advance beyond acceptance"):
        ContinuityItem(
            item_id="continuity-2",
            kind="referent",
            key="referent.current",
            value="the first draft",
            sources=("event-user-4",),
            epistemic_role="user_assertion",
            accepted_revision=4,
            expires_revision=4,
        )
