"""The app's resolution wrapper (``spectrastream.calibration.resolution_for``).

The algorithm itself is tested upstream in ramanchada2; here we only check the
wrapper: a ramanchada2 calibration yields a result, anything without a model
yields ``None``, and a JSON round-trip of the calibration gives identical curves
(the pickle/JSON equivalence).
"""

import numpy as np

from spectrastream.calibration import (
    ResolutionResult,
    engine_for_recipe,
    get_recipe,
    resolution_for,
)


def _engine():
    return engine_for_recipe(get_recipe("rc2.ne_si"))


def test_resolution_for_computes_from_a_real_calibration(fitted_ne_si, neon_spectrum):
    res = resolution_for(fitted_ne_si, neon_spectrum.spectrum, neon_units="cm-1")
    assert isinstance(res, ResolutionResult)
    assert res.n_neon_peaks >= 6
    assert res.curve_ok
    assert res.figure() is not None


def test_resolution_for_returns_none_without_a_model(neon_spectrum):
    """An engine that exposes no CalibrationModel cannot give resolution curves;
    the wrapper says so rather than crashing, and the page explains it."""

    class NoModel:
        engine_id = "fake"

        def apply(self, spe, spe_units="cm-1"):
            return spe

    assert resolution_for(NoModel(), neon_spectrum.spectrum) is None


def test_resolution_round_trips_through_json(fitted_ne_si, neon_spectrum):
    reloaded = _engine().load(fitted_ne_si.to_dict())
    before = resolution_for(fitted_ne_si, neon_spectrum.spectrum)
    after = resolution_for(reloaded, neon_spectrum.spectrum)
    assert before.n_neon_peaks == after.n_neon_peaks
    np.testing.assert_allclose(before.pixel_res, after.pixel_res, equal_nan=True)
