#!/usr/bin/env python3
"""Current finalized-source schema validation smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import relaylm_i1gb_durable_finalization_publication_smoke as i1gb
from relaylm.relaymem_slp_durable_finalization_record import (
    validate_finalized_source_mapping,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> None:
    _, _, seal = i1gb._records()
    current = seal["finalized_turn_source"]
    require(validate_finalized_source_mapping(current) == (), current)

    missing_formation = dict(current)
    missing_formation.pop("formation_summary_artifact")
    reasons = validate_finalized_source_mapping(missing_formation)
    require(
        "durable_finalization_finalized_source_shape_mismatch" in reasons,
        reasons,
    )

    invalid_formation = dict(current)
    invalid_formation["formation_summary_artifact"] = []
    reasons = validate_finalized_source_mapping(invalid_formation)
    require(
        "durable_finalization_formation_summary_artifact_invalid" in reasons,
        reasons,
    )

    print("relaylm_i1gb_finalized_source_current_schema_smoke: ok")


if __name__ == "__main__":
    main()
