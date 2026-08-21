from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = ROOT / ".ai" / "skills" / "repository-orientation" / "SKILL.md"


def _read_skill() -> tuple[dict[str, object], str, str]:
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    _, frontmatter_text, body = content.split("---\n", 2)
    frontmatter = yaml.safe_load(frontmatter_text)
    assert isinstance(frontmatter, dict)
    return frontmatter, body, content


def test_repository_orientation_skill_is_structured_and_read_only() -> None:
    assert SKILL_PATH.is_file()

    frontmatter, body, content = _read_skill()

    assert frontmatter["schema_version"] == 1
    assert frontmatter["id"] == "repository-orientation"
    assert frontmatter["mode"] == "read_only"
    assert isinstance(frontmatter["responsibility"], str)
    assert frontmatter["responsibility"].strip()

    for field in ("when_to_use", "when_not_to_use", "required_authority"):
        value = frontmatter[field]
        assert isinstance(value, list)
        assert value
        assert all(isinstance(item, str) and item.strip() for item in value)

    assert frontmatter["required_live_facts"] == [
        "repository_head",
        "open_pull_requests",
    ]
    assert frontmatter["authorization"] == {"writes": "prohibited"}

    assert ".ai/README.md" in frontmatter["required_authority"]
    assert ".ai/agent-contract.yaml" in frontmatter["required_authority"]
    assert "docs/reference/development-workflow.md" in frontmatter["required_authority"]

    for heading in (
        "## Procedure",
        "## Verification",
        "## Stop conditions",
        "## Authorization",
    ):
        assert heading in body

    assert re.search(r"\b[0-9a-f]{40}\b", content) is None
