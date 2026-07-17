"""Shared record types for the repository inventory.

Every record class here is a plain, order-preserving data holder. None of
them encode a removal, migration, or dead-code decision. ``classification_state``
on storage records is always the literal string ``"unclassified"``, and each
record carries ``heuristic_fields`` naming which of its own fields were
inferred rather than directly observed in source text.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class Evidence:
    file: str
    line: int
    snippet: str

    def to_dict(self) -> dict:
        return {"file": self.file, "line": self.line, "snippet": self.snippet}


def sort_key(evidence: Evidence) -> tuple:
    return (evidence.file, evidence.line, evidence.snippet)


@dataclass
class StorageRecord:
    artifact_pattern: str
    artifact_format: str
    probable_owner: str
    readers: list[str]
    writers: list[str]
    invocation_roots: list[str]
    namespace_or_character_scope: str
    durability_signals: list[str]
    locking_or_atomicity_signals: list[str]
    replay_or_retention_signals: list[str]
    user_owned_data_possible: bool
    reconstructible_candidate: str
    evidence: list[Evidence]
    heuristic_fields: list[str] = field(default_factory=list)
    classification_state: str = "unclassified"
    source_path: str = ""

    def sort_key(self) -> tuple:
        return (self.source_path, self.artifact_pattern)

    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "artifact_pattern": self.artifact_pattern,
            "artifact_format": self.artifact_format,
            "probable_owner": self.probable_owner,
            "readers": sorted(self.readers),
            "writers": sorted(self.writers),
            "invocation_roots": sorted(self.invocation_roots),
            "namespace_or_character_scope": self.namespace_or_character_scope,
            "durability_signals": sorted(self.durability_signals),
            "locking_or_atomicity_signals": sorted(self.locking_or_atomicity_signals),
            "replay_or_retention_signals": sorted(self.replay_or_retention_signals),
            "user_owned_data_possible": self.user_owned_data_possible,
            "reconstructible_candidate": self.reconstructible_candidate,
            "classification_state": self.classification_state,
            "evidence": [e.to_dict() for e in sorted(self.evidence, key=sort_key)],
            "heuristic_fields": sorted(set(self.heuristic_fields)),
        }


@dataclass
class InvocationRecord:
    root_id: str
    root_kind: str
    command_or_symbol: str
    source_path: str
    source_line: int | None
    reachable_from_fastapi_import_graph: bool | None
    notes: list[str]
    evidence: list[Evidence]
    heuristic_fields: list[str] = field(default_factory=list)

    def sort_key(self) -> tuple:
        return (self.root_kind, self.root_id)

    def to_dict(self) -> dict:
        return {
            "root_id": self.root_id,
            "root_kind": self.root_kind,
            "command_or_symbol": self.command_or_symbol,
            "source_path": self.source_path,
            "source_line": self.source_line,
            "reachable_from_fastapi_import_graph": self.reachable_from_fastapi_import_graph,
            "notes": list(self.notes),
            "evidence": [e.to_dict() for e in sorted(self.evidence, key=sort_key)],
            "heuristic_fields": sorted(set(self.heuristic_fields)),
        }


@dataclass
class ConfigRecord:
    key_kind: str
    name: str
    source_context: str
    referenced_in: list[str]
    evidence: list[Evidence]
    heuristic_fields: list[str] = field(default_factory=list)

    def sort_key(self) -> tuple:
        return (self.key_kind, self.name)

    def to_dict(self) -> dict:
        return {
            "key_kind": self.key_kind,
            "name": self.name,
            "source_context": self.source_context,
            "referenced_in": sorted(set(self.referenced_in)),
            "evidence": [e.to_dict() for e in sorted(self.evidence, key=sort_key)],
            "heuristic_fields": sorted(set(self.heuristic_fields)),
        }
