#!/usr/bin/env python3
import argparse
import hashlib
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
EXPECTED_DESCRIPTOR_GENERATION = "provenance-measured-descriptor-20260925-b"
EXPECTED_ATTEMPT_ID = "layer0-projection-provenance-20260925-a"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_output_root(root: Path):
    records = []
    manifest = root / "descriptor-artifact-manifest.sha256"
    for p in sorted(root.rglob("*")):
        if p == manifest:
            continue
        if p.is_symlink():
            raise RuntimeError(f"descriptor evidence symlink forbidden: {p}")
        if p.is_file():
            records.append((str(p.relative_to(root)), sha256(p)))
    manifest.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in records),
        encoding="utf-8",
    )
    manifest_sha = sha256(manifest)
    for p in sorted(root.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if p.is_file():
            os.chmod(p, 0o444)
        elif p.is_dir():
            os.chmod(p, 0o555)
    os.chmod(root, 0o555)
    return manifest_sha


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

def refresh_authority(repo_root: Path, authority_head: str):
    remote_ref = f"refs/remotes/origin/{AUTHORITY_BRANCH}"
    branch_ref = f"refs/heads/{AUTHORITY_BRANCH}"
    fetch = run_capture([
        "git", "-C", str(repo_root), "fetch", "--quiet", "origin",
        f"+{branch_ref}:{remote_ref}",
    ])
    if fetch.returncode != 0:
        raise RuntimeError(f"failed to refresh diagnostic authority: {fetch.stderr.strip()}")
    remote_head = git(repo_root, "rev-parse", remote_ref)
    if remote_head != authority_head:
        raise RuntimeError(
            f"diagnostic authority moved: remote={remote_head} expected={authority_head}"
        )
    return remote_head


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

    local_head = git(repo_root, "rev-parse", "HEAD")
    try:
        remote_head = refresh_authority(repo_root, authority_head)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
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
    for key in ("PYTHONPYCACHEPREFIX", "PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"

    authority = {
        "authority_head": authority_head,
        "local_head": local_head,
        "remote_head": remote_head,
        "tree": tree,
        "origin": origin,
        "premeasured_root": str(EXPECTED_PREMEASURED_ROOT),
        "model": str(model),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "isolated": bool(sys.flags.isolated),
            "no_user_site": bool(sys.flags.no_user_site),
            "dont_write_bytecode": bool(sys.dont_write_bytecode),
        },
    }
    write_json(out_root / "authority.json", authority)

    static_cp = run_capture([sys.executable, "-B", "-I", str(STATIC)], env=env)
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
    if static_obj.get("descriptor_generation") != EXPECTED_DESCRIPTOR_GENERATION:
        raise RuntimeError("static gate descriptor generation mismatch")
    if static_obj.get("attempt_id") != EXPECTED_ATTEMPT_ID:
        raise RuntimeError("static gate measured attempt mismatch")

    remote_head = refresh_authority(repo_root, authority_head)
    dirty_mid = git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if dirty_mid:
        raise RuntimeError("authority checkout changed during static qualification")

    descriptor_path = out_root / "descriptor.json"
    materialize_cp = run_capture([
        sys.executable, "-B", "-I", str(MATERIALIZER),
        "--premeasured-root", str(EXPECTED_PREMEASURED_ROOT),
        "--model", str(model),
        "--out", str(descriptor_path),
        "--measured-authority-head", local_head,
        "--measured-authority-tree", tree,
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
    if materialized.get("descriptor_generation") != EXPECTED_DESCRIPTOR_GENERATION:
        raise RuntimeError("materialized descriptor generation mismatch")
    if materialized.get("measured_attempt_id") != EXPECTED_ATTEMPT_ID:
        raise RuntimeError("materialized measured attempt mismatch")
    if (
        materialized.get("measured_authority_head") != local_head
        or materialized.get("measured_authority_tree") != tree
    ):
        raise RuntimeError("materialized measured authority identity mismatch")

    remote_head = refresh_authority(repo_root, authority_head)
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
    manifest_sha = seal_output_root(out_root)
    output = {
        **terminal,
        "descriptor_artifact_manifest_sha256": manifest_sha,
        "descriptor_root_mode": "0555",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
