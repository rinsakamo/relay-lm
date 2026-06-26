"""Named I-4C2 continuation boundary for one durable Forget prepare.

The caller must hold the canonical per-memory mutation lock.  This module does
not invent any identity or timestamp; it delegates deterministic M3e publication
to the completed I-4C1 authority and then canonically rereads the hidden page.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .relaymem_primary_forget_artifact import validate_forget_prepared
from .relaymem_primary_forget_commit import _publish_hidden
from .relaymem_primary_lifecycle_page import verify_hidden_page_against_prepared


class PrimaryForgetHiddenResumeError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def resume_prepared_forget_hidden_successor_locked(
    store_root: str | Path, *, prepared: Mapping[str, Any]
) -> tuple[Mapping[str, Any], bool]:
    """Publish or reread the exact deterministic hidden successor under lock."""

    if not validate_forget_prepared(prepared):
        raise PrimaryForgetHiddenResumeError("target_corrupt")
    root = Path(store_root)
    try:
        receipt, existing = _publish_hidden(root, prepared, PrimaryForgetHiddenResumeError)
    except PrimaryForgetHiddenResumeError:
        raise
    except Exception as exc:  # bounded translation; raw exception never escapes
        raise PrimaryForgetHiddenResumeError("reconciliation_required") from exc
    if not verify_hidden_page_against_prepared(root, prepared=prepared):
        raise PrimaryForgetHiddenResumeError("target_corrupt")
    return receipt, existing


__all__ = [
    "PrimaryForgetHiddenResumeError",
    "resume_prepared_forget_hidden_successor_locked",
]
