from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import permutations

from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import (
    CALIBRATION_V2_REGIMES,
    CALIBRATION_V2_SEEDS,
    CalibrationV2RegimeSummary,
    select_calibration_v2_regime,
)
from relaylm.v2_transfer_experiment import (
    PublicExample,
    TargetStep,
    TransferFamily,
    VectorRule,
)


S2_SELECTED_LABEL = "relaylm2-cognitive-ir-s2-selected-regime-v1"
S2_SELECTED_REGIME = "V2_IDENTITY_OFFSET_NO_WRAP"
S2_SELECTED_MODULUS = 10
S2_SELECTED_VECTOR_WIDTH = 4
S2_SELECTED_STEP_INDEX = 0
S2_SELECTED_EXAMPLES_VISIBLE = 0
S2_SELECTED_SOURCE_EXAMPLES = 4
S2_SELECTED_TARGET_EXAMPLES = 3
S2_SELECTED_PHYSICAL_CALLS = 10

CALIBRATION_V2_ADMISSION_REPOSITORY_COMMIT = (
    "ff89c5cb20bb4089ad52ea4a2d1992e64e5c5ea9"
)
CALIBRATION_V2_ADMISSION_RUN_ID = (
    "calv2-8eb503b4598857c6768cdc67948e5f42e4dac76b4e268e43b0ee009320966ee0"
)
CALIBRATION_V2_ADMISSION_IDENTITY_FINGERPRINT = (
    "sha256:21a9b484df100f616386f55165f5aec5f71de2235f40d9b0e44ff00b96cce310"
)


class S2SelectedRegimeError(ValueError):
    """The selected-regime #2211 S2 preregistration contract was violated."""


def _seed_bytes(seed: int, label: str) -> bytes:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if not isinstance(label, str) or not label:
        raise TypeError("seed label must be non-empty")
    return hashlib.sha256(f"{S2_SELECTED_LABEL}|{seed}|{label}".encode("utf-8")).digest()


def _derive_seed() -> int:
    raw = hashlib.sha256(f"{S2_SELECTED_LABEL}|seed|0".encode("utf-8")).digest()
    seed = int.from_bytes(raw[:4], "big") & 0x7FFFFFFF
    forbidden = {2211, *CALIBRATION_SEEDS, *CALIBRATION_V2_SEEDS}
    if seed in forbidden:
        raise AssertionError("selected-regime S2 seed overlaps historical calibration evidence")
    return seed


S2_SELECTED_SEED = _derive_seed()


def calibration_v2_admission_summaries() -> tuple[CalibrationV2RegimeSummary, ...]:
    """Freeze the completed calibration-v2 counts used to admit this S2 family.

    These are historical admission evidence, not current physical authority. Replaying
    them only proves that the preregistered calibration-v2 selector chooses the same
    task regime from the recorded completed transaction.
    """

    counts = {
        "V2_SINGLE_SWAP_ZERO_OFFSET": (6, 6, 5),
        "V2_IDENTITY_OFFSET_NO_WRAP": (6, 5, 4),
        "V2_IDENTITY_OFFSET_WRAP": (6, 2, 1),
        "V2_SINGLE_SWAP_OFFSET_NO_WRAP": (2, 0, 0),
    }
    return tuple(
        CalibrationV2RegimeSummary(
            regime=regime,
            sample_count=6,
            application_correct=counts[regime][0],
            formation_correct=counts[regime][1],
            end_to_end_joint_correct=counts[regime][2],
        )
        for regime in CALIBRATION_V2_REGIMES
    )


def replay_selected_regime() -> str:
    selected = select_calibration_v2_regime(calibration_v2_admission_summaries())
    if selected != S2_SELECTED_REGIME:
        raise S2SelectedRegimeError(
            "frozen calibration-v2 evidence no longer selects the preregistered S2 regime"
        )
    return selected


def _identity_permutation() -> tuple[int, ...]:
    return tuple(range(S2_SELECTED_VECTOR_WIDTH))


def _nonzero_offsets(seed: int) -> tuple[int, ...]:
    return tuple(
        1 + (_seed_bytes(seed, f"factor:offsets:offset:{index}")[0] % 3)
        for index in range(S2_SELECTED_VECTOR_WIDTH)
    )


def _rule(seed: int) -> VectorRule:
    return VectorRule(
        _identity_permutation(),
        _nonzero_offsets(seed),
        S2_SELECTED_MODULUS,
    )


def _bounded_no_wrap_vector(
    seed: int,
    label: str,
    *,
    rule: VectorRule,
) -> tuple[int, ...]:
    raw = _seed_bytes(seed, label)
    maximum_by_input = [rule.modulus - 1] * S2_SELECTED_VECTOR_WIDTH
    for output_index, input_index in enumerate(rule.permutation):
        maximum_by_input[input_index] = rule.modulus - 1 - rule.offsets[output_index]
    return tuple(
        raw[index] % (maximum_by_input[index] + 1)
        for index in range(S2_SELECTED_VECTOR_WIDTH)
    )


