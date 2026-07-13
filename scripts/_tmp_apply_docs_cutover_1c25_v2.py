#!/usr/bin/env python3
"""Run the Cutover 1C-25 applicator without editing its temporary host workflow."""
from pathlib import Path

source = Path(__file__).with_name("_tmp_apply_docs_cutover_1c25.py")
text = source.read_text(encoding="utf-8")
start_marker = '\nreplace_once(\n    Path(".github/workflows/e1-evaluation-consolidation.yml"),'
end_marker = '\nreplace_once(\n    Path(".github/workflows/wave5-cross-slice-convergence.yml"),'
start = text.index(start_marker)
end = text.index(end_marker, start)
text = text[:start] + text[end:]
exec(compile(text, str(source), "exec"), {"__name__": "__main__"})
