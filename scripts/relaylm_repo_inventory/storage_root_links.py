"""Attach direct invocation roots to storage records.

A storage-bearing operator or smoke script is itself an invocation root even
when its source text does not mention its own filename. This post-processing
step preserves that direct source-path relationship in generated inventory.
"""
from __future__ import annotations

from .records import InvocationRecord, StorageRecord


def attach_direct_roots(
    records: list[StorageRecord],
    roots: list[InvocationRecord],
) -> list[StorageRecord]:
    by_source: dict[str, set[str]] = {}
    for root in roots:
        by_source.setdefault(root.source_path, set()).add(root.root_id)
    for record in records:
        direct = by_source.get(record.source_path)
        if direct:
            record.invocation_roots = sorted(set(record.invocation_roots) | direct)
    return records
