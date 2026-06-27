"""Phase I-7C held governance API source-boundary smoke."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_PATH = REPO_ROOT / "relaylm" / "lab_held_governance_api.py"
APP_PATH = REPO_ROOT / "relaylm" / "soul_lab_app.py"
CONTRACT_PATH = REPO_ROOT / "relaylm" / "soul_lab_held_governance.py"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> None:
    api = API_PATH.read_text(encoding="utf-8")
    app = APP_PATH.read_text(encoding="utf-8")
    contract = CONTRACT_PATH.read_text(encoding="utf-8")

    for route in (
        "/lab/api/characters/{character_id}/held/{candidate_id}/apply/preflight",
        "/lab/api/characters/{character_id}/held/{candidate_id}/apply",
        "/lab/api/characters/{character_id}/held/{candidate_id}/discard/preflight",
        "/lab/api/characters/{character_id}/held/{candidate_id}/discard",
        "/lab/api/characters/{character_id}/held/{candidate_id}/history",
    ):
        require(route in api, route)

    require("install_held_governance_routes" in app, "route installer missing")
    require("require_loopback_management=require_loopback_management" in app, "loopback guard missing")
    require("observation_scope=correction_scope" in app, "scoped store resolver missing")
    require("exact_json=exact_json" in app, "strict json parser missing")

    require("LabHeldGovernancePreflightRequest" in contract, "preflight request contract")
    require("LabHeldGovernanceDecisionRequest" in contract, "decision request contract")
    require("extra=\"forbid\"" in contract, "exact request schema")
    require("relaylm.lab.held_governance_preflight_request.v0" in contract, "preflight schema")
    require("relaylm.lab.held_governance_decision_request.v0" in contract, "decision schema")

    for forbidden in (
        "source_evidence_digest",
        "candidate_digest",
        "reason_digest",
        "token_digest",
        "source_path",
        "protected_source",
    ):
        require(f'"{forbidden}"' in api, f"forbidden token guard missing: {forbidden}")
    require("safe_projection(result)" in api, "safe projection guard missing")
    require("Cache-Control" in api and "no-store" in api, "no-store responses missing")
    require("preflight_held_governance_decision" in api, "preflight runtime hook missing")
    require("apply_held_governance_decision" in api, "decision runtime hook missing")
    require("list_held_governance_history" in api, "history runtime hook missing")

    print("Phase I-7C held governance API source-boundary smoke passed")


if __name__ == "__main__":
    main()
