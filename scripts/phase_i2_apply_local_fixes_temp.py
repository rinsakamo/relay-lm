from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"expected text missing: {path}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    replace_once(
        "scripts/relaylm_phase_i2_lab_observation_security_smoke.py",
        '''            for verb in (client.post, client.put, client.patch, client.delete):
                response = verb(
                    f"{base}/lab/last-run?namespace={NAMESPACE}",
                    json={"mutation": True},
                )
                require(response.status_code == 405, response.text)
''',
        '''            for method in ("POST", "PUT", "PATCH", "DELETE"):
                response = client.request(
                    method,
                    f"{base}/lab/last-run?namespace={NAMESPACE}",
                    json={"mutation": True},
                )
                require(response.status_code == 405, response.text)
''',
    )
    replace_once(
        "relaylm/soul_lab_observation_projection.py",
        'memory_id=identity, title=bounded_text(summary, maximum=160),',
        'memory_id=identity, title="",',
    )
    replace_once(
        "apps/soul-lab/src/app/RootApp.tsx",
        '''        <div className="sidebar-note">
          <span className="mock-pill">{translate(language, "app.mockBadge")}</span>
          <p>
            {navigationLock
              ? translate(language, "nav.locked")
              : translate(language, "nav.boundaryNote")}
          </p>
        </div>''',
        '''        <div className="sidebar-note">
          <span className="mock-pill">
            {route === "observation"
              ? "REAL / EXPLICIT PREVIEW"
              : translate(language, "app.mockBadge")}
          </span>
          <p>
            {navigationLock
              ? translate(language, "nav.locked")
              : route === "observation"
                ? language === "ja"
                  ? "実データを優先し、ローカルプレビューは明示的に切り替えます。"
                  : "Runtime data is primary; local preview requires an explicit switch."
                : translate(language, "nav.boundaryNote")}
          </p>
        </div>''',
    )


if __name__ == "__main__":
    main()
