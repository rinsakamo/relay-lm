"""Read saved maps completely; never launch, load libraries, or attest closure.

This diagnostic compares recorded map identities to recorded manifest identities.
Even a match does not verify current files, hashes, mounts, or process ownership.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from tools.wsl_nvidia_runtime_closure_rehearsal import _mapped_file_inventory


_MAP_LINE = re.compile(
    r"^[0-9a-fA-F]+-[0-9a-fA-F]+\s+[r-][w-][x-][ps]\s+"
    r"[0-9a-fA-F]+\s+[0-9a-fA-F]+:[0-9a-fA-F]+\s+\d+(?:\s.*)?$"
)


def diagnose(snapshot: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Return every saved line and defect without changing acceptance policy."""
    content = snapshot.get("content")
    if (
        not isinstance(content, str)
        or not content
        or snapshot.get("complete_snapshot") is not True
        or snapshot.get("line_count") != len(content.splitlines())
        or snapshot.get("sha256") != hashlib.sha256(content.encode()).hexdigest()
    ):
        raise ValueError("saved snapshot completeness/hash/line count is invalid")
    expected: dict[str, dict[str, Any]] = {}

    def add(path: str, record: dict[str, Any]) -> None:
        sealed = {"identity": record["identity"], "sha256": record["sha256"]}
        if path in expected and expected[path] != sealed:
            raise ValueError(f"conflicting sealed records: {path}")
        expected[path] = sealed

    add(manifest["server"]["path"], manifest["server"])
    for path, record in manifest["build"]["shared_libraries"].items():
        add(path, record)
        for dependency in record["dependencies"].values():
            add(dependency["path"], dependency)
    closure = manifest["build"]["wsl_cuda_driver_closure"]
    for record in closure["accepted_mapped_objects"]:
        add(record["path"], record)
    model_path = manifest["model"]["path"]
    add(model_path, manifest["model"])
    rows = []
    for number, line in enumerate(content.splitlines(), 1):
        if not _MAP_LINE.fullmatch(line):
            rows.append({"line_number": number, "raw": line,
                         "diagnostic": "MALFORMED_MAP_LINE"})
            continue
        row = _mapped_file_inventory(line, manifest)[0]
        row.update(line_number=number, raw=line)
        path = row["path"]
        if path is None:
            result = "ANONYMOUS_OR_PSEUDO"
        elif path in expected:
            identity = expected[path]["identity"]
            sealed_id = [os.major(identity["device"]), os.minor(identity["device"]), identity["inode"]]
            map_id = [row["map_device_major"], row["map_device_minor"], row["map_inode"]]
            row["sealed_device_inode"] = sealed_id
            if row["deleted"]:
                result = "DELETED_SEALED_OBJECT"
            elif map_id != sealed_id:
                result = "SEALED_MAP_IDENTITY_MISMATCH"
            else:
                result = "SEALED_MODEL_MAP_IDENTITY_MATCH" if path == model_path else "SEALED_MAP_IDENTITY_MATCH"
        elif ".so" in Path(path).name or path.startswith(closure["driver_package"]["root"] + "/"):
            result = "UNSEALED_LIBRARY"
        else:
            result = "UNSEALED_NON_LIBRARY"
        row["diagnostic"] = result
        rows.append(row)
    return {
        "format_version": 1,
        "status": "OFFLINE_DIAGNOSTIC_NOT_ATTESTATION",
        "qualification_authority": False,
        "closure_attested": False,
        "sha256": snapshot["sha256"],
        "line_count": len(rows),
        "content": content,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    snapshot_bytes = args.snapshot.read_bytes()
    manifest_bytes = args.manifest.read_bytes()
    result = diagnose(json.loads(snapshot_bytes), json.loads(manifest_bytes))
    result["inputs"] = {
        "snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    # Exclusive output prevents overwriting historical evidence or input files.
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    main()
