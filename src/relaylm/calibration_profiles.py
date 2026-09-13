from __future__ import annotations

from types import MappingProxyType

from relaylm.calibration_profile import CalibrationProfile


# The single production carriage of the #2844 FastCal result owned by #1388.
FASTCAL_V1_CALIBRATION_PROFILE = CalibrationProfile(
    name="fastcal-v1",
    target_window=4352,
    output_allowance=512,
    authority="#1388 FastCal v1",
)

CALIBRATION_PROFILES = MappingProxyType(
    {FASTCAL_V1_CALIBRATION_PROFILE.name: FASTCAL_V1_CALIBRATION_PROFILE}
)
