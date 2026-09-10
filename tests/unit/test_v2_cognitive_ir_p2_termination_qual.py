from __future__ import annotations

import relaylm.v2_cognitive_ir_s3 as s3
from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm.v2_cognitive_ir_p2_termination_qual import (
    P2_TERMINATION_QUAL_CONTRACT,
    P2_TERMINATION_QUAL_MAX_CHARACTERS,
    P2_TERMINATION_QUAL_MAX_OUTPUT_TOKENS,
    P2_TERMINATION_QUAL_MAX_WORDS,
    P2_TERMINATION_QUAL_SEEDS,
    S3_R4_PRECOMMITTED_SEEDS,
    build_bounded_p2_formation_messages,
    derive_p2_termination_qual_seed,
    derive_s3_r4_precommitted_seed,
    generate_qualification_family,
    qualification_call_plan,
    validate_p2_termination_qualification,
)
from relaylm.v2_cognitive_ir_s3_r2 import (
    S3_R2_PREREGISTRATION_SHA256,
    S3_R2_SEEDS,
)
from relaylm.v2_cognitive_ir_s3_r3 import (
    S3_R3_MAX_OUTPUT_TOKENS,
    S3_R3_PREREGISTRATION_SHA256,
    S3_R3_SEEDS,
)


def test_qualification_and_r4_seed_rules_are_frozen_and_disjoint() -> None:
    validate_p2_termination_qualification()

    derived_qual = {
        regime: tuple(derive_p2_termination_qual_seed(regime, index) for index in range(3))
        for regime in s3.S3_REGIMES
    }
    derived_r4 = {
        regime: tuple(derive_s3_r4_precommitted_seed(regime, index) for index in range(3))
        for regime in s3.S3_REGIMES
    }
    assert derived_qual == dict(P2_TERMINATION_QUAL_SEEDS)
    assert derived_r4 == dict(S3_R4_PRECOMMITTED_SEEDS)

    qual = {seed for values in P2_TERMINATION_QUAL_SEEDS.values() for seed in values}
    r4 = {seed for values in S3_R4_PRECOMMITTED_SEEDS.values() for seed in values}
    historical = {
        *(seed for values in s3.S3_SEEDS.values() for seed in values),
        *(seed for values in S3_R2_SEEDS.values() for seed in values),
        *(seed for values in S3_R3_SEEDS.values() for seed in values),
    }
    assert len(qual) == 12
    assert len(r4) == 12
    assert qual.isdisjoint(r4)
    assert qual.isdisjoint(historical)
    assert r4.isdisjoint(historical)


def test_qualification_call_plan_is_exactly_twelve_p2_formations() -> None:
    plan = qualification_call_plan()
    assert len(plan) == 12
    assert plan[0] == "shared:0:961584193:form-p2"
    assert plan[3] == "null:0:1501099255:form-p2"
    assert plan[6] == "mismatch:0:1461365599:form-p2"
    assert plan[9] == "shift:0:137041362:form-p2"
    assert plan[-1] == "shift:2:9745268:form-p2"
    assert all(question_id.endswith(":form-p2") for question_id in plan)


def test_bounded_p2_builder_preserves_legacy_source_packet_and_semantics() -> None:
    original_label = s3.S3_LABEL
    original_seeds = s3.S3_SEEDS
    family = generate_qualification_family("shared", 0)
    assert s3.S3_LABEL == original_label
    assert s3.S3_SEEDS is original_seeds

    legacy = build_s2_formation_messages("P2_ORDINARY_SUMMARY", family)
    bounded = build_bounded_p2_formation_messages(family)
    assert bounded[1] == legacy[1]
    assert bounded[0]["content"] == legacy[0]["content"] + "\n" + P2_TERMINATION_QUAL_CONTRACT
    assert "evaluator-hidden rules" in bounded[0]["content"]
    assert "plain-text recap paragraph" in bounded[0]["content"]
    assert "120 words" in bounded[0]["content"]
    assert "800 Unicode characters" in bounded[0]["content"]
    assert P2_TERMINATION_QUAL_MAX_WORDS == 120
    assert P2_TERMINATION_QUAL_MAX_CHARACTERS == 800
    assert P2_TERMINATION_QUAL_MAX_OUTPUT_TOKENS == 1024


def test_historical_s3_r2_r3_identity_and_budget_remain_frozen() -> None:
    assert S3_R2_PREREGISTRATION_SHA256 == (
        "d3e19d59c2c6481178b942d462e4fca0a1ace02ed8deea1ae3c22f68c59f2166"
    )
    assert S3_R3_PREREGISTRATION_SHA256 == (
        "a0b137f023c260eb9da479f5722708f6cf6f955198e4234203753831e9278ed1"
    )
    assert S3_R3_MAX_OUTPUT_TOKENS == 1024
