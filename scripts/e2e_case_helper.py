from typing import Any


def check_backend(payload: dict[str, Any], current: dict[str, Any]) -> None:
    messages = payload.get("messages")
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[-1] == current
