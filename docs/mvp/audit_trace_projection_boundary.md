# MVP Audit Trace Projection Boundary

The P0-A1 trace boundary is typed projection, not heuristic recursive sanitization.

Supported top-level projectors live in `relaylm/audit_projection.py` and are intentionally exact. A new runtime artifact is not persisted until a projector is registered and covered by smoke tests. Pipeline node diagnostics are similarly documented by the node projector registry; unknown nodes must not become durable by accident.

The historical suffix/forbidden-token/cross-field-taint logic is no longer the primary persistence boundary. Any remaining validation is defense in depth for already-projected fields: scalar types, finite non-negative numbers, bounded opaque identifiers, exact media type grammar, and URL/path rejection.
