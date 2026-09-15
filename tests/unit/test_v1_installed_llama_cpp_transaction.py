from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

import tools.relay_physical_run as runner
import tools.v1_installed_llama_cpp_transaction as transaction
import tools.v1_installed_llama_cpp_wsl as wrapper
from relaylm.providers.llama_cpp_backend import (
    LLAMA_CPP_CHAT_COUNTER_CAPABILITY,
    LLAMA_CPP_CHAT_COUNTER_IMPLEMENTATION,
    LLAMA_CPP_CHAT_COUNTER_VERSION,
    build_llama_cpp_capability,
)
from relaylm.providers.openai_compatible_extraction_projection import (
    ExtractionProjectionMode,
    extraction_schema_name,
    extraction_wire_schema,
)
from relaylm.runtime_config_loader import resolve_runtime_config
from tools.relay_physical_env import PhysicalEnvironmentIdentity


REPO_ROOT = Path(__file__).parents[2]
LLAMA_REVISION = "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d"
MODEL = "gemma-local"


def _json_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _input_body(*, framing: bool) -> bytes:
    return _json_body(
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "" if framing else "system"},
                {"role": "user", "content": "" if framing else "hello"},
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 256,
            "cache_prompt": False,
            "reasoning_effort": "none",
        }
    )


def _generation_body(generation_index: int) -> bytes:
    body: dict[str, Any] = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "ordinary provider payload"}],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 256,
        "cache_prompt": False,
        "reasoning_effort": "none",
        "stream": generation_index == 3,
    }
    if generation_index in (2, 4):
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": extraction_schema_name(ExtractionProjectionMode.PRODUCTION),
                "strict": True,
                "schema": extraction_wire_schema(ExtractionProjectionMode.PRODUCTION),
            },
        }
    return _json_body(body)


