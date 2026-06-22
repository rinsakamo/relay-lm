"""Bounded read-only observation of M3g temporary names."""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any

MAX_MEM_DIRECTORY_ENTRIES = 512


def inspect_cleanup_artifacts(
    state: dict[str, Any], mem_fd: int, receipt: Mapping[str, Any]
) -> None:
    try:
        entries = os.listdir(mem_fd)
    except OSError:
        state["blocked_reasons"].append("primary_reconciliation_recovery_directory_listing_failed")
        return
    if len(entries) > MAX_MEM_DIRECTORY_ENTRIES:
        state["blocked_reasons"].append("primary_reconciliation_recovery_directory_entry_limit_exceeded")
        return
    identities = "|".join(
        re.escape(str(receipt[f"{role}_entry_identity"]))
        for role in ("index", "log")
    )
    pattern = re.compile(
        rf"\.relaymem-reconcile-(?:{identities})-[0-9a-f]{{16}}\.tmp"
    )
    matches = [name for name in entries if pattern.fullmatch(name)]
    state["cleanup_artifact_count"] = len(matches)
    state["cleanup_artifacts_present"] = bool(matches)
