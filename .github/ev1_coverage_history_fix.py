from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/evidence_user_input.py",
    "    stream_descriptor, sequence_log, previous_coverage = _load_stream(\n",
    "    stream_descriptor, sequence_log, coverage_log = _load_stream(\n",
)
replace_once(
    "relaylm/evidence_user_input.py",
    "    capture_attempt_id = _derive_id(\n",
    "    previous_coverage = coverage_log[-1] if coverage_log else None\n"
    "    capture_attempt_id = _derive_id(\n",
)
replace_once(
    "relaylm/evidence_user_input.py",
    '''                [
                    *([previous_coverage] if previous_coverage else []),
                    coverage.to_dict(),
                ],
''',
    '''                [*coverage_log, coverage.to_dict()],
''',
)
replace_once(
    "relaylm/evidence_user_input.py",
    '''    dict[str, object] | None,
]:
''',
    '''    list[dict],
]:
''',
)
replace_once(
    "relaylm/evidence_user_input.py",
    '''    previous = checkpoints[-1] if checkpoints else None
    return descriptor, CaptureSequenceLog.from_events(descriptor, events), previous
''',
    '''    return descriptor, CaptureSequenceLog.from_events(descriptor, events), list(checkpoints)
''',
)

path = Path("tests/test_evidence_contract_integrity.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    '''    second = _capture_user(
        store, "user-two", "second", now=NOW + timedelta(seconds=1)
    )
    assert first.status == second.status == "admitted"
    assert first.capture_sequence == 0
    assert second.capture_sequence == 1
''',
    '''    second = _capture_user(
        store, "user-two", "second", now=NOW + timedelta(seconds=1)
    )
    third = _capture_user(
        store, "user-three", "third", now=NOW + timedelta(seconds=2)
    )
    assert first.status == second.status == third.status == "admitted"
    assert first.capture_sequence == 0
    assert second.capture_sequence == 1
    assert third.capture_sequence == 2
''',
    1,
)
text = text.replace(
    '    assert [event["partition_sequence"] for event in projections] == [0, 1]\n',
    '    assert [event["partition_sequence"] for event in projections] == [0, 1, 2]\n',
    1,
)
text = text.replace(
    '    assert [item["coverage_revision"] for item in checkpoints] == [1, 2]\n'
    '    assert checkpoints[-1]["expected_previous_coverage_revision_or_null"] == 1\n',
    '    assert [item["coverage_revision"] for item in checkpoints] == [1, 2, 3]\n'
    '    assert checkpoints[-1]["expected_previous_coverage_revision_or_null"] == 2\n',
    1,
)
path.write_text(text, encoding="utf-8")
