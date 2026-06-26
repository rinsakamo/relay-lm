from pathlib import Path

path = Path("relaylm/relaymem_primary_forget_artifact.py")
body = path.read_text(encoding="utf-8")

replacements = (
    (
        "from typing import Any, Mapping\n\nfrom ._relaymem_primary_page_writer_common import bad_text, is_sha256, stable_hash\n",
        "from typing import Any, Mapping\n\nfrom . import _relaymem_primary_current_state_impl as _current_impl\nfrom ._relaymem_primary_page_writer_common import bad_text, is_sha256, stable_hash\n",
    ),
    (
        '''    path = root / MUTATION_ROOT / memory_id / f"{operation_key}.prepared.json"\n    if not path.exists() and not path.is_symlink():\n''',
        '''    directory = root / MUTATION_ROOT / memory_id\n    if _descendant_has_symlink(root, directory):\n        raise PrimaryForgetArtifactError("target_corrupt")\n    path = directory / f"{operation_key}.prepared.json"\n    if not path.exists() and not path.is_symlink():\n''',
    ),
    (
        '''    directory = root / MUTATION_ROOT / memory_id\n    if not directory.exists() and not directory.is_symlink():\n        return None, False\n    if directory.is_symlink() or not directory.is_dir():\n''',
        '''    directory = root / MUTATION_ROOT / memory_id\n    if _descendant_has_symlink(root, directory):\n        return None, True\n    if not directory.exists() and not directory.is_symlink():\n        return None, False\n    if directory.is_symlink() or not directory.is_dir():\n''',
    ),
    (
        '''        elif schema == CORRECTION_PREPARED_SCHEMA:\n            if not path.name.endswith(".prepared.json"):\n                corrupt = True\n        elif schema == CORRECTION_RECEIPT_SCHEMA:\n            if not path.name.endswith(".applied.json"):\n                corrupt = True\n''',
        '''        elif schema == CORRECTION_PREPARED_SCHEMA:\n            namespace = value.get("namespace")\n            logical_id = value.get("memory_id")\n            if (\n                not path.name.endswith(".prepared.json")\n                or not isinstance(namespace, str)\n                or not isinstance(logical_id, str)\n                or not _current_impl._valid_prepared(\n                    value, namespace=namespace, memory_id=logical_id\n                )\n            ):\n                corrupt = True\n        elif schema == CORRECTION_RECEIPT_SCHEMA:\n            namespace = value.get("namespace")\n            logical_id = value.get("memory_id")\n            if (\n                not path.name.endswith(".applied.json")\n                or not isinstance(namespace, str)\n                or not isinstance(logical_id, str)\n                or not _current_impl._valid_applied(\n                    value, namespace=namespace, memory_id=logical_id\n                )\n            ):\n                corrupt = True\n''',
    ),
    (
        '''def _path_has_symlink(path: Path) -> bool:\n    current = Path(path.anchor) if path.is_absolute() else Path()\n    for part in path.parts[1:] if path.is_absolute() else path.parts:\n        current = current / part\n        if current.is_symlink():\n            return True\n    return False\n\n\ndef _safe_relative_path''',
        '''def _path_has_symlink(path: Path) -> bool:\n    current = Path(path.anchor) if path.is_absolute() else Path()\n    for part in path.parts[1:] if path.is_absolute() else path.parts:\n        current = current / part\n        if current.is_symlink():\n            return True\n    return False\n\n\ndef _descendant_has_symlink(root: Path, path: Path) -> bool:\n    try:\n        relative = path.relative_to(root)\n    except ValueError:\n        return True\n    current = root\n    for part in relative.parts:\n        current = current / part\n        if current.is_symlink():\n            return True\n    return False\n\n\ndef _safe_relative_path''',
    ),
)

for old, new in replacements:
    if old in body:
        body = body.replace(old, new, 1)
    elif new not in body:
        raise RuntimeError(f"Forget artifact safety anchor missing: {old[:80]!r}")

path.write_text(body, encoding="utf-8")
