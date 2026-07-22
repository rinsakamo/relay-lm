from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected fragment not found in {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/evidence_store.py",
    '''        space_dir = self._space_dir(evidence_space_id)
        space_dir.mkdir(parents=True, exist_ok=True)
        lock_path = space_dir / ".lock"
        fd = os.open(
            lock_path,
            os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
''',
    '''        space_dir = self._space_dir(evidence_space_id)
        if not _ensure_safe_directory_chain(space_dir):
            raise RuntimeError("evidence_store_path_unsafe")
        lock_path = space_dir / ".lock"
        fd = os.open(
            lock_path,
            os.O_CREAT
            | os.O_RDWR
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''        target.parent.mkdir(parents=True, exist_ok=True)
        return _atomic_create_or_verify(target, canonical_json_bytes(payload))
''',
    '''        return _atomic_create_or_verify(target, canonical_json_bytes(payload))
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''        target.parent.mkdir(parents=True, exist_ok=True)
        return _atomic_replace(target, canonical_json_bytes(list(events)))
''',
    '''        return _atomic_replace(target, canonical_json_bytes(list(events)))
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''        target.parent.mkdir(parents=True, exist_ok=True)
        prepared = {**body, "transaction_digest": digest, "state": "prepared"}
''',
    '''        prepared = {**body, "transaction_digest": digest, "state": "prepared"}
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''                target.parent.mkdir(parents=True, exist_ok=True)
                result = _atomic_create_or_verify(
''',
    '''                result = _atomic_create_or_verify(
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''        directory = self._space_dir(evidence_space_id) / "transactions"
        if not directory.exists():
            return EvidenceStoreResult("duplicate_existing")
''',
    '''        directory = self._space_dir(evidence_space_id) / "transactions"
        try:
            directory_info = directory.lstat()
        except FileNotFoundError:
            return EvidenceStoreResult("duplicate_existing")
        except OSError:
            return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
        if stat.S_ISLNK(directory_info.st_mode) or not stat.S_ISDIR(
            directory_info.st_mode
        ):
            return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''def _atomic_create_or_verify(target: Path, data: bytes) -> EvidenceStoreResult:
    if target.exists():
''',
    '''def _atomic_create_or_verify(target: Path, data: bytes) -> EvidenceStoreResult:
    if not _ensure_safe_directory_chain(target.parent):
        return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
    if target.exists():
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''def _atomic_write(target: Path, data: bytes, *, replace: bool) -> EvidenceStoreResult:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(
''',
    '''def _atomic_write(target: Path, data: bytes, *, replace: bool) -> EvidenceStoreResult:
    if not _ensure_safe_directory_chain(target.parent):
        return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
    temp = target.with_name(
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''        finally:
            os.close(fd)
        if replace:
''',
    '''        finally:
            os.close(fd)
        if not _ensure_safe_directory_chain(target.parent):
            if temp.exists():
                os.unlink(temp)
            return EvidenceStoreResult("failed", ("evidence_store_path_unsafe",))
        if replace:
''',
)
replace_once(
    "relaylm/evidence_store.py",
    '''def _atomic_create_or_verify(target: Path, data: bytes) -> EvidenceStoreResult:
''',
    '''def _ensure_safe_directory_chain(directory: Path) -> bool:
    """Create missing directories one component at a time and reject links/files."""

    if not directory.is_absolute():
        return False
    current = Path(directory.anchor)
    try:
        for part in directory.parts[1:]:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                try:
                    current.mkdir(mode=0o700)
                except FileExistsError:
                    pass
                info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                return False
    except OSError:
        return False
    return True


def _atomic_create_or_verify(target: Path, data: bytes) -> EvidenceStoreResult:
''',
)

path = Path("tests/test_evidence_final_review_regressions.py")
text = path.read_text(encoding="utf-8")
needle = '''def test_nonstream_raw_2xx_fails_closed_in_evidence_apply(tmp_path: Path) -> None:
'''
insert = '''def test_store_rejects_symlinked_record_subdirectory(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    store = EvidenceRecordStore(str(root))
    outside = tmp_path / "outside"
    outside.mkdir()
    linked_directory = root / "space-1" / "records" / "source_event"
    linked_directory.parent.mkdir(parents=True)
    linked_directory.symlink_to(outside, target_is_directory=True)

    result = store.write_record(
        evidence_space_id="space-1",
        record_kind="source_event",
        record_id="source-1",
        payload={"schema": "test"},
    )

    assert result.status == "failed"
    assert result.reasons == ("evidence_store_path_unsafe",)
    assert not (outside / "source-1.json").exists()


def test_nonstream_raw_2xx_fails_closed_in_evidence_apply(tmp_path: Path) -> None:
'''
if needle not in text:
    raise RuntimeError("test insertion point not found")
path.write_text(text.replace(needle, insert, 1), encoding="utf-8")
