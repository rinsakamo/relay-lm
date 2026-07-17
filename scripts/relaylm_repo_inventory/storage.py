"""Part A: storage artifact inventory.

Scans Python and JavaScript/TypeScript source for concrete storage anchors:
literal artifact paths, file/database/browser-storage APIs, locking helpers, and
durability operations. Broader words such as ``memory``, ``cache``, ``queue``,
or ``evidence`` only classify an already-anchored record; vocabulary alone
never creates a storage record.

Every record defaults ``classification_state`` to ``"unclassified"``. Nothing
here decides that an artifact is safe to delete, dead, reconstructible, or
approved for migration.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import repo
from .invocations import InvocationRecord, collect_all as collect_invocation_roots
from .records import Evidence, StorageRecord

_SIGNAL_GROUPS: dict[str, tuple[str, ...]] = {
    "markdown": (r"\.md['\"]", r"character_workspace", r"MemoryDoc", r"memory\.md"),
    "json": (r"json\.dump\(", r"json\.dumps\(", r"json\.load\(", r"json\.loads\(", r"\.json['\"]"),
    "jsonl": (r"\.jsonl['\"]", r"\bjsonl\b"),
    "sqlite": (r"sqlite3", r"\.db['\"]", r"\.sqlite3?['\"]"),
    "index_log_cache_manifest": (r"index_log", r"\bcache\b", r"\bmanifest\b", r"\bprojection\b", r"_log\b"),
    "queue_lease_checkpoint_replay": (
        r"\bqueue\b",
        r"\bclaim\b",
        r"\blease\b",
        r"checkpoint",
        r"\breplay\b",
        r"publication",
        r"finaliz",
    ),
    "audit_evidence_receipt_tombstone": (
        r"\baudit\b",
        r"\breceipt\b",
        r"tombstone",
        r"source_evidence",
        r"\bevidence\b",
    ),
    "lock_atomic_durability": (
        r"portable_lock",
        r"fcntl\.flock",
        r"msvcrt\.locking",
        r"os\.replace\(",
        r"os\.rename\(",
        r"NamedTemporaryFile",
        r"fsync",
    ),
}
_COMPILED_GROUPS = {name: [re.compile(p) for p in pats] for name, pats in _SIGNAL_GROUPS.items()}

_FORMAT_LABELS = {
    "markdown": "markdown",
    "json": "json",
    "jsonl": "jsonl",
    "sqlite": "sqlite",
    "index_log_cache_manifest": "index/log/cache/manifest",
    "queue_lease_checkpoint_replay": "queue/lease/checkpoint/replay/finalization-state",
    "audit_evidence_receipt_tombstone": "audit/evidence/receipt/tombstone",
    "lock_atomic_durability": "lock/atomic-write/durability-helper",
}

_READER_INDICATORS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\.read_text\("), "read_text()"),
    (re.compile(r"\.read_bytes\("), "read_bytes()"),
    (re.compile(r"json\.load\("), "json.load()"),
    (re.compile(r"json\.loads\("), "json.loads()"),
    (re.compile(r"(?:^|[^\w])open\([^)]*['\"]r", re.MULTILINE), "open(..., 'r')"),
    (re.compile(r"\.open\([^)]*['\"]r"), "Path.open(..., 'r')"),
    (re.compile(r"\.read\(\)"), "read()"),
    (re.compile(r"\.exists\(\)"), "exists()"),
    (re.compile(r"(?:os\.(?:open|fdopen|stat|lstat|fstat)|\.lstat)\("), "low-level file open/stat"),
    (re.compile(r"\.(?:glob|rglob|iterdir)\("), "filesystem enumeration"),
    (re.compile(r"\bSELECT\s+[A-Za-z_*][\w*,.\s]*\s+FROM\s+[A-Za-z_]", re.IGNORECASE), "SQL SELECT"),
    (re.compile(r"sqlite3\.connect\("), "sqlite3.connect()"),
    (re.compile(r"(?:window\.)?localStorage\.getItem\("), "localStorage.getItem()"),
    (re.compile(r"(?:window\.)?sessionStorage\.getItem\("), "sessionStorage.getItem()"),
    (re.compile(r"\bindexedDB\.open\("), "indexedDB.open()"),
)
_WRITER_INDICATORS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\.write_text\("), "write_text()"),
    (re.compile(r"\.write_bytes\("), "write_bytes()"),
    (re.compile(r"json\.dump\("), "json.dump()"),
    (re.compile(r"json\.dumps\("), "json.dumps()"),
    (re.compile(r"(?:^|[^\w])open\([^)]*['\"][waxWAX]", re.MULTILINE), "open(..., 'w'/'a'/'x')"),
    (re.compile(r"\.open\([^)]*['\"][waxWAX]"), "Path.open(..., 'w'/'a'/'x')"),
    (re.compile(r"\.write\("), "write()"),
    (re.compile(r"\.(?:mkdir|touch|unlink)\("), "filesystem mutation"),
    (re.compile(r"os\.replace\("), "os.replace() [atomic rename]"),
    (re.compile(r"os\.rename\("), "os.rename()"),
    (re.compile(r"\bINSERT\s+INTO", re.IGNORECASE), "SQL INSERT"),
    (re.compile(r"\bUPDATE\s+[A-Za-z_][\w.]*\s+SET\b", re.IGNORECASE), "SQL UPDATE"),
    (re.compile(r"\bDELETE\s+FROM", re.IGNORECASE), "SQL DELETE"),
    (re.compile(r"(?:window\.)?localStorage\.(?:setItem|removeItem)\("), "localStorage mutation"),
    (re.compile(r"(?:window\.)?sessionStorage\.(?:setItem|removeItem)\("), "sessionStorage mutation"),
)
_LOCK_ATOMICITY_INDICATORS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"portable_lock"), "portable_lock()"),
    (re.compile(r"fcntl\.flock"), "fcntl.flock()"),
    (re.compile(r"msvcrt\.locking"), "msvcrt.locking()"),
    (re.compile(r"os\.replace\("), "os.replace() [atomic rename]"),
    (re.compile(r"os\.rename\("), "os.rename()"),
)
_DURABILITY_INDICATORS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"fsync"), "fsync"),
    (re.compile(r"NamedTemporaryFile"), "NamedTemporaryFile (write-then-rename pattern)"),
    (re.compile(r"\.flush\("), "flush()"),
)
_REPLAY_RETENTION_INDICATORS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\breplay\b"), "replay"),
    (re.compile(r"retention"), "retention"),
    (re.compile(r"checkpoint"), "checkpoint"),
    (re.compile(r"finaliz"), "finalization"),
    (re.compile(r"publication"), "publication"),
    (re.compile(r"\bclaim\b"), "claim"),
    (re.compile(r"\blease\b"), "lease"),
    (re.compile(r"\bqueue\b"), "queue"),
)
_CHARACTER_SCOPE_TOKENS = ("character_workspace", "{character}", "character_id", "character_name", "namespace")
_LITERAL_PATH_RE = re.compile(r'["\']([\w./{}\-]+\.(?:md|json|jsonl|db|sqlite3?))["\']')

_PATH_DECLARATION_RE = re.compile(
    r"(?m)^(?:"
    r"\s*[A-Z][A-Z0-9_]*\s*(?::[^=\n]+)?=\s*[\"\'][^\"\']+\.(?:md|json|jsonl|db|sqlite3?)[\"\']"
    r"|\s*[A-Za-z_][A-Za-z0-9_]*\s*(?::[^=\n]+)?=\s*Path\(\s*[\"\'][^\"\']+\.(?:md|json|jsonl|db|sqlite3?)[\"\']"
    r")"
)

_OWNER_PREFIX_TABLE: tuple[tuple[str, str], ...] = (
    ("relaymem_slp", "RelayMEM SLP subsystem (heuristic, from filename prefix)"),
    ("relaymem_primary", "RelayMEM primary-memory subsystem (heuristic, from filename prefix)"),
    ("relaymem_held", "RelayMEM held-governance subsystem (heuristic, from filename prefix)"),
    ("character_", "Character workspace/store subsystem (heuristic, from filename prefix)"),
    ("_client_instruction", "Client instruction cache subsystem (heuristic, from filename prefix)"),
    ("soul_lab", "Soul Lab app/API layer (heuristic, from filename prefix)"),
    ("audit_", "Audit/evidence subsystem (heuristic, from filename prefix)"),
    ("_analyzer", "Analyzer subsystem (heuristic, from filename prefix)"),
    ("o3_", "O-series scheduler/orchestration subsystem (heuristic, from filename prefix)"),
    ("o2_", "O-series scheduler/orchestration subsystem (heuristic, from filename prefix)"),
    ("o1_", "O-series scheduler/orchestration subsystem (heuristic, from filename prefix)"),
)

_SELF_SCAN_PREFIXES = (
    "scripts/relaylm_repo_inventory/",
    "tests/test_relaylm_repo_inventory.py",
)


def _probable_owner(stem: str) -> str:
    trimmed = stem.lstrip("_")
    for prefix, owner in _OWNER_PREFIX_TABLE:
        if trimmed.startswith(prefix):
            return owner
    return "unknown (heuristic default; needs human review)"


def _matched_groups(text: str) -> dict[str, list[tuple[int, str]]]:
    hits: dict[str, list[tuple[int, str]]] = {}
    lines = text.splitlines()
    for group_name, patterns in _COMPILED_GROUPS.items():
        group_hits: list[tuple[int, str]] = []
        for lineno, line in enumerate(lines, start=1):
            if any(p.search(line) for p in patterns):
                group_hits.append((lineno, line.strip()[:160]))
        if group_hits:
            hits[group_name] = group_hits
    return hits


def _indicator_hits(text: str, indicators: tuple[tuple[re.Pattern, str], ...]) -> set[str]:
    found: set[str] = set()
    for pattern, label in indicators:
        if pattern.search(text):
            found.add(label)
    return found


_SHARED_ENTRY_ROOT_KINDS = frozenset({"npm_script", "github_actions_step", "frontend_route"})


def _invocation_roots_referencing(
    module_stem: str,
    roots: list[InvocationRecord],
    root_texts: dict[str, str],
) -> list[str]:
    matches: list[str] = []
    for root in roots:
        if root.root_kind in _SHARED_ENTRY_ROOT_KINDS:
            if module_stem in root.command_or_symbol:
                matches.append(root.root_id)
            continue
        text = root_texts.get(root.source_path)
        if text is None:
            continue
        if module_stem in text:
            matches.append(root.root_id)
    return sorted(set(matches))


def scan_storage_artifacts(
    invocation_roots: list[InvocationRecord] | None = None,
) -> list[StorageRecord]:
    if invocation_roots is None:
        invocation_roots = collect_invocation_roots()

    root_texts: dict[str, str] = {}
    for root in invocation_roots:
        if root.source_path not in root_texts:
            text = repo.read_text(repo.ROOT / root.source_path)
            if text is not None:
                root_texts[root.source_path] = text

    records: list[StorageRecord] = []
    scan_suffixes = (".py", ".ts", ".tsx", ".mjs", ".js")
    for path in repo.iter_repo_files(suffixes=scan_suffixes):
        rel = repo.relative(path)
        if not (
            rel.startswith("relaylm/")
            or rel.startswith("scripts/")
            or rel.startswith("apps/")
        ):
            continue
        if any(rel.startswith(prefix) for prefix in _SELF_SCAN_PREFIXES):
            continue
        text = repo.read_text(path)
        if text is None:
            continue

        literal_paths = sorted({m.group(1) for m in _LITERAL_PATH_RE.finditer(text)})
        readers = sorted(_indicator_hits(text, _READER_INDICATORS))
        writers = sorted(_indicator_hits(text, _WRITER_INDICATORS))
        locking = sorted(_indicator_hits(text, _LOCK_ATOMICITY_INDICATORS))
        durability = sorted(_indicator_hits(text, _DURABILITY_INDICATORS))
        persistent_readers = [value for value in readers if value != "json.loads()"]
        persistent_writers = [value for value in writers if value != "json.dumps()"]
        path_declaration = path.suffix.lower() == ".py" and bool(_PATH_DECLARATION_RE.search(text))

        # Concrete storage evidence is required. Domain vocabulary, UI labels,
        # and in-memory JSON conversion alone are intentionally insufficient.
        # A path-only record survives only when the path is bound as code data
        # (for example a Python path constant), rather than merely displayed.
        if not (
            path_declaration
            or persistent_readers
            or persistent_writers
            or locking
            or durability
        ):
            continue

        groups = _matched_groups(text)
        if not groups:
            formats = ["storage-api"]
            evidence: list[Evidence] = []
        else:
            formats = sorted({_FORMAT_LABELS[g] for g in groups})
            evidence = [
                Evidence(rel, lineno, snippet)
                for group_hits in groups.values()
                for lineno, snippet in group_hits
            ]

        lines = text.splitlines()
        for label_set, indicators in (
            (readers, _READER_INDICATORS),
            (writers, _WRITER_INDICATORS),
            (locking, _LOCK_ATOMICITY_INDICATORS),
            (durability, _DURABILITY_INDICATORS),
        ):
            if not label_set:
                continue
            for lineno, line in enumerate(lines, start=1):
                if any(pattern.search(line) for pattern, _ in indicators):
                    evidence.append(Evidence(rel, lineno, line.strip()[:160]))

        evidence = sorted(set(evidence), key=lambda e: (e.file, e.line, e.snippet))[:20]
        replay_retention = (
            sorted(_indicator_hits(text, _REPLAY_RETENTION_INDICATORS))
            if "queue_lease_checkpoint_replay" in groups
            else []
        )

        artifact_pattern = (
            "; ".join(literal_paths[:3])
            if literal_paths
            else f"module:{rel} (concrete storage API, no literal artifact path)"
        )

        is_character_scoped = any(token in text for token in _CHARACTER_SCOPE_TOKENS)
        namespace_scope = (
            "character/namespace-scoped (heuristic)"
            if is_character_scoped
            else "global/unscoped (heuristic, unconfirmed)"
        )
        user_owned_possible = is_character_scoped or bool(
            set(groups) & {"markdown", "audit_evidence_receipt_tombstone"}
        )

        if "index_log_cache_manifest" in groups and "queue_lease_checkpoint_replay" not in groups:
            reconstructible = (
                "possibly reconstructible (heuristic: cache/index/log/projection naming; "
                "not a deletion recommendation)"
            )
        else:
            reconstructible = "unknown (heuristic default; no destructive inference should be drawn)"

        roots_referencing = _invocation_roots_referencing(path.stem, invocation_roots, root_texts)
        owner = _probable_owner(Path(rel).stem)

        records.append(
            StorageRecord(
                source_path=rel,
                artifact_pattern=artifact_pattern,
                artifact_format="+".join(formats),
                probable_owner=owner,
                readers=readers,
                writers=writers,
                invocation_roots=roots_referencing,
                namespace_or_character_scope=namespace_scope,
                durability_signals=durability,
                locking_or_atomicity_signals=locking,
                replay_or_retention_signals=replay_retention,
                user_owned_data_possible=user_owned_possible,
                reconstructible_candidate=reconstructible,
                evidence=evidence,
                heuristic_fields=[
                    "artifact_pattern",
                    "artifact_format",
                    "probable_owner",
                    "readers",
                    "writers",
                    "invocation_roots",
                    "namespace_or_character_scope",
                    "durability_signals",
                    "locking_or_atomicity_signals",
                    "replay_or_retention_signals",
                    "user_owned_data_possible",
                    "reconstructible_candidate",
                ],
            )
        )

    records.sort(key=lambda r: r.sort_key())
    return records
