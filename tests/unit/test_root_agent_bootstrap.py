from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_root_agent_bootstrap_is_a_thin_authority_router() -> None:
    path = ROOT / "AGENTS.md"
    assert path.is_file()

    content = path.read_text(encoding="utf-8")

    assert ".ai/README.md" in content
    assert ".ai/agent-contract.yaml" in content
    assert "docs/reference/development-workflow.md" not in content
    assert "docs/reference/repository-practices.md" not in content
    assert re.search(r"\b[0-9a-f]{40}\b", content) is None

    repository_paths = set(re.findall(r"`([^`]*[/][^`]*)`", content))
    assert repository_paths == {".ai/README.md", ".ai/agent-contract.yaml"}


def test_authority_root_discovers_repository_native_procedures() -> None:
    content = (ROOT / ".ai" / "README.md").read_text(encoding="utf-8")

    assert "## Repository-native procedures" in content
    assert ".ai/skills/" in content
    assert "loaded only when" in content
    assert "not semantic authority" in content
