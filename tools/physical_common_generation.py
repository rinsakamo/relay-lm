from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = 1
GIT_OBJECT_FORMAT = "sha1"
AGGREGATE_DOMAIN = b"relay-lm-common-physical-generation-v1\0"
DEFAULT_CERTIFICATE = Path(".ai/physical/common_generation.json")
COMMON_PHYSICAL_SURFACE = (
    ".ai/physical/python_environment_policy.json",
    ".ai/skills/physical-execution-queue/SKILL.md",
    "docs/reference/physical-execution-queue.md",
    "tests/integration/test_physical_execution_queue_process_smoke.py",
    "tests/unit/test_physical_execution_queue.py",
    "tests/unit/test_physical_execution_queue_smoke_target.py",
    "tests/unit/test_relay_physical_env.py",
    "tests/unit/test_relay_physical_env_manifest_integrity.py",
    "tests/unit/test_relay_physical_run.py",
    "tools/physical_execution_queue.py",
    "tools/physical_execution_queue_smoke_target.py",
    "tools/relay_physical_env.py",
    "tools/relay_physical_run.py",
)
SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
GENERATION_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
ROOT_KEYS = {"schema_version", "generation_id", "git_object_format", "aggregate_identity", "surface", "provenance"}
SURFACE_KEYS = {"path", "git_blob_oid"}
PROVENANCE_KEYS = {"origin_commit", "origin_tree", "promotion_owner", "predecessor_issue", "predecessor_commit"}


class CommonGenerationError(ValueError):
    pass


def _keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    if set(value) != expected:
        raise CommonGenerationError(
            f"{where} keys mismatch: missing={sorted(expected - set(value))} extra={sorted(set(value) - expected)}"
        )


def _int(value: Any, where: str) -> int:
    if type(value) is not int:
        raise CommonGenerationError(f"{where} must be an integer")
    return value


def _sha1(value: Any, where: str) -> str:
    if not isinstance(value, str) or SHA1_RE.fullmatch(value) is None:
        raise CommonGenerationError(f"{where} must be a lowercase 40-hex Git SHA-1")
    return value