def _generation_response(generation_index: int) -> bytes:
    if generation_index == 3:
        return (
            b'data: {"choices":[{"delta":{"content":"visible"}}]}\n\n'
            b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
            b"data: [DONE]\n\n"
        )
    content = "ordinary" if generation_index in (1, 3) else "{\"state_candidates\":[],\"continuity_candidates\":[]}"
    return _json_body(
        {
            "choices": [
                {"message": {"content": content}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        }
    )


def _record_input_count_pair(
    ledger: transaction.RequestLedger,
    *,
    full_count: int,
) -> None:
    full = ledger.begin(
        path="/v1/chat/completions/input_tokens",
        body=_input_body(framing=False),
    )
    ledger.complete(
        full,
        status=200,
        body=_json_body({"input_tokens": full_count}),
        streaming=False,
    )
    framing = ledger.begin(
        path="/v1/chat/completions/input_tokens",
        body=_input_body(framing=True),
    )
    ledger.complete(
        framing,
        status=200,
        body=_json_body({"input_tokens": 18}),
        streaming=False,
    )


def _record_generation(
    ledger: transaction.RequestLedger,
    *,
    generation_index: int,
) -> None:
    generation = ledger.begin(
        path="/v1/chat/completions",
        body=_generation_body(generation_index),
    )
    ledger.complete(
        generation,
        status=200,
        body=_generation_response(generation_index),
        streaming=generation_index == 3,
    )


def _populate_canonical_two_turn_topology(
    ledger: transaction.RequestLedger,
    *,
    full_counts: tuple[int, ...] = (883, 883, 2927, 883, 883, 2927),
    omit_logical_operation_index: int | None = None,
) -> None:
    operation_index = 0
    for generation_index, (_, budget_roles) in enumerate(
        transaction.CANONICAL_TWO_TURN_TOPOLOGY,
        start=1,
    ):
        for _ in budget_roles:
            operation_index += 1
            if operation_index != omit_logical_operation_index:
                _record_input_count_pair(
                    ledger,
                    full_count=full_counts[operation_index - 1],
                )
        _record_generation(ledger, generation_index=generation_index)


def _runtime_identity() -> transaction.LlamaCppRuntimeIdentity:
    return transaction.LlamaCppRuntimeIdentity(
        upstream_revision=LLAMA_REVISION,
        build_info=f"llama.cpp {LLAMA_REVISION} build 10874",
        model_alias=MODEL,
        model_path="/models/gemma.gguf",
        model_ftype="Q4_K_M",
        artifact_sha256="a" * 64,
        chat_template_sha256="b" * 64,
        context_limit=8192,
        total_slots=1,
        context_shift_enabled=False,
    )


def _runtime_capability() -> transaction.LlamaCppCapabilityAttestation:
    identity = _runtime_identity()
    return build_llama_cpp_capability(
        upstream_revision=identity.upstream_revision,
        build_info=identity.build_info,
        model_alias=identity.model_alias,
        model_path=identity.model_path,
        model_ftype=identity.model_ftype,
        artifact_sha256=identity.artifact_sha256,
        chat_template_sha256=identity.chat_template_sha256,
        context_limit=identity.context_limit,
        total_slots=identity.total_slots,
        context_shift_enabled=False,
        reasoning_effort_none_supported=True,
        native_structured_output_supported=True,
        streaming_supported=True,
        decoding_controls=frozenset({"max_output_tokens", "temperature", "top_p"}),
        cache_policy="disabled",
    )


def test_installed_target_registry_dispatches_only_to_the_new_wrapper() -> None:
    targets = runner._load_targets(REPO_ROOT)

    assert targets[transaction.TARGET_NAME].module == "tools.v1_installed_llama_cpp_wsl"
    assert targets[transaction.TARGET_NAME].branch == "v1"
    assert targets[transaction.TARGET_NAME].required_distributions == ("build", "httpx")
    assert targets["v1:stage-r"].module == "tools.v1_stage_r_llama_cpp_wsl"
    assert targets["v1:crystallization"].module == "tools.v1_crystallization_llama_cpp_wsl"


def test_unknown_target_fails_closed_before_command_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = PhysicalEnvironmentIdentity(
        home=tmp_path,
        manifest_path=tmp_path / "manifest.json",
        python_executable=sys.executable,
        python_version=sys.version,
        implementation="cpython",
        policy_sha256="a" * 64,
        distribution_fingerprint="fingerprint",
    )
    monkeypatch.setattr(runner, "_environment_identity", lambda _: environment)

    with pytest.raises(runner.RelayPhysicalRunError, match="unknown llama.cpp physical target"):
        runner.prepare_run(repo_root=REPO_ROOT, target_name="v1:not-registered")


def test_public_wrapper_is_a_dry_dispatch_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[object] = []

    def fake_transaction(argv: object) -> int:
        observed.append(argv)
        return 0

    monkeypatch.setattr(wrapper, "_run_transaction", fake_transaction)

    assert wrapper.main([]) == 0
    assert observed == [[]]


def test_request_ledger_proves_canonical_two_turn_topology_and_exact_counter_framing() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _populate_canonical_two_turn_topology(ledger)

    transaction._validate_successful_ledger(ledger)
    evidence = ledger.input_evidence()
    provider = ledger.provider_evidence()

    assert len(ledger.generation_entries()) == 4
    assert len(ledger.input_operations()) == 6
    assert len(ledger.input_entries()) == 12
    assert [entry["generation_index"] for entry in ledger.input_entries()] == [
        1,
        1,
        1,
        1,
        2,
        2,
        3,
        3,
        3,
        3,
        4,
        4,
    ]
    assert [entry["framing_role"] for entry in ledger.input_entries()] == [
        "full",
        "framing",
        "full",
        "framing",
        "full",
        "framing",
        "full",
        "framing",
        "full",
        "framing",
        "full",
        "framing",
    ]
    assert [
        operation["generation_index"] for operation in ledger.input_operations()
    ] == [1, 1, 2, 3, 3, 4]
    assert [
        operation["generation_phase"] for operation in ledger.input_operations()
    ] == [
        "buffered_pass1",
        "buffered_pass1",
        "buffered_pass2",
        "streaming_pass1",
        "streaming_pass1",
        "streaming_pass2",
    ]
    assert [
        operation["budget_role"] for operation in ledger.input_operations()
    ] == [
        "protected_floor",
        "selected_plan",
        "extraction",
        "protected_floor",
        "selected_plan",
        "extraction",
    ]
    assert all(
        operation["endpoint_calls"] == len(transaction.COUNTER_ENDPOINT_ROLES)
        and operation["endpoint_roles"] == ["full", "framing"]
        and operation["framing_call_index"] == operation["full_call_index"] + 1
        for operation in ledger.input_operations()
    )
    assert [
        operation["budget_role"] for operation in evidence["logical_operations"]
    ] == [
        "protected_floor",
        "selected_plan",
        "extraction",
        "protected_floor",
        "selected_plan",
        "extraction",
    ]
    assert [entry["phase"] for entry in ledger.generation_entries()] == [
        "buffered_pass1",
        "buffered_pass2",
        "streaming_pass1",
        "streaming_pass2",
    ]
    assert [entry["controls"]["stream"] for entry in ledger.generation_entries()] == [
        False,
        False,
        True,
        False,
    ]
    assert all(
        entry["controls"]["cache_prompt"] is False
        and entry["controls"]["reasoning_effort"] == "none"
        for entry in ledger.generation_entries()
    )
    assert all(
        entry["controls"]["cache_prompt"] is False
        and entry["controls"]["reasoning_effort"] == "none"
        for entry in ledger.input_entries()
    )
    assert evidence["logical_operation_generation_mapping"] == [1, 1, 2, 3, 3, 4]
    assert evidence["endpoint_generation_mapping"] == [
        1,
        1,
        1,
        1,
        2,
        2,
        3,
        3,
        3,
        3,
        4,
        4,
    ]
    assert [
        operation["full"]["framing_role"] for operation in evidence["logical_operations"]
    ] == ["full"] * 6
    assert [
        operation["framing"]["framing_role"]
        for operation in evidence["logical_operations"]
    ] == ["framing"] * 6
    assert [
        operation["full"]["response"]["input_tokens"]
        for operation in evidence["logical_operations"]
    ] == [883, 883, 2927, 883, 883, 2927]
    assert [
        operation["framing"]["response"]["input_tokens"]
        for operation in evidence["logical_operations"]
    ] == [18] * 6
    assert evidence["counter_evidence_identity"] == {
        "capability": LLAMA_CPP_CHAT_COUNTER_CAPABILITY,
        "implementation": LLAMA_CPP_CHAT_COUNTER_IMPLEMENTATION,
        "version": LLAMA_CPP_CHAT_COUNTER_VERSION,
        "mode": "exact",
    }
    assert provider["semantic_generation_count"] == 4
    assert provider["semantic_retry_count"] == 0
    assert provider["replay_count"] == 0
    assert provider["reseed_count"] == 0


def test_former_four_generation_eight_endpoint_shape_is_rejected() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    ledger._input_operations = [
        {
            "logical_operation_index": index,
            "generation_index": index,
            "generation_phase": transaction.CANONICAL_GENERATION_PHASES[index - 1],
            "budget_role": "selected_plan",
            "endpoint_calls": len(transaction.COUNTER_ENDPOINT_ROLES),
        }
        for index in range(1, 5)
    ]
    ledger._calls = [
        {
            "call_index": call_index,
            "kind": kind,
            "generation_index": generation_index,
            "phase": (
                transaction.CANONICAL_GENERATION_PHASES[generation_index - 1]
                if kind == "generation"
                else None
            ),
            "framing_role": framing_role,
        }
        for generation_index in range(1, 5)
        for call_index, (kind, framing_role) in enumerate(
            (
                ("input_token_count", "full"),
                ("input_token_count", "framing"),
                ("generation", None),
            ),
            start=(generation_index - 1) * 3 + 1,
        )
    ]

    with pytest.raises(
        transaction.RequestLedgerError,
        match="six logical operations and twelve endpoint calls",
    ):
        transaction._validate_successful_ledger(ledger)


def test_logical_role_and_pair_mutations_fail_closed() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _populate_canonical_two_turn_topology(ledger)

    ledger._input_operations[1]["budget_role"] = "extraction"
    with pytest.raises(transaction.RequestLedgerError, match="role/order"):
        transaction._validate_successful_ledger(ledger)

    ledger = transaction.RequestLedger(expected_model=MODEL)
    _populate_canonical_two_turn_topology(ledger)
    ledger._input_operations[0]["framing_call_index"] = ledger._input_operations[1][
        "full_call_index"
    ]
    with pytest.raises(transaction.RequestLedgerError, match="full/framing pair"):
        transaction._validate_successful_ledger(ledger)


def test_topology_validation_does_not_use_counter_values_as_an_oracle() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _populate_canonical_two_turn_topology(
        ledger,
        full_counts=(1, 2, 3, 4, 5, 6),
    )

    transaction._validate_successful_ledger(ledger)


@pytest.mark.parametrize("missing_operation_index", (1, 2, 3))
def test_missing_canonical_count_operation_fails_closed(
    missing_operation_index: int,
) -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)

    with pytest.raises(transaction.RequestLedgerError):
        _populate_canonical_two_turn_topology(
            ledger,
            omit_logical_operation_index=missing_operation_index,
        )


def test_extra_pass1_count_fails_before_generation() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _record_input_count_pair(ledger, full_count=883)
    _record_input_count_pair(ledger, full_count=883)

    with pytest.raises(transaction.RequestLedgerError, match="upcoming generation"):
        _record_input_count_pair(ledger, full_count=2927)


def test_extra_pass2_count_fails_closed_after_canonical_completion() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _populate_canonical_two_turn_topology(ledger)

    with pytest.raises(transaction.RequestLedgerError, match="extra logical operation"):
        _record_input_count_pair(ledger, full_count=2927)


def test_generation_before_required_count_topology_fails_closed() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _record_input_count_pair(ledger, full_count=883)

    with pytest.raises(
        transaction.RequestLedgerError,
        match="before required count topology complete",
    ):
        _record_generation(ledger, generation_index=1)


def test_count_sequence_on_wrong_upcoming_generation_fails_closed() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _record_input_count_pair(ledger, full_count=883)
    _record_input_count_pair(ledger, full_count=883)
    _record_generation(ledger, generation_index=1)
    _record_input_count_pair(ledger, full_count=2927)

    with pytest.raises(transaction.RequestLedgerError, match="upcoming generation"):
        _record_input_count_pair(ledger, full_count=883)


def test_request_ledger_enforces_wire_controls_and_ceiling() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)

    with pytest.raises(transaction.RequestLedgerError, match="framing count"):
        ledger.begin(
            path="/v1/chat/completions/input_tokens",
            body=_input_body(framing=True),
        )
    with pytest.raises(transaction.RequestLedgerError, match="model"):
        ledger.begin(
            path="/v1/chat/completions",
            body=_json_body({"model": "wrong", "messages": [{"role": "user", "content": "x"}]}),
        )

    _populate_canonical_two_turn_topology(ledger)
    with pytest.raises(transaction.RequestLedgerError, match="ceiling"):
        ledger.begin(
            path="/v1/chat/completions",
            body=_generation_body(4),
        )


