from pathlib import Path

path = Path("relaylm/subjective_mem_lifecycle_runtime.py")
text = path.read_text(encoding="utf-8")
old = '''        if (
            intent is None
            or intent.get("operation_id") != identity.operation_id
            or claim != _claim_from_intent(identity=identity, intent=intent)
        ):
            return _result(
                "fail_closed",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_lifecycle_intent_missing_or_corrupt",),
            )
'''
new = '''        if intent is None:
            return _result(
                "fail_closed",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_lifecycle_intent_missing_or_corrupt",),
            )
        if (
            intent.get("operation_id") != identity.operation_id
            or claim != _claim_from_intent(identity=identity, intent=intent)
        ):
            return _result(
                "fail_closed",
                identity=identity,
                proposal=proposal,
                reasons=("subjective_mem_lifecycle_intent_corrupt",),
            )
'''
if text.count(old) != 1:
    raise SystemExit("expected exactly one intent validation block")
text = text.replace(old, new)
compile(text, str(path), "exec")
path.write_text(text, encoding="utf-8")
