from __future__ import annotations

import base64
from pathlib import Path

import pytest

from tools.repository_docs import generate


def test_emit_repository_owned_projection_for_2942() -> None:
    projection = generate(
        Path("."),
        source_commit="ec23fe7955abff36517e41afa193d6dcdb24270e",
    )["ARCHITECTURE.md"]
    encoded = base64.b64encode(projection.encode("utf-8")).decode("ascii")
    print("RELAY2942_PROJECTION_BEGIN")
    print(encoded)
    print("RELAY2942_PROJECTION_END")
    pytest.fail("temporary #2942 projection emitter")
