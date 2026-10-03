"""Exploratory execution requires a separate exact structured owner grant."""

import copy
import json

import pytest

from tools import wsl_cuda_exploration_authority as authority
from tools import wsl_cuda_exploration_ledger as ledger


def grant() -> dict:
    return {
        "frozen_campaign_sha256": "f" * 64,
        "schema_version": 1,
        "kind": authority.MARKER,
        "campaign_id": ledger.CAMPAIGN_ID,
        "proposal_sha256": ledger.PROPOSAL_SHA256,
        "budget_comment_id": ledger.BUDGET_COMMENT_ID,
        "maximum_exploration_trials": 8,
        "contract_version": 1,
        "approved_base_head": "a" * 40,
        "target_id": authority.TARGET,
        "resource_key": authority.RESOURCE,
        "evidence_root": "/home/rinsa/relaylm-evidence/exploratory-campaign",
        "python_executable": "/home/rinsa/.venv/bin/python",
        "python_policy_sha256": "b" * 64,
        "python_fingerprint": "c" * 64,
        "server_binary": "/home/rinsa/build/bin/llama-server",
        "server_sha256": "d" * 64,
        "model_path": "/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf",
        "model_sha256": "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed",
        "gpu_uuid": "GPU-3f02099a-88fd-abbc-f59d-dd16ffc63b23",
        "driver_version": "591.44",
        "wsl_kernel": "6.18.33.2-microsoft-standard-WSL2",
        "cuda_toolkit_version": "12.8",
        "port": 1234,
        "startup_timeout_seconds": 600,
        "cleanup_timeout_seconds": 60,
        "allowed_change_paths": ["tools/wsl_cuda_exploration_authority.py"],
        "maximum_server_launches_per_trial": 1,
        "maximum_model_loads_per_trial": 1,
        "allowed_http_methods": [],
        "maximum_generation_requests": 0,
        "maximum_input_count_requests": 0,
        "maximum_public_completions": 0,
    }


def body(value: dict) -> str:
    fence = chr(96) * 3
    return authority.MARKER + "\n" + fence + "json\n" + json.dumps(value, sort_keys=True) + "\n" + fence


def reader(comment_body: str, *, user: str = "rinsakamo", after: str = ""):
    comment_id = ledger.BUDGET_COMMENT_ID + 1
    comments = [
        {"id": ledger.BUDGET_COMMENT_ID, "user": {"login": "rinsakamo"},
         "body": "WSL_CUDA_EXPLORATION_BUDGET_APPROVED_NON_EXECUTABLE"},
        {"id": comment_id, "created_at": "2026-10-03T08:00:00Z",
         "user": {"login": user}, "body": comment_body},
    ]
    if after:
        comments.append({
            "id": comment_id + 1, "created_at": "2026-10-03T09:00:00Z",
            "user": {"login": "rinsakamo"}, "body": after,
        })
    return lambda: {"number": 3018, "state": "open", "user": {"login": "rinsakamo"}}, lambda: comments


def test_exact_structured_grant_and_canonical_digest() -> None:
    expected = grant()
    first, second = reader(body(expected))
    decoded, digest = authority.verify_owner_execution_grant(
        ledger.BUDGET_COMMENT_ID + 1, issue_reader=first, comments_reader=second
    )
    assert decoded == expected
    assert digest == authority.grant_sha256(decoded)
    assert len(digest) == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("maximum_exploration_trials", 9),
        ("maximum_exploration_trials", True),
        ("budget_comment_id", ledger.BUDGET_COMMENT_ID + 1),
        ("allowed_http_methods", ["GET"]),
        ("maximum_generation_requests", 1),
        ("maximum_server_launches_per_trial", 2),
        ("maximum_model_loads_per_trial", 2),
        ("target_id", "diagnostic:3018-wsl-nvidia-runtime-closure-rehearsal"),
        ("resource_key", "other-gpu"),
        ("gpu_uuid", "other-gpu"),
        ("cuda_toolkit_version", "12.9"),
        ("model_sha256", "0" * 64),
        ("approved_base_head", "not-head"),
        ("server_sha256", "not-a-hash"),
        ("startup_timeout_seconds", 0),
        ("cleanup_timeout_seconds", 901),
        ("allowed_change_paths", ["../../unrelated"]),
        ("evidence_root", "/home/rinsa/../unsafe"),
        ("allowed_change_paths", []),
    ],
)
def test_prohibited_grant_modifications_fail_closed(field: str, value: object) -> None:
    changed = grant()
    changed[field] = value
    with pytest.raises(authority.ExplorationGrantError):
        authority.validate_grant(changed)


def test_extra_field_and_non_structured_comment_rejected() -> None:
    modified = grant()
    modified["allow_scientific_spend"] = True
    with pytest.raises(authority.ExplorationGrantError, match="missing or extra"):
        authority.validate_grant(modified)
    for candidate in (
        "WSL_CUDA_EXPLORATION_BUDGET_APPROVED_NON_EXECUTABLE",
        "Ready " + body(grant()),
        body(grant()) + "\nAdditional text",
    ):
        with pytest.raises(authority.ExplorationGrantError):
            authority.extract_grant(candidate)


def test_owner_and_later_revocation_and_closed_issue_fail() -> None:
    selected_id = ledger.BUDGET_COMMENT_ID + 1
    own_issue, wrong_author = reader(body(grant()), user="other")
    with pytest.raises(authority.ExplorationGrantError, match="exact later owner"):
        authority.verify_owner_execution_grant(
            selected_id, issue_reader=own_issue, comments_reader=wrong_author
        )
    own_issue, revoked = reader(body(grant()), after=authority.REVOKE_MARKERS[0])
    with pytest.raises(authority.ExplorationGrantError, match="revoked"):
        authority.verify_owner_execution_grant(
            selected_id, issue_reader=own_issue, comments_reader=revoked
        )
    _, comments = reader(body(grant()))
    with pytest.raises(authority.ExplorationGrantError, match="open #3018"):
        authority.verify_owner_execution_grant(
            selected_id,
            issue_reader=lambda: {"number": 3018, "state": "closed", "user": {"login": "rinsakamo"}},
            comments_reader=comments,
        )
    with pytest.raises(authority.ExplorationGrantError, match="distinct later"):
        authority.verify_owner_execution_grant(ledger.BUDGET_COMMENT_ID)


def test_duplicate_json_keys_fail_closed() -> None:
    fence = chr(96) * 3
    raw = json.dumps(grant(), sort_keys=True)
    ambiguous = raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
    with pytest.raises(authority.ExplorationGrantError, match="duplicate keys"):
        authority.extract_grant(authority.MARKER + "\n" + fence + "json\n" + ambiguous + "\n" + fence)


def test_grant_scope_is_a_frozen_copy() -> None:
    original = grant()
    decoded = authority.validate_grant(copy.deepcopy(original))
    decoded["maximum_exploration_trials"] = 1
    assert original["maximum_exploration_trials"] == 8
