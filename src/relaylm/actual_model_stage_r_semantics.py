from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from relaylm.actual_model_evaluation import (
    ActualModelCognitionPassRequests,
    ExplicitContinuityRuntimeConfiguration,
)
from relaylm.actual_model_scenarios import (
    ActualModelScenarioSet,
    load_actual_model_scenario_set,
)
from relaylm.cognition_execution import (
    CognitionPassRequest,
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
from relaylm.cognition_execution_evidence import CognitionExecutionEvidenceIdentity


CURRENT_STAGE_R_SEMANTIC_AUTHORITY_PATH = Path(
    "evaluation/actual_model/screenings/stage-r-current-v1.json"
)
CURRENT_STAGE_R_SEMANTIC_AUTHORITY_FORMAT_VERSION = 1
CURRENT_STAGE_R_SEMANTIC_AUTHORITY_ID = "stage-r-current-v1"


class StageRSemanticAuthorityError(ValueError):
    """The provider-neutral current Stage R semantic authority is invalid."""


@dataclass(frozen=True, slots=True)
class StageRSemanticAuthority:
    authority_id: str
    scenario_set_path: str
    scenario_set_revision: str
    execution_path: str
    continuity_runtime: ExplicitContinuityRuntimeConfiguration
    scenario_ids: tuple[str, ...]
    temperature: int | float
    top_p: int | float
    seed: int | None
    reasoning_preference: str
    pass1_structured_output: str | None
    pass2_structured_output: str
    format_version: int = CURRENT_STAGE_R_SEMANTIC_AUTHORITY_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != CURRENT_STAGE_R_SEMANTIC_AUTHORITY_FORMAT_VERSION:
            raise StageRSemanticAuthorityError(
                "unsupported current Stage R semantic authority format_version"
            )
        if self.authority_id != CURRENT_STAGE_R_SEMANTIC_AUTHORITY_ID:
            raise StageRSemanticAuthorityError(
                "unexpected current Stage R semantic authority_id"
            )
        scenario_path = Path(self.scenario_set_path)
        if scenario_path.is_absolute() or ".." in scenario_path.parts:
            raise StageRSemanticAuthorityError(
                "current Stage R scenario-set path must be repository-relative"
            )
        if (
            not self.scenario_set_revision.startswith("sha256:")
            or len(self.scenario_set_revision) != 71
        ):
            raise StageRSemanticAuthorityError(
                "current Stage R scenario-set revision must be sha256"
            )
        if self.execution_path != "buffered":
            raise StageRSemanticAuthorityError(
                "current Stage R semantic reference must use buffered execution"
            )
        if not self.scenario_ids or len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise StageRSemanticAuthorityError(
                "current Stage R scenario_ids must be non-empty and unique"
            )
        if self.reasoning_preference != "off":
            raise StageRSemanticAuthorityError(
                "current Stage R reasoning preference must remain off"
            )
        if self.pass1_structured_output is not None:
            raise StageRSemanticAuthorityError(
                "current Stage R Pass 1 must remain ordinary plain conversation"
            )
        if self.pass2_structured_output != "native":
            raise StageRSemanticAuthorityError(
                "current Stage R Pass 2 must require native structured output"
            )

    @property
    def cognition_execution(self) -> CognitionExecutionEvidenceIdentity:
        return CognitionExecutionEvidenceIdentity.two_pass(
            execution_path=self.execution_path
        )

    def pass_requests(
        self,
        *,
        reasoning_mode: CognitionReasoningMode | None,
    ) -> ActualModelCognitionPassRequests:
        """Build the exact requests for the actually realized reasoning condition.

        `reasoning_mode=None` means no per-request reasoning field is carried. The
        semantic authority still records OFF as the preferred reference; the run
        evidence must separately record the observed provider/model default.
        """

        if reasoning_mode is CognitionReasoningMode.AUTO:
            raise StageRSemanticAuthorityError(
                "reasoning auto is unresolved and cannot enter Stage R evidence"
            )
        pass1 = CognitionPassRequest(
            reasoning_mode=reasoning_mode,
            temperature=self.temperature,
            top_p=self.top_p,
            structured_output_mode=None,
        )
        pass2 = CognitionPassRequest(
            reasoning_mode=reasoning_mode,
            temperature=self.temperature,
            top_p=self.top_p,
            structured_output_mode=CognitionStructuredOutputMode.NATIVE,
        )
        return ActualModelCognitionPassRequests.two_pass(
            pass1=pass1,
            pass2=pass2,
        )


def load_stage_r_semantic_authority(
    path: str | Path,
) -> StageRSemanticAuthority:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StageRSemanticAuthorityError(
            f"cannot load current Stage R semantic authority: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise StageRSemanticAuthorityError(
            "current Stage R semantic authority must be a JSON object"
        )
    expected = {
        "format_version",
        "authority_id",
        "scenario_set_path",
        "scenario_set_revision",
        "execution_path",
        "continuity_runtime",
        "scenario_ids",
        "decoding",
        "reasoning_preference",
        "pass1_structured_output",
        "pass2_structured_output",
    }
    _require_exact_keys(raw, expected, "current Stage R semantic authority")
    continuity = _mapping(raw["continuity_runtime"], "continuity_runtime")
    _require_exact_keys(
        continuity,
        {"max_items", "lifetime_revisions"},
        "continuity_runtime",
    )
    decoding = _mapping(raw["decoding"], "decoding")
    _require_exact_keys(decoding, {"temperature", "top_p", "seed"}, "decoding")
    scenario_ids_raw = raw["scenario_ids"]
    if not isinstance(scenario_ids_raw, list) or not all(
        isinstance(item, str) and item.strip() for item in scenario_ids_raw
    ):
        raise StageRSemanticAuthorityError(
            "scenario_ids must be an array of non-empty strings"
        )
    seed = decoding["seed"]
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise StageRSemanticAuthorityError("decoding seed must be integer or null")
    return StageRSemanticAuthority(
        format_version=_integer(raw["format_version"], "format_version"),
        authority_id=_string(raw["authority_id"], "authority_id"),
        scenario_set_path=_string(raw["scenario_set_path"], "scenario_set_path"),
        scenario_set_revision=_string(
            raw["scenario_set_revision"], "scenario_set_revision"
        ),
        execution_path=_string(raw["execution_path"], "execution_path"),
        continuity_runtime=ExplicitContinuityRuntimeConfiguration(
            max_items=_integer(continuity["max_items"], "continuity max_items"),
            lifetime_revisions=_integer(
                continuity["lifetime_revisions"],
                "continuity lifetime_revisions",
            ),
        ),
        scenario_ids=tuple(scenario_ids_raw),
        temperature=_number(decoding["temperature"], "temperature"),
        top_p=_number(decoding["top_p"], "top_p"),
        seed=seed,
        reasoning_preference=_string(
            raw["reasoning_preference"], "reasoning_preference"
        ),
        pass1_structured_output=_optional_string(
            raw["pass1_structured_output"], "pass1_structured_output"
        ),
        pass2_structured_output=_string(
            raw["pass2_structured_output"], "pass2_structured_output"
        ),
    )


def load_current_stage_r_scenario_set(
    *,
    repo_root: str | Path,
    authority: StageRSemanticAuthority,
) -> ActualModelScenarioSet:
    root = Path(repo_root).resolve()
    path = (root / authority.scenario_set_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise StageRSemanticAuthorityError(
            "current Stage R scenario set must remain inside repo_root"
        ) from exc
    scenario_set = load_actual_model_scenario_set(path)
    if scenario_set.revision != authority.scenario_set_revision:
        raise StageRSemanticAuthorityError(
            "current Stage R scenario-set revision does not match semantic authority"
        )
    observed_ids = tuple(item.scenario.scenario_id for item in scenario_set.scenarios)
    if observed_ids != authority.scenario_ids:
        raise StageRSemanticAuthorityError(
            "current Stage R scenario IDs do not match semantic authority"
        )
    return scenario_set


def _require_exact_keys(mapping: dict[str, object], expected: set[str], label: str) -> None:
    if set(mapping) != expected:
        missing = sorted(expected - set(mapping))
        unknown = sorted(set(mapping) - expected)
        detail: list[str] = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if unknown:
            detail.append("unknown: " + ", ".join(unknown))
        suffix = ": " + "; ".join(detail) if detail else ""
        raise StageRSemanticAuthorityError(f"{label} fields are not exact{suffix}")


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise StageRSemanticAuthorityError(f"{label} must be an object")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StageRSemanticAuthorityError(f"{label} must be a non-empty string")
    return value


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StageRSemanticAuthorityError(f"{label} must be an integer")
    return value


def _number(value: object, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StageRSemanticAuthorityError(f"{label} must be numeric")
    return value
