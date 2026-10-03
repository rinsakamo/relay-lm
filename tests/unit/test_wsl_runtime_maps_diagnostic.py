"""Offline discovery must retain later defects without granting attestation."""

import hashlib
import importlib.util
import json

import pytest


def diagnostic():
    spec = importlib.util.find_spec("tools.wsl_runtime_maps_diagnostic")
    assert spec is not None, "complete offline maps diagnostic is missing"
    from tools.wsl_runtime_maps_diagnostic import diagnose
    return diagnose


def manifest():
    record = {"sha256": "0" * 64, "identity": {"device": 44, "inode": 7}}
    return {
        "server": {"path": "/bin/server", **record},
        "model": {"path": "/model.gguf", **record},
        "build": {
            "shared_libraries": {},
            "wsl_cuda_driver_closure": {
                "shim": {"aliases": []},
                "driver_package": {"root": "/usr/lib/wsl/drivers/pkg", "runtime_objects": []},
                "accepted_mapped_objects": [],
            },
        },
    }


def snapshot(content):
    return {"content": content, "complete_snapshot": True,
            "line_count": len(content.splitlines()),
            "sha256": hashlib.sha256(content.encode()).hexdigest()}


def test_diagnostic_retains_every_line_and_all_defects():
    content = ("100-200 r-xp 0 00:29 7 /bin/server\n"
               "200-300 r-xp 0 00:29 8 /usr/lib/wsl/lib/libdxcore.so\n"
               "300-400 r-xp 0 00:29 9 /another/libunknown.so\n"
               "400-500 rw-s 0 00:01 10 /dev/zero (deleted)\n"
               "500-600 r--s 0 00:2c 7 /model.gguf\n"
               "600-700 rw-p 0 00:00 0\n")
    frozen = manifest()
    before = json.dumps(frozen, sort_keys=True)
    result = diagnostic()(snapshot(content), frozen)
    assert result["content"] == content
    assert len(result["rows"]) == 6
    assert [r["diagnostic"] for r in result["rows"]] == [
        "SEALED_MAP_IDENTITY_MISMATCH", "UNSEALED_LIBRARY", "UNSEALED_LIBRARY",
        "UNSEALED_NON_LIBRARY", "SEALED_MODEL_MAP_IDENTITY_MATCH",
        "ANONYMOUS_OR_PSEUDO"]
    assert result["qualification_authority"] is False
    assert result["closure_attested"] is False
    assert json.dumps(frozen, sort_keys=True) == before


def test_bad_line_does_not_hide_following_unknown_library():
    result = diagnostic()(snapshot("bad\n100-200 r-xp 0 00:29 8 /unknown.so\n"), manifest())
    assert result["rows"][0]["diagnostic"] == "MALFORMED_MAP_LINE"
    assert result["rows"][1]["diagnostic"] == "UNSEALED_LIBRARY"


@pytest.mark.parametrize("field,value", [("sha256", "bad"), ("line_count", 9), ("complete_snapshot", False)])
def test_corrupt_snapshot_never_claims_complete(field, value):
    data = snapshot("100-200 r-xp 0 00:29 7 /bin/server\n")
    data[field] = value
    with pytest.raises(ValueError, match="snapshot"):
        diagnostic()(data, manifest())


def test_deleted_sealed_library_and_conflicting_manifest_records():
    data = snapshot("100-200 r-xp 0 00:2c 7 /bin/server (deleted)\n")
    assert diagnostic()(data, manifest())["rows"][0]["diagnostic"] == "DELETED_SEALED_OBJECT"
    frozen = manifest()
    frozen["build"]["shared_libraries"]["/bin/server"] = {
        "sha256": "1" * 64, "identity": {"device": 44, "inode": 7}, "dependencies": {}}
    with pytest.raises(ValueError, match="conflicting"):
        diagnostic()(data, frozen)
