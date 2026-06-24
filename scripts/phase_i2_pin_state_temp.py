from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"missing replacement anchor: {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: str, old: str, new: str, expected: int) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        if text.count(new) == expected:
            return
        raise RuntimeError(f"missing replacement anchors: {path}")
    if text.count(old) != expected:
        raise RuntimeError(f"unexpected replacement count: {path}")
    target.write_text(text.replace(old, new), encoding="utf-8")


replace_once(
    "relaylm/soul_lab_observation_projection.py",
    "from dataclasses import dataclass\n",
    "from dataclasses import dataclass\nfrom datetime import datetime, timezone\n",
)
replace_once(
    "relaylm/soul_lab_observation_projection.py",
    "    pinned: bool = False\n",
    "    pinned: bool | None = None\n",
)
replace_once(
    "relaylm/soul_lab_observation_projection.py",
    "\n\ndef build_lab_last_run_projection(scope: LabObservationScope) -> LabLastRunProjection:\n",
    '''\n\ndef _run_order_key(item: dict[str, object]) -> tuple[datetime, str]:
    completed = datetime.fromisoformat(str(item["completed_at"]).replace("Z", "+00:00"))
    return completed.astimezone(timezone.utc), str(item["run_id"])


def build_lab_last_run_projection(scope: LabObservationScope) -> LabLastRunProjection:
''',
)
replace_all(
    "relaylm/soul_lab_observation_projection.py",
    'max(runs, key=lambda item: (str(item["completed_at"]), str(item["run_id"])))',
    "max(runs, key=_run_order_key)",
    2,
)
replace_once(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    "  pinned: boolean;\n",
    "  pinned: boolean | null;\n",
)
replace_once(
    "apps/soul-lab/src/features/lab/observationApi.ts",
    '    !isNullableString(value.formed_at) || typeof value.pinned !== "boolean" ||\n',
    '    !isNullableString(value.formed_at) || !(value.pinned === null || typeof value.pinned === "boolean") ||\n',
)
replace_once(
    "apps/soul-lab/scripts/observationApiSmoke.mjs",
    "          pinned: false,\n",
    "          pinned: null,\n",
)
replace_once(
    "scripts/relaylm_phase_i2_lab_observation_security_smoke.py",
    '''        write_run_receipt(str(scoped), run_receipt("run-a", same_completion))
        write_run_receipt(str(scoped), run_receipt("run-b", same_completion))
''',
    '''        write_run_receipt(str(scoped), run_receipt("run-a", same_completion))
        write_run_receipt(str(scoped), run_receipt("run-b", same_completion))
        # A later-looking local timestamp that is earlier in UTC must not win.
        write_run_receipt(
            str(scoped),
            run_receipt("run-c-offset", "2026-06-24T17:09:00+09:00"),
        )
''',
)
