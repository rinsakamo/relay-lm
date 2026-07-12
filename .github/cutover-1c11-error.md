Traceback (most recent call last):
  File "/home/runner/work/relay-lm/relay-lm/.github/scripts/docs_cutover_1c11.py", line 123, in <module>
    replace("scripts/relaylm_documentation_current_boundary_smoke.py", OLD, NEW, 1)
  File "/home/runner/work/relay-lm/relay-lm/.github/scripts/docs_cutover_1c11.py", line 35, in replace
    raise AssertionError(f"{path}: expected {expected} occurrences, found {count}: {old!r}")
AssertionError: scripts/relaylm_documentation_current_boundary_smoke.py: expected 1 occurrences, found 2: 'docs/mvp/wave8/mvp_eval_runner_completion_report.md'