def test_stream_response_evidence_keeps_full_response_hash() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _record_input_count_pair(ledger, full_count=883)
    _record_input_count_pair(ledger, full_count=883)
    _record_generation(ledger, generation_index=1)
    _record_input_count_pair(ledger, full_count=2927)
    _record_generation(ledger, generation_index=2)
    _record_input_count_pair(ledger, full_count=883)
    _record_input_count_pair(ledger, full_count=883)
    body = _generation_body(3)
    entry = ledger.begin(path="/v1/chat/completions", body=body)
    response = _generation_response(3)
    ledger.complete(entry, status=200, body=response, streaming=True)

    observed = next(
        entry["response"]
        for entry in ledger.generation_entries()
        if entry["generation_index"] == 3
    )
    assert observed["body_sha256"] == f"sha256:{hashlib.sha256(response).hexdigest()}"
    assert observed["body_truncated_for_parser"] is False


def test_probe_and_attestation_are_management_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    responses = iter(
        [
            {"status": "ok"},
            {"data": [{"id": MODEL}]},
            {
                "build_info": f"llama.cpp {LLAMA_REVISION} build 10874",
                "model_alias": MODEL,
                "model_path": str(tmp_path / "model.gguf"),
                "model_ftype": "Q4_K_M",
                "chat_template": "{{ bos_token }}{{ messages }}",
                "total_slots": 1,
                "default_generation_settings": {"n_ctx": 8192},
            },
            [{"id": 0, "n_ctx": 8192}],
        ]
    )
    calls: list[str] = []

    def get_json(url: str) -> object:
        calls.append(url)
        return next(responses)

    monkeypatch.setattr(transaction, "_get_json", get_json)
    probe = transaction._probe_server(
        origin="http://127.0.0.1:1234",
        expected_slots=1,
    )
    target = transaction._load_artifact_target(
        REPO_ROOT / transaction.DEFAULT_TARGET_PATH
    )
    verification = SimpleNamespace(
        artifact_sha256=target.artifact_sha256,
        to_mapping=lambda: {"artifact_sha256": target.artifact_sha256},
    )
    identity, capability = transaction._attest_runtime(
        probe=probe,
        revision=LLAMA_REVISION,
        version="llama.cpp build 10874",
        build_number=10874,
        request_model=MODEL,
        artifact_path=tmp_path / "model.gguf",
        verification=verification,
        target=target,
    )

    assert [url.rsplit("/", 1)[-1] for url in calls] == [
        "health",
        "models",
        "props",
        "slots",
    ]
    assert identity.context_limit == 8192
    assert identity.total_slots == 1
    assert identity.context_shift_enabled is False
    assert capability.native_structured_output_supported is True
    assert capability.streaming_supported is True


