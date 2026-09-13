from __future__ import annotations

from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
    freeze_consumer_identity,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction_strict_physical import (
    generate_synthetic_canonical_payload,
    run_strict_semantic_reconstruction_campaign,
)


def _identity() -> FrozenConsumerIdentity:
    identity = freeze_consumer_identity(
        repository_commit="a" * 40,
        repository_tree="b" * 40,
        model="gemma-test",
        runtime_attestation={
            "upstream_revision": "c" * 40,
            "build_info": "llama.cpp build test",
            "model_alias": "gemma-test",
            "model_path": "/tmp/model.gguf",
            "model_ftype": "Q4_K_M",
            "artifact_sha256": "d" * 64,
            "chat_template_sha256": "e" * 64,
            "context_limit": 8192,
            "total_slots": 1,
            "context_shift_enabled": False,
        },
    )
    identity.validate()
    return identity


class _CountAttemptFailureClient:
    provider_attempts = 0
    provider_completions = 0
    input_count_attempts = 0
    input_count_completions = 0

    def complete_named(self, question_id, messages, *, output_kind):
        del question_id, messages, output_kind
        self.input_count_attempts += 1
        raise RuntimeError("synthetic input counter failure after request attempt")

    def require_complete_plan(self) -> None:
        raise AssertionError("terminal partial campaign must not require full plan")


def _synthetic_factory(index: int, _seed: int, identity: FrozenConsumerIdentity):
    identity.validate()
    return generate_synthetic_canonical_payload(91_000_003_000_000 + index)


def test_input_count_attempt_before_provider_post_is_terminal_scientific_spend() -> None:
    client = _CountAttemptFailureClient()
    result = run_strict_semantic_reconstruction_campaign(
        client,
        frozen_identity=_identity(),
        family_factory=_synthetic_factory,
    )

    assert result.completed is False
    assert result.measurement_admitted is False
    assert result.classification == (
        "MEASUREMENT_OR_RUNTIME_FAILURE_AFTER_SCIENTIFIC_SPEND"
    )
    assert result.citable_for_accessibility_claim is False
    assert result.semantic_calls == 0
    assert result.provider_completions == 0
    assert result.input_token_requests == 1
    assert result.input_token_completions == 0
    assert result.cells == ()
    assert result.paired is None
    assert result.p_value is None
    assert result.failure == (
        "RuntimeError: synthetic input counter failure after request attempt"
    )
