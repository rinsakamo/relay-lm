from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"missing replacement anchor: {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "relaylm/soul_lab_observation_projection.py",
    "    pinned: bool = False\n",
    "    pinned: bool | None = None\n",
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
