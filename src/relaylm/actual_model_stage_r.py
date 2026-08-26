from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from relaylm.actual_model_fast_screening import SCREENING_CONDITION_ROLES
from relaylm.actual_model_host import main as _host_main


CURRENT_STAGE_R_AUTHORITY_PATH = Path(
    "evaluation/actual_model/screenings/stage-r0-vllm-current-v1.json"
)
CURRENT_STAGE_R_AUTHORITY_FORMAT_VERSION = 1
CURRENT_STAGE_R_AUTHORITY_ID = "stage-r0-vllm-current-v1"
CURRENT_CONTEXT_WINDOW_SOURCE = "fresh_external_capacity_evidence"
CURRENT_HARDWARE_CAPABILITY_SOURCE = "fresh_vllm_profiler_auto_kv"


class StageRAuthorityError(ValueError):
    """The current Stage R authority cannot be executed truthfully."""


@dataclass(frozen=True, slots=True)
class CurrentStageRAuthority:
    authority_id: str
    execution_template_path: str
    context_window_source: str
    hardware_capability_source: str
    format_version: int = CURRENT_STAGE_R_AUTHORITY_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != CURRENT_STAGE_R_AUTHORITY_FORMAT_VERSION:
            raise StageRAuthorityError("unsupported current Stage R authority format_version")
        if self.authority_id != CURRENT_STAGE_R_AUTHORITY_ID:
            raise StageRAuthorityError("unexpected current Stage R authority_id")
        if self.context_window_source != CURRENT_CONTEXT_WINDOW_SOURCE:
            raise StageRAuthorityError(
                "current Stage R context window must come from fresh external capacity evidence"
            )
        if self.hardware_capability_source != CURRENT_HARDWARE_CAPABILITY_SOURCE:
            raise StageRAuthorityError(
                "current Stage R hardware capability must come from fresh vLLM profiling"
            )
        template = Path(self.execution_template_path)
        if template.is_absolute() or ".." in template.parts:
            raise StageRAuthorityError(
                "current Stage R execution template path must be repository-relative"
            )


def load_current_stage_r_authority(path: str | Path) -> CurrentStageRAuthority:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StageRAuthorityError(f"cannot load current Stage R authority: {exc}") from exc
    if not isinstance(raw, dict):
        raise StageRAuthorityError("current Stage R authority must be a JSON object")
    expected = {
        "format_version",
        "authority_id",
        "execution_template_path",
        "context_window_source",
        "hardware_capability_source",
    }
    if set(raw) != expected:
        missing = sorted(expected - set(raw))
        unknown = sorted(set(raw) - expected)
        detail: list[str] = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if unknown:
            detail.append("unknown: " + ", ".join(unknown))
        raise StageRAuthorityError(
            "current Stage R authority fields are not exact" + (
                ": " + "; ".join(detail) if detail else ""
            )
        )
    try:
        return CurrentStageRAuthority(
            format_version=_integer(raw["format_version"], "format_version"),
            authority_id=_string(raw["authority_id"], "authority_id"),
            execution_template_path=_string(
                raw["execution_template_path"], "execution_template_path"
            ),
            context_window_source=_string(
                raw["context_window_source"], "context_window_source"
            ),
            hardware_capability_source=_string(
                raw["hardware_capability_source"], "hardware_capability_source"
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, StageRAuthorityError):
            raise
        raise StageRAuthorityError(f"invalid current Stage R authority: {exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run current Stage R through a small authority surface that always "
            "binds screening capacity from fresh external evidence."
        )
    )
    parser.add_argument(
        "--operation",
        choices=("capacity", "screening"),
        required=True,
    )
    parser.add_argument(
        "--condition",
        choices=SCREENING_CONDITION_ROLES,
        required=True,
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--snapshot-root", required=True)
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--model-runner", required=True, choices=("v1", "v2"))
    parser.add_argument("--replicate-id", default="0")
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--cognitive-budget")
    parser.add_argument("--capacity-evidence-id")
    parser.add_argument("--capacity-evidence-root")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    repo_root = Path(args.repo_root).resolve()
    authority = load_current_stage_r_authority(
        repo_root / CURRENT_STAGE_R_AUTHORITY_PATH
    )
    template_path = repo_root / authority.execution_template_path
    try:
        template_path.resolve().relative_to(repo_root)
    except ValueError as exc:
        raise StageRAuthorityError(
            "current Stage R execution template must remain inside repo_root"
        ) from exc
    if not template_path.is_file():
        raise StageRAuthorityError(
            "current Stage R execution template does not exist"
        )

    capacity_pair = (
        args.capacity_evidence_id is not None,
        args.capacity_evidence_root is not None,
    )
    if capacity_pair[0] != capacity_pair[1]:
        raise StageRAuthorityError(
            "--capacity-evidence-id and --capacity-evidence-root must be supplied together"
        )
    if args.operation == "screening" and not all(capacity_pair):
        raise StageRAuthorityError(
            "current Stage R screening requires fresh external capacity evidence"
        )
    if args.operation == "capacity" and any(capacity_pair):
        raise StageRAuthorityError(
            "current Stage R capacity acquisition must not consume prior capacity evidence"
        )
    if args.operation == "capacity" and args.cognitive_budget is not None:
        raise StageRAuthorityError(
            "--cognitive-budget is valid only for current Stage R screening"
        )

    delegated = [
        "--backend",
        "vllm",
        "--operation",
        args.operation,
        "--condition",
        args.condition,
        "--repo-root",
        str(repo_root),
        "--snapshot-root",
        args.snapshot_root,
        "--provider-base-url",
        args.provider_base_url,
        "--workspace-root",
        args.workspace_root,
        "--artifact-root",
        args.artifact_root,
        "--model-runner",
        args.model_runner,
        "--replicate-id",
        args.replicate_id,
        "--screening-plan",
        authority.execution_template_path,
    ]
    if args.provider_api_key_env is not None:
        delegated.extend(["--provider-api-key-env", args.provider_api_key_env])
    if args.cognitive_budget is not None:
        delegated.extend(["--cognitive-budget", args.cognitive_budget])
    if args.operation == "screening":
        assert args.capacity_evidence_id is not None
        assert args.capacity_evidence_root is not None
        delegated.extend(
            [
                "--capacity-evidence-id",
                args.capacity_evidence_id,
                "--capacity-evidence-root",
                args.capacity_evidence_root,
                "--context-window-from-capacity-evidence",
            ]
        )
    return _host_main(delegated)


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StageRAuthorityError(f"{label} must be a non-empty string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StageRAuthorityError(f"{label} must be an integer")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
