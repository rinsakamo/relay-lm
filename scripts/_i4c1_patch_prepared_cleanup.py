from pathlib import Path

path = Path("relaylm/relaymem_primary_forget_artifact.py")
body = path.read_text(encoding="utf-8")
old = '''        try:\n            temporary.unlink()\n        except FileNotFoundError:\n            pass\n        except OSError:\n            if linked:\n                raise PrimaryForgetArtifactError("publication_ambiguous") from None\n'''
new = '''        temporary_removed = False\n        try:\n            temporary.unlink()\n            temporary_removed = True\n        except FileNotFoundError:\n            pass\n        except OSError:\n            if linked:\n                raise PrimaryForgetArtifactError("publication_ambiguous") from None\n        if temporary_removed:\n            try:\n                _fsync_directory(path.parent)\n            except OSError as exc:\n                raise PrimaryForgetArtifactError("publication_ambiguous") from exc\n'''
if old not in body:
    if new in body:
        raise SystemExit(0)
    raise RuntimeError("prepared cleanup anchor missing")
path.write_text(body.replace(old, new, 1), encoding="utf-8")
