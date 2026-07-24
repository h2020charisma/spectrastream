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
from ramanchada2.protocols.calibration.xcalibration import (
    LazerZeroingComponent,
    XCalibrationComponent,
)
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


def build_component(
    action: str,
    spe: Spectrum,
    spe_units: str,
    laser_wl_nm: float | None,
    ref: Mapping[float, float] | None = None,
):
    """The ramanchada2 component this recipe step will use.

    Constructed exactly as the engine constructs it, so its ``fit_peaks`` does
    the same unit conversion and the same search.
    """
    if action == "laser_zero":
        return LazerZeroingComponent(
            laser_wl_nm,
            spe,
            spe_units,
            dict(ref or {SI_REF_CM1: 1}),
            "cm-1",
        )
    reference = dict(ref) if ref else neon_reference(laser_wl_nm)
    if not reference:
        raise PeakFindError(
            "No reference lines for this wavelength; set the laser wavelength "
            "on the optical path."
        )
    return XCalibrationComponent(
        laser_wl_nm,
        spe=spe,
        ref=reference,
        spe_units=spe_units,
        ref_units="nm",
    )


def run(
    component,
    find_kw: Mapping[str, Any] | None = None,
    prominence_coeff: float = 3.0,
    should_fit: bool = False,
) -> tuple[pd.DataFrame, str | None]:
    """Call the component's own ``fit_peaks`` and report what happened.

    Returns its peak table and an error message, never raising: the point is to
    surface a failure beside the controls that fix it rather than to stop.
    """
    kwargs = dict(find_kw or DEFAULT_FIND_KW)
    kwargs["prominence"] = float(component.spe.y_noise_MAD()) * float(prominence_coeff)
    try:
        frame = component.fit_peaks(kwargs, {}, should_fit)
    except Exception as err:  # noqa: BLE001 - reported, that is the feature
        return pd.DataFrame(), str(err)

    if frame is None:
        frame = pd.DataFrame()
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    return frame, None


def searched_spectrum(component) -> tuple[Spectrum, str]:
    """The spectrum the component actually searches, and its units.

    ``fit_peaks`` converts into the reference's units before searching -- neon
    is matched against reference lines in nm, not Raman shift -- so a plot of
    the uploaded axis would not show where the peaks were found.
    """
    units = component.ref_units or component.spe_units
    return (
        component.convert_units(component.spe, component.spe_units, units),
        units,
    )


def positions(component) -> pd.DataFrame:
    """Found positions and heights, from the component's own dict."""
    found = getattr(component, "spe_pos_dict", None) or {}
    frame = pd.DataFrame(
        {"position": list(found.keys()), "height": list(found.values())}
    )
    if not frame.empty:
        frame = frame.sort_values("position").reset_index(drop=True)
    return frame
