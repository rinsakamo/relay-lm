"""Structured, exact, fresh future execution grant for WSL CUDA exploration.

Budget comment 5965167490 deliberately grants ZERO physical invocations.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from tools import wsl_cuda_exploration_ledger as ledger
from tools import wsl_nvidia_runtime_closure_rehearsal as rehearsal

MARKER = "WSL_CUDA_EXPLORATION_EXECUTION_GRANTED_V1"
TARGET = "diagnostic:3018-wsl-cuda-exploration"
RESOURCE = "llama-cpp:local-gpu"
OWNER = "rinsakamo"
REVOKE_MARKERS = ("WSL_CUDA_EXPLORATION_EXECUTION_REVOKED", "WSL_CUDA_EXPLORATION_BUDGET_REVOKED")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
FIELDS = frozenset({
    "schema_version", "kind", "campaign_id", "proposal_sha256", "budget_comment_id",
    "maximum_exploration_trials", "contract_version", "approved_base_head", "target_id",
    "resource_key", "evidence_root", "python_executable", "python_policy_sha256",
    "python_fingerprint", "server_binary", "server_sha256", "model_path", "model_sha256",
    "gpu_uuid", "driver_version", "wsl_kernel", "cuda_toolkit_version", "port",
    "startup_timeout_seconds", "cleanup_timeout_seconds", "allowed_change_paths",
    "maximum_server_launches_per_trial", "maximum_model_loads_per_trial",
    "allowed_http_methods", "maximum_generation_requests", "maximum_input_count_requests",
    "maximum_public_completions",
})


class ExplorationGrantError(RuntimeError):
    """No valid fresh executable owner grant is available."""


def canonical_grant(grant: Mapping[str, Any]) -> bytes:
    return json.dumps(grant, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def grant_sha256(grant: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_grant(grant)).hexdigest()


def _absolute_path(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("/")
        and "\x00" not in value
        and ".." not in Path(value).parts
        and str(Path(value)) == value
    )


def validate_grant(grant: Any) -> dict[str, Any]:
    if not isinstance(grant, dict) or frozenset(grant) != FIELDS:
        raise ExplorationGrantError("grant fields are missing or extra execution powers were supplied")
    expected = {
        "schema_version": 1, "kind": MARKER, "campaign_id": ledger.CAMPAIGN_ID,
        "proposal_sha256": ledger.PROPOSAL_SHA256,
        "budget_comment_id": ledger.BUDGET_COMMENT_ID,
        "maximum_exploration_trials": ledger.APPROVED_BUDGET,
        "contract_version": 1, "target_id": TARGET, "resource_key": RESOURCE,
        "port": 1234, "maximum_server_launches_per_trial": 1,
        "maximum_model_loads_per_trial": 1, "allowed_http_methods": [],
        "maximum_generation_requests": 0, "maximum_input_count_requests": 0,
        "maximum_public_completions": 0,
    }
    if any(type(grant.get(k)) is not type(v) or grant[k] != v for k, v in expected.items()):
        raise ExplorationGrantError("grant altered the approved campaign or zero-request limits")
    if not isinstance(grant["approved_base_head"], str) or not SHA1.fullmatch(grant["approved_base_head"]):
        raise ExplorationGrantError("grant lacks an exact protected-v1 base HEAD")
    for key in ("python_policy_sha256", "python_fingerprint", "server_sha256", "model_sha256"):
        if not isinstance(grant[key], str) or not SHA256.fullmatch(grant[key]):
            raise ExplorationGrantError(f"grant {key} requires exact SHA256")
    for key in ("evidence_root", "python_executable", "server_binary", "model_path"):
        if not _absolute_path(grant[key]):
            raise ExplorationGrantError(f"grant {key} requires a clean absolute path")
    if grant["model_sha256"] != "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed":
        raise ExplorationGrantError("the #3013 model may not be substituted")
    if grant["gpu_uuid"] != "GPU-3f02099a-88fd-abbc-f59d-dd16ffc63b23":
        raise ExplorationGrantError("GPU UUID differs from authorized RTX 3060")
    for key in ("driver_version", "wsl_kernel", "cuda_toolkit_version"):
        if not isinstance(grant[key], str) or not 1 <= len(grant[key]) <= 128:
            raise ExplorationGrantError(f"grant {key} missing or unbounded")
    if grant["cuda_toolkit_version"] != "12.8":
        raise ExplorationGrantError("toolkit update requires a fresh approval")
    if any(type(grant[key]) is not int or not 1 <= grant[key] <= 900 for key in ("startup_timeout_seconds", "cleanup_timeout_seconds")):
        raise ExplorationGrantError("startup/cleanup time bounds invalid")
    paths = grant["allowed_change_paths"]
    if (
        not isinstance(paths, list) or not 1 <= len(paths) <= 32
        or any(
            not isinstance(item, str) or item.startswith("/") or ".." in Path(item).parts
            or str(Path(item)) != item or not item.startswith(("tools/", "tests/", "docs/", ".ai/"))
            for item in paths
        )
        or len(paths) != len(set(paths))
    ):
        raise ExplorationGrantError("grant path-change scope missing, duplicated or unbounded")
    return dict(grant)


def extract_grant(body: Any) -> dict[str, Any]:
    if not isinstance(body, str):
        raise ExplorationGrantError("owner grant is not text")
    lines = body.strip().splitlines()
    fence = chr(96) * 3
    if len(lines) < 4 or lines[0] != MARKER or lines[1] != fence + "json" or lines[-1] != fence:
        raise ExplorationGrantError("owner grant must be one standalone structured JSON comment")
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ExplorationGrantError("execution JSON contains duplicate keys")
            result[key] = value
        return result

    try:
        return validate_grant(json.loads(
            "\n".join(lines[2:-1]),
            object_pairs_hook=reject_duplicate_keys,
        ))
    except json.JSONDecodeError as exc:
        raise ExplorationGrantError("owner execution JSON is invalid") from exc


def verify_owner_execution_grant(
    comment_id: int,
    *,
    issue_reader: Callable[[], Any] | None = None,
    comments_reader: Callable[[], Any] | None = None,
) -> tuple[dict[str, Any], str]:
    if type(comment_id) is not int or comment_id <= ledger.BUDGET_COMMENT_ID:
        raise ExplorationGrantError("a distinct later exact owner execution comment is required")
    if issue_reader is None:
        issue_reader = lambda: rehearsal._gh_json(["repos/rinsakamo/relay-lm/issues/3018"])
    if comments_reader is None:
        comments_reader = rehearsal._gh_comments
    try:
        issue, comments = issue_reader(), comments_reader()
    except Exception as exc:
        raise ExplorationGrantError("fresh #3018 owner lookup failed") from exc
    if (
        not isinstance(issue, dict) or issue.get("number") != 3018 or issue.get("state") != "open"
        or not isinstance(issue.get("user"), dict) or issue["user"].get("login") != OWNER
        or not isinstance(comments, list)
    ):
        raise ExplorationGrantError("owner issue is not the required open #3018")
    selected = next((c for c in comments if isinstance(c, dict) and c.get("id") == comment_id), None)
    if not isinstance(selected, dict) or not isinstance(selected.get("user"), dict) or selected["user"].get("login") != OWNER:
        raise ExplorationGrantError("exact later owner grant was not found")
    grant = extract_grant(selected.get("body"))
    selected_time = str(selected.get("created_at", ""))
    for c in comments:
        if not isinstance(c, dict) or not isinstance(c.get("user"), dict) or c["user"].get("login") != OWNER:
            continue
        later_id = c.get("id")
        later = (type(later_id) is int and later_id > comment_id) or (
            bool(selected_time) and str(c.get("created_at", "")) > selected_time
        )
        if later and isinstance(c.get("body"), str) and any(
            c["body"].strip().startswith(marker) for marker in REVOKE_MARKERS
        ):
            raise ExplorationGrantError("a later owner comment revoked this campaign")
    return grant, grant_sha256(grant)
