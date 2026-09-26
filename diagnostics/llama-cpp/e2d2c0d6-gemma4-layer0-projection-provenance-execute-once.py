#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ATTEMPT_ID = "layer0-projection-provenance-20260925-a"
EXPECTED_DESCRIPTOR_GENERATION = "provenance-measured-descriptor-20260925-b"
QUEUE_LEASE_FD_ENV = "RELAYLM_PHYSICAL_QUEUE_LEASE_FD"

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-run.py"
RUNNER_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-measured-run-selftest.py"
POSTHOC_SELFTEST = HERE / "e2d2c0d6-gemma4-layer0-projection-provenance-posthoc-selftest.py"
DIGEST_SELFTEST = HERE / "e2d2c0d6-gemma4-canonical-kv-directory-digest-selftest.py"
RESOURCE_GUARD = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard.py"
RESOURCE_GUARD_SELFTEST = HERE / "e2d2c0d6-gemma4-kv-logical-prefix-resource-guard-selftest.py"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: Path, *args):
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed rc={cp.returncode}: {cp.stderr.strip()}")
    return cp.stdout.strip()


def validate_descriptor_and_checkout(descriptor_path: Path, descriptor_sha: str):
    if not descriptor_path.is_file():
        raise RuntimeError(f"descriptor missing: {descriptor_path}")
    if sha256(descriptor_path) != descriptor_sha:
        raise RuntimeError("descriptor SHA mismatch before execute-once preflight")
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if descriptor.get("descriptor_generation") != EXPECTED_DESCRIPTOR_GENERATION:
        raise RuntimeError("descriptor generation mismatch before execute-once preflight")
    if descriptor.get("measured_attempt_id") != ATTEMPT_ID:
        raise RuntimeError("descriptor measured attempt mismatch before execute-once preflight")

    repo_root = HERE.parents[1]
    head = git(repo_root, "rev-parse", "HEAD")
    tree = git(repo_root, "rev-parse", "HEAD^{tree}")
    dirty = git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise RuntimeError("measured authority checkout is not clean")
    if descriptor.get("measured_authority_head") != head:
        raise RuntimeError("descriptor measured authority HEAD differs from current checkout")
    if descriptor.get("measured_authority_tree") != tree:
        raise RuntimeError("descriptor measured authority tree differs from current checkout")

    gpu_inventory = descriptor.get("preparation_gpu_inventory")
    if not isinstance(gpu_inventory, list) or len(gpu_inventory) != 1:
        raise RuntimeError("descriptor preparation GPU inventory invalid")

    return descriptor, {"head": head, "tree": tree}


def measured_seal_sha(root: Path):
    terminal_path = root / "terminal.json"
    manifest = root / "measured-artifact-manifest.sha256"
    if not terminal_path.is_file() or not manifest.is_file() or not root.is_dir():
        return None
    if root.stat().st_mode & 0o222 or manifest.stat().st_mode & 0o222:
        return None
    expected = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            return None
        digest, name = parts
        expected[name.strip()] = digest
    if "terminal.json" not in expected:
        return None
    actual_files = {
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and p != manifest
    }
    if actual_files != set(expected):
        return None
    for name, digest in expected.items():
        p = root / name
        resolved = p.resolve()
        if root.resolve() not in resolved.parents:
            return None
        if not p.is_file() or sha256(p) != digest:
            return None
        if p.stat().st_mode & 0o222:
            return None
    for p in root.rglob("*"):
        if p.is_dir() and p.stat().st_mode & 0o222:
            return None
    return sha256(manifest)


def seal_preflight_root(root: Path):
    manifest = root / "execute-once-artifact-manifest.sha256"
    records = []
    for p in sorted(root.rglob("*")):
        if p == manifest:
            continue
        if p.is_symlink():
            raise RuntimeError(f"execute-once evidence symlink forbidden: {p}")
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

