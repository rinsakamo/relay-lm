# Native evaluation check verdict contract

`EvaluationCheck.passed` is an executable verdict boundary, not a truthy/falsy convenience field.

The native evaluation core accepts only the actual Python boolean values `True` and `False` for `passed`. Any non-boolean value is rejected when the check is constructed, before scenario or report aggregation.

This prevents producer mistakes such as `passed="false"`, `passed=1`, or other truthy values from being interpreted by scenario aggregation as a PASS. Static type annotations are not treated as the enforcement mechanism; the runtime evaluation contract fails closed independently.

The contract does not change scenario semantics, scenario registration, scenario count, boundary labels, metrics, or the report's no-composite-score policy.
