"""Finding peaks the way the engine will, for inspection.

This is a diagnostic, not a pipeline stage. It runs exactly the call the
calibration step will run, with the same parameters, so what you see is what
the fit will get. Seeing thirty candidates in what should be a clean neon
spectrum is how you learn the crop is too wide or the prominence too low --
before a fit fails somewhere deeper with a message about vector lengths.

Peak-finding parameters are per material: neon and silicon want different
windows, which is why the VAMAS pipeline keys them by sample.
"""

from typing import Any, Mapping

import numpy as np
import pandas as pd
from ramanchada2.spectrum import Spectrum

DEFAULT_FIND_KW = {"wlen": 200, "width": 1}


class PeakFindError(RuntimeError):
    """Peak finding could not run on this spectrum."""


def find(
    spe: Spectrum,
    find_kw: Mapping[str, Any] | None = None,
    prominence_coeff: float = 3.0,
) -> tuple[pd.DataFrame, float]:
    """Candidate peaks, as the engine would find them.

    Returns a frame of positions and heights plus the absolute prominence
    threshold used, since that number is the one worth arguing with.
    """
    kwargs = dict(find_kw or DEFAULT_FIND_KW)
    kwargs.setdefault("sharpening", None)
    noise = float(spe.y_noise_MAD())
    prominence = noise * float(prominence_coeff)
    kwargs["prominence"] = prominence

    try:
        candidates = spe.find_peak_multipeak(**kwargs)
    except Exception as err:  # noqa: BLE001 - reported to the UI
        raise PeakFindError(str(err)) from err

    rows: list[dict[str, float]] = []
    smallest_group = None
    x = np.asarray(spe.x)
    for group in candidates.root:
        low, high = group.boundaries
        # The number of points the fit would see for this group. A group with
        # fewer points than the model has parameters is exactly what makes a
        # fit fail, so it is worth surfacing before it does.
        points = int(np.count_nonzero((x > low) & (x < high)))
        smallest_group = (
            points if smallest_group is None else min(smallest_group, points)
        )
        for peak in group.peaks:
            rows.append(
                {
                    "position": float(peak.position),
                    "height": float(peak.amplitude),
                    "fwhm": float(peak.sigma) * 2.355,
                    "group_points": points,
                }
            )

    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("position").reset_index(drop=True)
    return frame, prominence


def too_few_points(frame: pd.DataFrame, parameters_per_peak: int = 3) -> pd.DataFrame:
    """Groups that cannot be fitted: fewer points than the model has parameters."""
    if frame.empty:
        return frame
    counts = frame.groupby("group_points").size()
    bad = [
        points
        for points, peaks in counts.items()
        if points < peaks * parameters_per_peak + 2
    ]
    return frame[frame["group_points"].isin(bad)]
