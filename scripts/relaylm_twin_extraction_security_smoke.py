#!/usr/bin/env python3
"""Security smoke for the Twin Extraction offline tooling.

Dedicated verification that public output (stdout, stderr, and exception
text) from the preprocess, batch runner, and merge CLIs never contains
post/utterance bodies, absolute filesystem paths, or credential-like
values. No LLM, network, or real archive is required.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

import relaylm_twin_extraction_batch_runner as batch_runner
import relaylm_twin_extraction_merge as merge
import relaylm_twin_extraction_preprocess as preprocess

PRIVATE_CANARIES = (
    "CANARY_POST_BODY_do_not_leak_this_text",
    "CANARY_UTTERANCE_BODY_do_not_leak_this_text",
    "CANARY_ASSISTANT_CONTEXT_do_not_leak_this_text",
    "sk-FAKE_CREDENTIAL_TOKEN_1234567890",
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _capture(func, *args, **kwargs) -> tuple[int, str, str]:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        exit_code = func(*args, **kwargs)
    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


def _assert_content_free(combined: str, absolute_path_canary: str) -> None:
    for canary in PRIVATE_CANARIES:
        require(canary not in combined, f"leaked canary: {canary}")
    require(absolute_path_canary not in combined, "leaked absolute path")


def check_preprocess_x(tmp_path: Path) -> None:
    input_path = tmp_path / "secret_subdir" / "tweets.js"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    out_dir = tmp_path / "secret_subdir" / "x_out"
    tweets = [
        {
            "tweet": {
                "id_str": "1",
                "created_at": "Mon Jan 02 10:00:00 +0000 2023",
                "full_text": "CANARY_POST_BODY_do_not_leak_this_text",
            }
        }
    ]
    input_path.write_text(f"window.YTD.tweets.part0 = {json.dumps(tweets)};", encoding="utf-8")

    exit_code, stdout, stderr = _capture(
        preprocess.main,
        ["--source", "x", "--input", str(input_path), "--out-dir", str(out_dir)],
    )
    require(exit_code == 0, stderr)
    _assert_content_free(stdout + stderr, str(tmp_path))

    # Fail-closed error path: input missing must not echo the absolute path.
    missing_path = tmp_path / "secret_subdir" / "does_not_exist.js"
    exit_code, stdout, stderr = _capture(
        preprocess.main,
        ["--source", "x", "--input", str(missing_path), "--out-dir", str(out_dir)],
    )
    require(exit_code != 0, "missing input must fail")
    _assert_content_free(stdout + stderr, str(tmp_path))

    # Fail-closed error path: malformed input must not echo file content or path.
    malformed_path = tmp_path / "secret_subdir" / "malformed.js"
    malformed_path.write_text("window.YTD.tweets.part0 = CANARY_POST_BODY_do_not_leak_this_text", encoding="utf-8")
    exit_code, stdout, stderr = _capture(
        preprocess.main,
        ["--source", "x", "--input", str(malformed_path), "--out-dir", str(out_dir)],
    )
    require(exit_code != 0, "malformed input must fail")
    _assert_content_free(stdout + stderr, str(tmp_path))


def check_preprocess_chatgpt(tmp_path: Path) -> None:
    input_path = tmp_path / "secret_subdir" / "conversations.json"
    out_dir = tmp_path / "secret_subdir" / "chatgpt_out"
    conversations = [
        {
            "conversation_id": "conv-a",
            "mapping": {
                "n1": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"content_type": "text", "parts": ["CANARY_UTTERANCE_BODY_do_not_leak_this_text"]},
                        "create_time": 1.0,
                    }
                },
                "n2": {
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": ["CANARY_ASSISTANT_CONTEXT_do_not_leak_this_text"]},
                        "create_time": 2.0,
                    }
                },
            },
        }
    ]
    input_path.write_text(json.dumps(conversations), encoding="utf-8")

    exit_code, stdout, stderr = _capture(
        preprocess.main,
        ["--source", "chatgpt", "--input", str(input_path), "--out-dir", str(out_dir)],
    )
    require(exit_code == 0, stderr)
    _assert_content_free(stdout + stderr, str(tmp_path))


def check_batch_runner(tmp_path: Path) -> None:
    batch_dir = tmp_path / "secret_subdir" / "batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "batch_0001.jsonl").write_text(
        json.dumps({"id": "1", "text": "CANARY_POST_BODY_do_not_leak_this_text"}) + "\n", encoding="utf-8"
    )
    prompt_path = tmp_path / "secret_subdir" / "prompt.txt"
    prompt_path.write_text("SYSTEM PROMPT", encoding="utf-8")
    out_dir = tmp_path / "secret_subdir" / "runner_out"

    # dry-run: no network, must stay content-free even with a credential-like base URL.
    exit_code, stdout, stderr = _capture(
        batch_runner.main,
        [
            "--base-url",
            "http://user:sk-FAKE_CREDENTIAL_TOKEN_1234567890@127.0.0.1:1234/v1",
            "--model",
            "fake-model",
            "--prompt-file",
            str(prompt_path),
            "--batch-dir",
            str(batch_dir),
            "--out-dir",
            str(out_dir),
            "--dry-run",
        ],
    )
    require(exit_code == 0, stderr)
    _assert_content_free(stdout + stderr, str(tmp_path))

    # fail-closed live path: fake completion echoes the private body back in a
    # malformed way; the runner must still not print it anywhere.
    def fake_call(_base_url: str, payload: dict) -> dict:
        return {"choices": [{"message": {"content": "not-json: " + json.dumps(payload)}}]}

    original = batch_runner.call_chat_completions
    batch_runner.call_chat_completions = fake_call
    try:
        exit_code, stdout, stderr = _capture(
            batch_runner.main,
            [
                "--model",
                "fake-model",
                "--prompt-file",
                str(prompt_path),
                "--batch-dir",
                str(batch_dir),
                "--out-dir",
                str(out_dir),
                "--retries",
                "0",
            ],
        )
    finally:
        batch_runner.call_chat_completions = original
    require(exit_code == 0, stderr)
    _assert_content_free(stdout + stderr, str(tmp_path))

    # missing prompt/batch-dir errors must not echo absolute paths.
    exit_code, stdout, stderr = _capture(
        batch_runner.main,
        [
            "--model",
            "fake-model",
            "--prompt-file",
            str(tmp_path / "secret_subdir" / "missing_prompt.txt"),
            "--batch-dir",
            str(batch_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    require(exit_code != 0, "missing prompt file must fail")
    _assert_content_free(stdout + stderr, str(tmp_path))


def check_merge(tmp_path: Path) -> None:
    results_dir = tmp_path / "secret_subdir" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "batch_0001.result.json").write_text(
        json.dumps(
            {
                "style_observations": [
                    {
                        "category": "tone",
                        "description": "CANARY_POST_BODY_do_not_leak_this_text",
                        "evidence_ids": ["1"],
                        "strength": "low",
                    }
                ],
                "fact_candidates": [
                    {
                        "statement": "CANARY_UTTERANCE_BODY_do_not_leak_this_text",
                        "type": "knowledge",
                        "provenance": "x_post",
                        "evidence_ids": ["1"],
                        "sensitivity": "private_only",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "secret_subdir" / "review.json"

    exit_code, stdout, stderr = _capture(merge.main, ["--results-dir", str(results_dir), "--out", str(out_path)])
    require(exit_code == 0, stderr)
    _assert_content_free(stdout + stderr, str(tmp_path))

    # The written review artifact is an intentional work product and is
    # allowed to contain the material; only stdout/stderr must stay clean.
    review_text = out_path.read_text(encoding="utf-8")
    require("CANARY_UTTERANCE_BODY_do_not_leak_this_text" in review_text, "review artifact should retain merged material")

    # missing results dir must not echo the absolute path.
    exit_code, stdout, stderr = _capture(
        merge.main, ["--results-dir", str(tmp_path / "secret_subdir" / "missing_results"), "--out", str(out_path)]
    )
    require(exit_code != 0, "missing results dir must fail")
    _assert_content_free(stdout + stderr, str(tmp_path))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        check_preprocess_x(tmp_path)
        check_preprocess_chatgpt(tmp_path)
        check_batch_runner(tmp_path)
        check_merge(tmp_path)

    print("RelayLM Twin Extraction tooling security smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
