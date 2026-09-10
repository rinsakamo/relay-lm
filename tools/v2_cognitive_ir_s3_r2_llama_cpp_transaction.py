from __future__ import annotations

from collections.abc import Sequence

from relaylm.v2_cognitive_ir_s3_r2 import (
    S3_R2_PREREGISTRATION_SHA256,
    activate_s3_r2_preregistration,
)


# The replacement preregistration must be active before the shared transaction
# module binds its imported preregistration identity.  This module is launched
# in a fresh child process by the WSL wrapper.
activate_s3_r2_preregistration()

import tools.v2_cognitive_ir_s3_llama_cpp_transaction as transaction
from tools.v2_cognitive_ir_s3_llama_cpp_transaction_listener_safe import (
    main as _listener_safe_main,
)


# Fail closed even if Python import ordering changes in a non-physical caller.
# All other scientific constants are unchanged and the shared functions read
# the activated base-module globals dynamically.
transaction.S3_PREREGISTRATION_SHA256 = S3_R2_PREREGISTRATION_SHA256


def main(argv: Sequence[str] | None = None) -> int:
    activate_s3_r2_preregistration()
    transaction.S3_PREREGISTRATION_SHA256 = S3_R2_PREREGISTRATION_SHA256
    return _listener_safe_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
