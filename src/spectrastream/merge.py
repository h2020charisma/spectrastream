"""Combining several acquisitions of the same reference material.

Two different things get called "merging" and they are not interchangeable:

* **Averaging** is for replicates -- the same measurement repeated at the same
  exposure. It improves signal to noise.
* **HDR** is for the same material measured at *different* exposures. Neon is
  the case that forces it: its lines span orders of magnitude, so any single
  exposure either saturates the strong lines or loses the weak ones. The VAMAS
  pipeline HDR-merges neon for exactly this reason.

Averaging spectra taken at different exposures would be wrong -- it mixes
saturated and unsaturated data and blunts both -- so the default strategy
inspects the exposure times and picks.
"""

from typing import Literal, Sequence

import numpy as np
from ramanchada2.spectrum import Spectrum
from ramanchada2.spectrum.creators.hdr_from_multi_exposure import (
    hdr_from_multi_exposure,
)

MergeStrategy = Literal["auto", "hdr", "average", "none"]

#: ramanchada2 reads the exposure from spectrum metadata under these names.
EXPOSURE_KEY = "integration_time_ms"
YMAX_KEY = "yaxis_max"

#: Fraction of the brightest spectrum's peak treated as the saturation ceiling.
#: Mirrors the VAMAS pipeline, which uses 0.9 * max of the longest exposure.
DEFAULT_SATURATION_FRACTION = 0.9


class MergeError(ValueError):
    """The given spectra cannot be combined."""


def _require_common_axis(spectra: Sequence[Spectrum]) -> None:
    first = np.asarray(spectra[0].x)
    for spe in spectra[1:]:
        other = np.asarray(spe.x)
        if other.shape != first.shape or not np.allclose(other, first):
            raise MergeError(
                "these spectra are on different x axes, so they cannot be "
                "combined. Acquisitions to be merged must come from the same "
                "instrument settings."
            )


def average(spectra: Sequence[Spectrum]) -> Spectrum:
    """Mean of replicates measured under identical conditions."""
    if not spectra:
        raise MergeError("nothing to average")
    if len(spectra) == 1:
        return spectra[0]
    _require_common_axis(spectra)
    total = spectra[0]
    for spe in spectra[1:]:
        total = total + spe
    return total / len(spectra)


def hdr(
    spectra: Sequence[Spectrum],
    exposures: Sequence[float | None],
    saturation: float | None = None,
) -> Spectrum:
    """High-dynamic-range merge of the same material at different exposures.

    Strong lines are taken from the short exposures that did not saturate, weak
    ones from the long exposures that could see them; everything is normalised
    to counts per unit time so the pieces are comparable.
    """
    if len(spectra) != len(exposures):
        raise MergeError("every spectrum needs an exposure time for an HDR merge")
    if len(spectra) < 2:
        raise MergeError("an HDR merge needs at least two exposures")
    if any(not e or e <= 0 for e in exposures):
        raise MergeError(
            "every spectrum needs a positive exposure time for an HDR merge. "
            "Fill in the integration time for each file, or average instead."
        )
    _require_common_axis(spectra)

    longest = max(range(len(spectra)), key=lambda i: exposures[i])
    if saturation is None:
        saturation = DEFAULT_SATURATION_FRACTION * float(
            np.max(np.asarray(spectra[longest].y))
        )

    tagged = [
        Spectrum(
            spe.x,
            spe.y,
            metadata={EXPOSURE_KEY: float(exposure), YMAX_KEY: float(saturation)},
        )
        for spe, exposure in zip(spectra, exposures, strict=True)
    ]
    try:
        return hdr_from_multi_exposure(
            tagged, meta_exposure_time=EXPOSURE_KEY, meta_ymax=YMAX_KEY
        )
    except Exception as err:  # noqa: BLE001 - reported with context
        raise MergeError(f"HDR merge failed: {err}") from err


def combine(
    spectra: Sequence[Spectrum],
    exposures: Sequence[float | None] | None = None,
    strategy: MergeStrategy = "auto",
    saturation: float | None = None,
) -> tuple[Spectrum, str]:
    """Combine ``spectra``, returning the result and what was actually done.

    ``auto`` picks HDR when the exposures genuinely differ and averaging when
    they do not, because averaging different exposures together is wrong and
    HDR of identical exposures is pointless.
    """
    if not spectra:
        raise MergeError("no spectra to combine")
    if len(spectra) == 1:
        return spectra[0], "single acquisition"

    times = list(exposures or [None] * len(spectra))
    known = [t for t in times if t]
    exposures_differ = len(set(known)) > 1 and len(known) == len(spectra)

    if strategy == "none":
        raise MergeError("this input takes a single spectrum, but several were given")
    if strategy == "auto":
        strategy = "hdr" if exposures_differ else "average"

    if strategy == "hdr":
        # Pass the times through unconverted: hdr() validates them and explains
        # a missing exposure, which a float(None) here would pre-empt with a
        # TypeError nobody can act on.
        merged = hdr(spectra, times, saturation=saturation)
        return merged, f"HDR merge of {len(spectra)} exposures"

    return average(spectra), f"average of {len(spectra)} acquisitions"
