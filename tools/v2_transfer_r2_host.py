from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from relaylm.v2_transfer_actual_model import (
    ExperimentCompletion,
    StructureProposalError,
    prepare_r1_arms,
    render_target_prompt,
    run_source_learning,
    run_target_probe,
)
from tools.external_qualification import (
    DurableQuestion,
    DurableQuestionRun,
    ExternalQualificationError,
    FrozenExperimentIdentity,
    freeze_experiment_identity,
)
from tools.v2_transfer_r1_host import RepositoryState, probe_git_repository
from tools.v2_transfer_r2_prereg import (
    FAMILY_COUNT,
    PROVIDER_CALL_COUNT,
    R2CallPlanEntry,
    R2FamilyOutcome,
    R2PlanStructuredClient,
    analyze_r2,
    call_plan,
    call_plan_digest,
    generate_families,
    preregistration_digest,
    source_hypothesis_matches_family,
    transport_identity,
)


PREREGISTRATION_COMMIT = "aeb8f8d477ba46650cb2f3d97b7154b69366431c"
PREREGISTRATION_DIGEST = (
    "sha256:1323fadd94e18d073c07629dd3ce2d2ec9735eea583d5bdfb49606aeec099cf6"
)
CALL_PLAN_DIGEST = (
    "sha256:0890dbaf7d99821592f771225b38af42aa024351d48283f11069980709393d70"
)
TRANSPORT_IDENTITY_DIGEST = (
    "sha256:c78e50b122a447b1d7ee10afc6a0a702b0c83bc59ca84508e8ac11963f0b8376"
)
CLAIM_STATUS = "R2_SHARED_NULL_PREREGISTERED_PHYSICAL_RESULT"
CANDIDATE_ID = "relaylm2-transfer-r2-shared-null"
HARNESS_ID = "relaylm2-transfer-r2-host-v1"
RESULT_NAME = "r2-result.json"
HOST_FAILURE_NAME = "r2-host-failure.json"

_MATERIAL_BINDING_FIELDS = (
    "model",
    "artifact",
    "tokenizer",
    "template",
    "backend",
    "runtime",
    "decoding",
    "reasoning",
    "structured_output",
    "context_capacity",
    "hardware",
    "launch_admission",
)


class R2TransferHostError(ValueError):
    """The hard-bound R2 transfer host cannot satisfy its frozen contract."""


@dataclass(frozen=True, slots=True)
class R2TransferHostResult:
    run_id: str
    identity_fingerprint: str
    status: str
    claim_status: str
    citable: bool
    category: str
    provider_calls: int
    family_count: int
    result_path: str


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise R2TransferHostError("R2 host value must be canonical JSON") from exc


def _sha256(value: object) -> str:
    payload = (
        value.encode("utf-8")
        if isinstance(value, str)
        else _canonical_json(value).encode("utf-8")
    )
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise R2TransferHostError(f"{label} must be an object")
    return value


def _json_object_copy(value: Mapping[str, object], label: str) -> dict[str, object]:
    copied = json.loads(_canonical_json(dict(value)))
    if not isinstance(copied, dict):
        raise R2TransferHostError(f"{label} must be an object")
    return copied


def benchmark_identity() -> dict[str, object]:
    return {
        "owner": 2341,
        "version": "relaylm2-transfer-r2-shared-null-v1",
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_digest": PREREGISTRATION_DIGEST,
        "call_plan_digest": CALL_PLAN_DIGEST,
        "provider_calls": PROVIDER_CALL_COUNT,
        "families": FAMILY_COUNT,
    }


def execution_order() -> list[str]:
    return [
        f"r2-call-{entry.call_index:03d}"
        for entry in call_plan(PREREGISTRATION_COMMIT)
    ]


