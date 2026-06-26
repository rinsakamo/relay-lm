from pathlib import Path

path = Path("relaylm/relaymem_slp_scheduler_replay_lane.py")
text = path.read_text(encoding="utf-8")

if "import importlib\n" not in text:
    raise SystemExit("optional import anchor missing")
text = text.replace("import importlib\n", "", 1)

old = '''from .relaymem_slp_durable_finalization_replay import (
    replay_relaymem_slp_durable_finalization_record,
    validate_completion_marker,
)
'''
new = '''from .relaymem_slp_durable_finalization_replay import (
    replay_relaymem_slp_durable_finalization_record,
    validate_completion_marker,
)
from .relaymem_slp_durable_finalization_isolation import (
    ISOLATION_MAX_BYTES,
    is_isolation_temp_filename,
    parse_isolation_filename,
    read_relaymem_slp_durable_finalization_isolation_fd,
)
'''
if old not in text:
    raise SystemExit("replay import anchor missing")
text = text.replace(old, new, 1)

old = '''    isolation = _isolation_module()
    if isolation is not None and name.startswith(_PREFIX):
        candidate = name[len(_PREFIX): len(_PREFIX) + 64]
        if _DIGEST_RE.fullmatch(candidate):
            try:
                if isolation.isolation_filename(candidate) == name:
                    return "isolation", candidate, None
            except (AttributeError, TypeError, ValueError):
                return None
    return None'''
new = '''    isolation_locator = parse_isolation_filename(name)
    if isolation_locator is not None:
        return "isolation", isolation_locator, None
    return None'''
if old not in text:
    raise SystemExit("replay isolation parser anchor missing")
text = text.replace(old, new, 1)

old = '''    if _isolation_module() is not None and re.fullmatch(
        r"^\\.durable-finalization-isolation-[0-9a-f]{32}\\.tmp$", name
    ):
        return "temp"'''
new = '''    if is_isolation_temp_filename(name):
        return "temp"'''
if old not in text:
    raise SystemExit("replay temp parser anchor missing")
text = text.replace(old, new, 1)

old = '''def _isolation_module():
    try:
        return importlib.import_module(
            ".relaymem_slp_durable_finalization_isolation", package=__package__
        )
    except ImportError:
        return None


def _read_isolation(config: RelayLMConfig, locator: str) -> str:
    module = _isolation_module()
    if module is None:
        return "unsupported"
    root_fd, reasons = _open_store_root(config.relaymem_slp_durable_finalization_root)
    if root_fd is None:
        return "unsafe"
    try:
        result = module.read_relaymem_slp_durable_finalization_isolation_fd(root_fd, locator)
    except Exception:
        return "unsafe"
    finally:
        os.close(root_fd)
    return "loaded" if getattr(result, "status", None) == "loaded" else "unsafe"


def _isolation_max_bytes() -> int:
    module = _isolation_module()
    value = getattr(module, "ISOLATION_MAX_BYTES", 16 * 1024) if module else 16 * 1024
    return value if type(value) is int and value > 0 else 16 * 1024
'''
new = '''def _read_isolation(config: RelayLMConfig, locator: str) -> str:
    root_fd, reasons = _open_store_root(config.relaymem_slp_durable_finalization_root)
    if root_fd is None:
        return "unsafe"
    try:
        result = read_relaymem_slp_durable_finalization_isolation_fd(root_fd, locator)
    except Exception:
        return "unsafe"
    finally:
        os.close(root_fd)
    return "loaded" if result.status == "loaded" else "unsafe"
'''
if old not in text:
    raise SystemExit("replay optional module block missing")
text = text.replace(old, new, 1)

old = '        return _isolation_max_bytes()'
new = '        return ISOLATION_MAX_BYTES'
if old not in text:
    raise SystemExit("replay isolation size anchor missing")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
