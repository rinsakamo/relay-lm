from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from relaylm.actual_model_targets import load_actual_model_repository_snapshot_target
from relaylm.actual_model_vllm_counter import VLLMServingTokenizerCounter
from relaylm.actual_model_vllm_host import (
    CANONICAL_VLLM_TARGET_PATH,
    VLLMScreeningPlan,
    acquire_vllm_reasoning_capability,
    load_vllm_reasoning_probe_proof,
    prepare_vllm_screening_condition as _prepare_vllm_screening_condition,
)
from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetDegradationStep,
    BudgetLayer,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_runtime import (
    TwoPassCognitiveBudgetRuntimeConfig,
    TwoPassSerializedInputTokenCounter,
)
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleTwoPassSerializedInputCounter,
)


VLLM_TWO_PASS_BUDGET_DECLARATION_FORMAT_VERSION = 1
FetchJSON = Callable[[str, str | None], object]


class VLLMCognitiveBudgetDeclarationError(ValueError):
    """A caller-supplied vLLM cognitive-budget declaration is not citable."""


@dataclass(frozen=True, slots=True)
class VLLMTwoPassCognitiveBudgetDeclaration:
    """Counter-independent caller authority for one explicit two-pass budget.

    The caller owns only numeric Pass 1 / Pass 2 totals and the existing #1387
    deterministic degradation policy. Provider/tokenizer counting remains a
    fresh host-owned fact and is deliberately absent from this declaration.
    """

    pass1_total: TotalBudgetConfig
    pass2_total: TotalBudgetConfig
    policy: BudgetDegradationPolicy
    format_version: int = VLLM_TWO_PASS_BUDGET_DECLARATION_FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != VLLM_TWO_PASS_BUDGET_DECLARATION_FORMAT_VERSION:
            raise VLLMCognitiveBudgetDeclarationError(
                "unsupported vLLM cognitive budget declaration format_version"
            )
        if not isinstance(self.pass1_total, TotalBudgetConfig):
            raise TypeError("pass1_total must be TotalBudgetConfig")
        if not isinstance(self.pass2_total, TotalBudgetConfig):
            raise TypeError("pass2_total must be TotalBudgetConfig")
        if not isinstance(self.policy, BudgetDegradationPolicy):
            raise TypeError("policy must be BudgetDegradationPolicy")

    def to_runtime(
        self,
        *,
        token_counter: TwoPassSerializedInputTokenCounter,
    ) -> TwoPassCognitiveBudgetRuntimeConfig:
        return TwoPassCognitiveBudgetRuntimeConfig(
            pass1_total=self.pass1_total,
            pass2_total=self.pass2_total,
            policy=self.policy,
            token_counter=token_counter,
        )


