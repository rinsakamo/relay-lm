from __future__ import annotations

from pathlib import Path

import yaml


_REPO_ROOT = Path(__file__).resolve().parents[2]
_AUTHORITY_ROOT = _REPO_ROOT / ".ai" / "authority"
_SEMANTIC_FIRST_OWNER = "lm_studio_semantic_first_qualification"
_SKILL_PATH = ".ai/skills/lm-studio-semantic-first-preflight/SKILL.md"
_FORBIDDEN_PRE_PROVIDER_SURFACES = (
    "describe_openai_compatible_cognition_capabilities",
    "/api/v1/models",
    "/v1/models",
)


def _authorities() -> dict[str, dict[str, object]]:
    loaded: dict[str, dict[str, object]] = {}
    for path in sorted(_AUTHORITY_ROOT.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("id"), str):
            loaded[raw["id"]] = raw
    return loaded


def _depends_on_semantic_first(
    owner_id: str,
    authorities: dict[str, dict[str, object]],
    *,
    seen: frozenset[str] = frozenset(),
) -> bool:
    if owner_id == _SEMANTIC_FIRST_OWNER:
        return True
    if owner_id in seen:
        return False
    owner = authorities[owner_id]
    dependencies = owner.get("depends_on", [])
    if not isinstance(dependencies, list):
        return False
    return any(
        isinstance(dependency, str)
        and dependency in authorities
        and _depends_on_semantic_first(
            dependency,
            authorities,
            seen=seen | {owner_id},
        )
        for dependency in dependencies
    )


def test_semantic_first_owner_materializes_v2_style_host_owned_preflight_skill() -> None:
    authorities = _authorities()
    owner = authorities[_SEMANTIC_FIRST_OWNER]
    implementations = owner.get("implementation", [])
    assert isinstance(implementations, list)
    assert _SKILL_PATH in implementations

    skill = (_REPO_ROOT / _SKILL_PATH).read_text(encoding="utf-8")
    assert "Controller observes and assembles. Host validates and freezes." in skill
    assert "Do not implement a second host outside the host." in skill
    assert "provider HTTP preflight remains zero" in skill


def test_semantic_first_dependency_closure_has_no_duplicate_pre_provider_capability_gate() -> None:
    authorities = _authorities()
    implementation_paths: set[str] = set()

    for owner_id, owner in authorities.items():
        if not _depends_on_semantic_first(owner_id, authorities):
            continue
        implementations = owner.get("implementation", [])
        if not isinstance(implementations, list):
            continue
        implementation_paths.update(
            path
            for path in implementations
            if isinstance(path, str) and path.endswith(".py")
        )

    assert "src/relaylm/actual_model_stage_r_lm_studio_semantic_first.py" in implementation_paths
    assert "src/relaylm/actual_model_stage_r_lm_studio_fixed_continuity_slots.py" in implementation_paths

    violations: list[str] = []
    for relative_path in sorted(implementation_paths):
        source = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_PRE_PROVIDER_SURFACES:
            if forbidden in source:
                violations.append(f"{relative_path}: {forbidden}")

    assert violations == [], (
        "LM Studio semantic-first consumers must not implement controller-side "
        "or pre-provider capability admission; actual semantic requests own the "
        f"runtime boundary. violations={violations!r}"
    )
