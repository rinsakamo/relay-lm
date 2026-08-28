from __future__ import annotations

from pathlib import Path

import pytest

from relaylm.runtime_config import RuntimeConfigErrorCode
from relaylm.runtime_config_loader import RuntimeConfigResolutionError, resolve_runtime_config


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _runtime_config(profiles: str, *, runtime: str = "") -> str:
    return f"""\
format_version: 1
profiles:
{profiles}
provider:
  adapter: openai_compatible
  base_url: http://127.0.0.1:1234/v1
  model: shared-physical-model
{runtime}"""


def test_profiles_are_explicit_public_ids_with_cognitive_roots_and_optional_model_override(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path / "runtime.yaml",
        _runtime_config(
            """\
  - name: rin
    root: /packages/rin
  - name: medical-soap
    root: /packages/medical-soap
    provider:
      model: heavyweight-physical-model
"""
        ),
    )

    resolved = resolve_runtime_config(config_path=path, environ={})

    assert [profile.name for profile in resolved.config.profiles] == [
        "rin",
        "medical-soap",
    ]
    assert [profile.root for profile in resolved.config.profiles] == [
        "/packages/rin",
        "/packages/medical-soap",
    ]
    assert resolved.config.profiles[0].provider.model is None
    assert resolved.config.profiles[1].provider.model == "heavyweight-physical-model"
    assert resolved.config.provider.model == "shared-physical-model"


def test_duplicate_profile_names_fail_closed(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "runtime.yaml",
        _runtime_config(
            """\
  - name: rin
    root: /packages/rin
  - name: rin
    root: /packages/other
"""
        ),
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == "profiles[1].name"
    assert "duplicate" in str(caught.value).lower()


@pytest.mark.parametrize(
    ("profiles", "field"),
    [
        (
            """\
  - name: ""
    root: /packages/rin
""",
            "profiles[0].name",
        ),
        (
            """\
  - name: rin
    root: ""
""",
            "profiles[0].root",
        ),
    ],
)
def test_profile_identity_and_root_are_non_empty(
    tmp_path: Path,
    profiles: str,
    field: str,
) -> None:
    path = _write(tmp_path / "runtime.yaml", _runtime_config(profiles))

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_VALUE
    assert caught.value.field == field


def test_profile_provider_override_is_model_only(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "runtime.yaml",
        _runtime_config(
            """\
  - name: rin
    root: /packages/rin
    provider:
      base_url: http://other.example/v1
"""
        ),
    )

    with pytest.raises(RuntimeConfigResolutionError) as caught:
        resolve_runtime_config(config_path=path, environ={})

    assert caught.value.code is RuntimeConfigErrorCode.UNKNOWN_FIELD
    assert caught.value.field == "profiles[0].provider.base_url"


def test_profiles_are_required_and_character_selection_is_not_a_parallel_authority(
    tmp_path: Path,
) -> None:
    missing = _write(
        tmp_path / "missing.yaml",
        """\
format_version: 1
provider:
  adapter: openai_compatible
  base_url: http://127.0.0.1:1234/v1
  model: physical-model
""",
    )
    with pytest.raises(RuntimeConfigResolutionError) as caught_missing:
        resolve_runtime_config(config_path=missing, environ={})
    assert caught_missing.value.code is RuntimeConfigErrorCode.MISSING_REQUIRED
    assert caught_missing.value.field == "profiles"

    old = _write(
        tmp_path / "old.yaml",
        """\
format_version: 1
character:
  directory: /packages/rin
provider:
  adapter: openai_compatible
  base_url: http://127.0.0.1:1234/v1
  model: physical-model
""",
    )
    with pytest.raises(RuntimeConfigResolutionError) as caught_old:
        resolve_runtime_config(config_path=old, environ={})
    assert caught_old.value.code is RuntimeConfigErrorCode.UNKNOWN_FIELD
    assert caught_old.value.field == "character"


def test_calibration_profile_name_is_disambiguated_from_cognitive_profiles(
    tmp_path: Path,
) -> None:
    old = _write(
        tmp_path / "old-runtime-profile.yaml",
        _runtime_config(
            """\
  - name: rin
    root: /packages/rin
""",
            runtime="""\
runtime:
  profile: standard
""",
        ),
    )
    with pytest.raises(RuntimeConfigResolutionError) as caught_old:
        resolve_runtime_config(config_path=old, environ={})
    assert caught_old.value.code is RuntimeConfigErrorCode.UNKNOWN_FIELD
    assert caught_old.value.field == "runtime.profile"

    current = _write(
        tmp_path / "calibration-profile.yaml",
        _runtime_config(
            """\
  - name: rin
    root: /packages/rin
""",
            runtime="""\
runtime:
  calibration_profile: standard
""",
        ),
    )
    with pytest.raises(RuntimeConfigResolutionError) as caught_current:
        resolve_runtime_config(config_path=current, environ={})
    assert caught_current.value.code is RuntimeConfigErrorCode.INVALID_COMBINATION
    assert caught_current.value.field == "runtime.calibration_profile"
    assert "calibrated" in str(caught_current.value).lower()
