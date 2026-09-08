from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
import hashlib
import json
import math
import random
import re
from statistics import mean
from typing import Mapping

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureHypothesis
from relaylm.v2_transfer_experiment import TransferFamily, generate_transfer_family
from tools.v2_cognitive_work_structured_output_qualification import (
    OpenAICompatibleStructuredOutputClient,
    StructuredOutputClient,
)
from tools.v2_transfer_r1_structured_client import (
    source_structure_response_format,
    target_answer_response_format,
    transport_identity as r1_transport_identity,
)


PREREGISTRATION_VERSION = "relaylm2-transfer-r2-shared-null-v1"
SEED_DOMAIN = PREREGISTRATION_VERSION
R1_EXCLUDED_SEED = 2157001
REGIMES = ("shared", "null")
SEEDS_PER_REGIME = 8
FAMILY_COUNT = len(REGIMES) * SEEDS_PER_REGIME
MODULUS = 10
STEP_INDEX = 0
EXAMPLES_VISIBLE_LEVELS = (0, 1, 2, 3)
CALLS_PER_FAMILY = 1 + 3 * len(EXAMPLES_VISIBLE_LEVELS)
PROVIDER_CALL_COUNT = FAMILY_COUNT * CALLS_PER_FAMILY
SOURCE_CALL_COUNT = FAMILY_COUNT
TARGET_CALL_COUNT = PROVIDER_CALL_COUNT - SOURCE_CALL_COUNT
BOOTSTRAP_RESAMPLES = 10_000
ALPHA = 0.05
MATERIAL_INTERACTION = 0.25
SOURCE_LEARNING_MIN_RATE = 0.50
INTERPRETATION_CATEGORIES = (
    "INCONCLUSIVE",
    "NO_SOURCE_LEARNING",
    "GENERIC_CONTEXT_EFFECT",
    "TRANSFER_SIGNAL",
    "TRANSFER_EFFECT_UNCAPTURED_OR_UNSTABLE",
)

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class R2TransferPreregistrationError(ValueError):
    """The frozen R2 transfer preregistration contract is not satisfied."""


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: object) -> str:
    payload = (
        value.encode("utf-8")
        if isinstance(value, str)
        else _canonical_json(value).encode("utf-8")
    )
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _validate_commit(commit: str) -> str:
    if not isinstance(commit, str) or _COMMIT_RE.fullmatch(commit) is None:
        raise R2TransferPreregistrationError(
            "preregistration commit must be a lowercase 40-character SHA-1"
        )
    return commit


def _derived_seed(commit: str, *, regime: str, index: int, counter: int) -> int:
    payload = f"{SEED_DOMAIN}|{commit}|{regime}|{index}|{counter}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


@dataclass(frozen=True, slots=True)
class R2FamilySpec:
    family_index: int
    regime: str
    within_regime_index: int
    seed: int

    def __post_init__(self) -> None:
        if self.regime not in REGIMES:
            raise R2TransferPreregistrationError("R2 family regime must be shared or null")
        if self.family_index < 0 or self.within_regime_index < 0:
            raise R2TransferPreregistrationError("R2 family indices must be non-negative")
        if self.seed == R1_EXCLUDED_SEED:
            raise R2TransferPreregistrationError("R1 smoke seed cannot enter R2")


@dataclass(frozen=True, slots=True)
class R2CallPlanEntry:
    call_index: int
    family_index: int
    regime: str
    seed: int
    phase: str
    arm: str | None
    examples_visible: int | None
    step_index: int | None
    schema_kind: str

    def __post_init__(self) -> None:
        if self.call_index < 0 or self.family_index < 0:
            raise R2TransferPreregistrationError("R2 call indices must be non-negative")
        if self.regime not in REGIMES:
            raise R2TransferPreregistrationError("R2 call regime is invalid")
        if self.phase == "source-learning":
            if self.arm is not None or self.examples_visible is not None or self.step_index is not None:
                raise R2TransferPreregistrationError("source-learning call carries target fields")
            if self.schema_kind != "source_structure":
                raise R2TransferPreregistrationError("source-learning requires source schema")
        elif self.phase == "target":
            if self.arm not in {"T0", "T1", "T2"}:
                raise R2TransferPreregistrationError("target call arm is invalid")
            if self.examples_visible not in EXAMPLES_VISIBLE_LEVELS:
                raise R2TransferPreregistrationError("target evidence level is invalid")
            if self.step_index != STEP_INDEX:
                raise R2TransferPreregistrationError("target step index is invalid")
            if self.schema_kind != "target_answer":
                raise R2TransferPreregistrationError("target call requires answer schema")
        else:
            raise R2TransferPreregistrationError("R2 call phase is invalid")


