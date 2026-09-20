#!/usr/bin/env python3
import json
from pathlib import Path
import sys


PATCH = Path(__file__).resolve().parent / "e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch"


def without_cpp_line_comments(text: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def main():
    text = PATCH.read_text(encoding="utf-8")

    generated_anchor = "capture the first complete logical 0..511 prefix"
    retained_anchor = "after aligned reuse truncation"

    generated_start = text.find(generated_anchor)
    retained_start = text.find(retained_anchor)
    if generated_start < 0 or retained_start < 0:
        out = {
            "status": "LOGICAL_PREFIX_PATCH_SELFTEST_FAIL",
            "errors": ["required instrumentation anchors missing"],
        }
        print(json.dumps(out, indent=2, sort_keys=True))
        return 1

    generated = text[generated_start:]
    # Limit to the generated-prefix hook hunk so unrelated batch-size references
    # elsewhere in the source patch do not affect this contract.
    next_hunk = generated.find("\ndiff --git ")
    if next_hunk >= 0:
        generated = generated[:next_hunk]

    generated_code = without_cpp_line_comments(generated)

    checks = {
        "logical_position_511_trigger": "batch_view.pos[i] != 511" in generated,
        "no_physical_512_batch_requirement": "n_tokens == 512" not in generated_code,
        "physical_512_detector_catches_code": (
            "n_tokens == 512"
            in without_cpp_line_comments("if (n_tokens == 512) { return; }")
        ),
        "physical_512_detector_ignores_comment": (
            "n_tokens == 512"
            not in without_cpp_line_comments("// do not require n_tokens == 512")
        ),
        "prompt_only_trigger": "!batch.tokens[off + i].is_prompt" in generated,
        "single_sequence_requirement": "batch_view.n_seq_id[i] != 1" in generated,
        "duplicate_511_fails_closed": "multiple logical position-511 prompt tokens" in generated,
        "p512_dump_range_0_512": "llama_debug_dump_kv_prefix(ctx_tgt, probe_seq, 0, 512" in generated,
        "logical_prefix_failure_is_fatal": "RelayLM KV diagnostic failed at logical-prefix dump" in generated,
        "retained_reuse_boundary_512": "if (p0 == 512)" in text,
        "r512_dump_range_0_512": "llama_debug_dump_kv_prefix(ctx_tgt, slot.id, 0, 512" in text,
        "dump_requires_exact_row_count": "rows.size() != (size_t) (p1 - p0)" in text,
        "dump_requires_contiguous_positions": "rows[i].first != p0 + (llama_pos) i" in text,
        "dump_refuses_overwrite": "refusing to overwrite existing diagnostic dump" in text,
    }

    errors = [name for name, ok in checks.items() if not ok]
    out = {
        "status": (
            "LOGICAL_PREFIX_PATCH_SELFTEST_PASS"
            if not errors
            else "LOGICAL_PREFIX_PATCH_SELFTEST_FAIL"
        ),
        "patch": str(PATCH),
        "checks": checks,
        "errors": errors,
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
