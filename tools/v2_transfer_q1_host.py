from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from tools.external_qualification import (
    DurableQuestion,
    DurableQuestionRun,
    ExternalQualificationError,
    FrozenExperimentIdentity,
    freeze_experiment_identity,
)
from tools.v2_transfer_q1_structured_client import Q1PlanStructuredClient
from tools.v2_transfer_q1_target_range import (
    CALIBRATION_FAMILIES_PER_CANDIDATE,
    CANDIDATES,
    EVIDENCE_LEVELS,
    QUALIFICATION_FAMILIES,
    STAGE_CALIBRATION,
    STAGE_QUALIFICATION,
    CalibrationOutcome,
    Q1Call,
    build_manifest,
    calibration_call_plan,
    call_plan_digest,
    generate_family,
    model_runtime_identity_digest,
    q1_result,
    qualification_call_plan,
    select_calibration_candidate,
    task_family_identity,
    transport_identity,
)
from tools.v2_transfer_qualification import classify_q1, manifest_digest
from tools.v2_transfer_r1_host import RepositoryState, probe_git_repository

CALIBRATION_CANDIDATE = "relaylm2-transfer-q1-range-calibration"
QUALIFICATION_CANDIDATE = "relaylm2-transfer-q1-heldout-qualification"
CALIBRATION_HARNESS = "relaylm2-transfer-q1-calibration-host-v1"
QUALIFICATION_HARNESS = "relaylm2-transfer-q1-qualification-host-v1"
CALIBRATION_CLAIM = "NON_CITABLE_Q1_TARGET_RANGE_CALIBRATION"
QUALIFICATION_CLAIM = "Q1_TARGET_COMPETENCE_HELDOUT_RESULT"
CALIBRATION_RESULT_NAME = "q1-calibration-result.json"
QUALIFICATION_RESULT_NAME = "q1-qualification-result.json"
HOST_FAILURE_NAME = "q1-host-failure.json"

_MATERIAL_FIELDS = (
    "model", "artifact", "tokenizer", "template", "backend", "runtime",
    "decoding", "reasoning", "structured_output", "context_capacity",
    "hardware", "launch_admission",
)


class Q1HostError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Q1HostResult:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    verdict: str
    provider_calls: int
    result_path: str
    selected_candidate_id: str | None


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _copy(value: Mapping[str, object]) -> dict[str, object]:
    result = json.loads(_json(dict(value)))
    if not isinstance(result, dict):
        raise Q1HostError("Q1 host value must be an object")
    return result


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_json(value).encode()).hexdigest()


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise Q1HostError(f"{label} must be an object")
    return value


def material_binding_fields() -> tuple[str, ...]:
    return _MATERIAL_FIELDS


def _repo(identity: Mapping[str, object]) -> tuple[str, str]:
    value = _mapping(identity.get("repository"), "repository identity")
    if set(value) != {"commit", "tree", "clean_required"} or value.get("clean_required") is not True:
        raise Q1HostError("repository identity must freeze commit/tree and require clean")
    commit, tree = value.get("commit"), value.get("tree")
    if not isinstance(commit, str) or len(commit) != 40 or not isinstance(tree, str) or len(tree) != 40:
        raise Q1HostError("repository commit/tree identity is invalid")
    return commit, tree


def _validate_repo(identity: Mapping[str, object], observed: RepositoryState) -> str:
    commit, tree = _repo(identity)
    if not observed.clean or observed.commit != commit or observed.tree != tree:
        raise Q1HostError("repository checkout does not match frozen clean identity")
    return commit


def _binding(identity: Mapping[str, object]) -> dict[str, object]:
    if any(name not in identity for name in _MATERIAL_FIELDS):
        raise Q1HostError("material physical binding is incomplete")
    return _copy({name: identity[name] for name in _MATERIAL_FIELDS})


def _validate_binding(expected: Mapping[str, object], observed: Mapping[str, object]) -> None:
    if set(observed) != set(_MATERIAL_FIELDS):
        raise Q1HostError("physical binding field set drifted")
    for name in _MATERIAL_FIELDS:
        if _json(expected[name]) != _json(observed[name]):
            raise Q1HostError(f"physical binding drift: {name} changed")