def _path(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CommonGenerationError(f"{where} must be a normalized repository-relative path")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or str(parsed) != value or any(part in {"", ".", ".."} for part in parsed.parts):
        raise CommonGenerationError(f"{where} must be a normalized repository-relative path")
    return value


def git_blob_oid(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def aggregate_identity(surface: Iterable[tuple[str, str]]) -> str:
    entries = tuple(surface)
    paths = [path for path, _ in entries]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise CommonGenerationError("surface must be strictly path-sorted and unique")
    digest = hashlib.sha256(AGGREGATE_DOMAIN)
    for path, oid in entries:
        _path(path, "surface.path")
        _sha1(oid, f"surface[{path}].git_blob_oid")
        digest.update(path.encode("utf-8") + b"\0" + oid.encode("ascii") + b"\n")
    return f"sha256:{digest.hexdigest()}"


def validate_certificate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CommonGenerationError("certificate root must be an object")
    _keys(value, ROOT_KEYS, "certificate")
    if _int(value["schema_version"], "schema_version") != SCHEMA_VERSION:
        raise CommonGenerationError(f"schema_version must be exactly {SCHEMA_VERSION}")
    generation_id = value["generation_id"]
    if not isinstance(generation_id, str) or GENERATION_RE.fullmatch(generation_id) is None:
        raise CommonGenerationError("generation_id has invalid syntax")
    if value["git_object_format"] != GIT_OBJECT_FORMAT:
        raise CommonGenerationError(f"git_object_format must be {GIT_OBJECT_FORMAT!r}")
    if not isinstance(value["aggregate_identity"], str) or SHA256_RE.fullmatch(value["aggregate_identity"]) is None:
        raise CommonGenerationError("aggregate_identity must be sha256:<64 lowercase hex>")
    raw_surface = value["surface"]
    if not isinstance(raw_surface, list) or not raw_surface:
        raise CommonGenerationError("surface must be a non-empty array")
    pairs: list[tuple[str, str]] = []
    for index, entry in enumerate(raw_surface):
        if not isinstance(entry, dict):
            raise CommonGenerationError(f"surface[{index}] must be an object")
        _keys(entry, SURFACE_KEYS, f"surface[{index}]")
        pairs.append((_path(entry["path"], f"surface[{index}].path"), _sha1(entry["git_blob_oid"], f"surface[{index}].git_blob_oid")))
    computed = aggregate_identity(pairs)
    if value["aggregate_identity"] != computed:
        raise CommonGenerationError(
            f"aggregate_identity mismatch: declared={value['aggregate_identity']} computed={computed}"
        )
    provenance = value["provenance"]
    if not isinstance(provenance, dict):
        raise CommonGenerationError("provenance must be an object")
    _keys(provenance, PROVENANCE_KEYS, "provenance")
    _sha1(provenance["origin_commit"], "provenance.origin_commit")
    _sha1(provenance["origin_tree"], "provenance.origin_tree")
    if _int(provenance["promotion_owner"], "provenance.promotion_owner") != 2750:
        raise CommonGenerationError("provenance.promotion_owner must be exactly 2750")
    if _int(provenance["predecessor_issue"], "provenance.predecessor_issue") != 2731:
        raise CommonGenerationError("provenance.predecessor_issue must be exactly 2731")
    _sha1(provenance["predecessor_commit"], "provenance.predecessor_commit")
    return value


def load_certificate(path: Path) -> dict[str, Any]:
    try:
        return validate_certificate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CommonGenerationError(f"cannot read certificate {path}: {exc}") from exc


def verify_checkout(
    root: Path,
    certificate: Mapping[str, Any],
    *,
    expected_generation_id: str | None = None,
    expected_aggregate_identity: str | None = None,
) -> dict[str, str]:
    cert = validate_certificate(dict(certificate))
    if expected_generation_id is not None and cert["generation_id"] != expected_generation_id:
        raise CommonGenerationError(f"generation id mismatch: expected={expected_generation_id} actual={cert['generation_id']}")
    if expected_aggregate_identity is not None and cert["aggregate_identity"] != expected_aggregate_identity:
        raise CommonGenerationError(
            f"aggregate identity mismatch: expected={expected_aggregate_identity} actual={cert['aggregate_identity']}"
        )
    for entry in cert["surface"]:
        relative = entry["path"]
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise CommonGenerationError(f"certified surface is missing or not a regular file: {relative}")
        actual = git_blob_oid(path.read_bytes())
        if actual != entry["git_blob_oid"]:
            raise CommonGenerationError(f"certified surface drift: {relative}: expected={entry['git_blob_oid']} actual={actual}")
    return {
        "generation_id": cert["generation_id"],
        "aggregate_identity": cert["aggregate_identity"],
        "origin_commit": cert["provenance"]["origin_commit"],
        "origin_tree": cert["provenance"]["origin_tree"],
    }


def assert_generation_id_consistent(certificates: Iterable[Mapping[str, Any]]) -> None:
    seen: dict[str, str] = {}
    for raw in certificates:
        cert = validate_certificate(dict(raw))
        previous = seen.setdefault(cert["generation_id"], cert["aggregate_identity"])
        if previous != cert["aggregate_identity"]:
            raise CommonGenerationError(
                f"generation id collision: {cert['generation_id']}: first={previous} other={cert['aggregate_identity']}"
            )


def build_certificate(root: Path, *, generation_id: str, origin_commit: str, origin_tree: str, predecessor_commit: str) -> dict[str, Any]:
    if not isinstance(generation_id, str) or GENERATION_RE.fullmatch(generation_id) is None:
        raise CommonGenerationError("generation_id has invalid syntax")
    _sha1(origin_commit, "origin_commit")
    _sha1(origin_tree, "origin_tree")
    _sha1(predecessor_commit, "predecessor_commit")
    entries: list[dict[str, str]] = []
    pairs: list[tuple[str, str]] = []
    for relative in COMMON_PHYSICAL_SURFACE:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise CommonGenerationError(f"generation surface is missing or not a regular file: {relative}")
        oid = git_blob_oid(path.read_bytes())
        entries.append({"path": relative, "git_blob_oid": oid})
        pairs.append((relative, oid))
    return validate_certificate({
        "schema_version": SCHEMA_VERSION,
        "generation_id": generation_id,
        "git_object_format": GIT_OBJECT_FORMAT,
        "aggregate_identity": aggregate_identity(pairs),
        "surface": entries,
        "provenance": {
            "origin_commit": origin_commit,
            "origin_tree": origin_tree,
            "promotion_owner": 2750,
            "predecessor_issue": 2731,
            "predecessor_commit": predecessor_commit,
        },
    })


def _dump(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2) + "\n"


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify RelayLM common physical generation certificates.")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--root", type=Path, default=Path("."))
    verify.add_argument("--certificate", type=Path, default=DEFAULT_CERTIFICATE)
    verify.add_argument("--expect-generation-id")
    verify.add_argument("--expect-aggregate-identity")
    generate = sub.add_parser("generate")
    generate.add_argument("--root", type=Path, default=Path("."))
    generate.add_argument("--generation-id", required=True)
    generate.add_argument("--origin-commit", required=True)
    generate.add_argument("--origin-tree", required=True)
    generate.add_argument("--predecessor-commit", required=True)
    generate.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            certificate = args.certificate if args.certificate.is_absolute() else args.root / args.certificate
            result = verify_checkout(
                args.root,
                load_certificate(certificate),
                expected_generation_id=args.expect_generation_id,
                expected_aggregate_identity=args.expect_aggregate_identity,
            )
            print(_dump(result), end="")
            return 0
        result = build_certificate(
            args.root,
            generation_id=args.generation_id,
            origin_commit=args.origin_commit,
            origin_tree=args.origin_tree,
            predecessor_commit=args.predecessor_commit,
        )
        rendered = _dump(result)
        if args.output is None:
            print(rendered, end="")
        else:
            args.output.write_text(rendered, encoding="utf-8")
        return 0
    except (CommonGenerationError, OSError) as exc:
        print(f"physical-common-generation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