def _validate_preregistration_contract() -> None:
    if preregistration_digest(PREREGISTRATION_COMMIT) != PREREGISTRATION_DIGEST:
        raise R2TransferHostError("merged R2 preregistration digest drifted")
    if call_plan_digest(PREREGISTRATION_COMMIT) != CALL_PLAN_DIGEST:
        raise R2TransferHostError("merged R2 call-plan digest drifted")
    live_transport = transport_identity(PREREGISTRATION_COMMIT)
    if _sha256(live_transport) != TRANSPORT_IDENTITY_DIGEST:
        raise R2TransferHostError("merged R2 transport identity drifted")
    if len(call_plan(PREREGISTRATION_COMMIT)) != PROVIDER_CALL_COUNT:
        raise R2TransferHostError("merged R2 provider call count drifted")


def _validate_static_contract(identity: Mapping[str, object]) -> None:
    _validate_preregistration_contract()
    if identity.get("candidate") != CANDIDATE_ID:
        raise R2TransferHostError("R2 candidate identity is not frozen")
    if identity.get("harness") != HARNESS_ID:
        raise R2TransferHostError("R2 harness identity is not frozen")
    if identity.get("benchmark") != benchmark_identity():
        raise R2TransferHostError("R2 benchmark/preregistration identity is not frozen")
    if identity.get("structured_output") != transport_identity(PREREGISTRATION_COMMIT):
        raise R2TransferHostError("R2 structured-output identity is not frozen")
    if identity.get("execution_order") != execution_order():
        raise R2TransferHostError("R2 execution order is not the frozen 208-call plan")
    retry_policy = _mapping(identity.get("retry_policy"), "retry policy")
    if retry_policy != {"automatic_retry": False, "semantic_retry": False}:
        raise R2TransferHostError("R2 retry policy must disable all semantic retry")


def _validate_repository(identity: Mapping[str, object], observed: RepositoryState) -> None:
    expected = _mapping(identity.get("repository"), "repository identity")
    if set(expected) != {"commit", "tree", "clean_required"}:
        raise R2TransferHostError(
            "repository identity must contain exactly commit/tree/clean_required"
        )
    if expected.get("clean_required") is not True:
        raise R2TransferHostError("repository identity must require a clean checkout")
    if not observed.clean:
        raise R2TransferHostError("repository checkout is dirty")
    if observed.commit != expected.get("commit"):
        raise R2TransferHostError("repository commit does not match frozen identity")
    if observed.tree != expected.get("tree"):
        raise R2TransferHostError("repository tree does not match frozen identity")


def _validate_artifact_root_outside_repository(
    *, artifact_root: str | Path, repository_root: str | Path
) -> None:
    repository = Path(repository_root).resolve()
    artifact = Path(artifact_root).resolve()
    try:
        artifact.relative_to(repository)
    except ValueError:
        return
    raise R2TransferHostError("artifact root must resolve outside the repository checkout")


def _expected_binding(identity: Mapping[str, object]) -> dict[str, object]:
    missing = [name for name in _MATERIAL_BINDING_FIELDS if name not in identity]
    if missing:
        raise R2TransferHostError(
            "physical binding is missing frozen fields: " + ", ".join(missing)
        )
    return _json_object_copy(
        {name: identity[name] for name in _MATERIAL_BINDING_FIELDS},
        "physical binding",
    )


def _validate_live_binding(
    expected: Mapping[str, object], observed: Mapping[str, object]
) -> None:
    if set(observed) != set(_MATERIAL_BINDING_FIELDS):
        raise R2TransferHostError("physical binding drift: live binding field set changed")
    for name in _MATERIAL_BINDING_FIELDS:
        if _canonical_json(observed[name]) != _canonical_json(expected[name]):
            raise R2TransferHostError(f"physical binding drift: {name} changed")


def _questions() -> tuple[DurableQuestion, ...]:
    return tuple(
        DurableQuestion.from_content(
            f"r2-call-{entry.call_index:03d}",
            {
                "preregistration_commit": PREREGISTRATION_COMMIT,
                "call_plan_digest": CALL_PLAN_DIGEST,
                "entry": asdict(entry),
            },
            session_id=f"family-{entry.family_index:02d}",
        )
        for entry in call_plan(PREREGISTRATION_COMMIT)
    )


