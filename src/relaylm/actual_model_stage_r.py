from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit

from relaylm.actual_model_fast_screening import SCREENING_CONDITION_ROLES
from relaylm.actual_model_host import main as _host_main
from relaylm.actual_model_stage_r_lm_studio import main as _lm_studio_stage_r_main


CURRENT_STAGE_R_AUTHORITY_PATH = Path(
    "evaluation/actual_model/screenings/stage-r0-vllm-current-v1.json"
)
CURRENT_STAGE_R_AUTHORITY_FORMAT_VERSION = 1
CURRENT_STAGE_R_AUTHORITY_ID = "stage-r0-vllm-current-v1"
CURRENT_CONTEXT_WINDOW_SOURCE = "fresh_external_capacity_evidence"
CURRENT_HARDWARE_CAPABILITY_SOURCE = "qualified_vllm_token_capacity_reference"


class StageRAuthorityError(ValueError):
    """The current Stage R authority cannot be executed truthfully."""


@dataclass(frozen=True, slots=True)
class CurrentStageRAuthority:
    """Legacy/current vLLM physical admission authority for Stage R."""

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
                "current Stage R vLLM context window must come from fresh external capacity evidence"
            )
        if self.hardware_capability_source != CURRENT_HARDWARE_CAPABILITY_SOURCE:
            raise StageRAuthorityError(
                "current Stage R vLLM hardware capability must come from a qualified "
                "vLLM token-capacity reference"
            )
        template = Path(self.execution_template_path)
        if template.is_absolute() or ".." in template.parts:
            raise StageRAuthorityError(
                "current Stage R vLLM execution template path must be repository-relative"
            )


def load_current_stage_r_authority(path: str | Path) -> CurrentStageRAuthority:
    """Load the backend-specific vLLM physical admission descriptor."""

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
            "current Stage R authority fields are not exact"
            + (": " + "; ".join(detail) if detail else "")
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
            "Run current provider-neutral Stage R semantics through a selected "
            "backend-specific physical admission path."
        )
    )
    parser.add_argument(
        "--backend",
        choices=("vllm", "lm_studio"),
        default="vllm",
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
    parser.add_argument("--snapshot-root")
    parser.add_argument("--provider-base-url", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--model-runner", choices=("v1", "v2"))
    parser.add_argument("--request-model")
    parser.add_argument("--loaded-instance-id")
    parser.add_argument("--replicate-id", default="0")
    parser.add_argument("--provider-api-key-env")
    parser.add_argument("--cognitive-budget")
    parser.add_argument("--capacity-evidence-id")
    parser.add_argument("--capacity-evidence-root")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.backend == "lm_studio":
        return _run_lm_studio(args)
    return _run_vllm(args)


def _run_lm_studio(args: argparse.Namespace) -> int:
    if args.operation != "screening":
        raise StageRAuthorityError(
            "LM Studio Stage R consumes its observed loaded context directly and "
            "does not run vLLM capacity acquisition"
        )
    if args.condition != "reference_baseline":
        raise StageRAuthorityError(
            "LM Studio current Stage R exposes only the reference_baseline semantic run"
        )
    if not isinstance(args.request_model, str) or not args.request_model.strip():
        raise StageRAuthorityError(
            "LM Studio Stage R requires --request-model for unambiguous run evidence"
        )
    if args.snapshot_root is not None or args.model_runner is not None:
        raise StageRAuthorityError(
            "LM Studio Stage R must not consume vLLM snapshot/model-runner arguments"
        )
    if args.capacity_evidence_id is not None or args.capacity_evidence_root is not None:
        raise StageRAuthorityError(
            "LM Studio Stage R must not consume vLLM capacity evidence"
        )
    if args.cognitive_budget is not None:
        raise StageRAuthorityError(
            "LM Studio observed-context Stage R does not accept the vLLM screening cognitive-budget facade"
        )

    delegated = [
        "--repo-root",
        args.repo_root,
        "--provider-base-url",
        args.provider_base_url,
        "--request-model",
        args.request_model,
        "--workspace-root",
        args.workspace_root,
        "--artifact-root",
        args.artifact_root,
        "--replicate-id",
        args.replicate_id,
    ]
    if args.loaded_instance_id is not None:
        delegated.extend(["--loaded-instance-id", args.loaded_instance_id])
    if args.provider_api_key_env is not None:
        delegated.extend(["--provider-api-key-env", args.provider_api_key_env])
    return _lm_studio_stage_r_main(delegated)


def _run_vllm(args: argparse.Namespace) -> int:
    _require_vllm_openai_api_base_url(args.provider_base_url)
    if not isinstance(args.snapshot_root, str) or not args.snapshot_root.strip():
        raise StageRAuthorityError("vLLM Stage R requires --snapshot-root")
    if args.model_runner not in {"v1", "v2"}:
        raise StageRAuthorityError("vLLM Stage R requires --model-runner v1 or v2")
    if args.request_model is not None or args.loaded_instance_id is not None:
        raise StageRAuthorityError(
            "vLLM Stage R does not consume LM Studio request-model/instance arguments"
        )

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
            "current Stage R vLLM screening requires fresh external capacity evidence"
        )
    if args.operation == "capacity" and any(capacity_pair):
        raise StageRAuthorityError(
            "current Stage R vLLM capacity acquisition must not consume prior capacity evidence"
        )
    if args.operation == "capacity" and args.cognitive_budget is not None:
        raise StageRAuthorityError(
            "--cognitive-budget is valid only for current Stage R vLLM screening"
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


def _require_vllm_openai_api_base_url(base_url: str) -> None:
    if not isinstance(base_url, str) or not base_url.strip():
        raise StageRAuthorityError(
            "current Stage R vLLM provider base URL must be a non-empty HTTP(S) URL ending in /v1"
        )
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise StageRAuthorityError(
            "current Stage R vLLM provider base URL must be an HTTP(S) URL ending in /v1"
        )
    if parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/v1":
        raise StageRAuthorityError(
            "current Stage R vLLM provider base URL must use the OpenAI API base path /v1"
        )


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
