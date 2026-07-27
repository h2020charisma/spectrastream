"""CWA 18133:2024 §8 portable calibration files.

The load-bearing test here is the negative one: ramanchada2's exporter samples
the model and labels both CSV columns ``_cm1``, but a neon curve with no laser
zeroing outputs *nm*. Publishing that would be a mislabelled file, so the app
withholds the download instead.
"""

import json

import numpy as np
import pytest

from spectrastream.calibration import (
    CalibrationContext,
    engine_for_recipe,
    get_recipe,
)
from spectrastream.cwa import (
    CwaExportError,
    cm1_bounds,
    export_x_files,
    has_x_calibration,
    x_calibration_model,
)


def _neon_fit(spectrum):
    recipe = get_recipe("rc2.ne_si")
    return engine_for_recipe(recipe).fit(
        recipe, {"neon": spectrum}, CalibrationContext(laser_wl_nm=532)
    )


def _full_fit(neon, silicon):
    recipe = get_recipe("rc2.ne_si")
    return engine_for_recipe(recipe).fit(
        recipe,
        {"neon": neon, "si": silicon},
        CalibrationContext(laser_wl_nm=532),
    )


def test_curve_without_laser_zeroing_is_not_offered(neon_spectrum):
    """It would claim cm-1 in the header and carry nm in the column."""
    fit = _neon_fit(neon_spectrum.spectrum)
    assert has_x_calibration(fit.calmodel)
    assert fit.output_units == "nm"
    assert x_calibration_model(fit) is None


def test_model_with_no_x_component_is_rejected_loudly(neon_spectrum):
    calmodel = _neon_fit(neon_spectrum.spectrum).calmodel
    calmodel.components.clear()
    with pytest.raises(CwaExportError, match="no wavenumber-axis component"):
        export_x_files(calmodel, spectral_range=(100.0, 3000.0))


def test_non_rc2_engines_simply_do_not_offer_it():
    class Foreign:
        recipe_id = "x"
        engine_id = "other"

    assert x_calibration_model(Foreign()) is None


def test_zeroed_calibration_reports_wavenumbers_and_exports(
    neon_spectrum, silicon_spectrum
):
    fit = _full_fit(neon_spectrum.spectrum, silicon_spectrum)

    assert fit.output_units == "cm-1"
    assert x_calibration_model(fit) is not None

    csv_text, json_text = export_x_files(
        fit.calmodel, spectral_range=(200.0, 1800.0), npoints=50
    )

    header, *rows = csv_text.strip().splitlines()
    assert header == "uncalibrated_cm1,calibrated_cm1"
    assert len(rows) == 50
    calibrated = [float(row.split(",")[1]) for row in rows]
    # Raman shifts, not wavelengths clustered around 500-600 nm.
    assert all(100 < value < 4000 for value in calibrated)

    doc = json.loads(json_text)
    assert doc["format"] == "CWA18133-x-calibration"
    assert doc["laser_wl_nominal_nm"] == 532
    assert doc["model"]["format"] == "ramanchada2-calmodel"
    assert doc["si_peak_nm"] > 0


def test_cm1_bounds_is_the_spectrums_own_range_in_cm1(neon_spectrum):
    spe = neon_spectrum.spectrum
    assert cm1_bounds(spe, "cm-1", 532.0) == (float(min(spe.x)), float(max(spe.x)))


def test_cm1_bounds_converts_nm_using_the_laser_wavelength(neon_spectrum):
    """The bug: CWA export passed the raw upload's range straight through,
    unconverted, whatever unit it happened to be in."""
    from ramanchada2.misc.utils.ramanshift_to_wavelength import shift_cm_1_to_abs_nm

    spe = neon_spectrum.spectrum
    nm_spe = spe.set_new_xaxis(shift_cm_1_to_abs_nm(spe.x, 532.0))

    lo, hi = cm1_bounds(nm_spe, "nm", 532.0)
    assert lo == pytest.approx(float(min(spe.x)), rel=1e-3)
    assert hi == pytest.approx(float(max(spe.x)), rel=1e-3)


def test_cm1_bounds_refuses_pixel_input(neon_spectrum):
    """Pixel positions have no established conversion to Raman shift."""
    assert cm1_bounds(neon_spectrum.spectrum, "pixel", 532.0) is None


def test_cm1_bounds_refuses_nm_with_no_wavelength(neon_spectrum):
    assert cm1_bounds(neon_spectrum.spectrum, "nm", None) is None


def test_metadata_is_carried_into_the_json(neon_spectrum, silicon_spectrum):
    fit = _full_fit(neon_spectrum.spectrum, silicon_spectrum)
    _, json_text = export_x_files(
        fit.calmodel,
        spectral_range=(200.0, 1800.0),
        npoints=10,
        metadata={"profile": "Lab 2"},
    )
    assert json.loads(json_text)["metadata"]["profile"] == "Lab 2"


def test_zeroing_output_is_not_converted_a_second_time(neon_spectrum, silicon_spectrum):
    """LazerZeroingComponent stores a wavelength but outputs Raman shift.

    Trusting model_units to describe the output axis would send an already
    correct cm-1 axis back through the laser line. apply() must therefore add
    no conversion of its own once zeroing is present.
    """
    fit = _full_fit(neon_spectrum.spectrum, silicon_spectrum)

    applied = fit.apply(neon_spectrum.spectrum, spe_units="cm-1")
    raw = fit.calmodel.apply_calibration_x(neon_spectrum.spectrum, spe_units="cm-1")
    np.testing.assert_allclose(np.asarray(applied.x), np.asarray(raw.x))


def test_neon_only_output_is_converted_exactly_once(neon_spectrum):
    """The mirror case: without zeroing, apply() must convert nm back to cm-1."""
    fit = _neon_fit(neon_spectrum.spectrum)

    applied = fit.apply(neon_spectrum.spectrum, spe_units="cm-1")
    raw = fit.calmodel.apply_calibration_x(neon_spectrum.spectrum, spe_units="cm-1")

    assert not np.allclose(np.asarray(applied.x), np.asarray(raw.x))
    original = np.asarray(neon_spectrum.spectrum.x)
    result = np.asarray(applied.x)
    assert abs(result.min() - original.min()) < 0.05 * np.ptp(original)
    assert abs(result.max() - original.max()) < 0.05 * np.ptp(original)
