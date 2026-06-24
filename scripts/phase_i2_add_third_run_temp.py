from pathlib import Path

path = Path("scripts/relaylm_phase_i2_lab_observation_security_smoke.py")
text = path.read_text(encoding="utf-8")
old = '''        write_run_receipt(str(scoped), run_receipt("run-a", same_completion))
        write_run_receipt(str(scoped), run_receipt("run-b", same_completion))
        write_used_receipt(str(scoped), used_receipt("run-b", 16))
'''
new = '''        write_run_receipt(str(scoped), run_receipt("run-a", same_completion))
        write_run_receipt(str(scoped), run_receipt("run-b", same_completion))
        # A later-looking local timestamp that is earlier in UTC must not win.
        write_run_receipt(
            str(scoped),
            run_receipt("run-c-offset", "2026-06-24T17:09:00+09:00"),
        )
        write_used_receipt(str(scoped), used_receipt("run-b", 16))
'''
if new not in text:
    if old not in text:
        raise RuntimeError("third-run insertion anchor missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
