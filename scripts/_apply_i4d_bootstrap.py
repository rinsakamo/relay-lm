from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"patch anchor missing: {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


patch(
    "relaylm/relaymem_primary_recall.py",
    "import json\nimport re\n",
    "import json\nimport re\nimport stat\n",
)
patch(
    "relaylm/relaymem_primary_recall.py",
    """            # Correction metadata is an audit/revision selector only. M2 remains
            # relevance owner and the canonical page/index/log validator remains
            # unchanged. The local import avoids a module cycle because the
            # correction apply boundary reuses these private validation helpers.
            from .relaymem_primary_correction import (
                load_primary_correction_state,
                resolve_primary_correction_identity,
            )

            correction_state = load_primary_correction_state(
                root, namespace=namespace
            )
""",
    """            # M2 remains the relevance owner. I-4D applies one request-scoped,
            # read-only lifecycle index after the existing page/control validation.
            from .relaymem_primary_retrieval_eligibility import (
                load_primary_retrieval_eligibility_index,
            )

            lifecycle_index = load_primary_retrieval_eligibility_index(
                root, namespace=namespace
            )
""",
)
patch(
    "relaylm/relaymem_primary_recall.py",
    """                resolved_identity = resolve_primary_correction_identity(
                    correction_state, physical_identity
                )
                if resolved_identity is None:
                    reasons.append("primary_recall_correction_state_invalid")
                    continue
                identity, revision, is_current = resolved_identity
                if not is_current:
                    reasons.append("primary_recall_superseded_revision_excluded")
                    continue
""",
    """                eligibility = lifecycle_index.evaluate(physical_identity)
                if not eligibility.eligible:
                    reasons.append(eligibility.reason_id)
                    continue
                identity = eligibility.logical_memory_id
                revision = eligibility.current_revision
                if identity is None or revision is None:
                    reasons.append("excluded_unresolved_identity")
                    continue
""",
)
patch(
    "relaylm/relaymem_primary_recall.py",
    """    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path) or not path.is_file():
        return None, ["primary_recall_page_unsafe_or_missing"]
    try:
        raw = path.read_bytes()
    except OSError:
        return None, ["primary_recall_page_unreadable"]
    if not raw or len(raw) > MAX_PAGE_BYTES:
        return None, ["primary_recall_page_size_invalid"]
""",
    """    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path):
        return None, ["primary_recall_page_unsafe_or_missing"]
    raw, read_reason = _read_stable_regular_file(path, maximum=MAX_PAGE_BYTES)
    if raw is None:
        return None, [f"primary_recall_page_{read_reason}"]
""",
)
patch(
    "relaylm/relaymem_primary_recall.py",
    """def _read_markers(
    root: Path,
""",
    """def _read_stable_regular_file(
    path: Path, *, maximum: int
) -> tuple[bytes | None, str]:
    try:
        before = path.lstat()
    except OSError:
        return None, "unsafe_or_missing"
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
    ):
        return None, "unsafe_or_missing"
    if before.st_size <= 0 or before.st_size > maximum:
        return None, "size_invalid"
    try:
        raw = path.read_bytes()
        after = path.lstat()
    except OSError:
        return None, "unreadable"
    before_fingerprint = (
        before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode),
        before.st_nlink, before.st_size,
    )
    after_fingerprint = (
        after.st_dev, after.st_ino, stat.S_IFMT(after.st_mode),
        after.st_nlink, after.st_size,
    )
    if before_fingerprint != after_fingerprint or len(raw) != after.st_size:
        return None, "changed_during_reread"
    return raw, ""


def _read_markers(
    root: Path,
""",
)
patch(
    "relaylm/relaymem_primary_recall.py",
    """    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path) or not path.is_file():
        return None, "primary_recall_control_file_unsafe_or_missing"
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "primary_recall_control_file_unreadable"
    if len(raw) > _MAX_CONTROL_BYTES:
        return None, "primary_recall_control_file_size_exceeded"
""",
    """    path = root / PurePosixPath(relative)
    if _contains_symlink(root, path):
        return None, "primary_recall_control_file_unsafe_or_missing"
    raw, read_reason = _read_stable_regular_file(path, maximum=_MAX_CONTROL_BYTES)
    if raw is None:
        return None, f"primary_recall_control_file_{read_reason}"
""",
)

