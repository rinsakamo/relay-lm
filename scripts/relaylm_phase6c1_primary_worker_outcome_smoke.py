#!/usr/bin/env python3
"""Smoke coverage for the pure Phase 6-C1 Primary MEM outcome classifier."""
from relaylm_phase6c1_primary_worker_outcome_purity_cases import run_purity_cases
from relaylm_phase6c1_primary_worker_outcome_success_retry_cases import (
    run_success_retry_cases,
)
from relaylm_phase6c1_primary_worker_outcome_terminal_cases import (
    run_terminal_cases,
)
from relaylm_phase6c1_primary_worker_outcome_validation_cases import (
    run_validation_cases,
)


def main() -> None:
    results = (
        run_success_retry_cases()
        + run_terminal_cases()
        + run_validation_cases()
    )
    run_purity_cases(results)
    print("Phase 6-C1 Primary MEM worker outcome smoke passed.")


if __name__ == "__main__":
    main()