def load_vllm_two_pass_cognitive_budget_declaration(
    path: str | Path,
) -> VLLMTwoPassCognitiveBudgetDeclaration:
    """Load strict external budget policy without accepting live counter facts."""

    mapping = _load_json_mapping(path)
    _require_exact_keys(
        mapping,
        {
            "format_version",
            "mode",
            "pass1",
            "pass2",
            "initial_plan",
            "degradation_steps",
        },
        "cognitive budget declaration",
    )
    if _integer(mapping["format_version"], "format_version") != 1:
        raise VLLMCognitiveBudgetDeclarationError(
            "unsupported vLLM cognitive budget declaration format_version"
        )
    if _string(mapping["mode"], "mode") != "two_pass":
        raise VLLMCognitiveBudgetDeclarationError(
            "vLLM cognitive budget declaration mode must be two_pass"
        )
    try:
        return VLLMTwoPassCognitiveBudgetDeclaration(
            pass1_total=_parse_total(mapping["pass1"], "pass1"),
            pass2_total=_parse_total(mapping["pass2"], "pass2"),
            policy=BudgetDegradationPolicy(
                initial_plan=_parse_budget_plan(mapping["initial_plan"]),
                steps=tuple(_parse_degradation_steps(mapping["degradation_steps"])),
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, VLLMCognitiveBudgetDeclarationError):
            raise
        raise VLLMCognitiveBudgetDeclarationError(
            f"invalid cognitive budget declaration: {exc}"
        ) from exc


def prepare_vllm_screening_condition_with_budget_declaration(
    *,
    plan: VLLMScreeningPlan,
    condition_id: str,
    proof_path: str | Path,
    repo_root: str | Path,
    snapshot_root: str | Path,
    relaylm_commit: str,
    base_url: str,
    api_key: str | None,
    model_runner: str | None = None,
    replicate_id: str = "0",
    fetch_json: FetchJSON | None = None,
    capacity_evidence_root: str | Path | None = None,
    cognitive_budget: VLLMTwoPassCognitiveBudgetDeclaration | None = None,
):
    """Resolve an external declaration into the canonical host-owned runtime.

    The declaration never supplies a counter implementation or counter identity.
    For an explicit budget, this facade helper reconstructs the current live vLLM
    counting capability using the same canonical target/proof APIs, then delegates
    to the existing host preparation boundary. That boundary independently
    re-attests live identity, validates cited capacity evidence, and rebinds the
    runtime to its own fresh serving-tokenizer counter before generation.
    """

    if cognitive_budget is None:
        return _prepare_vllm_screening_condition(
            plan=plan,
            condition_id=condition_id,
            proof_path=proof_path,
            repo_root=repo_root,
            snapshot_root=snapshot_root,
            relaylm_commit=relaylm_commit,
            base_url=base_url,
            api_key=api_key,
            model_runner=model_runner,
            replicate_id=replicate_id,
            fetch_json=fetch_json,
            capacity_evidence_root=capacity_evidence_root,
            cognitive_budget=None,
        )
    if not isinstance(cognitive_budget, VLLMTwoPassCognitiveBudgetDeclaration):
        raise TypeError(
            "cognitive_budget must be VLLMTwoPassCognitiveBudgetDeclaration or None"
        )

    root = Path(repo_root).resolve()
    target = load_actual_model_repository_snapshot_target(
        root / CANONICAL_VLLM_TARGET_PATH
    )
    proof = load_vllm_reasoning_probe_proof(proof_path)
    capability = acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url=base_url,
        api_key=api_key,
        fetch_json=fetch_json,
    )
    live_counter = VLLMServingTokenizerCounter(
        base_url=base_url,
        target=target,
        reasoning_capability=capability,
        expected_max_model_len=capability.backend_attestation.max_model_len,
        api_key=api_key,
    )
    serialized_counter = OpenAICompatibleTwoPassSerializedInputCounter(
        model=capability.request_model,
        count_input=live_counter.count_input,
        decoding_config=plan.decoding_config,
        decoding_capabilities=plan.decoding_capabilities,
        vllm_reasoning_capability=capability,
        evidence_identity=live_counter.evidence_identity,
    )
    runtime = cognitive_budget.to_runtime(token_counter=serialized_counter)
    return _prepare_vllm_screening_condition(
        plan=plan,
        condition_id=condition_id,
        proof_path=proof_path,
        repo_root=repo_root,
        snapshot_root=snapshot_root,
        relaylm_commit=relaylm_commit,
        base_url=base_url,
        api_key=api_key,
        model_runner=model_runner,
        replicate_id=replicate_id,
        fetch_json=fetch_json,
        capacity_evidence_root=capacity_evidence_root,
        cognitive_budget=runtime,
    )


def _parse_total(value: object, label: str) -> TotalBudgetConfig:
    mapping = _mapping(value, label)
    _require_exact_keys(
        mapping,
        {"model_context_window", "reserved_output_tokens"},
        label,
    )
    return TotalBudgetConfig(
        model_context_window=_integer(
            mapping["model_context_window"], f"{label}.model_context_window"
        ),
        reserved_output_tokens=_integer(
            mapping["reserved_output_tokens"], f"{label}.reserved_output_tokens"
        ),
    )


