#!/usr/bin/env python3
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import sys


def load_runner():
    here = Path(__file__).resolve().parent
    runner_path = here / "e2d2c0d6-gemma4-kv-prefix-provenance-run.py"
    spec = importlib.util.spec_from_file_location("kv_prefix_provenance_runner_contract", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load KV provenance runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_dump(root: Path, name: str, *, base_kv_size: int = 8192, swa_kv_size: int = 1536):
    dump = root / name
    dump.mkdir(parents=True)
    for cache_name, layer in (("base", 0), ("swa", 1)):
        kv_size = base_kv_size if cache_name == "base" else swa_kv_size
        cells = dump / f"{cache_name}.cells.tsv"
        with cells.open("w", encoding="utf-8") as out:
            out.write("cache\tstream\thead\tkv_size\tv_trans\tposition\tcell\n")
            for pos in range(512):
                out.write(f"{cache_name}\t0\t0\t{kv_size}\t0\t{pos}\t{pos}\n")

        manifest = dump / f"{cache_name}.manifest.tsv"
        with manifest.open("w", encoding="utf-8") as out:
            out.write("cache\tlayer\tkind\ttype\trow_bytes\trows\n")
            out.write(f"{cache_name}\t{layer}\tK\tf16\t2\t512\n")
            out.write(f"{cache_name}\t{layer}\tV\tf16\t2\t512\n")

        (dump / f"{cache_name}.layer-{layer}.K.bin").write_bytes(b"K" * 1024)
        (dump / f"{cache_name}.layer-{layer}.V.bin").write_bytes(b"V" * 1024)
    return dump


def expect_runtime_error(fn):
    try:
        fn()
    except RuntimeError:
        return True
    return False


def success_path_static_check():
    here = Path(__file__).resolve().parent
    runner_path = here / "e2d2c0d6-gemma4-kv-prefix-provenance-run.py"
    tree = ast.parse(runner_path.read_text(encoding="utf-8"))
    main_fn = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"),
        None,
    )
    if main_fn is None:
        return {
            "ok": False,
            "reason": "runner main() not found",
        }

    assignments = []
    loads = []
    terminal_refs = []
    for node in ast.walk(main_fn):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "geometry_consistency" for t in node.targets):
                if (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "require_consistent_dump_geometry"
                ):
                    assignments.append(node.lineno)
        if isinstance(node, ast.Name) and node.id == "geometry_consistency" and isinstance(node.ctx, ast.Load):
            loads.append(node.lineno)
        if isinstance(node, ast.Dict):
            keys = node.keys
            values = node.values
            for key, value in zip(keys, values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "kv_dump_geometry_consistency"
                    and isinstance(value, ast.Name)
                    and value.id == "geometry_consistency"
                ):
                    terminal_refs.append(node.lineno)

    ok = (
        len(assignments) == 1
        and len(terminal_refs) == 1
        and loads
        and assignments[0] < min(loads)
        and assignments[0] < terminal_refs[0]
    )
    return {
        "ok": ok,
        "assignment_lines": assignments,
        "load_lines": sorted(loads),
        "terminal_reference_lines": terminal_refs,
    }


