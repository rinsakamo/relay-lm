from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

import tools.relay_physical_run as runner
import tools.v1_installed_llama_cpp_cache_on_experiment as experiment
import tools.v1_installed_llama_cpp_transaction as transaction


REPO_ROOT = Path(__file__).parents[2]
MODEL = "gemma-local"


def _json_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def _generation_payload(*, cache_prompt: object = False) -> dict[str, Any]:
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": "ordinary provider payload"}],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 256,
        "cache_prompt": cache_prompt,
        "reasoning_effort": "none",
        "stream": False,
    }


def _input_payload() -> dict[str, Any]:
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": "ordinary provider payload"}],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 256,
        "cache_prompt": False,
        "reasoning_effort": "none",
    }


def test_experimental_target_is_separate_and_control_target_is_unchanged() -> None:
    targets = runner._load_targets(REPO_ROOT)

    control = targets[transaction.TARGET_NAME]
    treatment = targets[experiment.EXPERIMENT_TARGET_NAME]

    assert control.module == "tools.v1_installed_llama_cpp_wsl"
    assert control.branch == "v1"
    assert control.required_distributions == ("build", "httpx")
    assert treatment.module == "tools.v1_installed_llama_cpp_cache_on_experiment"
    assert treatment.branch == "v1"
    assert treatment.required_distributions == ("build", "httpx")
    assert treatment.module != control.module


def test_generation_treatment_changes_exactly_cache_prompt_false_to_true() -> None:
    product = _generation_payload()
    product_body = _json_body(product)

    upstream_body, evidence = experiment._prepare_upstream_body(
        "/v1/chat/completions",
        product_body,
    )
    upstream = json.loads(upstream_body)

    assert product["cache_prompt"] is False
    assert upstream["cache_prompt"] is True
    assert evidence["applied"] is True
    assert evidence["normalized_delta"] == {
        "changed_keys": ["cache_prompt"],
        "cache_prompt": {"from": False, "to": True},
        "all_other_fields_equal": True,
    }
    assert evidence["product_controls"]["cache_prompt"] is False
    assert evidence["upstream_controls"]["cache_prompt"] is True
    assert evidence["product_request_sha256"] != evidence[
        "upstream_treatment_request_sha256"
    ]

    product_without_cache = copy.deepcopy(product)
    upstream_without_cache = copy.deepcopy(upstream)
    product_without_cache.pop("cache_prompt")
    upstream_without_cache.pop("cache_prompt")
    assert upstream_without_cache == product_without_cache


def test_input_token_request_is_forwarded_byte_identically_without_treatment() -> None:
    body = _json_body(_input_payload())

    upstream_body, evidence = experiment._prepare_upstream_body(
        "/v1/chat/completions/input_tokens",
        body,
    )

    assert upstream_body == body
    assert evidence["applied"] is False
    assert evidence["endpoint_class"] == "input_token_count"
    assert evidence["forwarding"] == "byte_identical"
    assert evidence["product_request_sha256"] == evidence["upstream_request_sha256"]
    assert evidence["input_token_rendering_equivalence"]["status"] == (
        "proven_for_supported_revision"
    )


def test_count_equivalence_proof_is_bound_to_exact_supported_llama_revision() -> None:
    proof = experiment.COUNT_RENDERING_EQUIVALENCE

    assert proof["llama_cpp_revision"] == (
        "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
    )
    assert proof["generation_source"] == "tools/server/server-context.cpp"
    assert proof["count_source"].endswith("::handle_count_tokens")
    assert "common-prefix KV reuse" in proof["generation_fact"]
    assert "without a cache_prompt branch" in proof["count_fact"]


@pytest.mark.parametrize(
    "payload, message",
    [
        (
            {
                key: value
                for key, value in _generation_payload().items()
                if key != "cache_prompt"
            },
            "explicit product-side cache_prompt=false",
        ),
        (_generation_payload(cache_prompt=True), "not cache_prompt=false"),
    ],
)
def test_generation_treatment_rejects_missing_or_non_false_product_policy(
    payload: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(experiment.CacheTreatmentError, match=message):
        experiment._prepare_upstream_body(
            "/v1/chat/completions",
            _json_body(payload),
        )


def test_generation_treatment_rejects_malformed_json() -> None:
    with pytest.raises(transaction.RequestLedgerError, match="not valid JSON"):
        experiment._prepare_upstream_body(
            "/v1/chat/completions",
            b"{not-json",
        )


def test_delta_proof_rejects_a_second_field_change() -> None:
    product = _generation_payload()
    treatment = copy.deepcopy(product)
    treatment["cache_prompt"] = True
    treatment["temperature"] = 0.5

    with pytest.raises(
        experiment.CacheTreatmentError,
        match="exactly cache_prompt and no second field",
    ):
        experiment._prove_exact_cache_delta(product, treatment)


def test_treatment_rejects_wrong_endpoint() -> None:
    with pytest.raises(experiment.CacheTreatmentError, match="unsupported"):
        experiment._prepare_upstream_body(
            "/v1/not-a-treatment-endpoint",
            _json_body(_generation_payload()),
        )


def test_experiment_wrapper_scopes_proxy_and_target_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    original_proxy = transaction._ForwardingProxy
    original_target = transaction.TARGET_NAME

    def fake_main(argv: object) -> int:
        observed["argv"] = argv
        observed["proxy"] = transaction._ForwardingProxy
        observed["target"] = transaction.TARGET_NAME
        return 7

    monkeypatch.setattr(transaction, "main", fake_main)

    assert experiment.main(["--repo-root", "."]) == 7
    assert observed == {
        "argv": ["--repo-root", "."],
        "proxy": experiment.CacheOnForwardingProxy,
        "target": experiment.EXPERIMENT_TARGET_NAME,
    }
    assert transaction._ForwardingProxy is original_proxy
    assert transaction.TARGET_NAME == original_target


def test_experimental_proxy_uses_only_the_cache_treatment_handler() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    proxy = experiment.CacheOnForwardingProxy(
        origin="http://127.0.0.1:1",
        ledger=ledger,
    )
    try:
        assert proxy.server.RequestHandlerClass is experiment._CacheOnProxyRequestHandler
        assert proxy.ledger is ledger
    finally:
        proxy.server.server_close()
