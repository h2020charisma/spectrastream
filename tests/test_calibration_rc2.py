"""End-to-end behaviour of the ramanchada2 engine.

The cases that matter for the redesign are the degraded ones: a missing silicon
spectrum must skip laser zeroing rather than fail, and the result must still
come back in cm-1 so a caller can hand it straight to the NeXus writer.
"""

import json

import numpy as np
import pytest

from spectrastream.calibration import (
    CalibrationContext,
    CalibrationError,
    engine_for_recipe,
    get_recipe,
)


@pytest.fixture(scope="module")
def neon_only_fit(neon_spectrum):
    recipe = get_recipe("rc2.ne_si")
    engine = engine_for_recipe(recipe)
    fit = engine.fit(
        recipe,
        {"neon": neon_spectrum.spectrum},
        CalibrationContext(laser_wl_nm=532),
    )
    return recipe, engine, fit


def test_neon_only_fit_skips_optional_steps(neon_only_fit):
    _, _, fit = neon_only_fit
    by_id = {o.step_id: o for o in fit.outcomes()}
    assert by_id["x_curve"].status == "applied"
    assert by_id["laser_zero"].status == "skipped"
    assert "Silicon" in by_id["laser_zero"].detail
    assert by_id["y_intensity"].status == "skipped"
    assert fit.applied_steps == ["x_curve"]


def test_result_is_returned_in_cm1_without_laser_zeroing(neon_only_fit, neon_spectrum):
    """The neon curve natively emits nm; zeroing normally converts back. With
    zeroing skipped the axis must still be Raman shift, not wavelength."""
    _, _, fit = neon_only_fit
    original = neon_spectrum.spectrum
    calibrated = fit.apply(original, spe_units="cm-1")

    assert np.isclose(min(calibrated.x), min(original.x), rtol=0.05)
    assert np.isclose(max(calibrated.x), max(original.x), rtol=0.05)
    # It must actually have changed something, or the test proves nothing.
    assert not np.allclose(calibrated.x, original.x)


def test_json_round_trip_reproduces_the_axis(neon_only_fit, neon_spectrum):
    _, engine, fit = neon_only_fit
    payload = json.loads(json.dumps(fit.to_dict()))
    restored = engine.load(payload)

    before = fit.apply(neon_spectrum.spectrum).x
    after = restored.apply(neon_spectrum.spectrum).x
    np.testing.assert_allclose(before, after)


def test_serialised_model_is_json_clean(neon_only_fit):
    _, _, fit = neon_only_fit
    payload = fit.to_dict()
    # Must survive a strict JSON encoder -- no numpy scalars, no pickled blobs.
    text = json.dumps(payload, allow_nan=False)
    assert payload["engine"] == "rc2"
    assert payload["model"]["format"] == "ramanchada2-calmodel"
    # Small enough for browser-local storage.
    assert len(text) < 512 * 1024


def test_missing_required_slot_is_rejected_with_a_readable_message():
    recipe = get_recipe("rc2.ne_si")
    engine = engine_for_recipe(recipe)
    with pytest.raises(CalibrationError, match="Neon lamp spectrum"):
        engine.fit(recipe, {}, CalibrationContext(laser_wl_nm=532))


def test_unknown_laser_wavelength_is_reported_not_crashed(neon_spectrum):
    recipe = get_recipe("rc2.ne_si")
    engine = engine_for_recipe(recipe)
    with pytest.raises(CalibrationError, match="No built-in Neon reference"):
        engine.fit(
            recipe,
            {"neon": neon_spectrum.spectrum},
            CalibrationContext(laser_wl_nm=999),
        )


def test_missing_laser_wavelength_is_reported(neon_spectrum):
    recipe = get_recipe("rc2.ne_si")
    engine = engine_for_recipe(recipe)
    with pytest.raises(CalibrationError, match="needs a laser wavelength"):
        engine.fit(
            recipe,
            {"neon": neon_spectrum.spectrum},
            CalibrationContext(laser_wl_nm=None),
        )


def test_laser_zeroing_runs_and_reports_the_band(neon_spectrum, silicon_spectrum):
    recipe = get_recipe("rc2.ne_si")
    fit = engine_for_recipe(recipe).fit(
        recipe,
        {"neon": neon_spectrum.spectrum, "si": silicon_spectrum},
        CalibrationContext(laser_wl_nm=532),
    )
    by_id = {o.step_id: o for o in fit.outcomes()}
    assert by_id["laser_zero"].status == "applied"
    assert "laser" in by_id["laser_zero"].detail
    assert fit.output_units == "cm-1"


def test_zeroing_crops_to_the_band_before_fitting(neon_spectrum, silicon_spectrum):
    """Peak finding over a whole spectrum picks up noise, and every spurious
    candidate costs a Pearson4 fit -- enough of them and the run never
    finishes. Cropping is what keeps this bounded."""
    import time

    recipe = get_recipe("rc2.ne_si")
    started = time.monotonic()
    engine_for_recipe(recipe).fit(
        recipe,
        {"neon": neon_spectrum.spectrum, "si": silicon_spectrum},
        CalibrationContext(laser_wl_nm=532),
    )
    elapsed = time.monotonic() - started
    # Uncropped this took minutes; a generous bound still catches a regression.
    assert elapsed < 30, f"laser zeroing took {elapsed:.0f}s -- is the crop gone?"


def test_calibration_applies_to_an_unrelated_target(neon_only_fit, target_spectrum):
    """A calibration derived from neon must apply to any other spectrum."""
    _, _, fit = neon_only_fit
    out = fit.apply(target_spectrum.spectrum, spe_units="cm-1")
    assert len(out.x) == len(target_spectrum.spectrum.x)
    assert np.all(np.isfinite(out.y))
