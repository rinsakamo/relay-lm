#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "e2d2c0d6-gemma4-kv-segmentation-control-measured-run.py"

EXPECTED_ATTEMPT = "logical-prefix-kv-segmentation-control-20260922-6802c20c"
EXPECTED_W_SHA = "d777877485b3307d8ee76e6b6df783d00b4302bb700c405ac5cbf2f6d7344f5d"
EXPECTED_C883_SHA = "1e490f609ac0b844521784cd4603ea79a9c5ab0b199117e4395c4a8cf2efa47c"
EXPECTED_REQUESTS = ("W", "W2", "C883")
EXPECTED_DUMPS = ("W-P512", "W2-P512", "C883-P512")


def load_runner():
    spec = importlib.util.spec_from_file_location("segmentation_control_runner_forensic", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load consumed runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def require_equal(actual, expected, message):
    if actual != expected:
        raise RuntimeError(f"{message}: {actual!r} != {expected!r}")


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_consumed_terminal(measured_root: Path):
    terminal_path = measured_root / "terminal.json"
    require(terminal_path.is_file(), "consumed measured terminal missing")
    terminal = load_json(terminal_path)
    require_equal(terminal.get("attempt_id"), EXPECTED_ATTEMPT, "attempt id")
    require_equal(
        terminal.get("primary_classification"),
        "PROBE_EXERCISED_INCOMPLETE",
        "consumed terminal classification",
    )
    require(terminal.get("measured_w_submitted") is True, "measured W must be submitted")
    require(terminal.get("measured_attempt_consumed") is True, "attempt must be consumed")
    require(terminal.get("rerun_authorized") is False, "rerun must be false")
    require_equal(
        terminal.get("submitted_requests"),
        list(EXPECTED_REQUESTS),
        "submitted request sequence",
    )
    require_equal(terminal.get("request_count_submitted"), 3, "submitted request count")
    reason = terminal.get("reason")
    require(isinstance(reason, str), "terminal reason missing")
    for old_name in ("WR-P512", "WR-R512", "WR2-P512", "C-P512"):
        require(old_name in reason, f"expected old geometry name absent from reason: {old_name}")
    return terminal_path, terminal


def validate_request_and_response(measured_root: Path, label: str, expected_sha: str):
    server_dir = measured_root / f"server-{label}"
    request_path = server_dir / f"{label}.request.json"
    response_path = server_dir / f"{label}.response.raw.json"
    http_path = server_dir / f"{label}.http.json"

    require(request_path.is_file(), f"{label} request record missing")
    require(response_path.is_file(), f"{label} response record missing")
    require(http_path.is_file(), f"{label} HTTP record missing")
    require_equal(sha256(request_path), expected_sha, f"{label} request SHA")

    http = load_json(http_path)
    require_equal(http.get("status"), 200, f"{label} HTTP status")

    response = load_json(response_path)
    timings = response.get("timings")
    require(isinstance(timings, dict), f"{label} timings missing")
    require_equal(timings.get("cache_n"), 0, f"{label} cache_n")
    require_equal(timings.get("prompt_n"), 883, f"{label} prompt_n")
    require_equal(timings.get("predicted_n"), 1, f"{label} predicted_n")

    return {
        "server_dir": str(server_dir),
        "request_path": str(request_path),
        "request_sha256": expected_sha,
        "response_path": str(response_path),
        "response_sha256": sha256(response_path),
        "http_path": str(http_path),
        "http_status": 200,
        "timings": {
            "cache_n": 0,
            "prompt_n": 883,
            "predicted_n": 1,
        },
        "response": response,
    }


def require_three_point_geometry(dump_geometry: dict):
    required = EXPECTED_DUMPS
    missing = [name for name in required if name not in dump_geometry]
    require(not missing, f"missing dump geometry records: {missing}")

    signature_fields = ("kv_size", "v_trans", "logical_rows", "layer_count")
    baseline_name = required[0]
    baseline = {
        cache_name: {
            field: dump_geometry[baseline_name][cache_name][field]
            for field in signature_fields
        }
        for cache_name in ("base", "swa")
    }

    for name in required[1:]:
        current = {
            cache_name: {
                field: dump_geometry[name][cache_name][field]
                for field in signature_fields
            }
            for cache_name in ("base", "swa")
        }
        require_equal(current, baseline, f"dump geometry differs: {name}")

    return {
        "baseline": baseline_name,
        "signature": baseline,
        "observations": list(required),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measured-root", type=Path, required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    args = ap.parse_args()

    if args.out_root.exists():
        raise SystemExit(f"output root must not exist: {args.out_root}")
    require(args.measured_root.is_dir(), "measured root missing")
    args.out_root.mkdir(parents=True)

    runner = load_runner()

    try:
        terminal_path, measured_terminal = validate_consumed_terminal(args.measured_root)

        observations = {
            "W": validate_request_and_response(
                args.measured_root, "W", EXPECTED_W_SHA
            ),
            "W2": validate_request_and_response(
                args.measured_root, "W2", EXPECTED_W_SHA
            ),
            "C883": validate_request_and_response(
                args.measured_root, "C883", EXPECTED_C883_SHA
            ),
        }

        kv_root = args.measured_root / "kv"
        require(kv_root.is_dir(), "KV root missing")

        dump_geometry = {
            name: runner.require_dump(kv_root, name)
            for name in EXPECTED_DUMPS
        }
        geometry_consistency = require_three_point_geometry(dump_geometry)

        comparison = runner.compare_three_dumps(kv_root)
        derived = comparison.get("classification")
        require(
            derived in {
                "SEGMENTATION_CONTROL_WARM_NOT_REPRODUCIBLE",
                "SEGMENTATION_CONTROL_KV_IDENTICAL",
                "SEGMENTATION_CONTROL_KV_DIFFERS",
            },
            f"unexpected derived classification: {derived}",
        )

        api = runner.api_compare(
            observations["W"]["response"],
            observations["C883"]["response"],
        )

        forensic = {
            "status": "SEGMENTATION_CONTROL_POSTHOC_RECONCILED",
            "source_measured_terminal": {
                "path": str(terminal_path),
                "sha256": sha256(terminal_path),
                "classification": measured_terminal.get("primary_classification"),
                "consumed": measured_terminal.get("measured_attempt_consumed"),
            },
            "derived_measured_classification": derived,
            "measured_attempt_remains_consumed": True,
            "rerun_authorized": False,
            "observations": {
                key: {k: v for k, v in value.items() if k != "response"}
                for key, value in observations.items()
            },
            "dump_geometry": dump_geometry,
            "geometry_consistency": geometry_consistency,
            "kv_comparison": comparison,
            "api_W_vs_C883": api,
            "model_calls": 0,
            "server_startups": 0,
            "gpu_guard_acquisitions": 0,
            "http_requests": 0,
            "subprocess_transitions": 0,
        }

        write_json(args.out_root / "geometry.json", {
            "dump_geometry": dump_geometry,
            "consistency": geometry_consistency,
        })
        write_json(args.out_root / "kv-comparison.json", comparison)
        write_json(args.out_root / "api-W-vs-C883.json", api)
        write_json(args.out_root / "terminal.json", forensic)
        print(json.dumps(forensic, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        failure = {
            "status": "SEGMENTATION_CONTROL_POSTHOC_NOT_RECONCILED",
            "reason": str(exc),
            "measured_attempt_remains_consumed": True,
            "rerun_authorized": False,
            "model_calls": 0,
            "server_startups": 0,
            "gpu_guard_acquisitions": 0,
            "http_requests": 0,
            "subprocess_transitions": 0,
        }
        write_json(args.out_root / "terminal.json", failure)
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