def _outside(artifact_root: str | Path, repository_root: str | Path) -> None:
    artifact, repository = Path(artifact_root).resolve(), Path(repository_root).resolve()
    try:
        artifact.relative_to(repository)
    except ValueError:
        return
    raise Q1HostError("artifact root must be outside the repository checkout")


def _qid(stage: str, entry: Q1Call) -> str:
    prefix = "q1-cal" if stage == STAGE_CALIBRATION else "q1-qual"
    return f"{prefix}-{entry.call_index:03d}"


def _order(stage: str, plan: Sequence[Q1Call]) -> list[str]:
    return [_qid(stage, entry) for entry in plan]


def calibration_execution_order(package_anchor: str) -> list[str]:
    return _order(STAGE_CALIBRATION, calibration_call_plan(package_anchor))


def qualification_execution_order(package_anchor: str, candidate_id: str) -> list[str]:
    return _order(STAGE_QUALIFICATION, qualification_call_plan(package_anchor, candidate_id))


def _benchmark(stage: str, anchor: str, plan: Sequence[Q1Call], candidate_id: str | None = None, calibration_digest: str | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "owner": 2393,
        "stage": stage,
        "package_anchor": anchor,
        "call_plan_digest": call_plan_digest(plan),
        "provider_calls": len(plan),
        "evidence_levels": list(EVIDENCE_LEVELS),
    }
    if stage == STAGE_CALIBRATION:
        result.update(candidate_order=[x.candidate_id for x in CANDIDATES], families_per_candidate=CALIBRATION_FAMILIES_PER_CANDIDATE)
    else:
        result.update(selected_candidate_id=candidate_id, families=QUALIFICATION_FAMILIES, calibration_result_digest=calibration_digest)
    return result


def calibration_benchmark_identity(anchor: str) -> dict[str, object]:
    return _benchmark(STAGE_CALIBRATION, anchor, calibration_call_plan(anchor))


def qualification_benchmark_identity(anchor: str, candidate_id: str, calibration_result: Mapping[str, object]) -> dict[str, object]:
    return _benchmark(STAGE_QUALIFICATION, anchor, qualification_call_plan(anchor, candidate_id), candidate_id, _digest(_copy(calibration_result)))


def _validate_static(identity: Mapping[str, object], stage: str, anchor: str, plan: Sequence[Q1Call], candidate_id: str | None = None, calibration_digest: str | None = None) -> None:
    expected_candidate = CALIBRATION_CANDIDATE if stage == STAGE_CALIBRATION else QUALIFICATION_CANDIDATE
    expected_harness = CALIBRATION_HARNESS if stage == STAGE_CALIBRATION else QUALIFICATION_HARNESS
    if identity.get("candidate") != expected_candidate or identity.get("harness") != expected_harness:
        raise Q1HostError("Q1 candidate/harness identity drifted")
    if identity.get("benchmark") != _benchmark(stage, anchor, plan, candidate_id, calibration_digest):
        raise Q1HostError("Q1 benchmark identity drifted")
    if identity.get("structured_output") != transport_identity(plan):
        raise Q1HostError("Q1 structured-output identity drifted")
    if identity.get("execution_order") != _order(stage, plan):
        raise Q1HostError("Q1 execution order drifted")
    if _mapping(identity.get("retry_policy"), "retry policy") != {"automatic_retry": False, "semantic_retry": False}:
        raise Q1HostError("Q1 retry policy must disable retry")


def _questions(stage: str, anchor: str, plan: Sequence[Q1Call]) -> tuple[DurableQuestion, ...]:
    digest = call_plan_digest(plan)
    return tuple(
        DurableQuestion.from_content(
            _qid(stage, entry),
            {"package_anchor": anchor, "call_plan_digest": digest, "entry": asdict(entry)},
            session_id=f"{entry.candidate_id}-family-{entry.family_index:02d}",
        )
        for entry in plan
    )


