from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.budget_enforcement import TokenCountMode
from relaylm.runtime_config import ConfigSource, RuntimeConfigErrorCode
from relaylm.runtime_config_loader import (
    RuntimeConfigOverrides,
    RuntimeConfigResolutionError,
    resolve_runtime_config,
)


def _write_config(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _basic_config(*, secret_env: str | None = None) -> str:
    secret = "" if secret_env is None else f"\n  api_key:\n    env: {secret_env}"
    return f"""\
format_version: 1
profiles:
  - name: relm
    root: /config/character
provider:
  adapter: openai_compatible
  base_url: http://config.example/v1
  model: config-model{secret}
server:
  host: 127.0.0.2
  port: 9000
"""


def _calibrated_budget_runtime(
    *,
    total: tuple[int | None, int | None] | None = None,
    include_policy: bool = True,
    include_token_counter: bool = True,
) -> str:
    lines = [
        "runtime:",
        "  calibration_profile: fastcal-v1",
        "  cognitive_budget:",
    ]
    if total is not None:
        lines.append("    total:")
        if total[0] is not None:
            lines.append(f"      model_context_window: {total[0]}")
        if total[1] is not None:
            lines.append(f"      reserved_output_tokens: {total[1]}")
    if include_policy:
        lines.extend(
            [
                "    policy:",
                "      initial_plan:",
                "        canonical_state: {max_items: 0, floor_items: 0}",
                "        working_context: {max_items: 0, floor_items: 0, max_chars: 0, floor_chars: 0}",
                "        retrieved_memory: {max_items: 0, floor_items: 0, max_chars: 0, floor_chars: 0}",
                "        event_evidence: {max_items: 0, floor_items: 0, max_chars: 0, floor_chars: 0}",
                "      steps: []",
            ]
        )
    if include_token_counter:
        lines.extend(
            [
                "    token_counter:",
                "      capability: test.counter",
                "      mode: exact",
            ]
        )
    return "\n".join(lines) + "\n"


def test_resolve_file_config_with_defaults_provenance_and_secret_reference(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config(secret_env="MODEL_API_KEY"),
    )

    resolved = resolve_runtime_config(
        config_path=config_path,
        environ={"MODEL_API_KEY": "super-secret"},
    )

    assert resolved.config.profiles[0].name == "relm"
    assert resolved.config.profiles[0].root == "/config/character"
    assert resolved.config.provider.model == "config-model"
    assert resolved.config.provider.api_key is not None
    assert resolved.config.provider.api_key.env == "MODEL_API_KEY"
    assert resolved.secrets.provider_api_key == "super-secret"
    assert resolved.source_for("profiles.0.root") is ConfigSource.CONFIG_FILE
    assert resolved.source_for("server.port") is ConfigSource.CONFIG_FILE
    assert resolved.secret_effective.source is ConfigSource.CONFIG_FILE
    assert resolved.secret_effective.material_source is ConfigSource.ENV
    assert resolved.config_path == config_path.expanduser()
    assert resolved.config_path_source is ConfigSource.CLI

    diagnostics = resolved.effective_diagnostics()
    assert diagnostics["validation_status"] == "valid"
    assert diagnostics["values"]["provider.model"] == {
        "value": "config-model",
        "source": "config_file",
    }
    assert diagnostics["secrets"]["provider.api_key"] == {
        "configured": True,
        "source": "config_file",
        "material_source": "env",
    }
    assert "super-secret" not in repr(diagnostics)
    assert "super-secret" not in repr(resolved.secrets)


def test_leaf_precedence_is_cli_then_env_then_file_without_sibling_erasure(
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path / "runtime.yaml", _basic_config())

    resolved = resolve_runtime_config(
        config_path=config_path,
        overrides=RuntimeConfigOverrides(provider_model="cli-model"),
        environ={
            "RELAYLM_PROVIDER_BASE_URL": "http://env.example/v1",
            "RELAYLM_PROVIDER_MODEL": "env-model",
            "RELAYLM_HOST": "127.0.0.3",
        },
    )

    assert resolved.config.profiles[0].root == "/config/character"
    assert resolved.config.provider.base_url == "http://env.example/v1"
    assert resolved.config.provider.model == "cli-model"
    assert resolved.config.server.host == "127.0.0.3"
    assert resolved.config.server.port == 9000
    assert resolved.source_for("profiles.0.root") is ConfigSource.CONFIG_FILE
    assert resolved.source_for("provider.base_url") is ConfigSource.ENV
    assert resolved.source_for("provider.model") is ConfigSource.CLI
    assert resolved.source_for("server.port") is ConfigSource.CONFIG_FILE


def test_config_discovery_prefers_explicit_cli_path_over_environment(tmp_path: Path) -> None:
    cli_path = _write_config(
        tmp_path / "cli.yaml",
        _basic_config().replace("config-model", "cli-file-model"),
    )
    env_path = _write_config(
        tmp_path / "env.yaml",
        _basic_config().replace("config-model", "env-file-model"),
    )

    resolved = resolve_runtime_config(
        config_path=cli_path,
        environ={"RELAYLM_CONFIG": str(env_path)},
    )

    assert resolved.config.provider.model == "cli-file-model"
    assert resolved.config_path == cli_path.expanduser()
    assert resolved.config_path_source is ConfigSource.CLI


def test_environment_only_startup_uses_release_owned_non_cognitive_defaults() -> None:
    resolved = resolve_runtime_config(
        environ={
            "RELAYLM_PROFILE_NAME": "relm",
            "RELAYLM_PROFILE_ROOT": "/characters/relm",
            "RELAYLM_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "RELAYLM_PROVIDER_MODEL": "model-id",
        }
    )

    assert resolved.config.format_version == 1
    assert resolved.config.profiles[0].name == "relm"
    assert resolved.config.profiles[0].root == "/characters/relm"
    assert resolved.config.provider.adapter == "openai_compatible"
    assert resolved.config.server.host == "127.0.0.1"
    assert resolved.config.server.port == 8090
    assert resolved.source_for("format_version") is ConfigSource.CANONICAL_DEFAULT
    assert resolved.source_for("profiles[0].name") is ConfigSource.ENV
    assert resolved.source_for("profiles[0].root") is ConfigSource.ENV
    assert resolved.source_for("provider.adapter") is ConfigSource.CANONICAL_DEFAULT
    assert resolved.source_for("server.host") is ConfigSource.CANONICAL_DEFAULT
    assert resolved.source_for("server.port") is ConfigSource.CANONICAL_DEFAULT
    assert resolved.config.runtime.calibration_profile is None
    assert resolved.config.runtime.cognitive_budget is None


def test_unknown_field_fails_closed_with_safe_field_path(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config().replace(
            "  model: config-model",
            "  model: config-model\n  invented: true",
        ),
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=config_path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.UNKNOWN_FIELD
    assert caught.value.field == "provider.invented"
    assert "invented" in str(caught.value)


def test_missing_required_value_after_precedence_fails_before_assembly() -> None:
    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(
            environ={
                "RELAYLM_PROFILE_NAME": "relm",
                "RELAYLM_PROFILE_ROOT": "/characters/relm",
                "RELAYLM_PROVIDER_MODEL": "model-id",
            }
        )

    assert caught.value.code is RuntimeConfigErrorCode.MISSING_REQUIRED
    assert caught.value.field == "provider.base_url"


@pytest.mark.parametrize(
    ("version", "code"),
    [
        ("true", RuntimeConfigErrorCode.INVALID_TYPE),
        ("2", RuntimeConfigErrorCode.UNSUPPORTED_FORMAT_VERSION),
    ],
)
def test_runtime_format_version_is_strict(
    tmp_path: Path,
    version: str,
    code: RuntimeConfigErrorCode,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config().replace("format_version: 1", f"format_version: {version}"),
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=config_path, environ={})

    assert caught.value.code is code
    assert caught.value.field == "format_version"


def test_duplicate_yaml_key_is_rejected_instead_of_last_value_wins(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config().replace(
            "  model: config-model",
            "  model: first-model\n  model: second-model",
        ),
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=config_path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.PARSE_ERROR
    assert "duplicate" in str(caught.value).lower()


def test_legacy_runtime_profile_is_not_reinterpreted_as_cognitive_profile(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config()
        + """\
runtime:
  profile: standard
""",
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=config_path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.UNKNOWN_FIELD
    assert caught.value.field == "runtime.profile"


def test_current_fastcal_profile_resolves_with_auditable_authority(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config()
        + """\
runtime:
  calibration_profile: fastcal-v1
""",
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})

    assert resolved.config.runtime.calibration_profile == "fastcal-v1"
    assert resolved.calibration_profile is not None
    assert resolved.calibration_profile.name == "fastcal-v1"
    assert resolved.calibration_profile.target_window == 4096
    assert resolved.calibration_profile.output_allowance == 512
    assert resolved.calibration_profile.authority == "#1388 FastCal v1"
    assert resolved.source_for("runtime.calibration_profile") is ConfigSource.CONFIG_FILE
    assert resolved.source_for(
        "runtime.calibration_profile.target_window"
    ) is ConfigSource.CANONICAL_DEFAULT

    values = resolved.effective_diagnostics()["values"]
    assert values["runtime.calibration_profile"] == {
        "value": "fastcal-v1",
        "source": "config_file",
    }
    assert values["runtime.calibration_profile.target_window"] == {
        "value": 4096,
        "source": "canonical_default",
    }
    assert values["runtime.calibration_profile.output_allowance"] == {
        "value": 512,
        "source": "canonical_default",
    }
    assert values["runtime.calibration_profile.authority"] == {
        "value": "#1388 FastCal v1",
        "source": "canonical_default",
    }
    assert resolved.config.runtime.cognitive_budget is None


def test_unsupported_calibration_profile_fails_closed(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config()
        + """\
runtime:
  calibration_profile: future-profile
""",
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=config_path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == "runtime.calibration_profile"
    assert "unsupported calibration profile" in str(caught.value)


def test_calibration_profile_selection_preserves_cli_precedence(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config()
        + """
runtime:
  calibration_profile: fastcal-v1
""",
    )

    resolved = resolve_runtime_config(
        config_path=config_path,
        overrides=RuntimeConfigOverrides(calibration_profile="fastcal-v1"),
        environ={"RELAYLM_CALIBRATION_PROFILE": "future-profile"},
    )

    assert resolved.config.runtime.calibration_profile == "fastcal-v1"
    assert resolved.source_for("runtime.calibration_profile") is ConfigSource.CLI


def test_calibrated_total_defaults_require_explicit_1387_policy_and_counter(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config() + _calibrated_budget_runtime(),
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})
    budget = resolved.config.runtime.cognitive_budget

    assert budget is not None
    assert budget.total.model_context_window == 4096
    assert budget.total.reserved_output_tokens == 512
    assert resolved.source_for(
        "runtime.cognitive_budget.total.model_context_window"
    ) is ConfigSource.CANONICAL_DEFAULT
    assert resolved.source_for(
        "runtime.cognitive_budget.total.reserved_output_tokens"
    ) is ConfigSource.CANONICAL_DEFAULT


def test_explicit_cognitive_budget_total_beats_calibrated_defaults(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config() + _calibrated_budget_runtime(total=(8192, 1024)),
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})
    budget = resolved.config.runtime.cognitive_budget

    assert budget is not None
    assert budget.total.model_context_window == 8192
    assert budget.total.reserved_output_tokens == 1024
    assert resolved.source_for(
        "runtime.cognitive_budget.total.model_context_window"
    ) is ConfigSource.CONFIG_FILE
    assert resolved.source_for(
        "runtime.cognitive_budget.total.reserved_output_tokens"
    ) is ConfigSource.CONFIG_FILE
    assert resolved.calibration_profile is not None
    assert resolved.calibration_profile.target_window == 4096


def test_explicit_cognitive_budget_total_precedence_is_leaf_level(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config() + _calibrated_budget_runtime(total=(8192, None)),
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})
    budget = resolved.config.runtime.cognitive_budget

    assert budget is not None
    assert budget.total.model_context_window == 8192
    assert budget.total.reserved_output_tokens == 512
    assert resolved.source_for(
        "runtime.cognitive_budget.total.model_context_window"
    ) is ConfigSource.CONFIG_FILE
    assert resolved.source_for(
        "runtime.cognitive_budget.total.reserved_output_tokens"
    ) is ConfigSource.CANONICAL_DEFAULT


@pytest.mark.parametrize("missing", ["policy", "token_counter"])
def test_calibration_profile_does_not_invent_1387_requirements(
    tmp_path: Path,
    missing: str,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config()
        + _calibrated_budget_runtime(
            include_policy=missing != "policy",
            include_token_counter=missing != "token_counter",
        ),
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=config_path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.MISSING_REQUIRED
    assert caught.value.field == f"runtime.cognitive_budget.{missing}"


def test_calibration_and_cognitive_profile_names_are_separate_namespaces(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config().replace("- name: relm", "- name: fastcal-v1")
        + """
runtime:
  calibration_profile: fastcal-v1
""",
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})

    assert resolved.config.profiles[0].name == "fastcal-v1"
    assert resolved.config.runtime.calibration_profile == "fastcal-v1"
    assert resolved.calibration_profile is not None
    assert resolved.calibration_profile.name == "fastcal-v1"


def test_calibration_selection_does_not_rewrite_auto_cognition_mode(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config()
        + """
runtime:
  calibration_profile: fastcal-v1
  cognition:
    mode: auto
""",
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})

    assert resolved.config.runtime.cognition.mode.value == "auto"


