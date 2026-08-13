"""Combining several acquisitions of one material.

Averaging and HDR are not interchangeable. Averaging spectra taken at different
exposures mixes saturated with unsaturated data and blunts both, so the choice
has to follow the exposure times rather than a user's guess.
"""

import numpy as np
import pytest
from ramanchada2.spectrum import Spectrum

from spectrastream.merge import MergeError, average, combine, hdr

X = np.arange(200.0, 1200.0, 1.0)


def _peak(centre, height, width=4.0):
    return height * np.exp(-((X - centre) ** 2) / (2 * width**2))


@pytest.fixture
def short_exposure():
    """Strong line well within range, weak line barely visible."""
    return Spectrum(X, np.clip(_peak(400, 4000) + _peak(900, 60) + 5, 0, 1000))


@pytest.fixture
def long_exposure():
    """Strong line clipped at the detector ceiling, weak line clear."""
    return Spectrum(X, np.clip(_peak(400, 40000) + _peak(900, 600) + 50, 0, 1000))


def test_different_exposures_are_hdr_merged(short_exposure, long_exposure):
    merged, how = combine([short_exposure, long_exposure], [10.0, 100.0])
    assert "HDR" in how
    assert np.all(np.isfinite(merged.y))
    # The strong line is recovered above the clipping ceiling of the long one.
    strong = merged.y[np.argmin(abs(X - 400))]
    weak = merged.y[np.argmin(abs(X - 900))]
    assert strong > weak


def test_equal_exposures_are_averaged(short_exposure):
    merged, how = combine([short_exposure, short_exposure], [10.0, 10.0])
    assert "average" in how
    np.testing.assert_allclose(merged.y, short_exposure.y)


def test_unknown_exposures_fall_back_to_averaging(short_exposure):
    """Without exposure times HDR is not possible; averaging still is."""
    merged, how = combine([short_exposure, short_exposure], [None, None])
    assert "average" in how


def test_a_single_acquisition_passes_straight_through(short_exposure):
    merged, how = combine([short_exposure], [10.0])
    assert merged is short_exposure
    assert how == "single acquisition"


def test_hdr_without_exposure_times_explains_itself(short_exposure, long_exposure):
    with pytest.raises(MergeError, match="positive exposure time"):
        combine([short_exposure, long_exposure], [10.0, None], strategy="hdr")


def test_hdr_needs_at_least_two_exposures(short_exposure):
    with pytest.raises(MergeError, match="at least two"):
        hdr([short_exposure], [10.0])


def test_mismatched_axes_are_refused_with_a_reason(short_exposure):
    other = Spectrum(np.arange(0.0, 500.0, 1.0), np.ones(500))
    with pytest.raises(MergeError, match="different x axes"):
        combine([short_exposure, other], [10.0, 20.0])


def test_a_single_input_slot_rejects_several_files(short_exposure):
    with pytest.raises(MergeError, match="single spectrum"):
        combine([short_exposure, short_exposure], [1.0, 1.0], strategy="none")


def test_averaging_halves_the_difference(short_exposure):
    doubled = Spectrum(X, short_exposure.y * 3)
    merged = average([short_exposure, doubled])
    np.testing.assert_allclose(merged.y, short_exposure.y * 2)
