from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
from itertools import permutations
import json
import re

from tools.v2_transfer_qualification import (
    QUALIFICATION_VERSION,
    QualificationManifest,
    QualificationThresholds,
    TargetCompetenceResult,
    manifest_digest,
    sha256_text,
)

Q1_RANGE_VERSION = "relaylm2-transfer-q1-target-range-v1"
PROMPT_VERSION = "relaylm2-transfer-q1-target-prompt-v1"
TRANSPORT_VERSION = "relaylm2-transfer-q1-target-json-schema-v1"
MODULUS = 10
EVIDENCE_LEVELS = (0, 1, 2, 3)
CALIBRATION_FAMILIES_PER_CANDIDATE = 4
QUALIFICATION_FAMILIES = 8
CALIBRATION_MIN_ENDPOINT_RATE = 0.25
CALIBRATION_MAX_ENDPOINT_RATE = 0.75
Q1_MIN_ENDPOINT_RATE = 0.25
Q1_MAX_ENDPOINT_RATE = 0.875

CALIBRATION_SELECTED = "CALIBRATION_SELECTED"
NO_MEASURABLE_TARGET_RANGE = "NO_MEASURABLE_TARGET_RANGE"
PROTOCOL_INVALID = "PROTOCOL_INVALID"
STAGE_CALIBRATION = "CALIBRATION"
STAGE_QUALIFICATION = "QUALIFICATION"
OFFSET_ONLY = "OFFSET_ONLY"
PERMUTATION_OFFSETS = "PERMUTATION_OFFSETS"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class Q1TargetRangeError(ValueError):
    pass


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: object) -> str:
    raw = value.encode() if isinstance(value, str) else _json(value).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _anchor(value: str) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise Q1TargetRangeError("package anchor must be a lowercase 40-character SHA-1")
    return value


@dataclass(frozen=True, slots=True)
class Q1Candidate:
    candidate_id: str
    width: int
    rule_kind: str
    modulus: int = MODULUS

    def __post_init__(self) -> None:
        if self.width not in {2, 3, 4} or self.rule_kind not in {OFFSET_ONLY, PERMUTATION_OFFSETS}:
            raise Q1TargetRangeError("invalid Q1 candidate")


CANDIDATES = (
    Q1Candidate("C0_W2_OFFSET_ONLY", 2, OFFSET_ONLY),
    Q1Candidate("C1_W2_PERMUTATION_OFFSETS", 2, PERMUTATION_OFFSETS),
    Q1Candidate("C2_W3_PERMUTATION_OFFSETS", 3, PERMUTATION_OFFSETS),
    Q1Candidate("C3_W4_PERMUTATION_OFFSETS", 4, PERMUTATION_OFFSETS),
)
CANDIDATE_BY_ID = {item.candidate_id: item for item in CANDIDATES}


@dataclass(frozen=True, slots=True)
class Q1Rule:
    permutation: tuple[int, ...]
    offsets: tuple[int, ...]
    modulus: int

    def apply(self, values: tuple[int, ...]) -> tuple[int, ...]:
        if len(values) != len(self.permutation):
            raise Q1TargetRangeError("input width drifted")
        return tuple(
            (values[self.permutation[i]] + self.offsets[i]) % self.modulus
            for i in range(len(values))
        )


@dataclass(frozen=True, slots=True)
class Q1Example:
    input_values: tuple[int, ...]
    output_values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Q1Family:
    seed: int
    candidate: Q1Candidate
    rule: Q1Rule
    examples: tuple[Q1Example, ...]
    query: tuple[int, ...]

    def payload(self, evidence_visible: int) -> dict[str, object]:
        if evidence_visible not in EVIDENCE_LEVELS:
            raise Q1TargetRangeError("evidence level drifted")
        return {
            "instruction": "Infer the hidden parameters of the declared transformation from the target-local examples, apply them to the query, and return only a JSON integer array.",
            "transformation_family": representation_semantics(self.candidate),
            "candidate_id": self.candidate.candidate_id,
            "examples": [
                {"input": list(item.input_values), "output": list(item.output_values)}
                for item in self.examples[:evidence_visible]
            ],
            "query": list(self.query),
        }

    def expected(self) -> tuple[int, ...]:
        return self.rule.apply(self.query)

    def verify(self, response: str) -> tuple[bool, str | None, tuple[int, ...] | None]:
        try:
            value = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return False, "invalid_json", None
        if not isinstance(value, list) or len(value) != self.candidate.width or any(type(x) is not int for x in value):
            return False, "invalid_shape", None
        parsed = tuple(value)
        if any(x < 0 or x >= self.candidate.modulus for x in parsed):
            return False, "out_of_range", parsed
        return parsed == self.expected(), None, parsed


@dataclass(frozen=True, slots=True)
class Q1Call:
    call_index: int
    stage: str
    candidate_id: str
    family_index: int
    seed: int
    evidence_visible: int
    width: int
    modulus: int


@dataclass(frozen=True, slots=True)
class CalibrationOutcome:
    candidate_id: str
    family_count: int
    evidence_level_correct: tuple[int, ...]
    endpoint_correct: int
    protocol_valid: bool = True
    replaced_seed_count: int = 0


