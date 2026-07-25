"""Resolution curves for a fitted calibration (CWA 18133 sections 3 & 4).

A thin adapter over ramanchada2's ``resolution_from_calibration``: it pulls the
live ``CalibrationModel`` off a fitted calibration and hands it the neon (and
optional calcite) spectrum. The algorithm lives upstream in ramanchada2 — this
keeps the app free of it and works for any engine that exposes a ``calmodel``.
"""

from __future__ import annotations

from ramanchada2.protocols.calibration.resolution import (
    ResolutionResult,
    resolution_from_calibration,
)
from ramanchada2.spectrum import Spectrum

from .engines.base import FittedCalibration


def resolution_for(
    fitted: FittedCalibration,
    neon_spe: Spectrum,
    *,
    neon_units: str = "cm-1",
    calcite_spe: Spectrum | None = None,
    calcite_units: str = "cm-1",
    title: str = "",
    **kwargs,
) -> ResolutionResult | None:
    """CWA resolution curves for ``fitted``, or ``None`` if it cannot supply a
    ramanchada2 calibration model.

    Resolution is derived from the neon FWHM on the *calibrated* axis, so it
    needs the model itself (not just its ``apply``); an engine that does not
    expose one — anything but the ramanchada2 engine today — returns ``None`` and
    the UI explains that resolution is unavailable for it.
    """
    calmodel = getattr(fitted, "calmodel", None)
    if calmodel is None or getattr(calmodel, "laser_wl", None) is None:
        return None
    return resolution_from_calibration(
        calmodel,
        neon_spe,
        neon_units=neon_units,
        spe_calcite=calcite_spe,
        calcite_units=calcite_units,
        title=title,
        **kwargs,
    )


__all__ = ["ResolutionResult", "resolution_for"]