def test_runtime_config_is_production_config_and_fixture_is_copied_unchanged(
    tmp_path: Path,
) -> None:
    source_fixture = REPO_ROOT / transaction.CANONICAL_FIXTURE_PATH
    before = transaction._directory_sha256(source_fixture)
    fixture = transaction._materialize_fixture(
        repo_root=REPO_ROOT,
        evidence_root=tmp_path,
        scenario_id=transaction.CANONICAL_SCENARIO_ID,
    )
    after = transaction._directory_sha256(source_fixture)
    config_path = tmp_path / "runtime-config.yaml"
    config = transaction._write_runtime_config(
        config_path=config_path,
        fixture=fixture,
        proxy_base_url="http://127.0.0.1:5555/v1",
        relay_port=5556,
        request_model=MODEL,
        artifact_path=Path("/models/gemma.gguf"),
        runtime_identity=_runtime_identity(),
        capability=_runtime_capability(),
    )
    resolved = resolve_runtime_config(config_path=str(config_path))

    assert before == after
    assert config["provider"]["backend"] == "llama_cpp"
    assert resolved.config.provider.backend.value == "llama_cpp"
    assert resolved.config.runtime.continuity is not None
    assert resolved.config.runtime.continuity.max_items == 8
    assert resolved.config.runtime.cognitive_budget is not None
    assert (
        resolved.config.runtime.cognitive_budget.token_counter.capability
        == LLAMA_CPP_CHAT_COUNTER_CAPABILITY
    )
    assert set(fixture["profile_roots"]) == {"installed-buffered", "installed-streaming"}


