"""Peak finding and fitting for inspection, via ramanchada2's own components.

Nothing here implements an algorithm. ``XCalibrationComponent.fit_peaks`` is
the code the calibration step runs -- it converts the spectrum into the
reference's units, finds candidates and fits them -- so the app calls that
directly and shows the result. Anything reimplemented here would drift from the
library and report peaks the calibration never sees.

This exists because no single set of peak-finding parameters suits every
instrument, so the app's job is to let them be tried and to show what the
component does with them.
"""

from typing import Any, Mapping

import pandas as pd
import ramanchada2.misc.constants as rc2const
from ramanchada2.misc.utils.ramanshift_to_wavelength import (
    abs_nm_to_shift_cm_1,
    shift_cm_1_to_abs_nm,
)
from ramanchada2.protocols.calibration.xcalibration import fit_peaks
from ramanchada2.spectrum import Spectrum

#: The VAMAS pipeline's tuned defaults, used when a recipe names none.
DEFAULT_FIND_KW = {"wlen": 200, "width": 1}

SI_REF_CM1 = 520.45


class PeakFindError(RuntimeError):
    """Peak finding could not run on this spectrum."""


def neon_reference(laser_wl_nm: float | None) -> dict[float, float] | None:
    if laser_wl_nm is None:
        return None
    return rc2const.NEON_WL.get(int(laser_wl_nm))


def searched_axis(action: str, spe_units: str) -> str:
    """The units this step searches in.

    The neon curve matches against reference lines in nm, so its peaks are
    found on a wavelength axis. Laser zeroing works on whatever axis reaches
    it. This mirrors what the components do, it does not decide it.
    """
    return "nm" if action == "x_curve" and spe_units == "cm-1" else spe_units


def to_axis(
    spe: Spectrum, spe_units: str, target_units: str, laser_wl_nm: float | None
) -> Spectrum:
    """Convert with ramanchada2's own converters."""
    if spe_units == target_units or laser_wl_nm is None:
        return spe
    if spe_units == "cm-1" and target_units == "nm":
        return spe.set_new_xaxis(shift_cm_1_to_abs_nm(spe.x, laser_wl_nm))
    if spe_units == "nm" and target_units == "cm-1":
        return spe.set_new_xaxis(abs_nm_to_shift_cm_1(spe.x, laser_wl_nm))
    return spe


def run(
    spe: Spectrum,
    find_kw: Mapping[str, Any] | None = None,
    prominence_coeff: float = 3.0,
    profile: str = "Gaussian",
    should_fit: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, str | None]:
    """Call ramanchada2's ``fit_peaks`` on a spectrum.

    That function is what the calibration components call, so what it returns
    here is what the calibration will get. Returns the fit table, the found
    positions, and an error message -- never raising, because the point is to
    surface a failure beside the controls that fix it.
    """
    kwargs = dict(find_kw or DEFAULT_FIND_KW)
    kwargs["prominence"] = float(spe.y_noise_MAD()) * float(prominence_coeff)
    try:
        fit_res, found = fit_peaks(
            spe, kwargs, {}, profile=profile, should_fit=should_fit
        )
    except Exception as err:  # noqa: BLE001 - reported, that is the feature
        return pd.DataFrame(), pd.DataFrame(), str(err)

    try:
        table = fit_res.to_dataframe_peaks()
    except Exception:  # noqa: BLE001 - the positions still stand
        table = pd.DataFrame()

    positions = pd.DataFrame(
        {"position": list(found.keys()), "height": list(found.values())}
    )
    if not positions.empty:
        positions = positions.sort_values("position").reset_index(drop=True)
    return table, positions, None
