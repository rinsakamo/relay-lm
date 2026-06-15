from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "relaylm_docs_link_check.py"


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def run_checker(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(root)],
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        fixture_root = Path(tmpdir)
        docs_dir = fixture_root / "docs"
        docs_dir.mkdir(parents=True)

        (fixture_root / "README.md").write_text(
            "\n".join(
                [
                    "# Fixture",
                    "",
                    "- [Docs](docs/README.md)",
                    "- [Japanese](README_ja.md)",
                    "- [External](https://example.com/docs)",
                    "- [Anchor](#fixture)",
                    "",
                    "```markdown",
                    "[Ignored broken sample](docs/missing-in-fence.md)",
                    "```",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (fixture_root / "README_ja.md").write_text(
            "# Fixture JA\n\n- [English](README.md)\n- [Docs](docs/README.md)\n",
            encoding="utf-8",
        )
        (docs_dir / "README.md").write_text(
            "\n".join(
                [
                    "# Docs",
                    "",
                    "- [Target](target.md#section)",
                    "",
                    "[reference-target]: target.md",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (docs_dir / "target.md").write_text(
            "# Target\n\n## Section\n",
            encoding="utf-8",
        )

        success = run_checker(fixture_root)
        require(success.returncode == 0, success.stderr or success.stdout)
        require("ok documentation links" in success.stdout, success.stdout)
        require("4 Markdown files" in success.stdout, success.stdout)
        print("ok docs link checker success fixture")

        with (fixture_root / "README_ja.md").open("a", encoding="utf-8") as handle:
            handle.write("\n- [Broken](docs/missing.md)\n")

        failure = run_checker(fixture_root)
        require(failure.returncode == 1, failure.stdout)
        require("README_ja.md" in failure.stderr, failure.stderr)
        require("missing target docs/missing.md" in failure.stderr, failure.stderr)
        require("1 broken local Markdown link(s) found" in failure.stderr, failure.stderr)
        print("ok docs link checker localized README failure fixture")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