def test_build_frontend_is_pinned_to_local_non_isolated_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_root = tmp_path / "wheel-build"
    observed: list[list[str]] = []
    monkeypatch.setattr(transaction.importlib.util, "find_spec", lambda name: object())

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        (build_root / "relaylm-1.0.0-py3-none-any.whl").write_bytes(b"wheel")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(transaction.subprocess, "run", fake_run)
    wheel = transaction._build_exact_wheel(repo_root=REPO_ROOT, build_root=build_root)

    assert wheel.name == "relaylm-1.0.0-py3-none-any.whl"
    assert observed[0][1:4] == ["-m", "build", "--wheel"]
    assert "--no-isolation" in observed[0]
    assert str(REPO_ROOT) == observed[0][-1]


def test_install_uses_fresh_venv_no_index_and_records_non_editable_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "relaylm-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    transaction_root = tmp_path / "installed-runtime"
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    dependency_overlay = tmp_path / "controlled-dependencies"
    dependency_overlay.mkdir()
    commands: list[tuple[list[str], dict[str, object]]] = []
    identities = iter(
        [
            None,
            {
                "missing": False,
                "version": "1.0.0",
                "module_path": str(tmp_path / "site-packages" / "relaylm" / "__init__.py"),
                "prefix": str(transaction_root / "venv"),
                "editable": False,
            },
        ]
    )

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append((command, kwargs))
        if command[1:4] == ["-m", "venv", "--system-site-packages"]:
            venv_root = Path(command[-1])
            (venv_root / "bin").mkdir(parents=True)
            (venv_root / "bin" / "python").touch()
            (venv_root / "bin" / "relaylm").touch()
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(transaction.subprocess, "run", fake_run)
    monkeypatch.setattr(
        transaction,
        "_prepare_dependency_overlay",
        lambda _: {"path": str(dependency_overlay)},
    )
    monkeypatch.setattr(
        transaction,
        "_installed_import_identity",
        lambda **_: next(identities),
    )
    monkeypatch.setattr(transaction, "_git_identity", lambda _: ("a" * 40, "b" * 40))

    installed = transaction._install_exact_wheel(
        wheel_path=wheel,
        package_version="1.0.0",
        transaction_root=transaction_root,
        evidence_root=evidence_root,
        repo_root=REPO_ROOT,
    )

    install_command = next(command for command, _ in commands if "install" in command)
    assert "--no-index" in install_command
    assert "--no-deps" in install_command
    assert not any(item in {"-e", "--editable"} for item in install_command)
    assert installed["non_editable"] is True
    assert installed["network_install"] is False
    for call, kwargs in commands[1:]:
        # The installation and inspection subprocesses must not inherit the
        # source checkout import path or RelayLM override variables.
        environment = kwargs.get("env")
        assert isinstance(environment, dict)
        assert environment["PYTHONPATH"] == str(dependency_overlay)
        assert str(REPO_ROOT) not in environment["PYTHONPATH"]
        assert "RELAYLM_CONFIG" not in environment


