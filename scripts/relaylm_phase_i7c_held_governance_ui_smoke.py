"""Phase I-7C SOUL Lab held governance UI source-boundary smoke."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "apps" / "soul-lab" / "src" / "features" / "lab"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> None:
    api = (LAB_ROOT / "heldGovernanceApi.ts").read_text(encoding="utf-8")
    panel = (LAB_ROOT / "HeldGovernancePanel.tsx").read_text(encoding="utf-8")
    page = (LAB_ROOT / "ConnectedLabObservationPage.tsx").read_text(encoding="utf-8")

    require("/held/${encodeURIComponent(candidateId)}${suffix}" in api, "held path builder")
    require("/${action}/preflight" in api and "/${action}" in api, "held action suffixes")
    require("credentials: \"same-origin\"" in api, "same-origin")
    require("cache: \"no-store\"" in api, "no-store")
    for forbidden in ("store_root", "queue_root", "source_path", "protected_source", "queue_payload", "claim_token", "lease_owner"):
        require(f"{forbidden}:" not in api, forbidden)

    require("generation.current === currentGeneration" in panel, "stale generation guard")
    require("AbortController" in panel, "abort controller")
    require("onClick={() => void confirmDecision()}" in panel, "explicit confirmation")
    require("onMouseEnter" not in panel, "no hover apply")
    require("dangerouslySetInnerHTML" not in panel + page, "no raw html")
    held_section = page.split("HELD / BLOCKED", 1)[1].split("{selectedOperation?.kind", 1)[0]
    require("item.title" not in held_section and "item.bounded_summary" not in held_section, "held content hidden")
    require("held_item_adopted_contract" in panel and "held_item_discarded_contract" in panel, "effect preview")
    require("worker / scheduler / retry" in page, "non-goal boundary")

    print("Phase I-7C held governance UI source smoke passed")


if __name__ == "__main__":
    main()