def run_json(label: str, path: Path, preflight_root: Path, expected_status: str):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    cp = subprocess.run(
        [sys.executable, "-B", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )
    (preflight_root / f"{label}.stdout").write_bytes(cp.stdout)
    (preflight_root / f"{label}.stderr").write_bytes(cp.stderr)
    if cp.returncode != 0:
        raise RuntimeError(f"{label} failed rc={cp.returncode}")
    obj = json.loads(cp.stdout)
    if obj.get("status") != expected_status:
        raise RuntimeError(f"{label}: unexpected status {obj.get('status')}")
    return obj

def reconcile(out_root: Path, child_rc: int):
    terminal_path = out_root / "terminal.json"
    w_record = out_root / "server-W" / "W.request.json"
    c_record = out_root / "server-C" / "C.request.json"

    seal_sha = measured_seal_sha(out_root)
    if terminal_path.is_file() and seal_sha is not None:
        measured = json.loads(terminal_path.read_text(encoding="utf-8"))
        return {
            "primary_classification": measured.get("primary_classification"),
            "measured_terminal_present": True,
            "measured_attempt_consumed": True,
            "measured_w_submitted": True,
            "measured_c_submitted": True,
            "rerun_authorized": False,
            "child_returncode": child_rc,
            "measured_terminal": measured,
            "measured_artifact_manifest_sha256": seal_sha,
            "measured_evidence_sealed": True,
        }

    if w_record.is_file() or terminal_path.is_file():
        return {
            "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_EXERCISED_INCOMPLETE",
            "measured_terminal_present": False,
            "measured_attempt_consumed": True,
            "measured_w_submitted": True,
            "measured_c_submitted": c_record.is_file(),
            "rerun_authorized": False,
            "child_returncode": child_rc,
        }

    return {
        "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED",
        "measured_terminal_present": False,
        "measured_attempt_consumed": False,
        "measured_w_submitted": False,
        "measured_c_submitted": False,
        "rerun_authorized": False,
        "child_returncode": child_rc,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--descriptor", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--preflight-root", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--port-w", type=int, required=True)
    ap.add_argument("--port-c", type=int, required=True)
    args = ap.parse_args()

    descriptor_sha = os.environ.get("RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256", "")
    if len(descriptor_sha) != 64:
        raise SystemExit("RELAYLM_PROVENANCE_MEASURED_DESCRIPTOR_SHA256 is required")
    queue_lease_text = os.environ.get(QUEUE_LEASE_FD_ENV, "")
    if not queue_lease_text.isdigit() or int(queue_lease_text) <= 2:
        raise SystemExit("canonical physical queue lease fd is required")
    queue_lease_fd = int(queue_lease_text)
    try:
        descriptor, authority_identity = validate_descriptor_and_checkout(
            args.descriptor, descriptor_sha
        )
    except Exception as exc:
        raise SystemExit(
            f"descriptor/authority preflight failed: {type(exc).__name__}: {exc}"
        ) from exc
    if args.preflight_root.exists():
        raise SystemExit(f"preflight root must not exist: {args.preflight_root}")
    if args.out_root.exists():
        raise SystemExit(f"measured output root must not exist: {args.out_root}")
    args.preflight_root.mkdir(parents=True)
    expected_gpu_path = args.preflight_root / "expected-preparation-gpu-inventory.json"
    write_json(expected_gpu_path, descriptor["preparation_gpu_inventory"])
    write_json(args.preflight_root / "measured-authority.json", authority_identity)

    required = [
        RUNNER, RUNNER_SELFTEST, POSTHOC_SELFTEST, DIGEST_SELFTEST,
        RESOURCE_GUARD, RESOURCE_GUARD_SELFTEST,
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        write_json(args.preflight_root / "terminal.json", {
            "attempt_id": ATTEMPT_ID,
            "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED",
            "stage": "helper_presence",
            "reason": f"missing helpers: {missing}",
            "measured_attempt_consumed": False,
            "rerun_authorized": False,
        })
        return 3

    for path in required:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            write_json(args.preflight_root / "terminal.json", {
                "attempt_id": ATTEMPT_ID,
                "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED",
                "stage": "compile",
                "reason": f"in-memory compile failed: {path}: {exc}",
                "measured_attempt_consumed": False,
                "rerun_authorized": False,
            })
            return 4

    try:
        run_json(
            "runner-selftest", RUNNER_SELFTEST, args.preflight_root,
            "LAYER0_PROJECTION_PROVENANCE_MEASURED_RUNNER_SELFTEST_PASS",
        )
        run_json(
            "digest-selftest", DIGEST_SELFTEST, args.preflight_root,
            "CANONICAL_KV_DIRECTORY_DIGEST_SELFTEST_PASS",
        )
        run_json(
            "resource-guard-selftest", RESOURCE_GUARD_SELFTEST, args.preflight_root,
            "LOGICAL_PREFIX_RESOURCE_GUARD_SELFTEST_PASS",
        )
        run_json(
            "posthoc-selftest", POSTHOC_SELFTEST, args.preflight_root,
            "LAYER0_PROJECTION_PROVENANCE_POSTHOC_SELFTEST_PASS",
        )

        preflight_cmd = [
            sys.executable, "-B", str(RUNNER),
            "--descriptor", str(args.descriptor),
            "--model", str(args.model),
            "--port-w", str(args.port_w),
            "--port-c", str(args.port_c),
            "--preflight-only",
        ]
        pf = subprocess.run(preflight_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        (args.preflight_root / "measured-runner-preflight.stdout.json").write_bytes(pf.stdout)
        (args.preflight_root / "measured-runner-preflight.stderr.txt").write_bytes(pf.stderr)
        if pf.returncode != 0:
            raise RuntimeError(f"measured runner preflight failed rc={pf.returncode}")
        pf_obj = json.loads(pf.stdout)
        if pf_obj.get("classification") != "LAYER0_PROJECTION_PROVENANCE_MEASURED_PREFLIGHT_PASS":
            raise RuntimeError("unexpected measured preflight classification")
        if pf_obj.get("descriptor_sha256") != descriptor_sha:
            raise RuntimeError("measured preflight descriptor SHA mismatch")
    except Exception as exc:
        write_json(args.preflight_root / "terminal.json", {
            "attempt_id": ATTEMPT_ID,
            "primary_classification": "LAYER0_PROJECTION_PROVENANCE_PROBE_NOT_EXERCISED",
            "stage": "static_preflight",
            "reason": f"{type(exc).__name__}: {exc}",
            "measured_attempt_consumed": False,
            "rerun_authorized": False,
        })
        return 5

    measured_cmd = [
        sys.executable, "-B", str(RUNNER),
        "--descriptor", str(args.descriptor),
        "--model", str(args.model),
        "--out-root", str(args.out_root),
        "--port-w", str(args.port_w),
        "--port-c", str(args.port_c),
    ]
    write_json(args.preflight_root / "measured-child.argv.json", measured_cmd)

    guard_root = args.preflight_root / "resource-guard"
    guard_cmd = [
        sys.executable, str(RESOURCE_GUARD),
        "--evidence-root", str(guard_root),
        "--expected-gpu-inventory", str(expected_gpu_path),
        "--inherited-lock-fd", str(queue_lease_fd),
        "--",
        *measured_cmd,
    ]
    cp = subprocess.run(guard_cmd, check=False, pass_fds=(queue_lease_fd,))
    result = reconcile(args.out_root, cp.returncode)

    try:
        guard = json.loads((guard_root / "guard.json").read_text(encoding="utf-8"))
        quiescence = json.loads((guard_root / "external-quiescence.json").read_text(encoding="utf-8"))
    except Exception:
        guard = None
        quiescence = None

    result.update({
        "attempt_id": ATTEMPT_ID,
        "descriptor_sha256": descriptor_sha,
        "descriptor_generation": EXPECTED_DESCRIPTOR_GENERATION,
        "measured_authority_head": authority_identity["head"],
        "measured_authority_tree": authority_identity["tree"],
        "resource_guard": guard,
        "external_quiescence": quiescence,
        "campaign_queue_receipt_created": False,
        "campaign_queue_or_spend_artifact_touched": False,
    })
    write_json(args.preflight_root / "terminal.json", result)
    preflight_manifest_sha = seal_preflight_root(args.preflight_root)
    output = {
        **result,
        "execute_once_artifact_manifest_sha256": preflight_manifest_sha,
        "execute_once_root_mode": "0555",
    }
    print(json.dumps(output, indent=2, sort_keys=True))

    if result["measured_terminal_present"]:
        return cp.returncode
    return 6 if result["measured_attempt_consumed"] else 7

if __name__ == "__main__":
    raise SystemExit(main())