def test_raw_secret_environment_override_beats_config_reference_and_stays_redacted(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config(secret_env="FILE_SECRET"),
    )

    resolved = resolve_runtime_config(
        config_path=config_path,
        environ={
            "FILE_SECRET": "file-secret",
            "RELAYLM_PROVIDER_API_KEY": "raw-env-secret",
        },
    )

    assert resolved.secrets.provider_api_key == "raw-env-secret"
    assert resolved.config.provider.api_key is None
    assert resolved.secret_effective.source is ConfigSource.ENV
    assert resolved.secret_effective.material_source is ConfigSource.ENV
    assert "raw-env-secret" not in repr(resolved)
    assert "raw-env-secret" not in repr(resolved.effective_diagnostics())


def test_cli_secret_reference_beats_raw_environment_override(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config(secret_env="FILE_SECRET"),
    )

    resolved = resolve_runtime_config(
        config_path=config_path,
        overrides=RuntimeConfigOverrides(provider_api_key_env="CLI_SECRET"),
        environ={
            "CLI_SECRET": "cli-secret",
            "FILE_SECRET": "file-secret",
            "RELAYLM_PROVIDER_API_KEY": "raw-env-secret",
        },
    )

    assert resolved.secrets.provider_api_key == "cli-secret"
    assert resolved.config.provider.api_key is not None
    assert resolved.config.provider.api_key.env == "CLI_SECRET"
    assert resolved.secret_effective.source is ConfigSource.CLI
    assert resolved.secret_effective.material_source is ConfigSource.ENV