@dataclass(frozen=True, slots=True)
class R2FamilyOutcome:
    family_index: int
    regime: str
    seed: int
    source_hypothesis_correct: bool
    t0: tuple[bool, bool, bool, bool]
    t1: tuple[bool, bool, bool, bool]
    t2: tuple[bool, bool, bool, bool]

    def __post_init__(self) -> None:
        if self.regime not in REGIMES:
            raise R2TransferPreregistrationError("R2 outcome regime is invalid")
        if not isinstance(self.source_hypothesis_correct, bool):
            raise R2TransferPreregistrationError("source correctness must be boolean")
        for name in ("t0", "t1", "t2"):
            curve = getattr(self, name)
            if len(curve) != len(EXAMPLES_VISIBLE_LEVELS) or any(
                not isinstance(value, bool) for value in curve
            ):
                raise R2TransferPreregistrationError(
                    f"{name} must contain exactly four boolean outcomes"
                )


@dataclass(frozen=True, slots=True)
class R2Analysis:
    source_correct_rate: float
    shared_t0_auc: float
    shared_t1_auc: float
    null_t0_auc: float
    null_t1_auc: float
    shared_gain: float
    null_gain: float
    interaction: float
    exact_p_value: float
    bootstrap_interval: tuple[float, float]
    t1_t2_auc_difference: float
    floor_saturated_families: int
    ceiling_saturated_families: int
    informative_families: int
    category: str


def family_specs(preregistration_commit: str) -> tuple[R2FamilySpec, ...]:
    commit = _validate_commit(preregistration_commit)
    used: set[int] = {R1_EXCLUDED_SEED}
    specs: list[R2FamilySpec] = []
    family_index = 0
    # Interleave regimes to reduce monotonic runtime-order confounding.
    for within_index in range(SEEDS_PER_REGIME):
        for regime in REGIMES:
            counter = 0
            while True:
                seed = _derived_seed(
                    commit,
                    regime=regime,
                    index=within_index,
                    counter=counter,
                )
                if seed not in used:
                    break
                counter += 1
            used.add(seed)
            specs.append(
                R2FamilySpec(
                    family_index=family_index,
                    regime=regime,
                    within_regime_index=within_index,
                    seed=seed,
                )
            )
            family_index += 1
    if len(specs) != FAMILY_COUNT:
        raise R2TransferPreregistrationError("R2 must contain exactly 16 families")
    return tuple(specs)


def generate_families(preregistration_commit: str) -> tuple[TransferFamily, ...]:
    return tuple(
        generate_transfer_family(seed=spec.seed, regime=spec.regime, modulus=MODULUS)
        for spec in family_specs(preregistration_commit)
    )


def call_plan(preregistration_commit: str) -> tuple[R2CallPlanEntry, ...]:
    entries: list[R2CallPlanEntry] = []
    call_index = 0
    for spec in family_specs(preregistration_commit):
        entries.append(
            R2CallPlanEntry(
                call_index=call_index,
                family_index=spec.family_index,
                regime=spec.regime,
                seed=spec.seed,
                phase="source-learning",
                arm=None,
                examples_visible=None,
                step_index=None,
                schema_kind="source_structure",
            )
        )
        call_index += 1
        for arm in ("T0", "T1", "T2"):
            for examples_visible in EXAMPLES_VISIBLE_LEVELS:
                entries.append(
                    R2CallPlanEntry(
                        call_index=call_index,
                        family_index=spec.family_index,
                        regime=spec.regime,
                        seed=spec.seed,
                        phase="target",
                        arm=arm,
                        examples_visible=examples_visible,
                        step_index=STEP_INDEX,
                        schema_kind="target_answer",
                    )
                )
                call_index += 1
    if len(entries) != PROVIDER_CALL_COUNT:
        raise R2TransferPreregistrationError("R2 call plan must contain exactly 208 calls")
    if tuple(entry.call_index for entry in entries) != tuple(range(PROVIDER_CALL_COUNT)):
        raise R2TransferPreregistrationError("R2 call indices are not contiguous")
    return tuple(entries)