def main():
    runner = load_runner()
    results = []

    static_check = success_path_static_check()
    results.append({
        "name": "success_path_geometry_consistency_bound_before_terminal",
        "ok": static_check["ok"],
        "observed": static_check,
    })

    with tempfile.TemporaryDirectory(prefix="relaylm-kv-contract-") as td:
        root = Path(td)

        make_dump(root, "valid")
        try:
            runner.require_dump(root, "valid")
            valid_ok = True
        except Exception:
            valid_ok = False
        results.append({"name": "valid_dump_passes", "ok": valid_ok})

        full_swa = make_dump(root, "full-swa", base_kv_size=8192, swa_kv_size=8192)
        results.append({
            "name": "full_size_swa_fails_compact_contract",
            "ok": expect_runtime_error(lambda: runner.require_dump(root, "full-swa")),
        })

        wrong_base = make_dump(root, "wrong-base", base_kv_size=4096, swa_kv_size=1536)
        results.append({
            "name": "wrong_base_kv_size_fails",
            "ok": expect_runtime_error(lambda: runner.require_dump(root, "wrong-base")),
        })

        truncated = make_dump(root, "truncated")
        (truncated / "base.layer-0.K.bin").write_bytes(b"K" * 1023)
        results.append({
            "name": "truncated_payload_fails",
            "ok": expect_runtime_error(lambda: runner.require_dump(root, "truncated")),
        })

        missing_meta = make_dump(root, "missing-meta")
        (missing_meta / "swa.manifest.tsv").unlink()
        results.append({
            "name": "missing_metadata_fails",
            "ok": expect_runtime_error(lambda: runner.require_dump(root, "missing-meta")),
        })

        bad_pos = make_dump(root, "bad-position")
        cells = bad_pos / "base.cells.tsv"
        lines = cells.read_text(encoding="utf-8").splitlines()
        fields = lines[-1].split("\t")
        fields[5] = "510"
        lines[-1] = "\t".join(fields)
        cells.write_text("\n".join(lines) + "\n", encoding="utf-8")
        results.append({
            "name": "logical_position_drift_fails",
            "ok": expect_runtime_error(lambda: runner.require_dump(root, "bad-position")),
        })

        missing_pair = make_dump(root, "missing-pair")
        manifest = missing_pair / "base.manifest.tsv"
        lines = manifest.read_text(encoding="utf-8").splitlines()
        manifest.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
        (missing_pair / "base.layer-0.V.bin").unlink()
        results.append({
            "name": "missing_kv_pair_fails",
            "ok": expect_runtime_error(lambda: runner.require_dump(root, "missing-pair")),
        })

    consistent_geometry = {
        name: {
            "base": {"stream": 0, "kv_size": 8192, "v_trans": 0, "logical_rows": 512, "layer_count": 1},
            "swa": {"stream": 0, "kv_size": 1536, "v_trans": 0, "logical_rows": 512, "layer_count": 1},
        }
        for name in ("WR-P512", "WR-R512", "WR2-P512", "C-P512")
    }
    try:
        consistency = runner.require_consistent_dump_geometry(consistent_geometry)
        geometry_ok = consistency["signature"]["base"]["kv_size"] == 8192 and consistency["signature"]["swa"]["kv_size"] == 1536
    except Exception:
        geometry_ok = False
    results.append({"name": "consistent_dump_geometry_passes", "ok": geometry_ok})

    inconsistent_geometry = json.loads(json.dumps(consistent_geometry))
    inconsistent_geometry["C-P512"]["swa"]["kv_size"] = 8192
    results.append({
        "name": "cross_observation_geometry_drift_fails",
        "ok": expect_runtime_error(
            lambda: runner.require_consistent_dump_geometry(inconsistent_geometry)
        ),
    })

    comparison = {
        "classification": "PREFIX_KV_GENERATION_DIFFERS",
        "kv": {
            "W_vs_C": {
                "different": ["swa.layer-3.V.bin"],
                "missing_left": ["base.layer-2.K.bin"],
                "missing_right": [],
            },
        },
        "layout_metadata": {
            "W_vs_C": {"equal": False},
        },
    }
    localized = runner.localize_kv(comparison)
    localization_ok = (
        localized["comparison_pair"] == "W_vs_C"
        and localized["mismatch_file_count"] == 2
        and localized["hash_diff_count"] == 1
        and localized["missing_left_count"] == 1
        and localized["missing_right_count"] == 0
        and localized["layout_metadata_differs"] is True
        and localized["first_mismatch"]["file"] == "base.layer-2.K.bin"
        and localized["first_mismatch"]["cache_class"] == "base"
        and localized["first_mismatch"]["layer"] == 2
        and localized["first_mismatch"]["kind"] == "K"
        and localized["first_mismatch"]["difference_types"] == ["missing_left"]
    )
    results.append({
        "name": "missing_payload_localization_counts",
        "ok": localization_ok,
        "observed": localized,
    })

    errors = [r["name"] for r in results if not r["ok"]]
    out = {
        "status": "KV_RUNNER_CONTRACT_SELFTEST_PASS" if not errors else "KV_RUNNER_CONTRACT_SELFTEST_FAIL",
        "results": results,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
