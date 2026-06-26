"""Focused Phase I-4D RelayCTX handoff exclusion smoke."""
from relaylm_phase_i4d_primary_retrieval_exclusion_smoke import active_corrected_and_finalized


def main() -> None:
    active_corrected_and_finalized()
    print("Phase I-4D RelayCTX exclusion smoke passed")


if __name__ == "__main__":
    main()