def wrap_count(rule: VectorRule, values: tuple[int, ...]) -> int:
    return sum(
        values[rule.permutation[index]] + rule.offsets[index] >= rule.modulus
        for index in range(S2_SELECTED_VECTOR_WIDTH)
    )


def _candidate_rules(examples: tuple[PublicExample, ...]) -> tuple[VectorRule, ...]:
    if not examples:
        return ()
    first = examples[0]
    candidates: list[VectorRule] = []
    for permutation in permutations(range(S2_SELECTED_VECTOR_WIDTH)):
        offsets = tuple(
            (
                first.output_values[index]
                - first.input_values[permutation[index]]
            )
            % S2_SELECTED_MODULUS
            for index in range(S2_SELECTED_VECTOR_WIDTH)
        )
        candidate = VectorRule(tuple(permutation), offsets, S2_SELECTED_MODULUS)
        if all(candidate.apply(item.input_values) == item.output_values for item in examples):
            candidates.append(candidate)
    return tuple(candidates)


def _source_examples(seed: int, *, rule: VectorRule) -> tuple[PublicExample, ...]:
    for salt in range(64):
        examples = tuple(
            PublicExample(
                values := _bounded_no_wrap_vector(
                    seed,
                    f"source:salt:{salt}:example:{index}",
                    rule=rule,
                ),
                rule.apply(values),
            )
            for index in range(S2_SELECTED_SOURCE_EXAMPLES)
        )
        if any(wrap_count(rule, item.input_values) for item in examples):
            raise AssertionError("selected-regime source example unexpectedly wraps")
        if _candidate_rules(examples) == (rule,):
            return examples
    raise S2SelectedRegimeError(
        "failed to generate globally identifiable selected-regime source examples"
    )


def _target_step(seed: int, *, rule: VectorRule) -> TargetStep:
    examples = tuple(
        PublicExample(
            values := _bounded_no_wrap_vector(
                seed,
                f"target:0:example:{index}",
                rule=rule,
            ),
            rule.apply(values),
        )
        for index in range(S2_SELECTED_TARGET_EXAMPLES)
    )
    query = _bounded_no_wrap_vector(seed, "target:0:query", rule=rule)
    if any(wrap_count(rule, item.input_values) for item in examples):
        raise AssertionError("selected-regime target example unexpectedly wraps")
    if wrap_count(rule, query):
        raise AssertionError("selected-regime target query unexpectedly wraps")
    return TargetStep(examples=examples, query=query)


def generate_selected_s2_family() -> TransferFamily:
    """Build the one fresh S2 family admitted by completed calibration-v2.

    The compatibility-level transfer regime remains ``shared`` because source and target
    use the same hidden rule. The calibrated task factor is frozen separately as
    ``V2_IDENTITY_OFFSET_NO_WRAP``. Calibration examples/seeds are never reused.
    """

    replay_selected_regime()
    rule = _rule(S2_SELECTED_SEED)
    source_examples = _source_examples(S2_SELECTED_SEED, rule=rule)
    target_step = _target_step(S2_SELECTED_SEED, rule=rule)
    return TransferFamily(
        seed=S2_SELECTED_SEED,
        regime="shared",
        modulus=S2_SELECTED_MODULUS,
        source_rule=rule,
        target_rules=(rule,),
        source_examples=source_examples,
        target_steps=(target_step,),
        shift_index=None,
    )


@dataclass(frozen=True, slots=True)
class S2SelectedPreregistration:
    calibration_repository_commit: str
    calibration_run_id: str
    calibration_identity_fingerprint: str
    selected_regime: str
    family_seed: int
    transfer_regime: str
    step_index: int
    examples_visible: int
    planned_provider_calls: int


def selected_s2_preregistration() -> S2SelectedPreregistration:
    family = generate_selected_s2_family()
    return S2SelectedPreregistration(
        calibration_repository_commit=CALIBRATION_V2_ADMISSION_REPOSITORY_COMMIT,
        calibration_run_id=CALIBRATION_V2_ADMISSION_RUN_ID,
        calibration_identity_fingerprint=CALIBRATION_V2_ADMISSION_IDENTITY_FINGERPRINT,
        selected_regime=replay_selected_regime(),
        family_seed=family.seed,
        transfer_regime=family.regime,
        step_index=S2_SELECTED_STEP_INDEX,
        examples_visible=S2_SELECTED_EXAMPLES_VISIBLE,
        planned_provider_calls=S2_SELECTED_PHYSICAL_CALLS,
    )
