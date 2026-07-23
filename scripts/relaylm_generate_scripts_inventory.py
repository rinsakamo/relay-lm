#!/usr/bin/env python3
"""Generate the maintainer-facing scripts inventory deterministically."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs" / "smoke" / "scripts_inventory.md"
HELPER_TOKENS = frozenset(
    {"fixture", "fixtures", "helper", "helpers", "support", "supports"}
)


def read_texts(paths: list[Path]) -> str:
    chunks: list[str] = []
    for path in paths:
        try:
            chunks.append(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
    return "\n".join(chunks)


def filename_signal(name: str) -> str:
    """Return a neutral filename-shape signal, never a responsibility decision."""

    stem = Path(name).stem
    tokens = frozenset(part for part in stem.split("_") if part)
    if name.startswith("_") or tokens.intersection(HELPER_TOKENS):
        return "helper-shaped"
    if "smoke" in tokens:
        return "smoke-named"
    return "other"


def generate() -> str:
    scripts = sorted(
        path
        for path in (ROOT / "scripts").rglob("*.py")
        if "__pycache__" not in path.parts
    )
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
    ci_sources = workflows + [ROOT / "scripts" / "relaylm_ci_consolidated_smoke.py"]
    ci_text = read_texts([path for path in ci_sources if path.exists()])
    docs_sources = sorted(
        path
        for path in (ROOT / "docs").rglob("*.md")
        if path.resolve() != INVENTORY_PATH.resolve()
    )
    docs_text = read_texts(docs_sources)

    rows: list[tuple[str, bool, bool, str]] = []
    for path in scripts:
        relative = path.relative_to(ROOT).as_posix()
        name = path.name
        ci_referenced = relative in ci_text
        docs_referenced = relative in docs_text or name in docs_text
        rows.append(
            (
                relative.removeprefix("scripts/"),
                ci_referenced,
                docs_referenced,
                filename_signal(name),
            )
        )

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ci_count = sum(row[1] for row in rows)
    docs_count = sum(row[2] for row in rows)
    neither_count = sum(not row[1] and not row[2] for row in rows)

    lines = [
        "# Scripts Inventory",
        "",
        "**Maintainer review only.** Generated mechanically; do not hand-edit rows.",
        "",
        f"Generated from commit `{sha}`.",
        "",
        "Regenerate with:",
        "",
        "```bash",
        "python scripts/relaylm_generate_scripts_inventory.py --output generated/scripts_inventory.md",
        "```",
        "",
        f"Snapshot stats: {len(rows)} Python scripts total, {ci_count} CI-referenced, "
        f"{docs_count} docs-referenced, {neither_count} referenced by neither.",
        "",
        "CI references include direct workflow invocations and commands registered in "
        "`scripts/relaylm_ci_consolidated_smoke.py`.",
        "The generated inventory itself is excluded from documentation-reference "
        "detection to prevent self-reference from marking every script as documented.",
        "",
        "Reference columns are mechanical facts. The filename signal describes only "
        "the path shape; it does not classify responsibility, lifecycle, or retention.",
        "Those decisions require reviewed Lane R evidence.",
        "",
        "| script | CI-referenced | docs-referenced | filename signal |",
        "| --- | --- | --- | --- |",
    ]
    for script, ci_ref, docs_ref, signal in rows:
        lines.append(
            f"| `{script}` | {'yes' if ci_ref else 'no'} | "
            f"{'yes' if docs_ref else 'no'} | {signal} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    content = generate()
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
