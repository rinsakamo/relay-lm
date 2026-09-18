#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").strip()


def read_sha_line(path: Path) -> str:
    line = read_text(path)
    if not line:
        raise ValueError(f"empty sha file: {path}")
    return line.split()[0]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plain", type=Path)
    ap.add_argument("probe", type=Path)
    args = ap.parse_args()

    evidence = {}
    errors = []

    for name, root in (("plain", args.plain), ("probe", args.probe)):
        if not root.is_dir():
            errors.append(f"missing {name} directory: {root}")
            continue
        try:
            evidence[name] = {
                "classification": read_text(root / "classification.txt"),
                "server_sha256": read_sha_line(root / "server-binary.sha256"),
                "model_sha256": read_sha_line(root / "model.sha256"),
                "argv_canonical_sha256": sha256(root / "server.argv.canonical.txt"),
            }
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if not errors:
        if evidence["plain"]["server_sha256"] != evidence["probe"]["server_sha256"]:
            errors.append("server binary SHA256 differs between plain and probe")
        if evidence["plain"]["model_sha256"] != evidence["probe"]["model_sha256"]:
            errors.append("model SHA256 differs between plain and probe")
        if evidence["plain"]["argv_canonical_sha256"] != evidence["probe"]["argv_canonical_sha256"]:
            errors.append("canonical server argv differs between plain and probe")

        probe_root = args.probe / "probe-root"
        if probe_root.exists() and any(probe_root.iterdir()):
            errors.append("unexpected probe dump/output exists during non-generative recovery")

    startup_failures = {
        "SERVER_EXITED_BEFORE_READINESS",
        "STARTUP_READINESS_TIMEOUT",
    }

    if errors:
        primary = "STARTUP_RECOVERY_INCONCLUSIVE"
    else:
        p = evidence["plain"]["classification"]
        q = evidence["probe"]["classification"]

        if p in startup_failures:
            primary = "INSTRUMENTED_BINARY_STARTUP_FAILED"
        elif p != "READY_NON_GENERATIVE":
            primary = "STARTUP_RECOVERY_INCONCLUSIVE"
        elif q in startup_failures:
            primary = "PROBE_ENV_STARTUP_FAILED"
        elif q != "READY_NON_GENERATIVE":
            primary = "STARTUP_RECOVERY_INCONCLUSIVE"
        else:
            primary = "STARTUP_RECOVERED"

    out = {
        "primary_classification": primary,
        "errors": errors,
        "evidence": evidence,
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
