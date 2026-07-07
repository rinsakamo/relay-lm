#!/usr/bin/env python3
"""Smoke tests for the Twin Extraction offline tooling.

No LLM, network, or real archive is required. Fixtures are small and
entirely fictional, generated inline below (fake tweets.js / conversations
.json content). Covers: X prefix stripping / RT exclusion / quote-RT
trimming / date filtering, ChatGPT user/context separation, batch
splitting, the batch runner's --dry-run path and fail-closed JSON-parse
handling, and merge exact-match/private_only/no-fuzzy-merge behavior.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

import relaylm_twin_extraction_batch_runner as batch_runner
import relaylm_twin_extraction_common as common
import relaylm_twin_extraction_merge as merge
import relaylm_twin_extraction_preprocess as preprocess


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


X_FIXTURE_TWEETS = [
    {
        "tweet": {
            "id_str": "1001",
            "created_at": "Mon Jan 02 10:00:00 +0000 2023",
            "full_text": "CANARY_POST_ONE thinking about hospital operations today",
        }
    },
    {
        "tweet": {
            "id_str": "1002",
            "created_at": "Tue Jan 03 10:00:00 +0000 2023",
            "full_text": "RT @otheruser: CANARY_RT_BODY should never appear in output",
        }
    },
    {
        "tweet": {
            "id_str": "1003",
            "created_at": "Wed Feb 01 10:00:00 +0000 2023",
            "full_text": "CANARY_QUOTE_COMMENT interesting point on this https://t.co/abc123XYZ",
            "is_quote_status": True,
        }
    },
    {
        "tweet": {
            "id_str": "1004",
            "created_at": "Thu Feb 02 10:00:00 +0000 2023",
            "full_text": "CANARY_REPLY_BODY responding to a thread",
            "in_reply_to_status_id_str": "999000111",
        }
    },
    {
        "tweet": {
            "id_str": "1005",
            "created_at": "Fri Dec 30 10:00:00 +0000 2022",
            "full_text": "CANARY_OUT_OF_RANGE this should be filtered by date",
        }
    },
    {"tweet": {"id_str": "1006", "created_at": "Sat Mar 04 10:00:00 +0000 2023", "full_text": "CANARY_POST_SIX more thoughts"}},
    {"tweet": {"id_str": "1007", "created_at": "Sun Mar 05 10:00:00 +0000 2023", "full_text": "CANARY_POST_SEVEN more thoughts"}},
    {"tweet": {"id_str": "1008", "created_at": "Mon Mar 06 10:00:00 +0000 2023", "full_text": "CANARY_POST_EIGHT more thoughts"}},
    {"tweet": {"id_str": "1009", "created_at": "Tue Mar 07 10:00:00 +0000 2023", "full_text": "CANARY_POST_NINE more thoughts"}},
    {"tweet": {"id_str": "1010", "created_at": "Wed Mar 08 10:00:00 +0000 2023", "full_text": "CANARY_POST_TEN more thoughts"}},
]


def _write_x_fixture(path: Path) -> None:
    body = json.dumps(X_FIXTURE_TWEETS, ensure_ascii=False)
    path.write_text(f"window.YTD.tweets.part0 = {body};", encoding="utf-8")


CHATGPT_FIXTURE = [
    {
        "conversation_id": "conv-a",
        "create_time": 1675209600.0,  # 2023-02-01
        "mapping": {
            "n1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["CANARY_CHATGPT_USER_ONE tell me about scheduling"]},
                    "create_time": 1675209600.0,
                }
            },
            "n2": {
                "message": {
                    "author": {"role": "assistant"},
                    "content": {"content_type": "text", "parts": ["CANARY_ASSISTANT_BODY here is context only"]},
                    "create_time": 1675209660.0,
                }
            },
            "n3": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["CANARY_CHATGPT_USER_TWO a followup question"]},
                    "create_time": 1675209720.0,
                }
            },
        },
    },
    {
        "conversation_id": "conv-b",
        "create_time": 1683000000.0,
        "mapping": {
            "n1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["CANARY_CHATGPT_USER_THREE minimal message"]},
                    "create_time": 1683000000.0,
                }
            }
        },
    },
]


def _write_chatgpt_fixture(path: Path) -> None:
    path.write_text(json.dumps(CHATGPT_FIXTURE, ensure_ascii=False), encoding="utf-8")


def _capture_stdout(func, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = func(*args, **kwargs)
    return result, buf.getvalue()


def check_x_preprocess(tmp_path: Path) -> list[Path]:
    input_path = tmp_path / "tweets.js"
    out_dir = tmp_path / "x_batches"
    _write_x_fixture(input_path)

    exit_code, stdout = _capture_stdout(
        preprocess.main,
        [
            "--source",
            "x",
            "--input",
            str(input_path),
            "--out-dir",
            str(out_dir),
            "--since",
            "2023-01",
            "--until",
            "2023-03",
            "--batch-size",
            "3",
        ],
    )
    require(exit_code == 0, stdout)
    summary = json.loads(stdout.strip())
    require(summary["total_seen"] == 10, summary)
    require(summary["kept"] == 8, summary)
    require(summary["excluded_retweet"] == 1, summary)
    require(summary["excluded_date_filtered"] == 1, summary)
    require(summary["batch_count"] == 3, summary)
    require("CANARY" not in stdout, "preprocess summary leaked post body")

    batch_paths = sorted(out_dir.glob("batch_*.jsonl"))
    require(len(batch_paths) == 3, batch_paths)

    all_records = []
    for path in batch_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            all_records.append(json.loads(line))
    require(len(all_records) == 8, all_records)

    by_id = {record["id"]: record for record in all_records}
    require("1002" not in by_id, "retweet must be excluded")
    require("1005" not in by_id, "out-of-range post must be excluded")
    require(by_id["1003"]["text"] == "CANARY_QUOTE_COMMENT interesting point on this", by_id["1003"])
    require("https://t.co" not in by_id["1003"]["text"], by_id["1003"])
    require(by_id["1004"]["in_reply_to_status_id"] == "999000111", by_id["1004"])
    require("in_reply_to_status_id" not in by_id["1001"], by_id["1001"])

    return batch_paths


def check_preprocess_rerun_clears_stale_batches(tmp_path: Path) -> None:
    input_path = tmp_path / "tweets_rerun.js"
    out_dir = tmp_path / "x_rerun_batches"
    _write_x_fixture(input_path)

    exit_code, stdout = _capture_stdout(
        preprocess.main,
        [
            "--source", "x", "--input", str(input_path), "--out-dir", str(out_dir),
            "--since", "2023-01", "--until", "2023-03", "--batch-size", "3",
        ],
    )
    require(exit_code == 0, stdout)
    require(sorted(p.name for p in out_dir.glob("batch_*.jsonl")) == ["batch_0001.jsonl", "batch_0002.jsonl", "batch_0003.jsonl"], list(out_dir.glob("batch_*.jsonl")))

    # Rerun into the same --out-dir with a narrower date range that produces
    # fewer batches. Stale higher-numbered batch files from the first run
    # must not survive, since batch discovery globs every batch_*.jsonl file.
    exit_code, stdout = _capture_stdout(
        preprocess.main,
        [
            "--source", "x", "--input", str(input_path), "--out-dir", str(out_dir),
            "--since", "2023-01", "--until", "2023-01", "--batch-size", "3",
        ],
    )
    require(exit_code == 0, stdout)
    rerun_summary = json.loads(stdout.strip())
    require(rerun_summary["kept"] == 1, rerun_summary)
    require(rerun_summary["batch_count"] == 1, rerun_summary)
    require(sorted(p.name for p in out_dir.glob("batch_*.jsonl")) == ["batch_0001.jsonl"], list(out_dir.glob("batch_*.jsonl")))


def check_chatgpt_preprocess(tmp_path: Path) -> None:
    input_path = tmp_path / "conversations.json"
    out_dir = tmp_path / "chatgpt_batches"
    _write_chatgpt_fixture(input_path)

    exit_code, stdout = _capture_stdout(
        preprocess.main,
        [
            "--source",
            "chatgpt",
            "--input",
            str(input_path),
            "--out-dir",
            str(out_dir),
            "--batch-size",
            "1",
        ],
    )
    require(exit_code == 0, stdout)
    summary = json.loads(stdout.strip())
    require(summary["total_seen"] == 2, summary)
    require(summary["kept"] == 2, summary)
    require(summary["batch_count"] == 2, summary)
    require("CANARY" not in stdout, "preprocess summary leaked utterance body")

    batch_paths = sorted(out_dir.glob("batch_*.jsonl"))
    require(len(batch_paths) == 2, batch_paths)

    all_records = []
    for path in batch_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            all_records.append(json.loads(line))

    conv_a_records = [r for r in all_records if r["conversation_id"] == "conv-a"]
    require(len(conv_a_records) == 3, conv_a_records)
    require([r["role"] for r in conv_a_records] == ["user", "context", "user"], conv_a_records)
    require(conv_a_records[0]["text"] == "CANARY_CHATGPT_USER_ONE tell me about scheduling", conv_a_records)
    require(conv_a_records[1]["role"] == "context", conv_a_records)
    require(conv_a_records[1]["text"] == "CANARY_ASSISTANT_BODY here is context only", conv_a_records)

    conv_b_records = [r for r in all_records if r["conversation_id"] == "conv-b"]
    require(len(conv_b_records) == 1 and conv_b_records[0]["role"] == "user", conv_b_records)


def check_batch_runner_dry_run(tmp_path: Path, batch_paths: list[Path]) -> None:
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("SYSTEM PROMPT PLACEHOLDER", encoding="utf-8")
    out_dir = tmp_path / "runner_dry_run_out"

    exit_code, stdout = _capture_stdout(
        batch_runner.main,
        [
            "--model",
            "fake-model",
            "--prompt-file",
            str(prompt_path),
            "--batch-dir",
            str(batch_paths[0].parent),
            "--out-dir",
            str(out_dir),
            "--dry-run",
        ],
    )
    require(exit_code == 0, stdout)
    summary = json.loads(stdout.strip())
    require(summary["mode"] == "dry_run", summary)
    require(summary["batch_count"] == len(batch_paths), summary)
    require(summary["total_records"] == 8, summary)
    require(summary["total_payload_bytes"] > 0, summary)
    require("CANARY" not in stdout, "dry-run summary leaked post body")
    require(not out_dir.exists(), "dry-run must not create results/failed directories")


def check_run_batch_success_and_fail_closed() -> None:
    good_payload_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "style_observations": [
                                {"category": "tone", "description": "uses short declarative sentences", "evidence_ids": ["1001"], "strength": "low"}
                            ],
                            "fact_candidates": [],
                        }
                    )
                }
            }
        ]
    }

    def fake_completion_ok(_payload: dict) -> dict:
        return good_payload_response

    outcome = batch_runner.run_batch(fake_completion_ok, "fake-model", "prompt", [{"id": "1"}], retries=1)
    require(outcome["status"] == "ok", outcome)
    require(outcome["attempts"] == 1, outcome)
    require(outcome["extraction"]["style_observations"][0]["category"] == "tone", outcome)

    attempts_seen = []

    def fake_completion_malformed(_payload: dict) -> dict:
        attempts_seen.append(1)
        return {"choices": [{"message": {"content": "not-json-at-all"}}]}

    outcome = batch_runner.run_batch(fake_completion_malformed, "fake-model", "prompt", [{"id": "1"}], retries=2)
    require(outcome["status"] == "failed", outcome)
    require(outcome["attempts"] == 3, outcome)
    require(len(attempts_seen) == 3, attempts_seen)


def check_batch_runner_main_fail_closed(tmp_path: Path, batch_paths: list[Path]) -> None:
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("SYSTEM PROMPT PLACEHOLDER", encoding="utf-8")
    out_dir = tmp_path / "runner_live_out"

    def fake_call(_base_url: str, _payload: dict) -> dict:
        return {"choices": [{"message": {"content": "not-json"}}]}

    original = batch_runner.call_chat_completions
    batch_runner.call_chat_completions = fake_call
    try:
        exit_code, stdout = _capture_stdout(
            batch_runner.main,
            [
                "--model",
                "fake-model",
                "--prompt-file",
                str(prompt_path),
                "--batch-dir",
                str(batch_paths[0].parent),
                "--out-dir",
                str(out_dir),
                "--retries",
                "0",
                "--max-batches",
                "1",
            ],
        )
    finally:
        batch_runner.call_chat_completions = original

    require(exit_code == 0, stdout)
    require("CANARY" not in stdout, "batch runner progress log leaked post body")
    failed_files = list((out_dir / "failed").glob("*.failed.json"))
    require(len(failed_files) == 1, failed_files)
    failed_record = json.loads(failed_files[0].read_text(encoding="utf-8"))
    require(failed_record["error_type"] == "JSONDecodeError", failed_record)
    require(len(list((out_dir / "results").glob("*.result.json"))) == 0, "fail-closed batch must not produce a result file")


def check_batch_runner_rerun_clears_stale_marker(tmp_path: Path, batch_paths: list[Path]) -> None:
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("SYSTEM PROMPT PLACEHOLDER", encoding="utf-8")
    out_dir = tmp_path / "runner_rerun_out"
    target_batch = batch_paths[0]

    good_content = json.dumps({"style_observations": [], "fact_candidates": []})

    def fake_call_ok(_base_url: str, _payload: dict) -> dict:
        return {"choices": [{"message": {"content": good_content}}]}

    def fake_call_bad(_base_url: str, _payload: dict) -> dict:
        return {"choices": [{"message": {"content": "not-json"}}]}

    original = batch_runner.call_chat_completions
    try:
        batch_runner.call_chat_completions = fake_call_ok
        exit_code, _stdout = _capture_stdout(
            batch_runner.main,
            [
                "--model", "fake-model", "--prompt-file", str(prompt_path),
                "--batch-dir", str(target_batch.parent), "--out-dir", str(out_dir),
                "--retries", "0", "--max-batches", "1",
            ],
        )
        require(exit_code == 0, "first (success) run must succeed")
        result_path = out_dir / "results" / f"{target_batch.stem}.result.json"
        require(result_path.is_file(), "first run must produce a result file")

        # Rerun the same batch into the same --out-dir but now fail. The
        # stale success result from the previous run must not survive,
        # since merge reads every *.result.json it finds under results/.
        batch_runner.call_chat_completions = fake_call_bad
        exit_code, _stdout = _capture_stdout(
            batch_runner.main,
            [
                "--model", "fake-model", "--prompt-file", str(prompt_path),
                "--batch-dir", str(target_batch.parent), "--out-dir", str(out_dir),
                "--retries", "0", "--max-batches", "1",
            ],
        )
        require(exit_code == 0, "second (failing) run must still complete")
        require(not result_path.is_file(), "stale prior-success result must be removed on a failing rerun")
        require((out_dir / "failed" / f"{target_batch.stem}.failed.json").is_file(), "failing rerun must record a failed marker")

        # Rerun once more and succeed again; the stale failed marker must
        # not survive either.
        batch_runner.call_chat_completions = fake_call_ok
        exit_code, _stdout = _capture_stdout(
            batch_runner.main,
            [
                "--model", "fake-model", "--prompt-file", str(prompt_path),
                "--batch-dir", str(target_batch.parent), "--out-dir", str(out_dir),
                "--retries", "0", "--max-batches", "1",
            ],
        )
        require(exit_code == 0, "third (success) run must succeed")
        require(result_path.is_file(), "third run must produce a result file")
        require(not (out_dir / "failed" / f"{target_batch.stem}.failed.json").is_file(), "stale failed marker must be removed on a succeeding rerun")
    finally:
        batch_runner.call_chat_completions = original


def check_merge(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    (results_dir / "batch_0001.result.json").write_text(
        json.dumps(
            {
                "style_observations": [
                    {"category": "tone", "description": "CANARY_DESC_A uses short sentences", "evidence_ids": ["1001"], "strength": "low"}
                ],
                "fact_candidates": [
                    {
                        "statement": "CANARY_FACT_ONE works in healthcare operations",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": ["1001"],
                        "time_context": "2023-01",
                        "sensitivity": "general",
                    },
                    {
                        "statement": "CANARY_FACT_FOUR statement",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": ["1006"],
                        "sensitivity": "general",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (results_dir / "batch_0002.result.json").write_text(
        json.dumps(
            {
                "style_observations": [
                    {"category": "tone", "description": "CANARY_DESC_A uses short sentences", "evidence_ids": ["1002"], "strength": "low"},
                    {"category": "tone", "description": "CANARY_DESC_SCALAR must be dropped", "evidence_ids": "1008", "strength": "low"},
                ],
                "fact_candidates": [
                    {
                        "statement": "CANARY_FACT_ONE works in healthcare operations",
                        "type": "knowledge",
                        "provenance": "chatgpt_reconstructed",
                        "evidence_ids": ["conv-a"],
                        "time_context": "2023-02",
                        "sensitivity": "private_only",
                    },
                    {
                        "statement": "CANARY_FACT_SCALAR_EVIDENCE must be dropped not corrupted",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": "1009",
                        "sensitivity": "general",
                    },
                    {
                        "statement": "CANARY_FACT_TWO completely different statement text",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": ["1003"],
                        "sensitivity": "general",
                    },
                    {
                        "statement": "CANARY_FACT_THREE missing sensitivity field",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": ["1004"],
                    },
                    {
                        "statement": "CANARY_FACT_FOUR statement.",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": ["1007"],
                        "sensitivity": "general",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (results_dir / "batch_0003.result.json").write_text("{not valid json", encoding="utf-8")

    out_path = tmp_path / "twin_extraction_review.json"
    exit_code, stdout = _capture_stdout(merge.main, ["--results-dir", str(results_dir), "--out", str(out_path)])
    require(exit_code == 0, stdout)
    require("CANARY" not in stdout, "merge summary leaked material body")

    summary = json.loads(stdout.strip())
    require(summary["batches_merged"] == 2, summary)

    review = json.loads(out_path.read_text(encoding="utf-8"))
    style = review["style_observations"]
    require(len(style) == 2, "style observations must never be auto-merged even if identical")
    require({obs["strength"] for obs in style} == {"low"}, style)
    require(
        "CANARY_DESC_SCALAR must be dropped" not in {obs["description"] for obs in style},
        "a scalar (non-list) evidence_ids must drop the observation, not corrupt it into single characters",
    )

    facts = {fact["statement"]: fact for fact in review["fact_candidates"]}
    require(len(facts) == 5, facts)
    require(
        "CANARY_FACT_SCALAR_EVIDENCE must be dropped not corrupted" not in facts,
        "a scalar (non-list) evidence_ids must drop the candidate, not corrupt it into single characters",
    )

    fact_one = facts["CANARY_FACT_ONE works in healthcare operations"]
    require(sorted(fact_one["evidence_ids"]) == ["1001", "conv-a"], fact_one)
    require(sorted(fact_one["provenance"]) == ["chatgpt_reconstructed", "x_post"], fact_one)
    require(sorted(fact_one["time_contexts"]) == ["2023-01", "2023-02"], fact_one)
    require(fact_one["sensitivity"] == "private_only", fact_one)

    fact_two = facts["CANARY_FACT_TWO completely different statement text"]
    require(fact_two["sensitivity"] == "general", fact_two)
    require(fact_two["time_contexts"] == ["unknown"], fact_two)

    fact_three = facts["CANARY_FACT_THREE missing sensitivity field"]
    require(fact_three["sensitivity"] == "private_only", "missing sensitivity must fail-closed to private_only")

    fact_four_a = facts["CANARY_FACT_FOUR statement"]
    fact_four_b = facts["CANARY_FACT_FOUR statement."]
    require(fact_four_a["evidence_ids"] == ["1006"], fact_four_a)
    require(fact_four_b["evidence_ids"] == ["1007"], fact_four_b)


def check_merge_multiple_results_dirs_do_not_collide(tmp_path: Path) -> None:
    # X and ChatGPT batch-runner output both use batch_0001.result.json,
    # batch_0002.result.json, ... numbering. Merging two sources must not
    # require copying them into one directory first (which would silently
    # overwrite one source's files with the other's); --results-dir must be
    # repeatable instead.
    x_results_dir = tmp_path / "collision_x_results"
    chatgpt_results_dir = tmp_path / "collision_chatgpt_results"
    x_results_dir.mkdir()
    chatgpt_results_dir.mkdir()

    (x_results_dir / "batch_0001.result.json").write_text(
        json.dumps(
            {
                "style_observations": [],
                "fact_candidates": [
                    {
                        "statement": "CANARY_COLLISION_X_FACT from the x source",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": ["1001"],
                        "sensitivity": "general",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (chatgpt_results_dir / "batch_0001.result.json").write_text(
        json.dumps(
            {
                "style_observations": [],
                "fact_candidates": [
                    {
                        "statement": "CANARY_COLLISION_CHATGPT_FACT from the chatgpt source",
                        "type": "knowledge",
                        "provenance": "chatgpt_reconstructed",
                        "evidence_ids": ["conv-a"],
                        "sensitivity": "general",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    out_path = tmp_path / "collision_review.json"
    exit_code, stdout = _capture_stdout(
        merge.main,
        ["--results-dir", str(x_results_dir), "--results-dir", str(chatgpt_results_dir), "--out", str(out_path)],
    )
    require(exit_code == 0, stdout)
    summary = json.loads(stdout.strip())
    require(summary["batches_merged"] == 2, summary)

    review = json.loads(out_path.read_text(encoding="utf-8"))
    statements = {fact["statement"] for fact in review["fact_candidates"]}
    require("CANARY_COLLISION_X_FACT from the x source" in statements, statements)
    require("CANARY_COLLISION_CHATGPT_FACT from the chatgpt source" in statements, statements)


def check_truncated_json_array_fails_closed(tmp_path: Path) -> None:
    # A truncated top-level array (EOF before the closing bracket) must
    # fail closed, not silently look like a clean end-of-array.
    truncated = io.StringIO('[{"tweet": {"id_str": "1", "created_at": "Mon Jan 02 10:00:00 +0000 2023", "full_text": "hi"}}')
    try:
        list(common.iter_json_array_stream(truncated, chunk_size=8))
        raise AssertionError("truncated JSON array must raise TwinExtractionInputError")
    except common.TwinExtractionInputError:
        pass

    input_path = tmp_path / "truncated_tweets.js"
    out_dir = tmp_path / "truncated_out"
    input_path.write_text(
        'window.YTD.tweets.part0 = [{"tweet": {"id_str": "1", "created_at": "Mon Jan 02 10:00:00 +0000 2023", '
        '"full_text": "CANARY_TRUNCATED_BODY"}}',
        encoding="utf-8",
    )
    # The truncated array fails the in-memory json.loads parse (unterminated
    # array), which load_json_array() already falls back from to the
    # streaming iterator regardless of file size -- exercising the same
    # fixed code path end to end through the preprocess CLI.
    exit_code, stdout = _capture_stdout(
        preprocess.main,
        ["--source", "x", "--input", str(input_path), "--out-dir", str(out_dir)],
    )
    require(exit_code != 0, "truncated archive input must fail closed, not exit 0")
    require(not out_dir.exists(), "a failed preprocess run must not write partial batches")


def check_missing_delimiter_json_array_fails_closed() -> None:
    # A missing ',' between elements (e.g. [{...}{...}]) must fail closed
    # instead of silently decoding both elements as if the input were
    # valid JSON.
    missing_comma = io.StringIO('[{"a": 1}{"b": 2}]')
    try:
        list(common.iter_json_array_stream(missing_comma, chunk_size=4))
        raise AssertionError("a missing ',' between array elements must raise TwinExtractionInputError")
    except common.TwinExtractionInputError:
        pass

    # A trailing comma before ']' is also invalid JSON and must fail closed.
    trailing_comma = io.StringIO('[{"a": 1},]')
    try:
        list(common.iter_json_array_stream(trailing_comma, chunk_size=4))
        raise AssertionError("a trailing comma before ']' must raise TwinExtractionInputError")
    except common.TwinExtractionInputError:
        pass

    # Well-formed arrays (with and without inter-chunk boundaries splitting
    # the delimiter) must still decode cleanly.
    for chunk_size in (4, 1024):
        well_formed = io.StringIO('[{"a": 1}, {"b": 2}, {"c": 3}]')
        require(
            list(common.iter_json_array_stream(well_formed, chunk_size=chunk_size))
            == [{"a": 1}, {"b": 2}, {"c": 3}],
            f"well-formed array must still decode cleanly at chunk_size={chunk_size}",
        )
        empty_array = io.StringIO("[]")
        require(list(common.iter_json_array_stream(empty_array, chunk_size=chunk_size)) == [], "empty array must decode to no elements")


def check_merge_rejects_non_scalar_evidence_ids(tmp_path: Path) -> None:
    results_dir = tmp_path / "nonscalar_results"
    results_dir.mkdir()
    (results_dir / "batch_0001.result.json").write_text(
        json.dumps(
            {
                "style_observations": [
                    {
                        "category": "tone",
                        "description": "CANARY_NONSCALAR_STYLE must be dropped not corrupted",
                        "evidence_ids": [{"id": "1001"}],
                        "strength": "low",
                    }
                ],
                "fact_candidates": [
                    {
                        "statement": "CANARY_NONSCALAR_FACT must be dropped not corrupted",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": [{"id": "1001"}, "1002"],
                        "sensitivity": "general",
                    },
                    {
                        "statement": "CANARY_NONE_EVIDENCE_TOLERATED stays valid",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": ["1003", None],
                        "sensitivity": "general",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "nonscalar_review.json"
    exit_code, stdout = _capture_stdout(merge.main, ["--results-dir", str(results_dir), "--out", str(out_path)])
    require(exit_code == 0, stdout)

    review = json.loads(out_path.read_text(encoding="utf-8"))
    descriptions = {obs["description"] for obs in review["style_observations"]}
    require("CANARY_NONSCALAR_STYLE must be dropped not corrupted" not in descriptions, descriptions)

    statements = {fact["statement"]: fact for fact in review["fact_candidates"]}
    require("CANARY_NONSCALAR_FACT must be dropped not corrupted" not in statements, statements)
    tolerated = statements["CANARY_NONE_EVIDENCE_TOLERATED stays valid"]
    require(tolerated["evidence_ids"] == ["1003"], tolerated)

    # No dict repr garbage (e.g. "{'id': '1001'}") must leak into the
    # written review artifact at all.
    review_text = out_path.read_text(encoding="utf-8")
    require("{'id'" not in review_text, "a non-scalar evidence id must never be stringified into the review artifact")


def check_dry_run_pipeline_one_loop(tmp_path: Path, batch_paths: list[Path]) -> None:
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("SYSTEM PROMPT PLACEHOLDER", encoding="utf-8")
    runner_out = tmp_path / "pipeline_runner_out"

    exit_code, _stdout = _capture_stdout(
        batch_runner.main,
        [
            "--model",
            "fake-model",
            "--prompt-file",
            str(prompt_path),
            "--batch-dir",
            str(batch_paths[0].parent),
            "--out-dir",
            str(runner_out),
            "--dry-run",
        ],
    )
    require(exit_code == 0, "dry-run batch stage must succeed with no LLM call")

    empty_results_dir = runner_out / "results"
    empty_results_dir.mkdir(parents=True, exist_ok=True)
    review_out = tmp_path / "pipeline_review.json"
    exit_code, stdout = _capture_stdout(merge.main, ["--results-dir", str(empty_results_dir), "--out", str(review_out)])
    require(exit_code == 0, "merge stage must complete one loop even with zero LLM-produced results")
    summary = json.loads(stdout.strip())
    require(summary["batches_merged"] == 0, summary)
    require(review_out.is_file(), "merge must still write a review artifact")


def check_chatgpt_prompt_is_self_contained() -> None:
    # The batch runner sends each prompt file standalone as the system
    # prompt, so the ChatGPT prompt must not merely refer to "prompt 1's
    # schema" without ever including it in the same file.
    prompt_path = Path(__file__).resolve().parent / "twin_extraction_prompts" / "chatgpt_extraction_prompt.txt"
    text = prompt_path.read_text(encoding="utf-8")
    require('"style_observations"' in text, "chatgpt prompt must inline the style_observations schema key")
    require('"fact_candidates"' in text, "chatgpt prompt must inline the fact_candidates schema key")
    require('"chatgpt_reconstructed"' in text, "chatgpt prompt must inline the fixed provenance value")
    require("プロンプト1と同一スキーマ" not in text, "chatgpt prompt must not rely on prompt 1 being sent alongside it")


def main() -> int:
    check_chatgpt_prompt_is_self_contained()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        batch_paths = check_x_preprocess(tmp_path)
        check_preprocess_rerun_clears_stale_batches(tmp_path)
        check_chatgpt_preprocess(tmp_path)
        check_batch_runner_dry_run(tmp_path, batch_paths)
        check_run_batch_success_and_fail_closed()
        check_batch_runner_main_fail_closed(tmp_path, batch_paths)
        check_batch_runner_rerun_clears_stale_marker(tmp_path, batch_paths)
        check_merge(tmp_path)
        check_merge_multiple_results_dirs_do_not_collide(tmp_path)
        check_merge_rejects_non_scalar_evidence_ids(tmp_path)
        check_truncated_json_array_fails_closed(tmp_path)
        check_missing_delimiter_json_array_fails_closed()
        check_dry_run_pipeline_one_loop(tmp_path, batch_paths)

    print("RelayLM Twin Extraction tooling smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
