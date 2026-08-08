"""RT-1D-R5 retirement proof for Phase I-4D prior-revision exclusion.

This smoke used to call `active_corrected_and_finalized()` from the Phase I-4D
primary retrieval exclusion smoke, which drove the ordinary Primary reader and
asserted that a superseded revision was excluded from what Primary served.

RT-1D-R5 retired that reader, so the exclusion can no longer be observed
through ordinary serving and the helper was removed with it. The underlying
intent survives as an absence proof: a prior revision cannot leak through
ordinary Retrieval because no ordinary Primary read path exists at all, which
is a strictly stronger guarantee than the ranking-level exclusion this smoke
previously asserted.

The lifecycle/currentness exclusion rules themselves are unchanged and remain
owned by the Primary retrieval-eligibility surface, which R5 did not touch.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_exclusion_helper_is_retirement_compatible() -> None:
    """The shared helper survives for its sibling smokes, proving absence.

    It is deliberately not deleted: the Phase I-4D security and recovery-state
    smokes import it and are outside this transaction's budget. What changed is
    its meaning — it now proves nothing is selected, rather than proving a
    superseded revision was filtered out of what Primary served.
    """

    module = importlib.import_module(
        "relaylm_phase_i4d_primary_retrieval_exclusion_smoke"
    )
    assert hasattr(module, "active_corrected_and_finalized")
    runtime = module.recall(None, [])["primary_recall_runtime"]
    assert runtime["selected_count"] == 0
    assert runtime["selected_memories"] == []
    assert runtime["primary_reader_fenced"] is True
    assert runtime["primary_store_read"] is False


def check_no_ordinary_primary_read_can_leak_a_prior_revision() -> None:
    """Absence proof: ordinary Retrieval reaches no Primary candidate at all.

    With no discovery, selection, or ranking left on the ordinary path, there
    is no stage at which a superseded revision could be surfaced and then need
    excluding.
    """

    body = (ROOT / "relaylm/relaymem_retrieval.py").read_text(encoding="utf-8")
    for retired in (
        "apply_relaymem_primary_recall_scope",
        "resolve_relaymem_character_store_root",
    ):
        assert retired not in body, retired
    # The RelayCTX contract shape survives, but its candidate slot is inert:
    # the fenced artifact declares it empty and nothing can populate it.
    assert '"selected_mem_candidates": []' in body
    stage = next(
        node
        for node in ast.parse(body).body
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_relaymem_retrieval_stage"
    )
    returns = [n for n in ast.walk(stage) if isinstance(n, ast.Return)]
    assert len(returns) == 1, "the ordinary stage has exactly one fenced exit"


def check_eligibility_owner_is_preserved() -> None:
    """R5 retired the reader, not the lifecycle/currentness exclusion rules."""

    eligibility = ROOT / "relaylm/relaymem_primary_retrieval_eligibility.py"
    assert eligibility.exists()
    body = eligibility.read_text(encoding="utf-8")
    for marker in ("excluded_prior_revision", "excluded_hidden"):
        assert marker in body, marker


def main() -> None:
    check_exclusion_helper_is_retirement_compatible()
    check_no_ordinary_primary_read_can_leak_a_prior_revision()
    check_eligibility_owner_is_preserved()
    print("Phase I-4D prior revision exclusion smoke passed")


if __name__ == "__main__":
    main()
