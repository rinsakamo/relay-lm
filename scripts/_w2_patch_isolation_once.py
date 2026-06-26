from pathlib import Path

path = Path("relaylm/relaymem_slp_durable_finalization_isolation.py")
text = path.read_text(encoding="utf-8")

old = '_DIGEST = re.compile(r"^[0-9a-f]{64}$")\n_MAX_REASONS = 16'
new = '''_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ISOLATION_FILENAME_RE = re.compile(
    rf"^{re.escape(_PREFIX)}([0-9a-f]{{64}}){re.escape(_SUFFIX)}$"
)
_ISOLATION_TEMP_RE = re.compile(
    r"^\\.durable-finalization-isolation-([0-9a-f]{32})\\.tmp$"
)
_MAX_REASONS = 16'''
if old not in text:
    raise SystemExit("isolation regex anchor missing")
text = text.replace(old, new, 1)

old = '''def isolation_filename(locator_digest: str) -> str:
    if not _is_digest(locator_digest):
        raise ValueError("durable_finalization_isolation_locator_invalid")
    return f"{_PREFIX}{locator_digest}{_SUFFIX}"


def build_isolation_marker('''
new = '''def isolation_filename(locator_digest: str) -> str:
    if not _is_digest(locator_digest):
        raise ValueError("durable_finalization_isolation_locator_invalid")
    return f"{_PREFIX}{locator_digest}{_SUFFIX}"


def parse_isolation_filename(name: object) -> str | None:
    if type(name) is not str:
        return None
    match = _ISOLATION_FILENAME_RE.fullmatch(name)
    return match.group(1) if match is not None else None


def isolation_temp_filename(token: str) -> str:
    if type(token) is not str or re.fullmatch(r"[0-9a-f]{32}", token) is None:
        raise ValueError("durable_finalization_isolation_temp_token_invalid")
    return f".durable-finalization-isolation-{token}.tmp"


def is_isolation_temp_filename(name: object) -> bool:
    return type(name) is str and _ISOLATION_TEMP_RE.fullmatch(name) is not None


def build_isolation_marker('''
if old not in text:
    raise SystemExit("isolation helper anchor missing")
text = text.replace(old, new, 1)

old = 'temp = f".durable-finalization-isolation-{secrets.token_hex(16)}.tmp"'
new = 'temp = isolation_temp_filename(secrets.token_hex(16))'
if old not in text:
    raise SystemExit("isolation temp anchor missing")
text = text.replace(old, new, 1)

old = '''    "build_isolation_marker",
    "isolation_filename",'''
new = '''    "build_isolation_marker",
    "is_isolation_temp_filename",
    "isolation_filename",
    "isolation_temp_filename",
    "parse_isolation_filename",'''
if old not in text:
    raise SystemExit("isolation export anchor missing")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