def call_plan_digest(preregistration_commit: str) -> str:
    return _sha256([asdict(entry) for entry in call_plan(preregistration_commit)])


def transport_identity(preregistration_commit: str) -> dict[str, object]:
    commit = _validate_commit(preregistration_commit)
    return {
        "transport_version": "relaylm2-transfer-r2-structured-plan-v1",
        "base_transport": r1_transport_identity(MODULUS),
        "preregistration_commit": commit,
        "provider_call_count": PROVIDER_CALL_COUNT,
        "source_call_count": SOURCE_CALL_COUNT,
        "target_call_count": TARGET_CALL_COUNT,
        "plan_digest": call_plan_digest(commit),
    }


class R2PlanStructuredClient:
    """Plan-aware R2 adapter over the already-qualified structured-output client."""

    def __init__(
        self,
        *,
        preregistration_commit: str,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
        structured_client: StructuredOutputClient | None = None,
    ) -> None:
        self.preregistration_commit = _validate_commit(preregistration_commit)
        self._plan = call_plan(self.preregistration_commit)
        if structured_client is not None:
            if any(value is not None for value in (base_url, model, api_key)):
                raise R2TransferPreregistrationError(
                    "structured_client cannot be combined with provider constructor arguments"
                )
            self._client = structured_client
            self._owned_client = None
        else:
            if not isinstance(base_url, str) or not base_url.strip():
                raise R2TransferPreregistrationError("provider base_url must be non-empty")
            if not isinstance(model, str) or not model.strip():
                raise R2TransferPreregistrationError("provider model must be non-empty")
            owned = OpenAICompatibleStructuredOutputClient(
                base_url=base_url,
                model=model,
                api_key=api_key,
                timeout=timeout,
            )
            self._client = owned
            self._owned_client = owned
        self._call_index = 0

    @property
    def call_count(self) -> int:
        return self._call_index

    @property
    def identity(self) -> dict[str, object]:
        return transport_identity(self.preregistration_commit)

    @property
    def next_plan_entry(self) -> R2CallPlanEntry | None:
        if self._call_index >= len(self._plan):
            return None
        return self._plan[self._call_index]

    def close(self) -> None:
        if self._owned_client is not None:
            self._owned_client.close()

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self._call_index >= len(self._plan):
            raise R2TransferPreregistrationError(
                "R2 structured transport permits exactly 208 model calls"
            )
        entry = self._plan[self._call_index]
        response_format: Mapping[str, object]
        if entry.schema_kind == "source_structure":
            response_format = source_structure_response_format(MODULUS)
        else:
            response_format = target_answer_response_format(MODULUS)
        # Consume the slot before provider invocation. A provider/protocol failure
        # spends that planned slot; the later fail-closed campaign must not retry it.
        self._call_index += 1
        completion = self._client.complete(messages, response_format=response_format)
        return ExperimentCompletion(
            content=completion.content,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            response_id=completion.response_id,
        )


def source_hypothesis_matches_family(
    hypothesis: StructureHypothesis,
    family: TransferFamily,
) -> bool:
    return (
        hypothesis.permutation == family.source_rule.permutation
        and hypothesis.offsets == family.source_rule.offsets
        and hypothesis.modulus == family.source_rule.modulus
    )


def _auc(curve: tuple[bool, bool, bool, bool]) -> float:
    return sum(1.0 for value in curve if value) / len(curve)


