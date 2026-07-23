from pathlib import Path

path = Path(".d1_completion_model_retirement.py")
text = path.read_text(encoding="utf-8")

replacements = [
    ('write("scripts/relaylm_mvp_eval_runner_registry.py", registry)\n\ndocs_readme = read("docs/README.md")\n', 'write("scripts/relaylm_mvp_eval_runner_registry.py", registry)\n\nconsolidated = read("scripts/relaylm_ci_consolidated_smoke.py")\nconsolidated = consolidated.replace(\n    \'["scripts/relaylm_mvp_completion_report_smoke.py", "--check-model", "--check-all"]\',\n    \'["scripts/relaylm_mvp_completion_report_smoke.py", "--check-all"]\',\n)\nif "--check-model" in consolidated:\n    raise SystemExit("consolidated smoke still invokes --check-model")\nwrite("scripts/relaylm_ci_consolidated_smoke.py", consolidated)\n\ndocs_readme = read("docs/README.md")\n', "consolidated invocation"),
    ('audit = audit.replace("    check_completion_report_template(errors)\\n", "")\n', 'audit = audit.replace("    check_completion_report_template(errors)\\n", "")\naudit = audit.replace("    check_completion_report_template,\\n", "")\n', "semantic audit check tuple"),
    ('    "docs/templates/README.md",\n    "docs/contracts/documentation-governance.md",\n]', '    "docs/templates/README.md",\n]', "active contract descriptive mention"),
]
for old, new, label in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label} anchor count: {count}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
