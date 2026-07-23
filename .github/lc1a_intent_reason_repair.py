from copy import deepcopy
import json
from pathlib import Path

runtime_path = Path("relaylm/subjective_mem_lifecycle_runtime.py")
text = runtime_path.read_text(encoding="utf-8")
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
compile(text, str(runtime_path), "exec")
runtime_path.write_text(text, encoding="utf-8")

schema_path = Path(
    "docs/contracts/schemas/subjective-mem-v1/"
    "relaylm-subjective-mem-v1.schema.json"
)
schema = json.loads(schema_path.read_text(encoding="utf-8"))
defs = schema["$defs"]
current = defs["SubjectiveMemCurrentState"]
if current.get("properties", {}).get("schema") != {
    "const": "relaylm.subjective_mem_current_state.v1"
}:
    raise SystemExit("unexpected current-state schema authority")

v1 = deepcopy(current)
v2 = deepcopy(current)
v2["required"] = [*v2["required"], "authority_binding"]
v2["properties"]["schema"] = {
    "const": "relaylm.subjective_mem_current_state.v2"
}
v2["properties"]["authority_binding"] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "workspace_authority_digest",
        "scope_binding_digest",
        "page_id",
        "block_id",
        "canonical_page_digest",
        "authorization_ref",
        "current_receipt_id",
    ],
    "properties": {
        "workspace_authority_digest": {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$",
        },
        "scope_binding_digest": {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$",
        },
        "page_id": {"type": "string", "minLength": 1, "maxLength": 128},
        "block_id": {"type": "string", "minLength": 1, "maxLength": 128},
        "canonical_page_digest": {
            "type": "string",
            "pattern": "^sha256:[0-9a-f]{64}$",
        },
        "authorization_ref": {"$ref": "#/$defs/AuthorizationRef"},
        "current_receipt_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128,
        },
    },
}
defs["SubjectiveMemCurrentState"] = {"oneOf": [v1, v2]}
schema_path.write_text(
    json.dumps(schema, ensure_ascii=False, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
