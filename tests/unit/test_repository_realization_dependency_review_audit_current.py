from __future__ import annotations

from collections import Counter
from pathlib import Path

from tools.repository_realization_dependencies import (
    realization_dependency_review_signals,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _owner_pair(signal: str) -> str:
    marker = "(importer owners: "
    suffix = signal.split(marker, 1)[1].removesuffix(")")
    importer, imported = suffix.split("; imported owners: ", 1)
    return f"{importer} -> {imported}"


def test_current_transitive_realization_review_audit() -> None:
    signals = realization_dependency_review_signals(REPOSITORY_ROOT)
    clusters = Counter(_owner_pair(signal) for signal in signals)
    summary = "\n".join(
        f"{count:>3}  {pair}"
        for pair, count in sorted(clusters.items(), key=lambda item: (-item[1], item[0]))
    )
    assert not signals, (
        f"current transitive-only realization review signals: {len(signals)}\n"
        f"owner-pair clusters: {len(clusters)}\n"
        + summary
    )