def _parse_budget_plan(value: object) -> BudgetPlan:
    label = "initial_plan"
    mapping = _mapping(value, label)
    _require_exact_keys(
        mapping,
        {"canonical_state", "working_context", "retrieved_memory", "event_evidence"},
        label,
    )
    return BudgetPlan(
        canonical_state=_parse_count_envelope(
            mapping["canonical_state"], f"{label}.canonical_state"
        ),
        working_context=_parse_count_character_envelope(
            mapping["working_context"], f"{label}.working_context"
        ),
        retrieved_memory=_parse_count_character_envelope(
            mapping["retrieved_memory"], f"{label}.retrieved_memory"
        ),
        event_evidence=_parse_count_character_envelope(
            mapping["event_evidence"], f"{label}.event_evidence"
        ),
    )


def _parse_degradation_steps(value: object) -> list[BudgetDegradationStep]:
    items = _list(value, "degradation_steps")
    steps: list[BudgetDegradationStep] = []
    for index, raw in enumerate(items):
        label = f"degradation_steps[{index}]"
        mapping = _mapping(raw, label)
        _require_exact_keys(mapping, {"layer", "tier", "target"}, label)
        layer_name = _string(mapping["layer"], f"{label}.layer")
        try:
            layer = BudgetLayer(layer_name)
        except ValueError as exc:
            raise VLLMCognitiveBudgetDeclarationError(
                f"{label}.layer is not a supported budget layer"
            ) from exc
        tier = _integer(mapping["tier"], f"{label}.tier")
        if tier != layer.tier:
            raise VLLMCognitiveBudgetDeclarationError(
                f"{label}.tier does not match the canonical layer tier"
            )
        if layer is BudgetLayer.CANONICAL_STATE:
            target = _parse_count_envelope(mapping["target"], f"{label}.target")
        else:
            target = _parse_count_character_envelope(
                mapping["target"], f"{label}.target"
            )
        steps.append(BudgetDegradationStep(layer=layer, target=target))
    return steps


def _parse_count_envelope(value: object, label: str) -> CountEnvelope:
    mapping = _mapping(value, label)
    _require_exact_keys(mapping, {"max_items", "floor_items"}, label)
    return CountEnvelope(
        max_items=_integer(mapping["max_items"], f"{label}.max_items"),
        floor_items=_integer(mapping["floor_items"], f"{label}.floor_items"),
    )


def _parse_count_character_envelope(
    value: object,
    label: str,
) -> CountCharacterEnvelope:
    mapping = _mapping(value, label)
    _require_exact_keys(
        mapping,
        {"max_items", "floor_items", "max_chars", "floor_chars"},
        label,
    )
    return CountCharacterEnvelope(
        max_items=_integer(mapping["max_items"], f"{label}.max_items"),
        floor_items=_integer(mapping["floor_items"], f"{label}.floor_items"),
        max_chars=_integer(mapping["max_chars"], f"{label}.max_chars"),
        floor_chars=_integer(mapping["floor_chars"], f"{label}.floor_chars"),
    )


def _load_json_mapping(path: str | Path) -> Mapping[str, object]:
    try:
        raw = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VLLMCognitiveBudgetDeclarationError(
            f"cannot load cognitive budget declaration: {exc}"
        ) from exc
    return _mapping(raw, "cognitive budget declaration")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VLLMCognitiveBudgetDeclarationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise VLLMCognitiveBudgetDeclarationError(f"{label} must be a JSON object")
    if not all(isinstance(key, str) for key in value):
        raise VLLMCognitiveBudgetDeclarationError(f"{label} keys must be strings")
    return value


def _list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise VLLMCognitiveBudgetDeclarationError(f"{label} must be a JSON array")
    return value


def _require_exact_keys(
    mapping: Mapping[str, object],
    expected: set[str],
    label: str,
) -> None:
    observed = set(mapping)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        raise VLLMCognitiveBudgetDeclarationError(
            f"{label} is missing fields: " + ", ".join(missing)
        )
    if unknown:
        raise VLLMCognitiveBudgetDeclarationError(
            f"{label} has unknown fields: " + ", ".join(unknown)
        )


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VLLMCognitiveBudgetDeclarationError(f"{label} must be a non-empty string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VLLMCognitiveBudgetDeclarationError(f"{label} must be an integer")
    return value
