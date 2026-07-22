from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/evidence_runtime.py",
    '''            and isinstance(content[0], dict)
            and isinstance(content[0].get("text"), str)
''',
    '''            and isinstance(content[0], dict)
            and content[0].get("type") in ("text", "input_text")
            and isinstance(content[0].get("text"), str)
''',
)
replace_once(
    "tests/test_evidence_final_review_regressions.py",
    '''def test_route_snapshot_rejects_non_string_expiry() -> None:
''',
    '''def test_non_text_single_content_part_with_text_field_fails_closed(
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "evidence"
    config_path = _write_config(
        tmp_path,
        evidence_enabled=True,
        evidence_dry_run_only=False,
        evidence_apply_enabled=True,
        evidence_data_root=str(evidence_root),
    )
    client = _client(config_path)
    payload = _chat_request(
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "text": "must not be admitted as user text",
                    }
                ],
            }
        ]
    )
    with respx.mock(assert_all_called=False) as mock:
        backend = mock.post(BACKEND_CHAT_COMPLETIONS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "ignored"},
                            "finish_reason": "stop",
                        }
                    ]
                },
            )
        )
        response = client.post("/v1/chat/completions", json=payload)

    assert response.status_code == 500
    assert response.json()["error"]["type"] == "evidence_capture_error"
    assert backend.called is False


def test_route_snapshot_rejects_non_string_expiry() -> None:
''',
)
