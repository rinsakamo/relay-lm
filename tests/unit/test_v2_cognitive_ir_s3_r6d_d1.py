from __future__ import annotations

from types import SimpleNamespace

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_attack_observability_calibration import ATTACK_OBS_SEEDS
from relaylm.v2_cognitive_ir_s3_r6d_d1 import (
    D1_CLAIM,
    D1_FAMILY_COUNT,
    D1_LABEL,
    D1_PREREGISTRATION_SHA256,
    D1_SCHEMA,
    D1_SEEDS,
    D1_TOTAL_INPUT_TOKEN_REQUESTS,
    D1_TOTAL_SEMANTIC_CALLS,
    activate_d1_preregistration,
    canonical_correct_counts,
    d1_call_plan,
    derive_d1_seed,
    evaluate_d1,
    generate_d1_family,
    validate_d1_preregistration,
)
import tools.v2_cognitive_ir_s3_r5_llama_cpp_wsl as legacy_wsl
import tools.v2_cognitive_ir_s3_r6d_d1_llama_cpp_transaction as d1_tx
import tools.v2_cognitive_ir_s3_r6d_d1_llama_cpp_wsl as d1_wsl


def _flatten(values):
    return {seed for seeds in values.values() for seed in seeds}


def test_d1_identity_seeds_and_collision_fence() -> None:
    validate_d1_preregistration()
    assert D1_SCHEMA == "relaylm2-cognitive-ir-s3-r6d-d1-prereg-v1"
    assert D1_LABEL == "relaylm2-cognitive-ir-s3-r6d-shared-discriminator-v1"
    assert D1_PREREGISTRATION_SHA256 == (
        "b3709c57d7c421060d3776932442ef1e06ea808be1abfb3833d7992c5cf5f1b4"
    )
    assert tuple(derive_d1_seed(index) for index in range(24)) == D1_SEEDS
    assert len(set(D1_SEEDS)) == 24
    assert set(D1_SEEDS).isdisjoint(_flatten(ATTACK_OBS_SEEDS))


def test_d1_shared_families_preserve_k3_geometry_and_no_wrap() -> None:
    for index in range(D1_FAMILY_COUNT):
        family = generate_d1_family("shared", index)
        assert family.seed == D1_SEEDS[index]
        assert family.regime == "shared"
        assert family.shift_index is None
        assert family.source_rule.permutation == (0, 1, 2, 3)
        assert sum(value != 0 for value in family.source_rule.offsets) == 3
        assert family.target_rules == (family.source_rule,) * 4
        assert len(family.source_examples) == 4
        assert len(family.target_steps) == 4
        assert all(len(step.examples) == 3 for step in family.target_steps)


def test_d1_call_plan_is_exact_24_by_41() -> None:
    plan = d1_call_plan("shared")
    assert len(plan) == 984
    assert len(set(plan)) == 984
    assert sum(":form-" in question for question in plan) == 72
    assert sum(":canonical:" in question for question in plan) == 168
    assert sum(":surface:" in question for question in plan) == 192
    assert sum(":semantic:" in question for question in plan) == 384
    assert sum(":option:" in question for question in plan) == 168
    assert not any(":anchor:" in question for question in plan)


def _synthetic_shard(*, p4_equals_p3: bool) -> base.S3ShardResult:
    families = []
    for index, seed in enumerate(D1_SEEDS):
        if p4_equals_p3:
            p4_correct = index < 18
        else:
            p4_correct = True
        correctness = {
            "P0_RAW_HISTORY": index < 10,
            "P1_RETRIEVAL_ONLY": index < 12,
            "P2_ORDINARY_SUMMARY": index < 12,
            "P3_SEMANTIC_CACHE": index < 18,
            "P4_MEMORY_PLUS_STRUCTURE": p4_correct,
            "P5_STRUCTURE_ONLY_RECONSTRUCTABLE": index < 20,
            "P6_GENERIC_EQUAL_INFORMATION": index >= 6,
        }
        records = [
            base.S3CallRecord(
                question_id=f"{seed}:form-p2",
                panel="formation",
                arm="P2",
                correct=None,
                input_tokens=10,
                output_tokens=5,
                projected_bytes=0,
            ),
            base.S3CallRecord(
                question_id=f"{seed}:form-p3",
                panel="formation",
                arm="P3",
                correct=None,
                input_tokens=11,
                output_tokens=5,
                projected_bytes=0,
            ),
            base.S3CallRecord(
                question_id=f"{seed}:form-p4",
                panel="formation",
                arm="P4",
                correct=None,
                input_tokens=12,
                output_tokens=5,
                projected_bytes=0,
            ),
        ]
        for arm_index, arm in enumerate(base.REPRESENTATION_KINDS):
            records.append(
                base.S3CallRecord(
                    question_id=f"{seed}:canonical:{arm}",
                    panel="canonical",
                    arm=arm,
                    correct=correctness[arm],
                    input_tokens=20 + arm_index,
                    output_tokens=4,
                    projected_bytes=80 + 10 * arm_index,
                )
            )
            records.append(
                base.S3CallRecord(
                    question_id=f"{seed}:option:{arm}",
                    panel="option_value",
                    arm=arm,
                    correct=(index + arm_index) % 2 == 0,
                    input_tokens=14,
                    output_tokens=2,
                    projected_bytes=80 + 10 * arm_index,
                )
            )
        families.append(
            base.S3FamilyResult(
                regime="shared",
                seed=seed,
                records=tuple(records),
                p4_p6_semantic_equal=True,
                shared_formation_lineage=True,
                provenance_audit_changed=True,
            )
        )
    return base.S3ShardResult(
        regime="shared",
        families=tuple(families),
        semantic_calls=984,
        work={},
        surface_perturbation_effect=0.05,
        semantic_intervention_effect=0.25,
        semantic_invariance_gate=True,
    )


