#!/usr/bin/env python3
"""Twin Extraction merge CLI.

Merges all batch extraction results under one or more --results-dir
directories into a single review artifact (--out). --results-dir is
repeatable so separate sources (for example X and ChatGPT batch-runner
output) can be merged directly without copying their files into one
directory first -- both sources reuse the same batch_NNNN.result.json
numbering, so a manual copy would silently overwrite one source's evidence
with the other's. Caller-invoked and bounded; this script is not part of
the RelayLM runtime and does not import the `relaylm` package.

This tool produces a review artifact only. It does not write to MEM/SOUL
and does not perform bootstrap ingestion.

Merge rules:
  - style_observations are never merged across records (similar-description
    auto-merge risks conflating unrelated observations). Each observation's
    `strength` is recomputed from its own evidence_ids count.
  - fact_candidates are merged only on an exact (statement, type) match.
    Ambiguous/fuzzy statement merging is never performed. Merged
    evidence_ids are unioned and provenance is collected into a sorted
    list. Candidates without at least one valid provenance label are
    dropped instead of emitting provenance-empty artifacts. If any merged
    member is `private_only`, the merged candidate is `private_only`. A
    candidate with no explicit sensitivity is treated as `private_only`
    (fail-closed default).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STRENGTH_HIGH_THRESHOLD = 3
STRENGTH_MEDIUM_THRESHOLD = 2


def _recompute_strength(evidence_count: int) -> str:
    if evidence_count >= STRENGTH_HIGH_THRESHOLD:
        return "high"
    if evidence_count >= STRENGTH_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _is_scalar_evidence_id(item: object) -> bool:
    return isinstance(item, (str, int, float)) and not isinstance(item, bool)


def _valid_evidence_id_list(raw_evidence_ids: object) -> list[str] | None:
    """Return a normalized, deduplicated, sorted evidence-id list, or None
    if ``raw_evidence_ids`` is not a non-empty list of scalars. Rejects a
    bare string (which would otherwise be iterated character-by-character)
    and rejects any non-scalar element such as a dict or list (which would
    otherwise be silently stringified into a garbage id via ``str()``).
    """
    if not isinstance(raw_evidence_ids, list) or not raw_evidence_ids:
        return None
    if not all(item is None or _is_scalar_evidence_id(item) for item in raw_evidence_ids):
        return None
    evidence_ids = sorted({str(item) for item in raw_evidence_ids if item is not None})
    if not evidence_ids:
        return None
    return evidence_ids


def _normalize_provenance(raw_provenance: object) -> list[str] | None:
    """Return non-empty provenance labels or None for invalid/missing data.

    The extraction prompts require a source label (for example ``x_post`` or
    ``chatgpt_reconstructed``). If an LLM response omits it, returns an empty
    value, or returns a nested/non-scalar shape, drop the fact candidate
    instead of emitting a review artifact with ``"provenance": []``.
    """
    if _is_scalar_evidence_id(raw_provenance):
        labels = {str(raw_provenance)}
    elif isinstance(raw_provenance, list) and raw_provenance:
        if not all(_is_scalar_evidence_id(item) for item in raw_provenance):
            return None
        labels = {str(item) for item in raw_provenance}
    else:
        return None
    labels = {label for label in labels if label}
    if not labels:
        return None
    return sorted(labels)


def _normalize_style_observation(raw: dict) -> dict | None:
    if not isinstance(raw.get("category"), str) or not isinstance(raw.get("description"), str):
        return None
    evidence_ids = _valid_evidence_id_list(raw.get("evidence_ids"))
    if evidence_ids is None:
        return None
    return {
        "category": raw["category"],
        "description": raw["description"],
        "evidence_ids": evidence_ids,
        "strength": _recompute_strength(len(evidence_ids)),
    }


def merge_style_observations(batches: list[dict]) -> list[dict]:
    observations = []
    for batch in batches:
        for raw in batch.get("style_observations", []):
            if not isinstance(raw, dict):
                continue
            normalized = _normalize_style_observation(raw)
            if normalized is not None:
                observations.append(normalized)
    observations.sort(key=lambda obs: (obs["category"], -len(obs["evidence_ids"]), obs["description"]))
    return observations


def merge_fact_candidates(batches: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []

    for batch in batches:
        for raw in batch.get("fact_candidates", []):
            if not isinstance(raw, dict):
                continue
            statement = raw.get("statement")
            fact_type = raw.get("type")
            if not isinstance(statement, str) or not statement or not isinstance(fact_type, str) or not fact_type:
                continue

            fact_evidence_ids = _valid_evidence_id_list(raw.get("evidence_ids"))
            if fact_evidence_ids is None:
                continue
            provenance = _normalize_provenance(raw.get("provenance"))
            if provenance is None:
                continue

            key = (statement, fact_type)
            if key not in grouped:
                grouped[key] = {
                    "statement": statement,
                    "type": fact_type,
                    "provenance": set(),
                    "evidence_ids": set(),
                    "time_contexts": set(),
                    "sensitivity": "general",
                }
                order.append(key)
            entry = grouped[key]

            entry["provenance"].update(provenance)
            entry["evidence_ids"].update(fact_evidence_ids)

            time_context = raw.get("time_context")
            if isinstance(time_context, str) and time_context and time_context != "unknown":
                entry["time_contexts"].add(time_context)

            sensitivity = raw.get("sensitivity")
            if sensitivity != "general":
                entry["sensitivity"] = "private_only"

    result = []
    for key in order:
        entry = grouped[key]
        result.append(
            {
                "statement": entry["statement"],
                "type": entry["type"],
                "provenance": sorted(entry["provenance"]),
                "evidence_ids": sorted(entry["evidence_ids"]),
                "time_contexts": sorted(entry["time_contexts"]) if entry["time_contexts"] else ["unknown"],
                "sensitivity": entry["sensitivity"],
            }
        )
    result.sort(key=lambda item: (item["statement"], item["type"]))
    return result


def load_result_batches(results_dir: Path) -> list[dict]:
    batches = []
    for path in sorted(results_dir.glob("*.result.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            batches.append(data)
    return batches


def build_review(batches: list[dict]) -> dict:
    style_observations = merge_style_observations(batches)
    fact_candidates = merge_fact_candidates(batches)
    private_only_count = sum(1 for fc in fact_candidates if fc["sensitivity"] == "private_only")
    return {
        "style_observations": style_observations,
        "fact_candidates": fact_candidates,
        "summary": {
            "batches_merged": len(batches),
            "style_observation_count": len(style_observations),
            "fact_candidate_count": len(fact_candidates),
            "private_only_fact_candidate_count": private_only_count,
        },
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        required=True,
        type=Path,
        action="append",
        help="a batch-runner --out-dir/results directory; repeat to merge multiple sources "
        "(e.g. X and ChatGPT) without combining their files by hand, since both sources "
        "reuse the same batch_NNNN.result.json numbering and a manual copy would collide",
    )
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if any(not results_dir.is_dir() for results_dir in args.results_dir):
        print("error: results directory not found", file=sys.stderr)
        return 2

    batches = []
    for results_dir in args.results_dir:
        batches.extend(load_result_batches(results_dir))
    review = build_review(batches)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(review["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
