#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

EXPECTED_GENERATION = "provenance-preparation-20260924-f"
EXPECTED_PREP_ROOT = Path("/home/rinsa/relaylm-evidence/provenance-preparation-20260924-e-20260924T002328-107161")
EXPECTED_MODEL = Path("/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf")
AUTHORITY_BRANCH = "diagnostic/llama-cpp-gemma4-swa-live-prefix-20260916"
CANONICAL_ORIGINS = {
    "https://github.com/rinsakamo/relay-lm",
    "https://github.com/rinsakamo/relay-lm.git",
    "git@github.com:rinsakamo/relay-lm.git",
}

HERE = Path(__file__).resolve().parent
STATIC_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-preparation-static-selftest.py"
PREFLIGHT = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-binary-preflight.py"
RECONCILE = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-generation-e-binary-marker-reconcile.py"

PRESERVED_SERVER = EXPECTED_PREP_ROOT / "build-stage" / "build" / "bin" / "llama-server"

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def run_capture(cmd, *, env=None):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )

def git(repo: Path, *args):
    cp = run_capture(["git", "-C", str(repo), *args])
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed rc={cp.returncode}: {cp.stderr.strip()}")
    return cp.stdout.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", type=Path, required=True)
    args = ap.parse_args()

    out_root = args.out_root
    if not out_root.is_absolute():
        raise SystemExit("absolute output root required")
    if out_root.exists():
        raise SystemExit(f"output root must not exist: {out_root}")
    if str(out_root).startswith("/tmp/") or str(out_root).startswith("/var/tmp/"):
        raise SystemExit("persistent non-/tmp output root required")

    authority_head = os.environ.get("RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD", "")
    if not authority_head:
        raise SystemExit("RELAYLM_DIAGNOSTIC_AUTHORITY_HEAD is required")

    repo_root_text = git(HERE, "rev-parse", "--show-toplevel")
    repo_root = Path(repo_root_text).resolve()
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

    for path in (STATIC_SELFTEST, PREFLIGHT, RECONCILE, PRESERVED_SERVER, EXPECTED_MODEL):
        if not path.is_file():
            raise SystemExit(f"required input missing: {path}")

    # Never place output inside the preserved failed-e evidence or authority checkout.
    resolved_out = out_root.resolve()
    preserved_root = EXPECTED_PREP_ROOT.resolve()
    if resolved_out == preserved_root or preserved_root in resolved_out.parents:
        raise SystemExit("output root must be outside preserved generation-e evidence")
    if resolved_out == repo_root or repo_root in resolved_out.parents:
        raise SystemExit("output root must be outside authority checkout")

    out_root.mkdir(parents=True)
    pycache = out_root / "pycache"
    env = dict(os.environ)
    env["PYTHONPYCACHEPREFIX"] = str(pycache)

    authority = {
        "authority_head": authority_head,
        "local_head": local_head,
        "remote_head": remote_head,
        "tree": tree,
        "origin": origin,
        "generation": EXPECTED_GENERATION,
        "preserved_generation_e_root": str(preserved_root),
        "model": str(EXPECTED_MODEL),
        "server": str(PRESERVED_SERVER),
    }
    write_json(out_root / "authority.json", authority)

    # Stage 1: canonical generation-f static qualification, exactly once.
    static_cp = run_capture([sys.executable, str(STATIC_SELFTEST)], env=env)
    (out_root / "static.stdout.txt").write_text(static_cp.stdout, encoding="utf-8")
    (out_root / "static.stderr.txt").write_text(static_cp.stderr, encoding="utf-8")
    (out_root / "static.exit-code.txt").write_text(f"{static_cp.returncode}\n", encoding="utf-8")

    if static_cp.returncode != 0:
        terminal = {
            "classification": "GENERATION_F_ZERO_GPU_QUALIFICATION_FAILED",
            "stage": "static",
            "errors": [f"canonical static gate failed rc={static_cp.returncode}"],
            **authority,
            "canonical_static_invocations": 1,
            "repaired_preflight_invocations": 0,
            "reconciliation_invocations": 0,
            "build_invocations": 0,
            "model_startups": 0,
            "gpu_runtime_calls": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "scientific_spend_consumed": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    try:
        static_json = json.loads(static_cp.stdout)
    except json.JSONDecodeError as exc:
        terminal = {
            "classification": "GENERATION_F_ZERO_GPU_QUALIFICATION_FAILED",
            "stage": "static-parse",
            "errors": [f"canonical static output not JSON: {exc}"],
            **authority,
            "canonical_static_invocations": 1,
            "repaired_preflight_invocations": 0,
            "reconciliation_invocations": 0,
            "build_invocations": 0,
            "model_startups": 0,
            "gpu_runtime_calls": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "scientific_spend_consumed": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    if (
        static_json.get("status") != "LAYER0_PROJECTION_PROVENANCE_PREPARATION_APPARATUS_STATIC_PASS"
        or static_json.get("preparation_generation") != EXPECTED_GENERATION
        or static_json.get("measured_execution_authorized") is not False
    ):
        terminal = {
            "classification": "GENERATION_F_ZERO_GPU_QUALIFICATION_FAILED",
            "stage": "static-classification",
            "errors": ["canonical static classification/generation mismatch"],
            **authority,
            "canonical_static_invocations": 1,
            "repaired_preflight_invocations": 0,
            "reconciliation_invocations": 0,
            "build_invocations": 0,
            "model_startups": 0,
            "gpu_runtime_calls": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "scientific_spend_consumed": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    # Stage 2: repaired binary preflight on the exact preserved generation-e binary closure.
    preflight_json_path = out_root / "repaired-binary-preflight.json"
    preflight_cp = run_capture([
        sys.executable,
        str(PREFLIGHT),
        "--server-bin", str(PRESERVED_SERVER),
        "--model", str(EXPECTED_MODEL),
        "--out", str(preflight_json_path),
    ], env=env)
    (out_root / "repaired-preflight.stdout.txt").write_text(preflight_cp.stdout, encoding="utf-8")
    (out_root / "repaired-preflight.stderr.txt").write_text(preflight_cp.stderr, encoding="utf-8")
    (out_root / "repaired-preflight.exit-code.txt").write_text(f"{preflight_cp.returncode}\n", encoding="utf-8")

    if preflight_cp.returncode != 0:
        terminal = {
            "classification": "GENERATION_F_ZERO_GPU_QUALIFICATION_FAILED",
            "stage": "repaired-preflight",
            "errors": [f"repaired binary preflight failed rc={preflight_cp.returncode}"],
            **authority,
            "canonical_static_invocations": 1,
            "repaired_preflight_invocations": 1,
            "reconciliation_invocations": 0,
            "build_invocations": 0,
            "model_startups": 0,
            "gpu_runtime_calls": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "scientific_spend_consumed": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    # Stage 3: historical-failure + repaired-preflight reconciliation, exactly once.
    reconcile_out = out_root / "reconciliation"
    reconcile_cp = run_capture([
        sys.executable,
        str(RECONCILE),
        "--prep-root", str(EXPECTED_PREP_ROOT),
        "--current-preflight", str(preflight_json_path),
        "--out", str(reconcile_out),
    ], env=env)
    (out_root / "reconciliation.stdout.txt").write_text(reconcile_cp.stdout, encoding="utf-8")
    (out_root / "reconciliation.stderr.txt").write_text(reconcile_cp.stderr, encoding="utf-8")
    (out_root / "reconciliation.exit-code.txt").write_text(f"{reconcile_cp.returncode}\n", encoding="utf-8")

    if reconcile_cp.returncode != 0:
        terminal = {
            "classification": "GENERATION_F_ZERO_GPU_QUALIFICATION_FAILED",
            "stage": "reconciliation",
            "errors": [f"generation-e reconciliation failed rc={reconcile_cp.returncode}"],
            **authority,
            "canonical_static_invocations": 1,
            "repaired_preflight_invocations": 1,
            "reconciliation_invocations": 1,
            "build_invocations": 0,
            "model_startups": 0,
            "gpu_runtime_calls": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "scientific_spend_consumed": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    reconciliation = json.loads((reconcile_out / "terminal.json").read_text(encoding="utf-8"))
    if reconciliation.get("classification") != "GENERATION_E_BINARY_MARKER_FALSE_NEGATIVE_RECONCILED":
        terminal = {
            "classification": "GENERATION_F_ZERO_GPU_QUALIFICATION_FAILED",
            "stage": "reconciliation-classification",
            "errors": ["unexpected reconciliation classification"],
            **authority,
            "canonical_static_invocations": 1,
            "repaired_preflight_invocations": 1,
            "reconciliation_invocations": 1,
            "build_invocations": 0,
            "model_startups": 0,
            "gpu_runtime_calls": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "scientific_spend_consumed": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    dirty_after = git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if dirty_after:
        terminal = {
            "classification": "GENERATION_F_ZERO_GPU_QUALIFICATION_FAILED",
            "stage": "authority-dirty-after",
            "errors": ["authority checkout changed during zero-GPU qualification"],
            **authority,
            "canonical_static_invocations": 1,
            "repaired_preflight_invocations": 1,
            "reconciliation_invocations": 1,
            "build_invocations": 0,
            "model_startups": 0,
            "gpu_runtime_calls": 0,
            "generation_requests": 0,
            "measured_requests": 0,
            "measured_attempt_consumed": False,
            "scientific_spend_consumed": False,
        }
        write_json(out_root / "terminal.json", terminal)
        print(json.dumps(terminal, indent=2, sort_keys=True))
        return 1

    terminal = {
        "classification": "GENERATION_F_STATIC_AND_E_RECONCILIATION_PASS",
        **authority,
        "static": static_json,
        "repaired_preflight_path": str(preflight_json_path),
        "reconciliation_path": str(reconcile_out / "terminal.json"),
        "canonical_static_invocations": 1,
        "repaired_preflight_invocations": 1,
        "reconciliation_invocations": 1,
        "build_invocations": 0,
        "model_startups": 0,
        "gpu_runtime_calls": 0,
        "generation_requests": 0,
        "measured_requests": 0,
        "measured_attempt_consumed": False,
        "scientific_spend_consumed": False,
        "measured_execution_authorized_by_this_result": False,
    }
    write_json(out_root / "terminal.json", terminal)
    print(json.dumps(terminal, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
