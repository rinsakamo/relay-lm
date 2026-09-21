#!/usr/bin/env python3
import json
from pathlib import Path
import re
import sys


PATCH = Path(__file__).resolve().parent / "e2d2c0d6-gemma4-kv-logical-prefix-dump-diagnostic.patch"


def without_cpp_line_comments(text: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


HUNK_HEADER = re.compile(
    r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@(?: .*)?$"
)


def unified_diff_hunk_counts_match(text: str) -> bool:
    lines = text.splitlines()
    seen = 0
    for i, line in enumerate(lines):
        if not line.startswith("@@ "):
            continue

        match = HUNK_HEADER.fullmatch(line)
        if match is None:
            return False

        seen += 1
        declared_old = int(match.group(1) or "1")
        declared_new = int(match.group(2) or "1")
        actual_old = 0
        actual_new = 0

        for body in lines[i + 1 :]:
            if body.startswith("@@ ") or body.startswith("diff --git "):
                break
            if body.startswith("\\ No newline at end of file"):
                continue
            if body.startswith("+"):
                actual_new += 1
            elif body.startswith("-"):
                actual_old += 1
            elif body.startswith(" "):
                actual_old += 1
                actual_new += 1
            else:
                break

        if actual_old != declared_old or actual_new != declared_new:
            return False

    return seen > 0


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

    added_code = "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    doubled_tab_escape = "\\\\t"
    doubled_newline_escape = "\\\\n"
    doubled_nul_escape = "\\\\0"

    checks = {
        "hunk_header_detector_accepts_valid_header": unified_diff_hunk_counts_match(
            "diff --git a/x b/x\n"
            "--- a/x\n"
            "+++ b/x\n"
            "@@ -1 +1,2 @@ optional context\n"
            " old\n"
            "+new\n"
        ),
        "unified_diff_hunk_counts_match": unified_diff_hunk_counts_match(text),
        "hunk_count_detector_rejects_bad_header": not unified_diff_hunk_counts_match(
            "diff --git a/x b/x\n"
            "--- a/x\n"
            "+++ b/x\n"
            "@@ -1 +1,3 @@\n"
            " old\n"
            "+new\n"
        ),
        "hunk_header_detector_rejects_unparseable_header": not unified_diff_hunk_counts_match(
            "diff --git a/x b/x\n"
            "--- a/x\n"
            "+++ b/x\n"
            "@@ malformed @@\n"
            " old\n"
        ),
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
        "metadata_writer_has_no_double_tab_escape": doubled_tab_escape not in added_code,
        "metadata_writer_has_no_double_newline_escape": doubled_newline_escape not in added_code,
        "diagnostic_char_literals_have_no_double_nul_escape": doubled_nul_escape not in added_code,
        "cells_header_uses_real_cxx_escapes": (
            'out << "cache\\tstream\\thead\\tkv_size\\tv_trans\\tposition\\tcell\\n";'
            in added_code
        ),
        "manifest_header_uses_real_cxx_escapes": (
            'out << "cache\\tlayer\\tkind\\ttype\\trow_bytes\\trows\\n";'
            in added_code
        ),
        "row_writer_uses_real_cxx_char_escapes": (
            "<< '\\t'" in added_code and "<< '\\n';" in added_code
        ),
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