@dataclass(frozen=True, slots=True)
class CalibrationSelection:
    status: str
    selected_candidate_id: str | None
    outcomes: tuple[CalibrationOutcome, ...]


def _seed(anchor: str, stage: str, candidate_id: str, index: int, attempt: int) -> int:
    payload = f"{Q1_RANGE_VERSION}|{anchor}|{stage}|{candidate_id}|{index}|{attempt}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & ((1 << 63) - 1)


def _vector(seed: int, candidate: Q1Candidate, label: str) -> tuple[int, ...]:
    raw = hashlib.sha256(f"{Q1_RANGE_VERSION}|{candidate.candidate_id}|{seed}|{label}".encode()).digest()
    return tuple(raw[i] % candidate.modulus for i in range(candidate.width))


def _rule(seed: int, candidate: Q1Candidate) -> Q1Rule:
    if candidate.rule_kind == OFFSET_ONLY:
        permutation = tuple(range(candidate.width))
    else:
        permutation = tuple(sorted(range(candidate.width), key=lambda i: hashlib.sha256(f"{Q1_RANGE_VERSION}|{seed}|perm|{i}".encode()).digest()))
    offsets = tuple(hashlib.sha256(f"{Q1_RANGE_VERSION}|{seed}|offset|{i}".encode()).digest()[0] % candidate.modulus for i in range(candidate.width))
    return Q1Rule(permutation, offsets, candidate.modulus)


def generate_family(seed: int, candidate_id: str) -> Q1Family:
    candidate = CANDIDATE_BY_ID.get(candidate_id)
    if candidate is None:
        raise Q1TargetRangeError("unknown candidate")
    rule = _rule(seed, candidate)
    examples = tuple(
        Q1Example(values, rule.apply(values))
        for values in (_vector(seed, candidate, f"example:{i}") for i in range(3))
    )
    return Q1Family(seed, candidate, rule, examples, _vector(seed, candidate, "query"))


def candidate_rule_count(family: Q1Family, evidence_visible: int) -> int:
    if evidence_visible not in EVIDENCE_LEVELS:
        raise Q1TargetRangeError("evidence level drifted")
    candidate = family.candidate
    visible = family.examples[:evidence_visible]
    if not visible:
        factorial = 1
        for n in range(2, candidate.width + 1):
            factorial *= n
        permutations_count = 1 if candidate.rule_kind == OFFSET_ONLY else factorial
        return permutations_count * candidate.modulus**candidate.width
    orders = (tuple(range(candidate.width)),) if candidate.rule_kind == OFFSET_ONLY else tuple(permutations(range(candidate.width)))
    count = 0
    for order in orders:
        first = visible[0]
        offsets = tuple((first.output_values[i] - first.input_values[order[i]]) % candidate.modulus for i in range(candidate.width))
        rule = Q1Rule(order, offsets, candidate.modulus)
        count += int(all(rule.apply(item.input_values) == item.output_values for item in visible))
    return count


def _seeds(package_anchor: str, stage: str, candidate_id: str, count: int) -> tuple[int, ...]:
    anchor = _anchor(package_anchor)
    if candidate_id not in CANDIDATE_BY_ID:
        raise Q1TargetRangeError("unknown candidate")
    values: list[int] = []
    for index in range(count):
        for attempt in range(256):
            seed = _seed(anchor, stage, candidate_id, index, attempt)
            if candidate_rule_count(generate_family(seed, candidate_id), 3) == 1:
                values.append(seed)
                break
        else:
            raise Q1TargetRangeError("could not derive an endpoint-identifiable family")
    return tuple(values)


def calibration_seeds(package_anchor: str, candidate_id: str) -> tuple[int, ...]:
    return _seeds(package_anchor, STAGE_CALIBRATION, candidate_id, CALIBRATION_FAMILIES_PER_CANDIDATE)


def qualification_seeds(package_anchor: str, candidate_id: str) -> tuple[int, ...]:
    result = _seeds(package_anchor, STAGE_QUALIFICATION, candidate_id, QUALIFICATION_FAMILIES)
    if set(result) & set(calibration_seeds(package_anchor, candidate_id)):
        raise Q1TargetRangeError("calibration/qualification seed collision")
    return result


def _plan(package_anchor: str, stage: str, candidate_ids: Sequence[str], families: int) -> tuple[Q1Call, ...]:
    entries: list[Q1Call] = []
    for candidate_id in candidate_ids:
        candidate = CANDIDATE_BY_ID[candidate_id]
        seeds = calibration_seeds(package_anchor, candidate_id) if stage == STAGE_CALIBRATION else qualification_seeds(package_anchor, candidate_id)
        if len(seeds) != families:
            raise Q1TargetRangeError("family count drifted")
        for family_index, seed in enumerate(seeds):
            for evidence in EVIDENCE_LEVELS:
                entries.append(Q1Call(len(entries), stage, candidate_id, family_index, seed, evidence, candidate.width, candidate.modulus))
    return tuple(entries)