patch(
    "relaylm/_relaymem_primary_current_state_impl.py",
    "import json\n",
    "import json\nimport stat\n",
)
patch(
    "relaylm/_relaymem_primary_current_state_impl.py",
    """    path = root / PurePosixPath(str(relative))
    if path.is_symlink() or not path.is_file():
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_not_regular",),
        )
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PrimaryCurrentStateError("store_unavailable") from exc
""",
    """    path = root / PurePosixPath(str(relative))
    try:
        before = path.lstat()
    except OSError:
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_not_regular",),
        )
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
    ):
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_not_regular",),
        )
    try:
        raw = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise PrimaryCurrentStateError("store_unavailable") from exc
    before_fingerprint = (
        before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode),
        before.st_nlink, before.st_size,
    )
    after_fingerprint = (
        after.st_dev, after.st_ino, stat.S_IFMT(after.st_mode),
        after.st_nlink, after.st_size,
    )
    if before_fingerprint != after_fingerprint or len(raw) != after.st_size:
        return _corrupt_state(
            memory_id,
            current_physical=current_physical,
            current_revision=current_revision,
            reasons=("primary_current_page_changed_during_reread",),
        )
""",
)
patch(
    "relaylm/_relaymem_primary_current_state_impl.py",
    """def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size <= 0
            or path.stat().st_size > _MAX_ARTIFACT_BYTES
        ):
            return None
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
""",
    """def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        before = path.lstat()
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > _MAX_ARTIFACT_BYTES
        ):
            return None
        raw = path.read_bytes()
        after = path.lstat()
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or stat.S_IFMT(before.st_mode) != stat.S_IFMT(after.st_mode)
            or before.st_nlink != after.st_nlink
            or before.st_size != after.st_size
            or len(raw) != after.st_size
        ):
            return None
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
""",
)

patch(
    "relaylm/soul_lab_observation_projection.py",
    """from .relaymem_primary_recall import (
    _load_control_state,
    _load_validated_page,
    resolve_relaymem_character_store_root,
)
""",
    """from .relaymem_primary_current_state import (
    PrimaryCurrentStateError,
    resolve_primary_current_state,
)
from .relaymem_primary_recall import (
    _load_control_state,
    _load_validated_page,
    resolve_relaymem_character_store_root,
)
""",
)
patch(
    "relaylm/soul_lab_observation_projection.py",
    """class LabUsedMemoryItem(_ExactModel):
    memory_id: str
    injected_summary: str = Field(max_length=512)
    current_summary: str | None = Field(default=None, max_length=512)
    representation_changed: bool
    source_kind: str
""",
    """class LabUsedMemoryItem(_ExactModel):
    memory_id: str
    injected_summary: str = Field(max_length=512)
    current_summary: str | None = Field(default=None, max_length=512)
    current_lifecycle_state: Literal["active", "hidden", "unknown"]
    representation_changed: bool
    lifecycle_changed: bool
    source_kind: str
""",
)
patch(
    "relaylm/soul_lab_observation_projection.py",
    """    current, current_reasons = _current_summaries(scope.store_root, scope.namespace)
    items: list[LabUsedMemoryItem] = []
    for item in receipt.get("items", []):
        memory_id = str(item["memory_id"])
        injected = bounded_text(item.get("injected_summary"), maximum=512)
        current_summary = current.get(memory_id)
        items.append(LabUsedMemoryItem(
            memory_id=memory_id, injected_summary=injected, current_summary=current_summary,
            representation_changed=current_summary is not None and current_summary != injected,
            source_kind=str(item.get("source_kind", "primary")),
        ))
""",
    """    receipt_items = list(receipt.get("items", []))[:16]
    overlays, current_reasons = _current_memory_overlays(
        scope.store_root,
        scope.namespace,
        [str(item.get("memory_id", "")) for item in receipt_items],
    )
    items: list[LabUsedMemoryItem] = []
    for item in receipt_items:
        memory_id = str(item["memory_id"])
        injected = bounded_text(item.get("injected_summary"), maximum=512)
        current_summary, lifecycle = overlays.get(memory_id, (None, "unknown"))
        items.append(LabUsedMemoryItem(
            memory_id=memory_id, injected_summary=injected, current_summary=current_summary,
            current_lifecycle_state=lifecycle,
            representation_changed=current_summary is not None and current_summary != injected,
            lifecycle_changed=lifecycle == "hidden",
            source_kind=str(item.get("source_kind", "primary")),
        ))
""",
)
patch(
    "relaylm/soul_lab_observation_projection.py",
    """def _current_summaries(store_root: str, namespace: str) -> tuple[dict[str, str], list[str]]:
    root = Path(store_root)
    control, reasons = _load_control_state(root)
    if control is None:
        return {}, reasons
    from .relaymem_primary_correction import (
        load_primary_correction_state,
        resolve_primary_correction_identity,
    )

    correction_state = load_primary_correction_state(root, namespace=namespace)
    summaries: dict[str, str] = {}
    output_reasons = list(reasons)
    for entry in control["index"]:
        if entry.get("namespace") != namespace:
            continue
        physical_identity = entry.get("idempotency_key")
        if not isinstance(physical_identity, str):
            continue
        resolved = resolve_primary_correction_identity(
            correction_state, physical_identity
        )
        if resolved is None:
            output_reasons.append("primary_correction_state_invalid")
            continue
        identity, _revision, is_current = resolved
        if not is_current:
            continue
        loaded, blocked = _load_validated_page(
            root, {"path": entry.get("page_relative_path")},
            expected_namespace=namespace, control=control,
        )
        if loaded is None:
            output_reasons.extend(blocked)
            continue
        summaries[identity] = bounded_text(loaded.get("summary"), maximum=512)
    return summaries, normalize_reason_ids(output_reasons)
""",
    """def _current_memory_overlays(
    store_root: str,
    namespace: str,
    memory_ids: list[str],
) -> tuple[dict[str, tuple[str | None, str]], list[str]]:
    overlays: dict[str, tuple[str | None, str]] = {}
    reasons: list[str] = []
    for memory_id in dict.fromkeys(memory_ids[:16]):
        try:
            state = resolve_primary_current_state(
                store_root, namespace=namespace, memory_id=memory_id
            )
        except PrimaryCurrentStateError:
            overlays[memory_id] = (None, "unknown")
            reasons.append("primary_current_state_unresolved")
            continue
        if state.lifecycle_state == "hidden":
            overlays[memory_id] = (None, "hidden")
            continue
        if (
            state.lifecycle_state == "active"
            and state.mutation_state == "none"
            and state.retrieval_eligible is True
            and state.controls_valid is True
            and state.page_valid is True
        ):
            overlays[memory_id] = (bounded_text(state.summary, maximum=512), "active")
            continue
        overlays[memory_id] = (None, "unknown")
        reasons.append("primary_current_state_ineligible")
    return overlays, normalize_reason_ids(reasons)
""",
)

