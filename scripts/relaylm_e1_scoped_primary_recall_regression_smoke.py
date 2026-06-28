"""Regression smoke for E1 scoped Primary MEM recall discovery."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from _relaylm_phase_i3_test_support import form_primary_memory, require
from relaylm import relaymem_primary_recall_runtime as primary_recall_runtime
from relaylm.relaymem_primary_recall import (
    apply_relaymem_primary_recall_scope,
    resolve_relaymem_character_store_root,
)
from relaylm.relaymem_retrieval import (
    _term_hints,
    build_relaymem_retrieval_dry_run_artifact,
)
from relaylm.relaymem_store import (
    build_relaymem_snippet_evidence_dry_run,
    build_relaymem_store_diagnostics,
)

NAMESPACE = "character/default"
CHARACTER_ID = "default"
SUMMARY = (
    "評価用に覚えておいて。私は朝の集中作業では、"
    "浅煎りのエチオピアコーヒーを飲むのが一番落ち着きます。"
)
QUERY = "私が朝の集中作業で落ち着く飲み物って何だっけ？"
ENGLISH_STOPWORD_QUERY = "do we need to ship today?"


def scene_artifact() -> dict[str, Any]:
    return {
        "scene_state": {
            "schema_version": "relayscn.scene_state.v0",
            "scene_type": "casual_chat",
            "confidence": 0.95,
            "stability": 0.95,
            "signals": ["explicit_home_memory_evaluation"],
        },
        "scene_policy": {
            "relaymem_retrieval_scope": "project_context",
        },
        "persistence_block": False,
        "persistence_block_reasons": [],
    }


def write_control_files(root: Path) -> None:
    mem_root = root / "memory" / "mem"
    mem_root.mkdir(parents=True, exist_ok=True)
    (mem_root / "index.md").write_text("# index\n", encoding="utf-8")
    (mem_root / "log.md").write_text("# log\n", encoding="utf-8")


def assert_disabled_diagnostics_bypass_effective_root(operator_root: Path) -> None:
    original = primary_recall_runtime._effective_read_root

    def forbidden_effective_root(root_path: str | None) -> str | None:
        raise AssertionError(("disabled diagnostics resolved root", root_path))

    try:
        primary_recall_runtime._effective_read_root = forbidden_effective_root
        diagnostics = build_relaymem_store_diagnostics(
            root_path=str(operator_root),
            store_enabled=False,
            retrieval_dry_run_only=True,
        )
    finally:
        primary_recall_runtime._effective_read_root = original

    require(diagnostics.get("fallback_reason") == "memory_store_disabled", diagnostics)
    require(diagnostics.get("root_path") == str(operator_root), diagnostics)


def assert_snippet_disabled_bypass_effective_root(operator_root: Path) -> None:
    original = primary_recall_runtime._effective_read_root

    def forbidden_effective_root(root_path: str | None) -> str | None:
        raise AssertionError(("disabled snippets resolved root", root_path))

    try:
        primary_recall_runtime._effective_read_root = forbidden_effective_root
        evidence = build_relaymem_snippet_evidence_dry_run(
            root_path=str(operator_root),
            selected_mem_candidates=[{"path": "memory/mem/primary/example.md"}],
            snippet_extraction_enabled=False,
            snippet_dry_run_only=True,
            max_snippet_chars=256,
            max_snippet_candidates=3,
        )
    finally:
        primary_recall_runtime._effective_read_root = original

    require(evidence.get("snippet_extraction_enabled") is False, evidence)
    require(evidence.get("root_path") == str(operator_root), evidence)
    require(evidence.get("snippet_candidates") == [], evidence)
    envelope = evidence.get("evidence_envelope")
    require(isinstance(envelope, Mapping), evidence)
    require(envelope.get("snippets") == [], envelope)
    require(envelope.get("blocked") == [], envelope)


def assert_character_root_scan_cap_falls_back(operator_root: Path) -> None:
    characters = operator_root / "characters"
    characters.mkdir(parents=True, exist_ok=True)
    for index in range(primary_recall_runtime._MAX_CHARACTER_ROOT_SCAN + 1):
        (characters / f"empty-{index:03d}").mkdir()
    write_control_files(characters / "zz-valid-after-cap")

    resolved_root = primary_recall_runtime._effective_read_root(str(operator_root))
    require(resolved_root == str(operator_root), resolved_root)


def assert_no_reason(value: Mapping[str, Any], reason_id: str) -> None:
    projection = value.get("primary_recall_projection")
    runtime = value.get("primary_recall_runtime")
    for payload in (projection, runtime):
        require(isinstance(payload, Mapping), payload)
        reasons = payload.get("blocked_reason_ids")
        require(isinstance(reasons, Sequence) and not isinstance(reasons, str), payload)
        require(reason_id not in reasons, (reason_id, reasons))


def assert_projection_content_free(value: Mapping[str, Any]) -> None:
    projection = value.get("primary_recall_projection")
    require(isinstance(projection, Mapping), projection)
    text = repr(projection)
    for forbidden in (
        SUMMARY,
        NAMESPACE,
        "浅煎りのエチオピアコーヒー",
        "memory/mem/",
        "page_digest",
        "lineage_fingerprint",
        "idempotency_key",
    ):
        require(forbidden not in text, (forbidden, text))


def primary_keyword_candidate(value: Mapping[str, Any]) -> Mapping[str, Any]:
    raw_candidates = value.get("selected_mem_candidates")
    require(
        isinstance(raw_candidates, Sequence) and not isinstance(raw_candidates, str),
        value,
    )
    for candidate in raw_candidates:
        if not isinstance(candidate, Mapping):
            continue
        if (
            candidate.get("memory_layer") == "primary"
            and candidate.get("reason") == "keyword_match"
        ):
            return candidate
    raise AssertionError(value)


def assert_no_primary_keyword_candidate(value: Mapping[str, Any]) -> None:
    raw_candidates = value.get("selected_mem_candidates")
    require(
        isinstance(raw_candidates, Sequence) and not isinstance(raw_candidates, str),
        value,
    )
    for candidate in raw_candidates:
        if not isinstance(candidate, Mapping):
            continue
        require(
            not (
                candidate.get("memory_layer") == "primary"
                and candidate.get("reason") == "keyword_match"
            ),
            candidate,
        )


def main() -> None:
    english_terms = _term_hints(ENGLISH_STOPWORD_QUERY)
    require("do" not in english_terms, english_terms)
    require("we" not in english_terms, english_terms)
    require("to" not in english_terms, english_terms)
    require("ship" in english_terms, english_terms)
    require("today" in english_terms, english_terms)

    with tempfile.TemporaryDirectory() as directory:
        disabled_root = Path(directory) / "disabled-root"
        write_control_files(disabled_root / "characters" / "only-character")
        assert_disabled_diagnostics_bypass_effective_root(disabled_root)
        assert_snippet_disabled_bypass_effective_root(disabled_root)

    with tempfile.TemporaryDirectory() as directory:
        capped_root = Path(directory) / "capped-root"
        assert_character_root_scan_cap_falls_back(capped_root)

    with tempfile.TemporaryDirectory() as directory:
        operator_root = Path(directory) / "memory-root"
        operator_root.mkdir()
        scoped_root_value = resolve_relaymem_character_store_root(
            str(operator_root), CHARACTER_ID
        )
        require(isinstance(scoped_root_value, str) and scoped_root_value, scoped_root_value)
        scoped_root = Path(scoped_root_value)

        # Slash-containing durable queue namespaces must be valid recall scopes.
        slash_namespace_probe = apply_relaymem_primary_recall_scope(
            {
                "artifact_version": "relaymem_retrieval.v0",
                "snippet_apply_decision": "dry_run_only",
                "scene_type": "casual_chat",
                "retrieval_scope": "project_context",
                "selected_mem_candidates": [],
            },
            scoped_store_root=str(scoped_root),
            expected_namespace=NAMESPACE,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
            chars_per_token=4,
        )
        assert_no_reason(slash_namespace_probe, "memory_namespace_invalid")
        projection = slash_namespace_probe["primary_recall_projection"]
        require(projection.get("namespace_scope_valid") is True, projection)

        form_primary_memory(
            scoped_root,
            namespace=NAMESPACE,
            candidate_id="e1-scoped-primary-recall-coffee",
            title="朝の集中作業の飲み物",
            summary=SUMMARY,
        )

        diagnostics = build_relaymem_store_diagnostics(
            root_path=str(operator_root),
            store_enabled=True,
            retrieval_dry_run_only=True,
        )
        require(diagnostics.get("index_present") is True, diagnostics)
        require(diagnostics.get("log_present") is True, diagnostics)
        page_paths = diagnostics.get("page_paths")
        require(isinstance(page_paths, Sequence) and not isinstance(page_paths, str), diagnostics)
        require(
            any(
                isinstance(path, str)
                and path.startswith("memory/mem/primary/")
                and path.endswith(".md")
                for path in page_paths
            ),
            diagnostics,
        )

        english_retrieval = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact=scene_artifact(),
            relayref_artifact=None,
            messages=[{"role": "user", "content": ENGLISH_STOPWORD_QUERY}],
            token_budget=512,
            store_diagnostics=diagnostics,
            max_candidates=3,
            ctx_block_apply_enabled=False,
            snippet_extraction_enabled=True,
            snippet_dry_run_only=True,
            snippet_apply_enabled=False,
            snippet_budget=512,
            max_snippet_chars=512,
            max_snippet_candidates=3,
        )
        assert_no_primary_keyword_candidate(english_retrieval)

        retrieval = build_relaymem_retrieval_dry_run_artifact(
            relayscn_scene_policy_artifact=scene_artifact(),
            relayref_artifact=None,
            messages=[{"role": "user", "content": QUERY}],
            token_budget=512,
            store_diagnostics=diagnostics,
            max_candidates=3,
            ctx_block_apply_enabled=False,
            snippet_extraction_enabled=True,
            snippet_dry_run_only=True,
            snippet_apply_enabled=False,
            snippet_budget=512,
            max_snippet_chars=512,
            max_snippet_candidates=3,
        )
        primary_keyword_candidate(retrieval)

        scoped = apply_relaymem_primary_recall_scope(
            retrieval,
            scoped_store_root=str(scoped_root),
            expected_namespace=NAMESPACE,
            max_snippet_chars=512,
            max_snippet_candidates=3,
            snippet_budget=512,
            chars_per_token=4,
        )
        runtime = scoped.get("primary_recall_runtime")
        projection = scoped.get("primary_recall_projection")
        require(isinstance(runtime, Mapping), scoped)
        require(isinstance(projection, Mapping), scoped)
        require(runtime.get("selected_count") == 1, runtime)
        require(projection.get("selected_count") == 1, projection)
        require(projection.get("namespace_scope_valid") is True, projection)
        assert_no_reason(scoped, "memory_namespace_invalid")
        assert_no_reason(scoped, "primary_recall_no_scoped_match")
        selected = runtime.get("selected_memories")
        require(isinstance(selected, Sequence) and len(selected) == 1, runtime)
        selected_summary = selected[0].get("summary") if isinstance(selected[0], Mapping) else None
        require(isinstance(selected_summary, str), selected)
        require("浅煎りのエチオピアコーヒー" in selected_summary, selected_summary)
        assert_projection_content_free(scoped)

    print("relaylm_e1_scoped_primary_recall_regression_smoke: ok")


if __name__ == "__main__":
    main()
