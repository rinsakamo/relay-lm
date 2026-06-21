#!/usr/bin/env python3
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def rep(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected one match: {old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


p = "docs/PROJECT_STATUS.md"
rep(p, "  - docs/architecture/soul_lab_ui_a3_communication_handoff.md\n---", "  - docs/architecture/soul_lab_ui_a3_communication_handoff.md\n  - docs/architecture/soul_lab_ui_a4_pod_handoff.md\n---")
rep(p, "Last reviewed: 2026-06-21 JST", "Last reviewed: 2026-06-22 JST")
rep(p, "Status baseline commit: `263708d39763c3d4e290928ea635f8c201836837`", "Status baseline commit: `f955a51cdc263a0e2303ce87e558ae6148bcffca`")
rep(p, "SOUL Lab UI independent track: UI-A0 through UI-A3 implemented as browser-local mock/presentation slices", "SOUL Lab UI independent track: UI-A0 through UI-A4 implemented as browser-local mock/presentation slices")
rep(p, "  SOUL Lab UI-A0 through UI-A3\n  + TypeScript/React/Vite shell, mock Home, and read-only Lab Observation preview\n  + browser-local first-launch and character-adoption draft flow\n  + mock Communication with peer classification, autonomous exchange, Soft Stop, and content-free timeline\n  + no peer network request, credentials, RelayRUN/RelaySLP mutation, transcript persistence, TTS, audio, or avatar execution", "  SOUL Lab UI-A0 through UI-A4\n  + TypeScript/React/Vite shell, mock Home, and read-only Lab Observation preview\n  + browser-local first-launch and character-adoption draft flow\n  + mock Communication with peer classification, autonomous exchange, Soft Stop, and content-free timeline\n  + mock Pod intervention with bounded targets, protected-trait locks, candidate diff, comparison, Hold/Discard, and non-executing Apply/Rollback previews\n  + no peer network request, durable RelaySOUL candidate, managed apply, rollback, RelayRUN/RelaySLP mutation, transcript persistence, TTS, audio, or avatar execution")
rep(p, "SOUL Lab UI-A0 through UI-A3 are complete as presentation-only browser slices. They provide the UI foundation, mock Home/Observation surfaces, first-launch/adoption drafts, and a browser-local autonomous Communication session surface without reading persona source contents, registering a character, sending peer network requests, calling `/lab/api/*`, or mutating RelayRUN, RelaySLP, SOUL, or MEM state.", "SOUL Lab UI-A0 through UI-A4 are complete as presentation-only browser slices. They provide the UI foundation, mock Home/Observation surfaces, first-launch/adoption drafts, browser-local autonomous Communication, and a browser-local Pod intervention workflow without reading persona source contents, registering a character, sending peer network requests, creating a durable RelaySOUL candidate, calling `/lab/api/*`, applying or rolling back SOUL, or mutating RelayRUN, RelaySLP, SOUL, or MEM state.")
rep(p, "- SOUL Lab UI-A4: read-only-to-candidate Pod / SOUL Intervention mock workflow with no mutation API,", "- SOUL Lab UI-A5: browser-local Memory Inspector for formed/held/blocked outcomes and non-persistent operation previews,")
rep(p, "- SOUL Lab UI-A3 browser-local mock Communication session surface,\n- Phase 6-A1", "- SOUL Lab UI-A3 browser-local mock Communication session surface,\n- SOUL Lab UI-A4 browser-local mock Pod / SOUL Intervention workflow,\n- Phase 6-A1")
rep(p, "The repository does include the presentation-only SOUL Lab UI-A0 through UI-A3 under `apps/soul-lab`;", "The repository does include the presentation-only SOUL Lab UI-A0 through UI-A4 under `apps/soul-lab`;")
rep(p, "- [SOUL Lab UI-A3 Communication Handoff](architecture/soul_lab_ui_a3_communication_handoff.md)\n", "- [SOUL Lab UI-A3 Communication Handoff](architecture/soul_lab_ui_a3_communication_handoff.md)\n- [SOUL Lab UI-A4 Pod Handoff](architecture/soul_lab_ui_a4_pod_handoff.md)\n")

p = "docs/architecture/pipeline_implementation_plan.md"
rep(p, "  - soul_lab_ui_a3_communication_handoff.md\n  - soul_lab_runtime_mvp.md", "  - soul_lab_ui_a3_communication_handoff.md\n  - soul_lab_ui_a4_pod_handoff.md\n  - soul_lab_runtime_mvp.md")
rep(p, "SOUL Lab UI independent track: complete through UI-A3 mock Communication", "SOUL Lab UI independent track: complete through UI-A4 mock Pod intervention")
rep(p, "  SOUL Lab UI-A0 through UI-A3 presentation-only slices", "  SOUL Lab UI-A0 through UI-A4 presentation-only slices")
rep(p, "  SOUL Lab UI: UI-A4 Pod / SOUL Intervention mock workflow", "  SOUL Lab UI: UI-A5 browser-local Memory Inspector")
rep(p, "The independent SOUL Lab UI track has progressed through UI-A3 mock Communication; UI-A4 Pod / SOUL Intervention is next while peer transport and real management APIs remain separate.", "The independent SOUL Lab UI track has progressed through UI-A4 mock Pod intervention; UI-A5 Memory Inspector is next while real management APIs, RelaySOUL apply/rollback, and persistence remain separate.")
rep(p, "  UI-A3 mock Communication: complete\n  UI-A4 Pod / SOUL Intervention mock workflow: next", "  UI-A3 mock Communication: complete\n  UI-A4 mock Pod / SOUL Intervention: complete\n  UI-A5 mock Memory Inspector: next")
rep(p, "UI-A0 through UI-A3 are not peer transport, management API, RelayRUN orchestration, or persistence implementation.", "UI-A0 through UI-A4 are not peer transport, management API, RelayRUN orchestration, RelaySOUL apply/rollback, or persistence implementation.")

p = "docs/architecture/README.md"
rep(p, "- [SOUL Lab UI-A3 Communication Handoff](soul_lab_ui_a3_communication_handoff.md) — browser-local peer classification, autonomous mock exchange loop, Soft Stop, emergency stop, and content-free timeline.\n- [SOUL Lab Runtime MVP]", "- [SOUL Lab UI-A3 Communication Handoff](soul_lab_ui_a3_communication_handoff.md) — browser-local peer classification, autonomous mock exchange loop, Soft Stop, emergency stop, and content-free timeline.\n- [SOUL Lab UI-A4 Pod Handoff](soul_lab_ui_a4_pod_handoff.md) — bounded intervention targets, locked protected traits, candidate diff, browser-local comparison, Hold/Discard, and non-executing Apply/Rollback previews.\n- [SOUL Lab Runtime MVP]")
rep(p, "The current UI implementation is complete through UI-A3. UI-A4 Pod / SOUL Intervention is the next independent UI slice; peer transport, server-side management APIs, and Runtime adapter execution remain separate.", "The current UI implementation is complete through UI-A4. UI-A5 Memory Inspector is the next independent UI slice; peer transport, server-side management APIs, RelaySOUL apply/rollback, memory mutation, and Runtime adapter execution remain separate.")

p = "docs/README.md"
rep(p, "- [SOUL Lab UI-A3 Communication handoff](architecture/soul_lab_ui_a3_communication_handoff.md) — current UI track through browser-local mock Communication", "- [SOUL Lab UI-A4 Pod handoff](architecture/soul_lab_ui_a4_pod_handoff.md) — current UI track through browser-local mock intervention")
rep(p, "SOUL Lab UI is implemented through UI-A3; UI-A4 Pod / SOUL Intervention is next.", "SOUL Lab UI is implemented through UI-A4; UI-A5 Memory Inspector is next.")
rep(p, "- [SOUL Lab UI-A3 Communication handoff](architecture/soul_lab_ui_a3_communication_handoff.md)\n- [SOUL Lab Runtime MVP]", "- [SOUL Lab UI-A3 Communication handoff](architecture/soul_lab_ui_a3_communication_handoff.md)\n- [SOUL Lab UI-A4 Pod handoff](architecture/soul_lab_ui_a4_pod_handoff.md)\n- [SOUL Lab Runtime MVP]")

subprocess.run(["python", "scripts/relaylm_docs_link_check.py"], cwd=ROOT, check=True)
subprocess.run(["python", "scripts/relaylm_phase6b0_durable_queue_contract_smoke.py"], cwd=ROOT, check=True)
subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT, check=True)
subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
subprocess.run(["git", "add", "docs"], cwd=ROOT, check=True)
subprocess.run(["git", "commit", "-m", "docs: include SOUL Lab UI-A4 in current status"], cwd=ROOT, check=True)
subprocess.run(["git", "push", "origin", "HEAD"], cwd=ROOT, check=True)
