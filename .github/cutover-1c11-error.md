Traceback (most recent call last):
  File "/home/runner/work/relay-lm/relay-lm/.github/scripts/docs_cutover_1c11.py", line 45, in <module>
    source = read(OLD)
             ^^^^^^^^^
  File "/home/runner/work/relay-lm/relay-lm/.github/scripts/docs_cutover_1c11.py", line 22, in read
    return (ROOT / path).read_text(encoding="utf-8")
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/pathlib.py", line 1027, in read_text
    with self.open(mode='r', encoding=encoding, errors=errors) as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/pathlib.py", line 1013, in open
    return io.open(self, mode, buffering, encoding, errors, newline)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '/home/runner/work/relay-lm/relay-lm/docs/mvp/wave8/mvp_eval_runner_completion_report.md'
