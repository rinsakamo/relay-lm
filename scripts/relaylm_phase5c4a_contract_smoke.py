from __future__ import annotations

import subprocess
from pathlib import Path

from phase5c4a_backend_e2e import main as backend_main
from relaylm_phase5c4a_renderer_smoke import main as renderer_main
from relaylm_phase5c4a_source_smoke import main as source_main

ROOT = Path(__file__).resolve().parents[1]
subprocess.run(
    ["git", "fetch", "origin", "main", "--depth=1"],
    cwd=ROOT,
    check=True,
)
subprocess.run(
    ["git", "diff", "--check", "FETCH_HEAD", "HEAD"],
    cwd=ROOT,
    check=True,
)
renderer_main()
source_main()
raise SystemExit(backend_main())
