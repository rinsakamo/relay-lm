from __future__ import annotations

from pathlib import Path

from tools.repository_authority import load_declarations


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_every_semantic_owner_has_canonical_authority() -> None:
    declarations = load_declarations(_REPOSITORY_ROOT)

    missing = sorted(
        declaration.id
        for declaration in declarations
        if not declaration.canonical_surfaces
    )

    assert missing == [], (
        "semantic owners must each own at least one canonical authority surface; "
        f"missing: {', '.join(missing)}"
    )