def _question_id(entry: R2CallPlanEntry) -> str:
    return f"r2-call-{entry.call_index:03d}"


def _write_json_atomically(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(_canonical_json(dict(payload)) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_host_failure(
    root: Path, *, kind: str, error: str, next_call_index: int
) -> None:
    _write_json_atomically(
        root / HOST_FAILURE_NAME,
        {
            "status": "INCOMPLETE",
            "claim_status": CLAIM_STATUS,
            "kind": kind,
            "error": error,
            "next_call_index": next_call_index,
            "authority": "instrumentation_only",
        },
    )


class _BoundR2Client:
    def __init__(
        self,
        *,
        client: R2PlanStructuredClient,
        durable_run: DurableQuestionRun,
        live_binding_probe: Callable[[], Mapping[str, object]],
        expected_binding: Mapping[str, object],
    ) -> None:
        self._client = client
        self._durable_run = durable_run
        self._live_binding_probe = live_binding_probe
        self._expected_binding = _json_object_copy(expected_binding, "physical binding")
        self._entry: R2CallPlanEntry | None = None

    def bind_entry(self, entry: R2CallPlanEntry) -> None:
        if self._client.next_plan_entry != entry:
            raise R2TransferHostError("R2 structured client plan cursor disagrees with host")
        self._entry = entry

    def _stop_with_evidence(self, *, kind: str, error: str) -> None:
        if self._entry is None:
            raise R2TransferHostError("terminal failure has no bound R2 plan entry")
        self._durable_run.append_request_evidence(
            question_id=_question_id(self._entry),
            evidence={
                "kind": kind,
                "authority": "instrumentation_only",
                "plan_entry": asdict(self._entry),
                "error": error,
            },
        )
        self._durable_run.mark_stopped()

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        if self._entry is None:
            raise R2TransferHostError("model call attempted without a bound R2 plan entry")
        if self._client.next_plan_entry != self._entry:
            error = "R2 structured client plan cursor drifted before provider call"
            self._stop_with_evidence(kind="call_plan_drift", error=error)
            raise R2TransferHostError(error)
        try:
            observed = self._live_binding_probe()
            if not isinstance(observed, Mapping):
                raise R2TransferHostError(
                    "physical binding drift: live probe did not return an object"
                )
            _validate_live_binding(self._expected_binding, observed)
        except R2TransferHostError as exc:
            self._stop_with_evidence(kind="physical_binding_drift", error=str(exc))
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._stop_with_evidence(kind="physical_binding_probe_failure", error=error)
            raise R2TransferHostError(f"physical binding probe failure: {error}") from exc

        try:
            completion = self._client.complete(messages)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self._stop_with_evidence(kind="provider_client_failure", error=error)
            raise R2TransferHostError(f"provider client failure: {error}") from exc

        self._durable_run.append_request_evidence(
            question_id=_question_id(self._entry),
            evidence={
                "kind": "model_exchange",
                "authority": "instrumentation_only",
                "plan_entry": asdict(self._entry),
                "messages": messages,
                "response": {
                    "content": completion.content,
                    "input_tokens": completion.input_tokens,
                    "output_tokens": completion.output_tokens,
                    "response_id": completion.response_id,
                },
            },
        )
        return completion


def _stop_after_protocol_failure(
    durable_run: DurableQuestionRun,
    *,
    entry: R2CallPlanEntry,
    error: str,
) -> R2TransferHostError:
    durable_run.append_request_evidence(
        question_id=_question_id(entry),
        evidence={
            "kind": "model_protocol_failure",
            "authority": "instrumentation_only",
            "plan_entry": asdict(entry),
            "error": error,
        },
    )
    durable_run.mark_stopped()
    return R2TransferHostError(f"R2 model protocol failure: {error}")


def _validate_arm_prompts(arms: object, family: object) -> None:
    for examples_visible in (0, 1, 2, 3):
        t0 = render_target_prompt(
            arms.t0, family, step_index=0, examples_visible=examples_visible
        )
        t1 = render_target_prompt(
            arms.t1, family, step_index=0, examples_visible=examples_visible
        )
        t2 = render_target_prompt(
            arms.t2, family, step_index=0, examples_visible=examples_visible
        )
        if not (t0.task_digest == t1.task_digest == t2.task_digest):
            raise R2TransferHostError("matched R2 target task digests differ across arms")
        if not (t0.task_packet == t1.task_packet == t2.task_packet):
            raise R2TransferHostError("matched R2 target task packets differ across arms")
        if t0.reusable_structure is not None:
            raise R2TransferHostError("R2 T0 unexpectedly receives reusable Structure")
        if t1.reusable_structure is None or t1.reusable_structure != t2.reusable_structure:
            raise R2TransferHostError("R2 T1/T2 reusable Structure is not identical")


def _resource_mapping(
    *, calls: int, input_tokens: int, output_tokens: int
) -> dict[str, int]:
    return {
        "calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _reconstruct_complete_result(
    durable_run: DurableQuestionRun,
) -> tuple[tuple[R2FamilyOutcome, ...], dict[str, dict[str, int]]]:
    records = durable_run.rebuild_completed_results()
    plan = call_plan(PREREGISTRATION_COMMIT)
    if len(records) != PROVIDER_CALL_COUNT:
        raise R2TransferHostError("complete R2 reconstruction requires 208 durable results")

    source_correct: dict[int, bool] = {}
    curves: dict[int, dict[str, dict[int, bool]]] = {
        index: {"T0": {}, "T1": {}, "T2": {}}
        for index in range(FAMILY_COUNT)
    }
    resources = {
        "physical": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
        "source-learning": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
        "T0": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
        "T1": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
        "T2": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
    }

    for record, entry in zip(records, plan, strict=True):
        if record.get("question_id") != _question_id(entry):
            raise R2TransferHostError("durable R2 result order does not match call plan")
        result = _mapping(record["result"], "durable R2 result")
        if (
            result.get("family_index") != entry.family_index
            or result.get("regime") != entry.regime
            or result.get("seed") != entry.seed
        ):
            raise R2TransferHostError("durable R2 family identity does not match call plan")

        resource = _mapping(result.get("resource_cost"), "durable R2 resource cost")
        calls = resource.get("calls")
        input_tokens = resource.get("input_tokens")
        output_tokens = resource.get("output_tokens")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (calls, input_tokens, output_tokens)
        ):
            raise R2TransferHostError("durable R2 resource cost is invalid")
        if calls != 1:
            raise R2TransferHostError("each R2 durable result must represent one provider call")

        bucket: str
        if entry.phase == "source-learning":
            if result.get("kind") != "source-learning":
                raise R2TransferHostError("durable source result kind is invalid")
            source_value = result.get("source_hypothesis_correct")
            if not isinstance(source_value, bool) or entry.family_index in source_correct:
                raise R2TransferHostError("durable R2 source result is invalid or duplicate")
            source_correct[entry.family_index] = source_value
            bucket = "source-learning"
        else:
            if result.get("kind") != "target-probe":
                raise R2TransferHostError("durable target result kind is invalid")
            if (
                result.get("arm") != entry.arm
                or result.get("examples_visible") != entry.examples_visible
                or result.get("verification_error") is not None
            ):
                raise R2TransferHostError("durable R2 target result disagrees with call plan")
            correct = result.get("correct")
            if not isinstance(correct, bool):
                raise R2TransferHostError("durable R2 target correctness is invalid")
            assert entry.arm is not None
            assert entry.examples_visible is not None
            curves[entry.family_index][entry.arm][entry.examples_visible] = correct
            bucket = entry.arm

        for resource_bucket in (resources["physical"], resources[bucket]):
            resource_bucket["calls"] += calls
            resource_bucket["input_tokens"] += input_tokens
            resource_bucket["output_tokens"] += output_tokens

    outcomes: list[R2FamilyOutcome] = []
    family_identity: dict[int, tuple[str, int]] = {}
    for entry in plan:
        family_identity.setdefault(entry.family_index, (entry.regime, entry.seed))
        if family_identity[entry.family_index] != (entry.regime, entry.seed):
            raise R2TransferHostError("R2 call plan family identity is inconsistent")

    for family_index in range(FAMILY_COUNT):
        if family_index not in source_correct:
            raise R2TransferHostError("R2 source result is missing")
        regime, seed = family_identity[family_index]
        arm_curves: dict[str, tuple[bool, bool, bool, bool]] = {}
        for arm in ("T0", "T1", "T2"):
            values = curves[family_index][arm]
            if set(values) != {0, 1, 2, 3}:
                raise R2TransferHostError("R2 target adaptation curve is incomplete")
            arm_curves[arm] = tuple(values[index] for index in range(4))  # type: ignore[assignment]
        outcomes.append(
            R2FamilyOutcome(
                family_index=family_index,
                regime=regime,
                seed=seed,
                source_hypothesis_correct=source_correct[family_index],
                t0=arm_curves["T0"],
                t1=arm_curves["T1"],
                t2=arm_curves["T2"],
            )
        )

    if resources["physical"]["calls"] != PROVIDER_CALL_COUNT:
        raise R2TransferHostError("R2 reconstructed physical call count is not 208")
    return tuple(outcomes), resources


def run_r2_transfer_host_campaign(
    *,
    artifact_root: str | Path,
    identity: Mapping[str, object],
    repository_root: str | Path,
    live_binding_probe: Callable[[], Mapping[str, object]],
    client: R2PlanStructuredClient,
    run_id: str | None = None,
) -> R2TransferHostResult:
    """Execute the frozen 208-call R2 shared/null campaign exactly once."""

    if not isinstance(identity, Mapping):
        raise R2TransferHostError("frozen experiment identity must be an object")
    identity_snapshot = _json_object_copy(identity, "frozen experiment identity")
    _validate_static_contract(identity_snapshot)
    observed_repository = probe_git_repository(repository_root)
    _validate_repository(identity_snapshot, observed_repository)
    _validate_artifact_root_outside_repository(
        artifact_root=artifact_root,
        repository_root=repository_root,
    )
    if client.identity != transport_identity(PREREGISTRATION_COMMIT):
        raise R2TransferHostError("R2 structured client identity is not frozen")
    first_entry = call_plan(PREREGISTRATION_COMMIT)[0]
    if client.call_count != 0 or client.next_plan_entry != first_entry:
        raise R2TransferHostError("R2 structured client must begin at call-plan cursor zero")

    proposed_binding = _expected_binding(identity_snapshot)
    try:
        initial_live_binding = live_binding_probe()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise R2TransferHostError(
            f"physical binding probe failure during preflight: {error}"
        ) from exc
    if not isinstance(initial_live_binding, Mapping):
        raise R2TransferHostError("physical binding drift: live probe did not return an object")
    _validate_live_binding(proposed_binding, initial_live_binding)

    try:
        frozen_identity: FrozenExperimentIdentity = freeze_experiment_identity(
            identity=identity_snapshot,
            live_attestation=_mapping(
                initial_live_binding["launch_admission"],
                "live launch admission",
            ),
        )
    except ExternalQualificationError as exc:
        raise R2TransferHostError(f"physical frozen identity is invalid: {exc}") from exc

    expected_binding = _expected_binding(frozen_identity.to_mapping())
    try:
        durable_run = DurableQuestionRun.start(
            artifact_root=artifact_root,
            identity=frozen_identity,
            questions=_questions(),
            run_id=run_id,
            run_mode="fresh_run",
        )
    except ExternalQualificationError as exc:
        raise R2TransferHostError(f"artifact root or durable identity rejected: {exc}") from exc

    root = Path(artifact_root)
    bound_client = _BoundR2Client(
        client=client,
        durable_run=durable_run,
        live_binding_probe=live_binding_probe,
        expected_binding=expected_binding,
    )
    plan = call_plan(PREREGISTRATION_COMMIT)
    families = generate_families(PREREGISTRATION_COMMIT)
    cursor = 0

    for family_index, family in enumerate(families):
        source_entry = plan[cursor]
        if (
            source_entry.family_index != family_index
            or source_entry.phase != "source-learning"
            or source_entry.seed != family.seed
            or source_entry.regime != family.regime
        ):
            durable_run.mark_stopped()
            _write_host_failure(
                root,
                kind="call_plan_mismatch",
                error="source-learning plan entry does not match generated family",
                next_call_index=cursor,
            )
            raise R2TransferHostError("R2 source-learning call plan mismatch")

        source_question = _question_id(source_entry)
        durable_run.begin_question(source_question)
        bound_client.bind_entry(source_entry)
        try:
            learned = run_source_learning(bound_client, family)
        except R2TransferHostError as exc:
            _write_host_failure(
                root,
                kind="execution_failure",
                error=str(exc),
                next_call_index=cursor,
            )
            raise
        except StructureProposalError as exc:
            error = str(exc)
            _write_host_failure(
                root,
                kind="model_protocol_failure",
                error=error,
                next_call_index=cursor,
            )
            raise _stop_after_protocol_failure(
                durable_run,
                entry=source_entry,
                error=error,
            ) from exc

        durable_run.commit_question(
            question_id=source_question,
            result={
                "kind": "source-learning",
                "claim_status": CLAIM_STATUS,
                "family_index": family_index,
                "regime": family.regime,
                "seed": family.seed,
                "structure_id": learned.structure_id,
                "hypothesis": learned.hypothesis.to_mapping(),
                "source_hypothesis_correct": source_hypothesis_matches_family(
                    learned.hypothesis,
                    family,
                ),
                "source_evidence_ids": list(learned.source_evidence_ids),
                "resource_cost": _resource_mapping(
                    calls=learned.resource_cost.calls,
                    input_tokens=learned.resource_cost.input_tokens,
                    output_tokens=learned.resource_cost.output_tokens,
                ),
            },
        )
        cursor += 1

        try:
            arms = prepare_r1_arms(family, learned)
            _validate_arm_prompts(arms, family)
        except (StructureProposalError, R2TransferHostError) as exc:
            durable_run.mark_stopped()
            _write_host_failure(
                root,
                kind="arm_preparation_failure",
                error=str(exc),
                next_call_index=cursor,
            )
            raise R2TransferHostError(f"R2 arm preparation failed: {exc}") from exc

        arm_by_name = {"T0": arms.t0, "T1": arms.t1, "T2": arms.t2}
        for arm_name in ("T0", "T1", "T2"):
            for examples_visible in (0, 1, 2, 3):
                entry = plan[cursor]
                if (
                    entry.family_index != family_index
                    or entry.phase != "target"
                    or entry.arm != arm_name
                    or entry.examples_visible != examples_visible
                    or entry.seed != family.seed
                    or entry.regime != family.regime
                ):
                    durable_run.mark_stopped()
                    _write_host_failure(
                        root,
                        kind="call_plan_mismatch",
                        error="target plan entry does not match host execution",
                        next_call_index=cursor,
                    )
                    raise R2TransferHostError("R2 target call plan mismatch")

                question_id = _question_id(entry)
                durable_run.begin_question(question_id)
                bound_client.bind_entry(entry)
                try:
                    probe = run_target_probe(
                        bound_client,
                        arm_by_name[arm_name],
                        family,
                        step_index=0,
                        examples_visible=examples_visible,
                    )
                except R2TransferHostError as exc:
                    _write_host_failure(
                        root,
                        kind="execution_failure",
                        error=str(exc),
                        next_call_index=cursor,
                    )
                    raise
                except StructureProposalError as exc:
                    error = str(exc)
                    _write_host_failure(
                        root,
                        kind="model_protocol_failure",
                        error=error,
                        next_call_index=cursor,
                    )
                    raise _stop_after_protocol_failure(
                        durable_run,
                        entry=entry,
                        error=error,
                    ) from exc

                if probe.verification.error is not None:
                    error = (
                        "target response violates the structured answer contract: "
                        + probe.verification.error
                    )
                    _write_host_failure(
                        root,
                        kind="model_protocol_failure",
                        error=error,
                        next_call_index=cursor,
                    )
                    raise _stop_after_protocol_failure(
                        durable_run,
                        entry=entry,
                        error=error,
                    )

                reusable = probe.prompt.reusable_structure
                durable_run.commit_question(
                    question_id=question_id,
                    result={
                        "kind": "target-probe",
                        "claim_status": CLAIM_STATUS,
                        "family_index": family_index,
                        "regime": family.regime,
                        "seed": family.seed,
                        "arm": arm_name,
                        "examples_visible": examples_visible,
                        "correct": probe.verification.correct,
                        "verification_error": None,
                        "task_digest": probe.prompt.task_digest,
                        "reusable_structure_present": reusable is not None,
                        "reusable_structure_digest": _sha256(reusable),
                        "resource_cost": _resource_mapping(
                            calls=probe.resource_cost.calls,
                            input_tokens=probe.resource_cost.input_tokens,
                            output_tokens=probe.resource_cost.output_tokens,
                        ),
                    },
                )
                cursor += 1

    if cursor != PROVIDER_CALL_COUNT or client.call_count != PROVIDER_CALL_COUNT:
        durable_run.mark_stopped()
        _write_host_failure(
            root,
            kind="counter_mismatch",
            error="R2 host/client did not consume exactly 208 provider calls",
            next_call_index=cursor,
        )
        raise R2TransferHostError("R2 provider call counter mismatch")
    if client.next_plan_entry is not None:
        durable_run.mark_stopped()
        raise R2TransferHostError("R2 structured client still has an unconsumed plan entry")

    outcomes, resources = _reconstruct_complete_result(durable_run)
    analysis = analyze_r2(
        outcomes,
        preregistration_commit=PREREGISTRATION_COMMIT,
        complete=True,
        protocol_valid=True,
    )
    result_payload: dict[str, object] = {
        "status": "COMPLETED",
        "claim_status": CLAIM_STATUS,
        "citable": True,
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_digest": PREREGISTRATION_DIGEST,
        "call_plan_digest": CALL_PLAN_DIGEST,
        "transport_identity_digest": TRANSPORT_IDENTITY_DIGEST,
        "provider_calls": PROVIDER_CALL_COUNT,
        "family_count": FAMILY_COUNT,
        "analysis": asdict(analysis),
        "family_outcomes": [asdict(outcome) for outcome in outcomes],
        "resource_totals": resources,
    }
    result_path = root / RESULT_NAME
    try:
        _write_json_atomically(result_path, result_payload)
        durable_run.mark_completed()
    except (OSError, ExternalQualificationError) as exc:
        result_path.unlink(missing_ok=True)
        durable_run.mark_stopped()
        _write_host_failure(
            root,
            kind="result_persistence_failure",
            error=str(exc),
            next_call_index=cursor,
        )
        raise R2TransferHostError(f"R2 result persistence failed: {exc}") from exc

    return R2TransferHostResult(
        run_id=durable_run.run_id,
        identity_fingerprint=frozen_identity.fingerprint,
        status="COMPLETED",
        claim_status=CLAIM_STATUS,
        citable=True,
        category=analysis.category,
        provider_calls=PROVIDER_CALL_COUNT,
        family_count=FAMILY_COUNT,
        result_path=str(result_path),
    )