def _write(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(_json(dict(value)) + "\n", encoding="utf-8")
    tmp.replace(path)


def _failure(root: Path, claim: str, kind: str, error: str, index: int) -> None:
    _write(root / HOST_FAILURE_NAME, {"status": "INCOMPLETE", "claim_status": claim, "kind": kind, "error": error, "next_call_index": index, "authority": "instrumentation_only"})


class _BoundClient:
    def __init__(self, client: Q1PlanStructuredClient, run: DurableQuestionRun, probe: Callable[[], Mapping[str, object]], expected: Mapping[str, object], stage: str) -> None:
        self.client, self.run, self.probe, self.expected, self.stage = client, run, probe, _copy(expected), stage
        self.entry: Q1Call | None = None

    def bind(self, entry: Q1Call) -> None:
        if self.client.next_plan_entry != entry:
            raise Q1HostError("Q1 client plan cursor drifted")
        self.entry = entry

    def complete(self, messages: tuple[dict[str, str], ...]):
        if self.entry is None or self.client.next_plan_entry != self.entry:
            raise Q1HostError("Q1 provider call is not bound to the frozen plan")
        qid = _qid(self.stage, self.entry)
        try:
            observed = self.probe()
            if not isinstance(observed, Mapping):
                raise Q1HostError("live binding probe did not return an object")
            _validate_binding(self.expected, observed)
        except Exception as exc:
            self.run.append_request_evidence(question_id=qid, evidence={"kind": "physical_binding_failure", "authority": "instrumentation_only", "error": f"{type(exc).__name__}: {exc}"})
            self.run.mark_stopped()
            raise Q1HostError(f"physical binding probe failure: {exc}") from exc
        try:
            completion = self.client.complete(self.entry, messages)
        except Exception as exc:
            self.run.append_request_evidence(question_id=qid, evidence={"kind": "provider_client_failure", "authority": "instrumentation_only", "error": f"{type(exc).__name__}: {exc}"})
            self.run.mark_stopped()
            raise Q1HostError(f"provider client failure: {exc}") from exc
        self.run.append_request_evidence(question_id=qid, evidence={"kind": "model_exchange", "authority": "instrumentation_only", "plan_entry": asdict(self.entry), "messages": messages, "response": {"content": completion.content, "input_tokens": completion.input_tokens, "output_tokens": completion.output_tokens, "response_id": completion.response_id}})
        return completion


def _prepare(stage: str, claim: str, artifact_root: str | Path, identity: Mapping[str, object], repository_root: str | Path, live_binding_probe: Callable[[], Mapping[str, object]], client: Q1PlanStructuredClient, plan: Sequence[Q1Call], run_id: str | None, candidate_id: str | None = None, calibration_digest: str | None = None) -> tuple[DurableQuestionRun, _BoundClient, FrozenExperimentIdentity, str]:
    snapshot = _copy(identity)
    anchor = _validate_repo(snapshot, probe_git_repository(repository_root))
    _outside(artifact_root, repository_root)
    _validate_static(snapshot, stage, anchor, plan, candidate_id, calibration_digest)
    if client.identity != transport_identity(plan) or client.call_count != 0 or client.next_plan_entry != tuple(plan)[0]:
        raise Q1HostError("Q1 structured client is not at the frozen initial state")
    proposed = _binding(snapshot)
    try:
        initial = live_binding_probe()
    except Exception as exc:
        raise Q1HostError(f"physical binding preflight failed: {exc}") from exc
    if not isinstance(initial, Mapping):
        raise Q1HostError("physical binding preflight did not return an object")
    _validate_binding(proposed, initial)
    try:
        frozen = freeze_experiment_identity(identity=snapshot, live_attestation=_mapping(initial["launch_admission"], "live launch admission"))
        run = DurableQuestionRun.start(artifact_root=artifact_root, identity=frozen, questions=_questions(stage, anchor, plan), run_id=run_id, run_mode="fresh_run")
    except ExternalQualificationError as exc:
        raise Q1HostError(f"host-owned freeze/durable initialization failed: {exc}") from exc
    return run, _BoundClient(client, run, live_binding_probe, _binding(frozen.to_mapping()), stage), frozen, anchor


def _execute(stage: str, claim: str, root: Path, run: DurableQuestionRun, bound: _BoundClient, plan: Sequence[Q1Call]) -> None:
    for entry in plan:
        qid = _qid(stage, entry)
        run.begin_question(qid)
        bound.bind(entry)
        family = generate_family(entry.seed, entry.candidate_id)
        messages = ({"role": "user", "content": _json(family.payload(entry.evidence_visible))},)
        try:
            completion = bound.complete(messages)
        except Q1HostError as exc:
            _failure(root, claim, "execution_failure", str(exc), entry.call_index)
            raise
        correct, error, parsed = family.verify(completion.content)
        if error is not None:
            run.append_request_evidence(question_id=qid, evidence={"kind": "model_protocol_failure", "authority": "instrumentation_only", "error": error})
            run.mark_stopped()
            _failure(root, claim, "model_protocol_failure", error, entry.call_index)
            raise Q1HostError(f"Q1 model protocol failure: {error}")
        run.commit_question(question_id=qid, result={"candidate_id": entry.candidate_id, "family_index": entry.family_index, "seed": entry.seed, "evidence_visible": entry.evidence_visible, "correct": correct, "parsed_output": list(parsed or ()), "verification_error": None, "resource_cost": {"calls": 1, "input_tokens": completion.input_tokens, "output_tokens": completion.output_tokens}})
    run.mark_completed()


def _curves(stage: str, run: DurableQuestionRun, plan: Sequence[Q1Call]) -> tuple[dict[str, tuple[int, ...]], dict[str, int]]:
    records = run.rebuild_completed_results()
    if len(records) != len(plan):
        raise Q1HostError("durable Q1 result count drifted")
    values: dict[tuple[str, int], dict[int, bool]] = {}
    resources = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
    for record, entry in zip(records, plan, strict=True):
        if record.get("question_id") != _qid(stage, entry):
            raise Q1HostError("durable Q1 result order drifted")
        result = _mapping(record.get("result"), "durable Q1 result")
        if (result.get("candidate_id"), result.get("family_index"), result.get("seed"), result.get("evidence_visible")) != (entry.candidate_id, entry.family_index, entry.seed, entry.evidence_visible):
            raise Q1HostError("durable Q1 result identity drifted")
        correct = result.get("correct")
        if not isinstance(correct, bool) or result.get("verification_error") is not None:
            raise Q1HostError("durable Q1 semantic result is invalid")
        values.setdefault((entry.candidate_id, entry.family_index), {})[entry.evidence_visible] = correct
        cost = _mapping(result.get("resource_cost"), "Q1 resource cost")
        for key in resources:
            item = cost.get(key)
            if type(item) is not int or item < 0:
                raise Q1HostError("Q1 resource cost is invalid")
            resources[key] += item
    curves: dict[str, tuple[int, ...]] = {}
    for candidate_id in {x.candidate_id for x in plan}:
        family_ids = sorted(i for cid, i in values if cid == candidate_id)
        if any(set(values[(candidate_id, i)]) != set(EVIDENCE_LEVELS) for i in family_ids):
            raise Q1HostError("Q1 adaptation curve is incomplete")
        curves[candidate_id] = tuple(sum(int(values[(candidate_id, i)][level]) for i in family_ids) for level in EVIDENCE_LEVELS)
    if resources["calls"] != len(plan):
        raise Q1HostError("Q1 reconstructed call count drifted")
    return curves, resources


def run_q1_calibration_host(*, artifact_root: str | Path, identity: Mapping[str, object], repository_root: str | Path, live_binding_probe: Callable[[], Mapping[str, object]], client: Q1PlanStructuredClient, run_id: str | None = None) -> Q1HostResult:
    anchor, _ = _repo(identity)
    plan = calibration_call_plan(anchor)
    run, bound, frozen, anchor = _prepare(STAGE_CALIBRATION, CALIBRATION_CLAIM, artifact_root, identity, repository_root, live_binding_probe, client, plan, run_id)
    root = Path(artifact_root)
    _execute(STAGE_CALIBRATION, CALIBRATION_CLAIM, root, run, bound, plan)
    curves, resources = _curves(STAGE_CALIBRATION, run, plan)
    outcomes = tuple(CalibrationOutcome(x.candidate_id, CALIBRATION_FAMILIES_PER_CANDIDATE, curves[x.candidate_id], curves[x.candidate_id][-1]) for x in CANDIDATES)
    selection = select_calibration_candidate(outcomes)
    payload = {"status": "COMPLETED", "claim_status": CALIBRATION_CLAIM, "citable": False, "verdict": selection.status, "selected_candidate_id": selection.selected_candidate_id, "package_anchor": anchor, "call_plan_digest": call_plan_digest(plan), "transport_identity": transport_identity(plan), "model_runtime_identity_digest": model_runtime_identity_digest(frozen.to_mapping()), "provider_calls": len(plan), "outcomes": [asdict(x) for x in outcomes], "resource_totals": resources}
    path = root / CALIBRATION_RESULT_NAME
    _write(path, payload)
    return Q1HostResult(run.run_id, frozen.fingerprint, "COMPLETED", CALIBRATION_CLAIM, False, selection.status, len(plan), str(path), selection.selected_candidate_id)


def _calibration_gate(calibration_result: Mapping[str, object], anchor: str, identity: Mapping[str, object]) -> tuple[str, str]:
    value = _copy(calibration_result)
    if value.get("status") != "COMPLETED" or value.get("claim_status") != CALIBRATION_CLAIM or value.get("citable") is not False or value.get("verdict") != "CALIBRATION_SELECTED":
        raise Q1HostError("held-out Q1 requires a successful complete non-citable calibration")
    candidate_id = value.get("selected_candidate_id")
    if not isinstance(candidate_id, str) or value.get("package_anchor") != anchor or value.get("provider_calls") != 64:
        raise Q1HostError("calibration result identity is invalid")
    if value.get("model_runtime_identity_digest") != model_runtime_identity_digest(identity):
        raise Q1HostError("Stage Q model/runtime differs from Stage C")
    return candidate_id, _digest(value)


def run_q1_qualification_host(*, artifact_root: str | Path, identity: Mapping[str, object], repository_root: str | Path, live_binding_probe: Callable[[], Mapping[str, object]], client: Q1PlanStructuredClient, calibration_result: Mapping[str, object], run_id: str | None = None) -> Q1HostResult:
    anchor, _ = _repo(identity)
    candidate_id, calibration_digest = _calibration_gate(calibration_result, anchor, identity)
    plan = qualification_call_plan(anchor, candidate_id)
    run, bound, frozen, anchor = _prepare(STAGE_QUALIFICATION, QUALIFICATION_CLAIM, artifact_root, identity, repository_root, live_binding_probe, client, plan, run_id, candidate_id, calibration_digest)
    root = Path(artifact_root)
    _execute(STAGE_QUALIFICATION, QUALIFICATION_CLAIM, root, run, bound, plan)
    curves, resources = _curves(STAGE_QUALIFICATION, run, plan)
    manifest = build_manifest(anchor, candidate_id, model_runtime_identity_digest(frozen.to_mapping()))
    q1 = q1_result(manifest, f"q1-heldout:{run.run_id}:{manifest_digest(manifest)}", curves[candidate_id])
    verdict = classify_q1(manifest, q1)
    payload = {"status": "COMPLETED", "claim_status": QUALIFICATION_CLAIM, "citable": True, "verdict": verdict, "selected_candidate_id": candidate_id, "package_anchor": anchor, "calibration_result_digest": calibration_digest, "task_family_identity_digest": task_family_identity(anchor, candidate_id), "call_plan_digest": call_plan_digest(plan), "transport_identity": transport_identity(plan), "model_runtime_identity_digest": model_runtime_identity_digest(frozen.to_mapping()), "provider_calls": len(plan), "manifest": asdict(manifest), "q1_result": asdict(q1), "resource_totals": resources}
    path = root / QUALIFICATION_RESULT_NAME
    _write(path, payload)
    return Q1HostResult(run.run_id, frozen.fingerprint, "COMPLETED", QUALIFICATION_CLAIM, True, verdict, len(plan), str(path), candidate_id)