def _family_gain(outcome: R2FamilyOutcome) -> float:
    return _auc(outcome.t1) - _auc(outcome.t0)


def _mean_for(outcomes: tuple[R2FamilyOutcome, ...], regime: str, arm: str) -> float:
    selected = [outcome for outcome in outcomes if outcome.regime == regime]
    return mean(_auc(getattr(outcome, arm)) for outcome in selected)


def _interaction_from_effects(effects: tuple[float, ...], labels: tuple[str, ...]) -> float:
    shared = [effect for effect, label in zip(effects, labels, strict=True) if label == "shared"]
    null = [effect for effect, label in zip(effects, labels, strict=True) if label == "null"]
    return mean(shared) - mean(null)


def exact_interaction_p_value(outcomes: tuple[R2FamilyOutcome, ...]) -> float:
    effects = tuple(_family_gain(outcome) for outcome in outcomes)
    labels = tuple(outcome.regime for outcome in outcomes)
    observed = abs(_interaction_from_effects(effects, labels))
    extreme = 0
    total = 0
    indices = range(len(outcomes))
    for shared_indices_tuple in combinations(indices, SEEDS_PER_REGIME):
        shared_indices = set(shared_indices_tuple)
        permuted_labels = tuple(
            "shared" if index in shared_indices else "null"
            for index in indices
        )
        statistic = abs(_interaction_from_effects(effects, permuted_labels))
        if statistic + 1e-12 >= observed:
            extreme += 1
        total += 1
    if total != math.comb(FAMILY_COUNT, SEEDS_PER_REGIME):
        raise R2TransferPreregistrationError("exact permutation count is inconsistent")
    return extreme / total


def _analysis_seed(preregistration_commit: str) -> int:
    commit = _validate_commit(preregistration_commit)
    digest = hashlib.sha256(
        f"{PREREGISTRATION_VERSION}|analysis-bootstrap|{commit}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def bootstrap_interaction_interval(
    outcomes: tuple[R2FamilyOutcome, ...],
    *,
    preregistration_commit: str,
) -> tuple[float, float]:
    shared = [outcome for outcome in outcomes if outcome.regime == "shared"]
    null = [outcome for outcome in outcomes if outcome.regime == "null"]
    rng = random.Random(_analysis_seed(preregistration_commit))
    estimates: list[float] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        shared_sample = [shared[rng.randrange(len(shared))] for _ in shared]
        null_sample = [null[rng.randrange(len(null))] for _ in null]
        shared_gain = mean(_family_gain(outcome) for outcome in shared_sample)
        null_gain = mean(_family_gain(outcome) for outcome in null_sample)
        estimates.append(shared_gain - null_gain)
    estimates.sort()
    lower_index = int(0.025 * BOOTSTRAP_RESAMPLES)
    upper_index = int(0.975 * BOOTSTRAP_RESAMPLES) - 1
    return estimates[lower_index], estimates[upper_index]


def _validate_outcomes(
    outcomes: tuple[R2FamilyOutcome, ...],
    preregistration_commit: str,
) -> None:
    specs = family_specs(preregistration_commit)
    if len(outcomes) != FAMILY_COUNT:
        raise R2TransferPreregistrationError("R2 analysis requires exactly 16 families")
    by_index = {outcome.family_index: outcome for outcome in outcomes}
    if len(by_index) != FAMILY_COUNT:
        raise R2TransferPreregistrationError("R2 family outcome indices must be unique")
    for spec in specs:
        outcome = by_index.get(spec.family_index)
        if outcome is None:
            raise R2TransferPreregistrationError("R2 family outcome is missing")
        if outcome.regime != spec.regime or outcome.seed != spec.seed:
            raise R2TransferPreregistrationError(
                "R2 outcome identity disagrees with preregistered family"
            )


