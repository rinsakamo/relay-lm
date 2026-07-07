#!/usr/bin/env python3
"""Smoke test for Twin Extraction merge provenance validation.

Verifies that malformed fact-candidate provenance is dropped before review
artifact creation, so reviewers never see provenance-empty fact candidates.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

import relaylm_twin_extraction_merge as merge


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _capture_stdout(func, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = func(*args, **kwargs)
    return result, buf.getvalue()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        (results_dir / "batch_0001.result.json").write_text(
            json.dumps(
                {
                    "style_observations": [],
                    "fact_candidates": [
                        {
                            "statement": "CANARY_VALID_PROVENANCE survives",
                            "type": "knowledge",
                            "provenance": "x_post",
                            "evidence_ids": ["1001"],
                            "sensitivity": "general",
                        },
                        {
                            "statement": "CANARY_LIST_PROVENANCE survives",
                            "type": "knowledge",
                            "provenance": ["x_post", "chatgpt_reconstructed"],
                            "evidence_ids": ["1002"],
                            "sensitivity": "general",
                        },
                        {
                            "statement": "CANARY_MISSING_PROVENANCE must be dropped",
                            "type": "knowledge",
                            "evidence_ids": ["1003"],
                            "sensitivity": "general",
                        },
                        {
                            "statement": "CANARY_EMPTY_PROVENANCE must be dropped",
                            "type": "knowledge",
                            "provenance": [],
                            "evidence_ids": ["1004"],
                            "sensitivity": "general",
                        },
                        {
                            "statement": "CANARY_NESTED_PROVENANCE must be dropped",
                            "type": "knowledge",
                            "provenance": {"source": "x_post"},
                            "evidence_ids": ["1005"],
                            "sensitivity": "general",
                        },
                        {
                            "statement": "CANARY_BOOL_PROVENANCE must be dropped",
                            "type": "knowledge",
                            "provenance": True,
                            "evidence_ids": ["1006"],
                            "sensitivity": "general",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        out_path = tmp_path / "review.json"
        exit_code, stdout = _capture_stdout(
            merge.main, ["--results-dir", str(results_dir), "--out", str(out_path)]
        )
        require(exit_code == 0, stdout)
        summary = json.loads(stdout.strip())
        require(summary["fact_candidate_count"] == 2, summary)

        review = json.loads(out_path.read_text(encoding="utf-8"))
        facts = {fact["statement"]: fact for fact in review["fact_candidates"]}
        require("CANARY_VALID_PROVENANCE survives" in facts, facts)
        require(facts["CANARY_VALID_PROVENANCE survives"]["provenance"] == ["x_post"], facts)
        require("CANARY_LIST_PROVENANCE survives" in facts, facts)
        require(
            facts["CANARY_LIST_PROVENANCE survives"]["provenance"]
            == ["chatgpt_reconstructed", "x_post"],
            facts,
        )
        for dropped in (
            "CANARY_MISSING_PROVENANCE must be dropped",
            "CANARY_EMPTY_PROVENANCE must be dropped",
            "CANARY_NESTED_PROVENANCE must be dropped",
            "CANARY_BOOL_PROVENANCE must be dropped",
        ):
            require(dropped not in facts, facts)
        require(all(fact["provenance"] for fact in review["fact_candidates"]), review)

    print("RelayLM Twin Extraction provenance smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
