from __future__ import annotations

from relaylm.cognitive import CognitiveInput
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import CanonicalState, STATE_CLASS_DEFINITIONS


def compile_cognitive_input(
    *,
    identity: Identity,
    state: CanonicalState,
    current_event: Event,
) -> CognitiveInput:
    """Build the minimal MVP cognitive context without transcript replay."""

    active_state = tuple(
        record
        for record in state.states
        if record.status == "active" and record.valid_to is None
    )
    return CognitiveInput(
        identity=identity,
        state_classes=STATE_CLASS_DEFINITIONS,
        state=active_state,
        context=(),
        input=current_event,
    )