def analyze_r2(
    outcomes: tuple[R2FamilyOutcome, ...],
    *,
    preregistration_commit: str,
    complete: bool = True,
    protocol_valid: bool = True,
) -> R2Analysis:
    _validate_outcomes(outcomes, preregistration_commit)
    ordered = tuple(sorted(outcomes, key=lambda outcome: outcome.family_index))
    source_correct_rate = mean(
        1.0 if outcome.source_hypothesis_correct else 0.0
        for outcome in ordered
    )
    shared_t0_auc = _mean_for(ordered, "shared", "t0")
    shared_t1_auc = _mean_for(ordered, "shared", "t1")
    null_t0_auc = _mean_for(ordered, "null", "t0")
    null_t1_auc = _mean_for(ordered, "null", "t1")
    shared_gain = shared_t1_auc - shared_t0_auc
    null_gain = null_t1_auc - null_t0_auc
    interaction = shared_gain - null_gain
    exact_p = exact_interaction_p_value(ordered)
    bootstrap = bootstrap_interaction_interval(
        ordered,
        preregistration_commit=preregistration_commit,
    )
    t1_t2_auc_difference = mean(
        _auc(outcome.t1) - _auc(outcome.t2)
        for outcome in ordered
    )

    floor = 0
    ceiling = 0
    for outcome in ordered:
        values = outcome.t0 + outcome.t1 + outcome.t2
        if not any(values):
            floor += 1
        elif all(values):
            ceiling += 1
    informative = FAMILY_COUNT - floor - ceiling

    if not complete or not protocol_valid:
        category = "INCONCLUSIVE"
    elif source_correct_rate < SOURCE_LEARNING_MIN_RATE:
        category = "NO_SOURCE_LEARNING"
    elif shared_gain >= MATERIAL_INTERACTION and interaction < MATERIAL_INTERACTION:
        category = "GENERIC_CONTEXT_EFFECT"
    elif (
        interaction >= MATERIAL_INTERACTION
        and exact_p <= ALPHA
        and bootstrap[0] > 0.0
    ):
        category = "TRANSFER_SIGNAL"
    else:
        category = "TRANSFER_EFFECT_UNCAPTURED_OR_UNSTABLE"

    return R2Analysis(
        source_correct_rate=source_correct_rate,
        shared_t0_auc=shared_t0_auc,
        shared_t1_auc=shared_t1_auc,
        null_t0_auc=null_t0_auc,
        null_t1_auc=null_t1_auc,
        shared_gain=shared_gain,
        null_gain=null_gain,
        interaction=interaction,
        exact_p_value=exact_p,
        bootstrap_interval=bootstrap,
        t1_t2_auc_difference=t1_t2_auc_difference,
        floor_saturated_families=floor,
        ceiling_saturated_families=ceiling,
        informative_families=informative,
        category=category,
    )


def preregistration_identity(preregistration_commit: str) -> dict[str, object]:
    commit = _validate_commit(preregistration_commit)
    return {
        "version": PREREGISTRATION_VERSION,
        "seed_domain": SEED_DOMAIN,
        "preregistration_commit": commit,
        "r1_excluded_seed": R1_EXCLUDED_SEED,
        "regimes": list(REGIMES),
        "seeds_per_regime": SEEDS_PER_REGIME,
        "modulus": MODULUS,
        "step_index": STEP_INDEX,
        "examples_visible_levels": list(EXAMPLES_VISIBLE_LEVELS),
        "provider_call_count": PROVIDER_CALL_COUNT,
        "family_specs": [asdict(spec) for spec in family_specs(commit)],
        "call_plan_digest": call_plan_digest(commit),
        "transport": transport_identity(commit),
        "statistics": {
            "family_effect": "AUC(T1)-AUC(T0)",
            "interaction": "mean(D|shared)-mean(D|null)",
            "exact_test": "two-sided balanced regime-label permutation",
            "alpha": ALPHA,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "bootstrap_interval": 0.95,
            "material_interaction": MATERIAL_INTERACTION,
            "source_learning_min_rate": SOURCE_LEARNING_MIN_RATE,
        },
        "interpretation_categories": list(INTERPRETATION_CATEGORIES),
    }


def preregistration_digest(preregistration_commit: str) -> str:
    return _sha256(preregistration_identity(preregistration_commit))