def test_d1_analysis_earns_type_only_when_both_primary_contrasts_survive() -> None:
    result = evaluate_d1(_synthetic_shard(p4_equals_p3=False))
    assert result["p4_gt_p3"]["first_only"] == 6
    assert result["p4_gt_p3"]["second_only"] == 0
    assert result["p4_gt_p3"]["exact_directional_p"] == 0.015625
    assert result["p4_gt_p6"]["first_only"] == 6
    assert result["p4_gt_p6"]["second_only"] == 0
    assert result["dedicated_type_earned"] is True
    assert result["semantic_cache_useful"] is False
    assert result["architecture_consequence"] == "NONE"


def test_d1_analysis_can_earn_semantic_cache_without_equivalence_claim() -> None:
    shard = _synthetic_shard(p4_equals_p3=True)
    counts = canonical_correct_counts(shard)
    assert counts["P3_SEMANTIC_CACHE"] == counts["P4_MEMORY_PLUS_STRUCTURE"] == 18
    result = evaluate_d1(shard)
    assert result["p4_gt_p3"]["exact_directional_p"] == 1.0
    assert result["p3_gt_p2"]["exact_directional_p"] == 0.015625
    assert result["p3_gt_p1"]["exact_directional_p"] == 0.015625
    assert result["dedicated_type_earned"] is False
    assert result["semantic_cache_useful"] is True


def test_d1_activation_binds_shared_only_campaign_and_restores_with_monkeypatch(
    monkeypatch,
) -> None:
    names = (
        "S3_PREREGISTRATION_SCHEMA",
        "S3_PREREGISTRATION_SHA256",
        "S3_LABEL",
        "S3_REGIMES",
        "S3_SEEDS",
        "S3_SHARD_CALLS",
        "S3_TOTAL_SEMANTIC_CALLS",
        "S3_TOTAL_INPUT_TOKEN_REQUESTS",
        "S3_CLAIM",
        "S3_INCOMPLETE_CLAIM",
        "generate_s3_family",
        "form_s2_representations",
        "run_s3_shard",
        "s3_call_plan",
    )
    with monkeypatch.context() as context:
        for name in names:
            context.setattr(base, name, getattr(base, name))
        activate_d1_preregistration()
        assert base.S3_REGIMES == ("shared",)
        assert base.S3_SEEDS == {"shared": D1_SEEDS}
        assert base.S3_SHARD_CALLS == {"shared": D1_TOTAL_SEMANTIC_CALLS}
        assert base.S3_TOTAL_SEMANTIC_CALLS == D1_TOTAL_SEMANTIC_CALLS
        assert base.S3_TOTAL_INPUT_TOKEN_REQUESTS == D1_TOTAL_INPUT_TOKEN_REQUESTS
        assert base.S3_CLAIM == D1_CLAIM
        assert base.s3_call_plan is d1_call_plan


def test_d1_transaction_loader_activates_before_import(monkeypatch) -> None:
    observed = []
    fake_transaction = SimpleNamespace(
        S3_PREREGISTRATION_SHA256="old",
        S3_LLAMA_CPP_MAX_OUTPUT_TOKENS=1,
        S3LlamaCppClient=object,
    )
    fake_listener = SimpleNamespace(main=lambda argv: 0)

    monkeypatch.setattr(
        d1_tx,
        "activate_d1_preregistration",
        lambda: observed.append("activated"),
    )

    def fake_import(name):
        observed.append(name)
        if name == "tools.v2_cognitive_ir_s3_llama_cpp_transaction":
            return fake_transaction
        if name == "tools.v2_cognitive_ir_s3_llama_cpp_transaction_listener_safe":
            return fake_listener
        raise AssertionError(name)

    monkeypatch.setattr(d1_tx.importlib, "import_module", fake_import)
    transaction, listener = d1_tx._load_listener_safe_transaction()
    assert observed[0] == "activated"
    assert transaction is fake_transaction
    assert listener is fake_listener
    assert transaction.S3_PREREGISTRATION_SHA256 == D1_PREREGISTRATION_SHA256
    assert transaction.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS == 1024


def test_d1_wsl_adapter_targets_dedicated_transaction_and_restores(monkeypatch) -> None:
    observed = []

    def fake_main(argv):
        observed.append(
            (legacy_wsl.INNER_TRANSACTION_MODULE, legacy_wsl.WALL_TIME_SCHEMA)
        )
        return 23

    monkeypatch.setattr(legacy_wsl, "main", fake_main)
    result = d1_wsl.main(["--repo-root", "."])
    assert result == 23
    assert observed == [
        (
            "tools.v2_cognitive_ir_s3_r6d_d1_llama_cpp_transaction",
            "relaylm2-cognitive-ir-s3-r6d-d1-wsl-wall-time-v1",
        )
    ]
    assert legacy_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_s3_r5_llama_cpp_transaction"
    )
    assert legacy_wsl.WALL_TIME_SCHEMA == (
        "relaylm2-cognitive-ir-s3-r5-wsl-wall-time-v1"
    )