def calibration_call_plan(package_anchor: str) -> tuple[Q1Call, ...]:
    return _plan(package_anchor, STAGE_CALIBRATION, [x.candidate_id for x in CANDIDATES], CALIBRATION_FAMILIES_PER_CANDIDATE)


def qualification_call_plan(package_anchor: str, candidate_id: str) -> tuple[Q1Call, ...]:
    if candidate_id not in CANDIDATE_BY_ID:
        raise Q1TargetRangeError("unknown candidate")
    return _plan(package_anchor, STAGE_QUALIFICATION, [candidate_id], QUALIFICATION_FAMILIES)


def call_plan_digest(plan: Sequence[Q1Call]) -> str:
    return _digest([asdict(x) for x in plan])


def representation_semantics(candidate: Q1Candidate) -> str:
    restriction = "permutation is the identity" if candidate.rule_kind == OFFSET_ONLY else "permutation is an unknown bijection"
    return f"length={candidate.width}; modulus={candidate.modulus}; y[i] = (x[permutation[i]] + offsets[i]) mod modulus; {restriction}; offsets are integers in [0, modulus-1]"


def select_calibration_candidate(outcomes: Sequence[CalibrationOutcome]) -> CalibrationSelection:
    values = tuple(outcomes)
    if tuple(x.candidate_id for x in values) != tuple(x.candidate_id for x in CANDIDATES):
        return CalibrationSelection(PROTOCOL_INVALID, None, values)
    if any(not x.protocol_valid or x.replaced_seed_count for x in values):
        return CalibrationSelection(PROTOCOL_INVALID, None, values)
    for item in values:
        if item.family_count != CALIBRATION_FAMILIES_PER_CANDIDATE or len(item.evidence_level_correct) != 4 or item.endpoint_correct != item.evidence_level_correct[-1]:
            return CalibrationSelection(PROTOCOL_INVALID, None, values)
        rate = item.endpoint_correct / item.family_count
        if CALIBRATION_MIN_ENDPOINT_RATE <= rate <= CALIBRATION_MAX_ENDPOINT_RATE:
            return CalibrationSelection(CALIBRATION_SELECTED, item.candidate_id, values)
    return CalibrationSelection(NO_MEASURABLE_TARGET_RANGE, None, values)


def task_family_identity(package_anchor: str, candidate_id: str) -> str:
    candidate = CANDIDATE_BY_ID[candidate_id]
    return _digest({"version": Q1_RANGE_VERSION, "prompt": PROMPT_VERSION, "package_anchor": _anchor(package_anchor), "candidate": asdict(candidate), "evidence_levels": list(EVIDENCE_LEVELS), "qualification_seeds": list(qualification_seeds(package_anchor, candidate_id))})


def thresholds() -> QualificationThresholds:
    return QualificationThresholds(8, Q1_MIN_ENDPOINT_RATE, Q1_MAX_ENDPOINT_RATE, 8, 0.50, 0.75, 8, 0.25, 0.20)


def build_manifest(package_anchor: str, candidate_id: str, model_runtime_digest: str) -> QualificationManifest:
    candidate = CANDIDATE_BY_ID[candidate_id]
    semantics = representation_semantics(candidate)
    return QualificationManifest(QUALIFICATION_VERSION, model_runtime_digest, task_family_identity(package_anchor, candidate_id), semantics, sha256_text(semantics), EVIDENCE_LEVELS, thresholds())


def target_response_format(width: int, modulus: int) -> dict[str, object]:
    if width not in {2, 3, 4} or modulus <= 1:
        raise Q1TargetRangeError("invalid response schema")
    schema = {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": modulus - 1}, "minItems": width, "maxItems": width}
    return {"type": "json_schema", "json_schema": {"name": f"relaylm2_q1_w{width}_m{modulus}_v1", "strict": True, "schema": schema}}


def transport_identity(plan: Sequence[Q1Call]) -> dict[str, object]:
    plan = tuple(plan)
    formats = {f"w{x.width}-m{x.modulus}": target_response_format(x.width, x.modulus) for x in plan}
    return {"transport_version": TRANSPORT_VERSION, "call_count": len(plan), "call_plan_digest": call_plan_digest(plan), "response_formats": {k: _digest(v) for k, v in sorted(formats.items())}}


def model_runtime_identity_digest(identity: Mapping[str, object]) -> str:
    fields = ("model", "artifact", "tokenizer", "template", "backend", "runtime", "decoding", "reasoning", "context_capacity", "hardware")
    if any(name not in identity for name in fields):
        raise Q1TargetRangeError("model/runtime identity is incomplete")
    return _digest({name: identity[name] for name in fields})


def q1_result(manifest: QualificationManifest, evidence_ref: str, curve: Sequence[int]) -> TargetCompetenceResult:
    curve = tuple(curve)
    if len(curve) != 4:
        raise Q1TargetRangeError("Q1 curve length drifted")
    return TargetCompetenceResult(manifest_digest(manifest), evidence_ref, True, True, "NONE", QUALIFICATION_FAMILIES, curve, curve[-1], 0)
