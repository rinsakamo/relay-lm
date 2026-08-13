"""Prove the post-retirement Primary recall structure.

Ordinary Primary recall entry points, selection, production reachability, and
store access from ordinary Retrieval remain absent. The explicitly retained
read-only history/admin helpers and store remain available.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RETIRED_RECALL_NAMES = (
    "apply_relaymem_primary_recall_scope",
    "prepare_primary_recall_selection",
    "compose_primary_recall_results",
    "run_primary_recall_selection",
)


def check_ordinary_recall_entry_point_is_gone() -> None:
    recall = importlib.import_module("relaylm.relaymem_primary_recall")
    for name in RETIRED_RECALL_NAMES:
        assert not hasattr(recall, name), name
    assert recall.__all__ == ["resolve_relaymem_character_store_root"]


def check_selection_owner_is_deleted() -> None:
    assert not (ROOT / "relaylm/relaymem_primary_recall_selection.py").exists()


def check_no_module_reaches_the_retired_recall() -> None:
    offenders = []
    for source in sorted((ROOT / "relaylm").glob("*.py")):
        body = source.read_text(encoding="utf-8")
        offenders += [
            (source.name, name) for name in RETIRED_RECALL_NAMES if name in body
        ]
    assert offenders == [], offenders


def check_ordinary_retrieval_opens_no_primary_store() -> None:
    body = (ROOT / "relaylm/retrieval/runtime.py").read_text(encoding="utf-8")
    assert "resolve_relaymem_character_store_root" not in body
    stage = next(
        node
        for node in ast.parse(body).body
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_relaymem_retrieval_stage"
    )
    returns = [n for n in ast.walk(stage) if isinstance(n, ast.Return)]
    assert len(returns) == 1, "the ordinary stage has exactly one fenced exit"


def check_read_only_history_admin_surface_survives() -> None:
    recall = importlib.import_module("relaylm.relaymem_primary_recall")
    for name in ("_load_control_state", "_load_validated_page", "_safe_root", "_token"):
        assert hasattr(recall, name), name
    assert callable(recall.resolve_relaymem_character_store_root)
    assert (ROOT / "relaylm/relaymem_primary_recall_store.py").exists()


def main() -> None:
    check_ordinary_recall_entry_point_is_gone()
    check_selection_owner_is_deleted()
    check_no_module_reaches_the_retired_recall()
    check_ordinary_retrieval_opens_no_primary_store()
    check_read_only_history_admin_surface_survives()
    print('Primary recall post-retirement structure smoke passed')


if __name__ == "__main__":
    main()