def test_missing_referenced_secret_fails_without_echoing_secret_material(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config(secret_env="MISSING_SECRET"),
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=config_path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.SECRET_UNAVAILABLE
    assert caught.value.field == "provider.api_key"
    assert "MISSING_SECRET" in str(caught.value)


def test_complex_runtime_controls_parse_into_existing_owner_types(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config()
        + """\
runtime:
  memory_retrieval:
    max_chunks: 3
    max_chars: 900
  event_retrieval:
    max_events: 4
    max_chars: 1200
  continuity:
    max_items: 5
    lifetime_revisions: 6
  cognitive_budget:
    total:
      model_context_window: 8192
      reserved_output_tokens: 1024
    policy:
      initial_plan:
        canonical_state:
          max_items: 8
          floor_items: 2
        working_context:
          max_items: 4
          floor_items: 1
          max_chars: 2000
          floor_chars: 500
        retrieved_memory:
          max_items: 4
          floor_items: 0
          max_chars: 1600
          floor_chars: 0
        event_evidence:
          max_items: 4
          floor_items: 0
          max_chars: 1600
          floor_chars: 0
      steps:
        - layer: retrieved_memory
          target:
            max_items: 2
            floor_items: 0
            max_chars: 800
            floor_chars: 0
    token_counter:
      capability: example.counter
      mode: conservative_estimate
""",
    )

    resolved = resolve_runtime_config(config_path=config_path, environ={})
    runtime = resolved.config.runtime

    assert runtime.memory_retrieval is not None
    assert runtime.memory_retrieval.max_chunks == 3
    assert runtime.event_retrieval is not None
    assert runtime.event_retrieval.max_events == 4
    assert runtime.continuity is not None
    assert runtime.continuity.lifetime_revisions == 6
    assert runtime.cognitive_budget is not None
    assert runtime.cognitive_budget.total.model_context_window == 8192
    assert runtime.cognitive_budget.policy.steps[0].layer.value == "retrieved_memory"
    assert runtime.cognitive_budget.token_counter.mode is TokenCountMode.CONSERVATIVE_ESTIMATE
    assert resolved.source_for("runtime.memory_retrieval.max_chunks") is ConfigSource.CONFIG_FILE
    assert resolved.source_for("runtime.cognitive_budget.total.model_context_window") is ConfigSource.CONFIG_FILE


def test_invalid_owner_budget_semantics_are_reported_as_invalid_value(
    tmp_path: Path,
) -> None:
    config_path = _write_config(
        tmp_path / "runtime.yaml",
        _basic_config()
        + """\
runtime:
  cognitive_budget:
    total:
      model_context_window: 8192
      reserved_output_tokens: 1024
    policy:
      initial_plan:
        canonical_state:
          max_items: 1
          floor_items: 2
        working_context:
          max_items: 0
          floor_items: 0
          max_chars: 0
          floor_chars: 0
        retrieved_memory:
          max_items: 0
          floor_items: 0
          max_chars: 0
          floor_chars: 0
        event_evidence:
          max_items: 0
          floor_items: 0
          max_chars: 0
          floor_chars: 0
      steps: []
    token_counter:
      capability: example.counter
      mode: exact
""",
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=config_path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == "runtime.cognitive_budget.policy"


def test_explicit_missing_config_path_does_not_fall_back(tmp_path: Path) -> None:
    fallback = _write_config(tmp_path / "fallback.yaml", _basic_config())

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(
            config_path=tmp_path / "missing.yaml",
            environ={"RELAYLM_CONFIG": str(fallback)},
        )

    assert caught.value.code is RuntimeConfigErrorCode.READ_ERROR
    assert caught.value.field == "config_path"