def test_install_rejects_source_checkout_import_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "relaylm-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    dependency_overlay = tmp_path / "controlled-dependencies"
    dependency_overlay.mkdir()
    identities = iter(
        [
            None,
            {
                "missing": False,
                "version": "1.0.0",
                "module_path": str(REPO_ROOT / "src" / "relaylm" / "__init__.py"),
                "prefix": str(tmp_path / "venv"),
                "editable": False,
            },
        ]
    )
    monkeypatch.setattr(
        transaction,
        "_installed_import_identity",
        lambda **_: next(identities),
    )
    monkeypatch.setattr(transaction, "_venv_binary", lambda *_: tmp_path / "binary")
    monkeypatch.setattr(
        transaction,
        "_prepare_dependency_overlay",
        lambda _: {"path": str(dependency_overlay)},
    )
    monkeypatch.setattr(transaction.subprocess, "run", lambda command, **_: subprocess.CompletedProcess(command, 0, stdout="", stderr=""))
    monkeypatch.setattr(transaction, "_git_identity", lambda _: ("a" * 40, "b" * 40))

    with pytest.raises(transaction.InstalledLlamaCppTransactionError, match="source checkout"):
        transaction._install_exact_wheel(
            wheel_path=wheel,
            package_version="1.0.0",
            transaction_root=tmp_path / "runtime",
            evidence_root=evidence_root,
            repo_root=REPO_ROOT,
        )