patch(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    """  current_summary: string | null;
  representation_changed: boolean;
  source_kind: string;
""",
    """  current_summary: string | null;
  current_lifecycle_state: "active" | "hidden" | "unknown";
  representation_changed: boolean;
  lifecycle_changed: boolean;
  source_kind: string;
""",
)
patch(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    """  "memory_id", "injected_summary", "current_summary", "representation_changed", "source_kind",
""",
    """  "memory_id", "injected_summary", "current_summary", "current_lifecycle_state",
  "representation_changed", "lifecycle_changed", "source_kind",
""",
)
patch(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    """    !(value.current_summary === null || isSafeText(value.current_summary, 512)) ||
    typeof value.representation_changed !== "boolean" || typeof value.source_kind !== "string"
""",
    """    !(value.current_summary === null || isSafeText(value.current_summary, 512)) ||
    !["active", "hidden", "unknown"].includes(String(value.current_lifecycle_state)) ||
    typeof value.representation_changed !== "boolean" ||
    typeof value.lifecycle_changed !== "boolean" ||
    typeof value.source_kind !== "string"
""",
)
patch(
    "apps/soul-lab/scripts/observationApiSmoke.mjs",
    """          current_summary: "The user prefers tea.",
          representation_changed: false,
          source_kind: "preference",
""",
    """          current_summary: "The user prefers tea.",
          current_lifecycle_state: "active",
          representation_changed: false,
          lifecycle_changed: false,
          source_kind: "preference",
""",
)
patch(
    "relaylm/relaymem_primary_retrieval_eligibility.py",
    "or any(character in namespace for character in \"\\0\\n\\r\\t\")",
    "or any(character in namespace for character in (chr(0), \"\\n\", \"\\r\", \"\\t\"))",
)

wrappers = {
    "scripts/relaylm_phase_i4d_prior_revision_exclusion_smoke.py": (
        "active_corrected_and_finalized", "prior revision exclusion"
    ),
    "scripts/relaylm_phase_i4d_recovery_state_exclusion_smoke.py": (
        "prepared_and_recovery_states", "recovery-state exclusion"
    ),
    "scripts/relaylm_phase_i4d_relayctx_exclusion_smoke.py": (
        "active_corrected_and_finalized", "RelayCTX exclusion"
    ),
    "scripts/relaylm_phase_i4d_security_smoke.py": (
        "content_free_decisions", "security"
    ),
}
for path, (function, label) in wrappers.items():
    write(
        path,
        "\n".join((
            '"""Permanent focused Phase I-4D smoke wrapper."""',
            f"from relaylm_phase_i4d_primary_retrieval_exclusion_smoke import {function}",
            "",
            "",
            "def main() -> None:",
            f"    {function}()",
            f"    print(\"Phase I-4D {label} smoke passed\")",
            "",
            "",
            'if __name__ == "__main__":',
            "    main()",
            "",
        )),
    )

for relative in (
    "scripts/_apply_i4d_bootstrap.py",
    ".github/workflows/_i4d-bootstrap.yml",
):
    path = ROOT / relative
    if path.exists():
        path.unlink()
