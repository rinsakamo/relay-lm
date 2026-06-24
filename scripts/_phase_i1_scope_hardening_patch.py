#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    body = target.read_text(encoding="utf-8")
    if old not in body:
        raise SystemExit(f"missing patch anchor in {path}: {old!r}")
    target.write_text(body.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/app.py",
    '''from relaylm.relayctx_repack import (
    apply_relayctx_short_term_runtime_injection_phase,
    apply_relaymem_runtime_injection_phase,
    apply_token_budget_truncation_phase,
)
from collections.abc import Mapping

def create_app''',
    '''from relaylm.relayctx_repack import (
    apply_relayctx_short_term_runtime_injection_phase,
    apply_relaymem_runtime_injection_phase,
    apply_token_budget_truncation_phase,
)


def create_app''',
)

replace_once(
    "relaylm/relaymem_primary_recall.py",
    '''    if not isinstance(character_id, str) or _TOKEN_RE.fullmatch(character_id) is None:
        return None
    digest = stable_hash((_CHARACTER_PARTITION_VERSION, character_id))
    return str(Path(configured_root) / "characters" / digest)
''',
    '''    if not isinstance(character_id, str) or _TOKEN_RE.fullmatch(character_id) is None:
        return None
    root = Path(configured_root)
    if _path_has_symlink_component(root):
        return None
    if root.exists() and not root.is_dir():
        return None
    character_root = root / "characters"
    if character_root.is_symlink():
        return None
    if character_root.exists() and not character_root.is_dir():
        return None
    digest = stable_hash((_CHARACTER_PARTITION_VERSION, character_id))
    return str(character_root / digest)
''',
)

replace_once(
    "scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py",
    '''        base = Path(directory)
        first_value = resolve_relaymem_character_store_root(str(base), CHARACTER)
''',
    '''        base = Path(directory)
        regular_file_root = base / "regular-file-root"
        regular_file_root.write_text("not-a-directory", encoding="utf-8")
        require(
            resolve_relaymem_character_store_root(
                str(regular_file_root), CHARACTER
            )
            is None,
            "regular-file configured root must fail closed",
        )
        invalid_partition_root = base / "invalid-partition-root"
        invalid_partition_root.mkdir()
        (invalid_partition_root / "characters").write_text(
            "not-a-directory", encoding="utf-8"
        )
        require(
            resolve_relaymem_character_store_root(
                str(invalid_partition_root), CHARACTER
            )
            is None,
            "regular-file characters partition must fail closed",
        )
        if hasattr(os, "symlink"):
            outside_root = base / "outside-root"
            outside_root.mkdir()
            configured_root_link = base / "configured-root-link"
            configured_root_link.symlink_to(
                outside_root, target_is_directory=True
            )
            require(
                resolve_relaymem_character_store_root(
                    str(configured_root_link), CHARACTER
                )
                is None,
                "symlink configured root must fail closed",
            )
            configured_root = base / "configured-root"
            configured_root.mkdir()
            real_characters = base / "real-characters"
            real_characters.mkdir()
            (configured_root / "characters").symlink_to(
                real_characters, target_is_directory=True
            )
            require(
                resolve_relaymem_character_store_root(
                    str(configured_root), CHARACTER
                )
                is None,
                "symlink characters partition must fail closed",
            )

        first_value = resolve_relaymem_character_store_root(str(base), CHARACTER)
''',
)
