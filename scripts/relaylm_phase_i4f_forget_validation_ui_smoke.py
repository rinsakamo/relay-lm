"""Phase I-4F SOUL Lab stale-browser and no-implicit-apply UI smoke."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "apps" / "soul-lab" / "src" / "features" / "lab"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def read(name: str) -> str:
    return (LAB / name).read_text(encoding="utf-8")


def no_private_terms(source: str, name: str) -> None:
    for forbidden in ("dangerouslySetInnerHTML", "token_claims", "token_digest", "reason_digest", "physical_id", "store_root", "filesystem_path", "tombstone_content"):
        require(forbidden not in source, f"{name}: {forbidden}")


def panel_fences_stale_responses() -> None:
    panel = read("PrimaryMemoryForgetPanel.tsx")
    no_private_terms(panel, "PrimaryMemoryForgetPanel.tsx")
    for required in ("AbortController", "generation.current === currentGeneration", "void confirmApply()", "明示的にForgetを適用", "preflightMemoryForget", "applyMemoryForget", "loadMemoryForgetHistory"):
        require(required in panel, required)
    for implicit_trigger in ("onMouseEnter", "onMouseOver", "onPointerEnter", "onFocus={", "onLoad={"):
        require(implicit_trigger not in panel, implicit_trigger)
    require(panel.count("applyMemoryForget(") == 1, "apply must have one call site")
    require("onClick={() => void confirmApply()}" in panel, "apply must be click-confirmed")


def api_rejects_unbounded_server_shapes() -> None:
    api = read("forgetApi.ts")
    for required in ("hasExactKeys(value, preflightKeys)", "hasExactKeys(value, applyKeys)", "hasExactKeys(value, historyKeys)", "credentials: \"same-origin\"", "cache: \"no-store\"", "boundedServerErrorCodes", "token_invalid", "token_expired", "already_hidden", "runtime_unavailable"):
        require(required in api, required)
    for browser_authority in ("route_authority", "storeRoot", "queueRoot", "backendBaseUrl"):
        require(browser_authority not in api, browser_authority)


def page_keeps_forget_on_user_action() -> None:
    page = read("ConnectedLabObservationPage.tsx")
    no_private_terms(page, "ConnectedLabObservationPage.tsx")
    require("Correct / Forget" in page, "row action label")
    require("loadUsedMemoryLifecycle" in page, "lifecycle overlay")
    require("setMockFallback(false)" in page, "real route")
    require("applyMemoryForget" not in page, "page must not apply directly")


def main() -> None:
    panel_fences_stale_responses()
    api_rejects_unbounded_server_shapes()
    page_keeps_forget_on_user_action()
    print("Phase I-4F Forget UI validation smoke passed")


if __name__ == "__main__":
    main()