def test_doctor_and_serve_use_the_installed_console(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    installed = {
        "console_path": str(tmp_path / "venv" / "bin" / "relaylm"),
        "transaction_root": str(tmp_path / "runtime"),
        "module_path": str(tmp_path / "venv" / "site-packages" / "relaylm" / "__init__.py"),
        "controlled_dependency_overlay": {"path": str(tmp_path / "dependencies")},
    }
    config_path = tmp_path / "runtime-config.yaml"
    config_path.write_text("format_version: 1\n", encoding="utf-8")
    observed: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {"status": "ok", "provider_capabilities": {"backend": "llama_cpp"}}
            ),
            stderr="",
        )

    monkeypatch.setattr(transaction.subprocess, "run", fake_run)
    doctor = transaction._run_installed_doctor(
        installed=installed,
        config_path=config_path,
        cwd=tmp_path,
    )

    assert doctor["non_generative"] is True
    assert observed[0][:2] == [installed["console_path"], "doctor"]

    class FakeProcess:
        pid = 123

    fake_process = FakeProcess()
    monkeypatch.setattr(transaction.subprocess, "Popen", lambda command, **_: fake_process)
    log_path = tmp_path / "relaylm-serve.log"
    process = transaction._start_installed_serve(
        installed=installed,
        config_path=config_path,
        cwd=tmp_path,
        log_path=log_path,
    )
    assert process is fake_process
    assert log_path.is_file()


def test_minimum_evidence_contract_and_review_boundary_are_explicit() -> None:
    assert transaction.MINIMUM_EVIDENCE_FILENAMES == (
        "binding.json",
        "transaction-summary.json",
        "installed-artifact.json",
        "runtime-config.yaml",
        "runtime-config.sha256",
        "doctor.json",
        "relaylm-serve.log",
        "llama-server.log",
        "runtime-attestation.json",
        "provider-request-ledger.json",
        "input-count-ledger.json",
        "buffered-execution.json",
        "streaming-execution.json",
        "state-continuity-before-after.json",
        "cleanup.json",
    )
    assert transaction.PHYSICAL_EVIDENCE_DISPOSITION == "EVIDENCE_RECORDED"
    assert transaction.PHYSICAL_INVALID_DISPOSITION == "PHYSICAL_INVALID"


def test_execution_evidence_distinguishes_observation_from_success_validation() -> None:
    ledger = transaction.RequestLedger(expected_model=MODEL)
    _populate_canonical_two_turn_topology(ledger)
    public_response = {"kind": "buffered", "response_first": True}

    observed = transaction._execution_evidence(
        kind="buffered",
        public_request=public_response,
        ledger=ledger,
        validation_state=transaction.EXECUTION_OBSERVATION_STATE,
    )
    validated = transaction._execution_evidence(
        kind="buffered",
        public_request=public_response,
        ledger=ledger,
        validation_state=transaction.EXECUTION_VALIDATION_STATE,
    )

    assert observed["validation_state"] == "observed_unvalidated"
    assert validated["validation_state"] == "validated_success"
    assert observed["product_quality"] == "not_declared_by_harness"
    assert validated["product_quality"] == "not_declared_by_harness"
