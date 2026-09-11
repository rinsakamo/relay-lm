from __future__ import annotations

import relaylm.v2_cognitive_ir_s3 as s3
from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm import v2_cognitive_ir_p2_termination_qual as historical
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    P2_BOUNDEDNESS_HARD_MAX_WORDS,
    P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS,
    P2_BOUNDEDNESS_QUAL_V2_CONTRACT,
    P2_BOUNDEDNESS_QUAL_V2_SEEDS,
    P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
    P2_BOUNDEDNESS_TARGET_MAX_WORDS,
    P2_BOUNDEDNESS_TARGET_MIN_WORDS,
    build_margin_p2_formation_messages,
    derive_p2_boundedness_qual_v2_seed,
    generate_qualification_family_v2,
    qualification_call_plan_v2,
    validate_p2_boundedness_qualification_v2,
)


def test_fresh_boundedness_seed_rules_and_call_plan() -> None:
    validate_p2_boundedness_qualification_v2()
    derived = {
        regime: tuple(derive_p2_boundedness_qual_v2_seed(regime, index) for index in range(3))
        for regime in s3.S3_REGIMES
    }
    assert derived == dict(P2_BOUNDEDNESS_QUAL_V2_SEEDS)
    fresh = {seed for values in P2_BOUNDEDNESS_QUAL_V2_SEEDS.values() for seed in values}
    consumed = {seed for values in historical.P2_TERMINATION_QUAL_SEEDS.values() for seed in values}
    r4 = {seed for values in historical.S3_R4_PRECOMMITTED_SEEDS.values() for seed in values}
    assert len(fresh) == 12
    assert fresh.isdisjoint(consumed)
    assert fresh.isdisjoint(r4)

    plan = qualification_call_plan_v2()
    assert len(plan) == 12
    assert plan[0] == "shared:0:1429064482:form-p2"
    assert plan[3] == "null:0:557367045:form-p2"
    assert plan[6] == "mismatch:0:2085578331:form-p2"
    assert plan[9] == "shift:0:534887107:form-p2"
    assert plan[-1] == "shift:2:304353334:form-p2"


def test_margin_builder_preserves_legacy_p2_source_semantics_without_historical_mutation() -> None:
    old_contract = historical.P2_TERMINATION_QUAL_CONTRACT
    old_seeds = dict(historical.P2_TERMINATION_QUAL_SEEDS)
    original_label = s3.S3_LABEL
    original_s3_seeds = s3.S3_SEEDS

    family = generate_qualification_family_v2("shared", 0)
    assert s3.S3_LABEL == original_label
    assert s3.S3_SEEDS is original_s3_seeds

    legacy = build_s2_formation_messages("P2_ORDINARY_SUMMARY", family)
    repaired = build_margin_p2_formation_messages(family)
    assert repaired[1] == legacy[1]
    assert repaired[0]["content"] == legacy[0]["content"] + "\n" + P2_BOUNDEDNESS_QUAL_V2_CONTRACT
    assert "evaluator-hidden rules" in repaired[0]["content"]
    assert "60 to 80 words" in repaired[0]["content"]
    assert "550 Unicode characters" in repaired[0]["content"]
    assert "Do not fill the available output budget" in repaired[0]["content"]

    assert historical.P2_TERMINATION_QUAL_CONTRACT == old_contract
    assert dict(historical.P2_TERMINATION_QUAL_SEEDS) == old_seeds
    assert "Use no more than 120 words and no more than 800 Unicode characters." in old_contract


def test_target_margin_is_strictly_inside_unchanged_hard_envelope() -> None:
    assert (P2_BOUNDEDNESS_TARGET_MIN_WORDS, P2_BOUNDEDNESS_TARGET_MAX_WORDS) == (60, 80)
    assert P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS == 550
    assert P2_BOUNDEDNESS_HARD_MAX_WORDS == 120
    assert P2_BOUNDEDNESS_HARD_MAX_CHARACTERS == 800
    assert P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS == 1024
    assert P2_BOUNDEDNESS_TARGET_MAX_WORDS < P2_BOUNDEDNESS_HARD_MAX_WORDS
    assert P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS < P2_BOUNDEDNESS_HARD_MAX_CHARACTERS
