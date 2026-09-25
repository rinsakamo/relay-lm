#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

AUTHORITY_BRANCH = "diagnostic/llama-cpp-gemma4-swa-live-prefix-20260916"
CANONICAL_ORIGINS = {
    "https://github.com/rinsakamo/relay-lm",
    "https://github.com/rinsakamo/relay-lm.git",
    "git@github.com:rinsakamo/relay-lm.git",
}
EXPECTED_PREMEASURED_ROOT = Path("/home/rinsa/relaylm-evidence/provenance-preparation-generation-f-20260925T102433Z-474088").resolve()
HERE = Path(__file__).resolve().parent
STATIC = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-apparatus-selftest.py"
MATERIALIZER = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-descriptor.py"

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def run_capture(cmd, *, env=None):
    return subprocess.run(
        cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, env=env,
    )

def git(repo: Path, *args):
    cp = run_capture(["git", "-C", str(repo), *args])
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed rc={cp.returncode}: {cp.stderr.strip()}")
    return cp.stdout.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    args = ap.parse_args()

    out_root = args.out_root.resolve()
    model = args.model.resolve()
    if not out_root.is_absolute():
        raise SystemExit("absolute output root required")
    if out_root.exists():
        raise SystemExit(f"output root must not exist: {out_root}")
    if str(out_root).startswith("/tmp/") or str(out_root).startswith("/var/tmp/"):
        raise SystemExit("persistent non-/tmp output root required")
    if out_root == EXPECTED_PREMEASURED_ROOT or EXPECTED_PREMEASURED_ROOT in out_root.parents:
        raise SystemExit("descriptor output root must be outside sealed premeasured root")

    authority_head = os.environ.get("RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD", "")
    if not authority_head:
        raise SystemExit("RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD is required")

    repo_root = Path(git(HERE, "rev-parse", "--show-toplevel")).resolve()
    if out_root == repo_root or repo_root in out_root.parents:
        raise SystemExit("descriptor output root must be outside authority checkout")
    origin = git(repo_root, "remote", "get-url", "origin")
    if origin not in CANONICAL_ORIGINS:
        raise SystemExit(f"unexpected RelayLM authority origin: {origin}")

    remote_ref = f"refs/remotes/origin/{AUTHORITY_BRANCH}"
    branch_ref = f"refs/heads/{AUTHORITY_BRANCH}"
    fetch = run_capture([
        "git", "-C", str(repo_root), "fetch", "--quiet", "origin",
        f"+{branch_ref}:{remote_ref}",
    ])
    if fetch.returncode != 0:
        raise SystemExit(f"failed to refresh diagnostic authority: {fetch.stderr.strip()}")

    local_head = git(repo_root, "rev-parse", "HEAD")
    remote_head = git(repo_root, "rev-parse", remote_ref)
    tree = git(repo_root, "rev-parse", "HEAD^{tree}")
    dirty = git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if local_head != authority_head or remote_head != authority_head:
        raise SystemExit(
            f"authority mismatch local={local_head} remote={remote_head} expected={authority_head}"
        )
    if dirty:
        raise SystemExit("authority checkout is not clean")

    for path in (STATIC, MATERIALIZER, EXPECTED_PREMEASURED_ROOT, model):
        if not path.exists():
            raise SystemExit(f"required input missing: {path}")

    out_root.mkdir(parents=True)
    env = dict(os.environ)
    env.pop("PYTHONPYCACHEPREFIX", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    authority = {
        "authority_head": authority_head,
        "local_head": local_head,
        "remote_head": remote_head,
        "tree": tree,
        "origin": origin,
        "premeasured_root": str(EXPECTED_PREMEASURED_ROOT),
        "model": str(model),
    }
    write_json(out_root / "authority.json", authority)

    static_cp = run_capture([sys.executable, str(STATIC)], env=env)
    (out_root / "static.stdout.json").write_text(static_cp.stdout, encoding="utf-8")
    (out_root / "static.stderr.txt").write_text(static_cp.stderr, encoding="utf-8")
    (out_root / "static.exit-code.txt").write_text(f"{static_cp.returncode}\n", encoding="utf-8")
    if static_cp.returncode != 0:
        terminal = {
            "classification": "LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_TRANSACTION_FAILED",
            "stage": "static",
            "errors": [f"measured apparatus static gate failed rc={static_cp.returncode}"],
            **authority,
            "static_invocations": 1,
            "descriptor_materializer_invocations": 0,
            "physical_calls": 0,
            "gpu_calls": 0,
            "model_loads": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "measured_execution_authorized_by_this_result": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    try:
        static_obj = json.loads(static_cp.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"static gate output is not JSON: {exc}") from exc
    if static_obj.get("status") != "LAYER0_PROJECTION_PROVENANCE_MEASURED_APPARATUS_STATIC_PASS":
        raise RuntimeError("unexpected measured apparatus static classification")
    if static_obj.get("measured_execution_authorized") is not False:
        raise RuntimeError("static gate improperly authorizes measured execution")

    descriptor_path = out_root / "descriptor.json"
    materialize_cp = run_capture([
        sys.executable, str(MATERIALIZER),
        "--premeasured-root", str(EXPECTED_PREMEASURED_ROOT),
        "--model", str(model),
        "--out", str(descriptor_path),
    ], env=env)
    (out_root / "materializer.stdout.json").write_text(materialize_cp.stdout, encoding="utf-8")
    (out_root / "materializer.stderr.txt").write_text(materialize_cp.stderr, encoding="utf-8")
    (out_root / "materializer.exit-code.txt").write_text(f"{materialize_cp.returncode}\n", encoding="utf-8")
    if materialize_cp.returncode != 0:
        terminal = {
            "classification": "LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_TRANSACTION_FAILED",
            "stage": "materializer",
            "errors": [f"descriptor materializer failed rc={materialize_cp.returncode}"],
            **authority,
            "static_invocations": 1,
            "descriptor_materializer_invocations": 1,
            "physical_calls": 0,
            "gpu_calls": 0,
            "model_loads": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "measured_execution_authorized_by_this_result": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    materialized = json.loads(materialize_cp.stdout)
    if materialized.get("status") != "LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_READY":
        raise RuntimeError("unexpected descriptor materializer status")

    dirty_after = git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if dirty_after:
        raise RuntimeError("authority checkout changed during descriptor transaction")

    terminal = {
        "classification": "LAYER0_PROJECTION_PROVENANCE_MEASURED_DESCRIPTOR_TRANSACTION_READY",
        **authority,
        "static": static_obj,
        "descriptor": materialized,
        "descriptor_path": str(descriptor_path),
        "descriptor_sha256": materialized.get("descriptor_sha256"),
        "prepared_artifact_manifest_sha256": materialized.get("prepared_artifact_manifest_sha256"),
        "static_invocations": 1,
        "descriptor_materializer_invocations": 1,
        "physical_calls": 0,
        "gpu_calls": 0,
        "model_loads": 0,
        "generation_requests": 0,
        "measured_requests": 0,
        "measured_attempt_consumed": False,
        "measured_execution_authorized_by_this_result": False,
    }
    write_json(out_root / "terminal.json", terminal)
    os.chmod(descriptor_path, 0o444)
    os.chmod(out_root / "terminal.json", 0o444)
    print(json.dumps(terminal, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
