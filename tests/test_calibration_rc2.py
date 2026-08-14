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
from spectrastream.calibration.engines.rc2 import Rc2Engine


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


def _prepared(recipe, slot_id, spectrum):
    """Run the recipe's declared preprocessing, as the app does before fitting.

    Handing raw silicon to the engine is not a path the UI ever takes -- the
    crop and baseline removal the recipe declares run first -- so a test that
    skipped them would be measuring something nobody does.
    """
    from spectrastream.preprocess import apply_steps

    steps = [s.model_copy(deep=True) for s in recipe.slot(slot_id).preprocess]
    prepared, _ = apply_steps(spectrum, steps)
    return prepared


def test_laser_zeroing_runs_and_reports_the_band(neon_spectrum, silicon_spectrum):
    recipe = get_recipe("rc2.ne_si")
    fit = engine_for_recipe(recipe).fit(
        recipe,
        {
            "neon": neon_spectrum.spectrum,
            "si": _prepared(recipe, "si", silicon_spectrum),
        },
        CalibrationContext(laser_wl_nm=532),
    )
    by_id = {o.step_id: o for o in fit.outcomes()}
    assert by_id["laser_zero"].status == "applied"
    assert "laser" in by_id["laser_zero"].detail
    assert fit.output_units == "cm-1"


def test_zeroing_finds_the_laser_near_its_nominal_wavelength(
    neon_spectrum, silicon_spectrum
):
    """The silicon fixture puts its band at exactly 520.45 cm-1, so a correct
    zeroing must recover a laser wavelength close to the nominal 532 nm."""
    recipe = get_recipe("rc2.ne_si")
    fit = engine_for_recipe(recipe).fit(
        recipe,
        {
            "neon": neon_spectrum.spectrum,
            "si": _prepared(recipe, "si", silicon_spectrum),
        },
        CalibrationContext(laser_wl_nm=532),
    )
    zeroing = next(o for o in fit.outcomes() if o.step_id == "laser_zero")
    laser_nm = float(zeroing.detail.split("laser ")[1].split(" nm")[0])
    assert abs(laser_nm - 532.0) < 1.0, f"laser came out at {laser_nm} nm"


def test_zeroing_crops_to_the_band_before_fitting(
    monkeypatch, neon_spectrum, silicon_spectrum
):
    """Peak finding over a whole spectrum picks up noise, and every spurious
    candidate costs a Pearson4 fit -- enough of them and the run effectively
    never finishes. Cropping is what keeps it bounded.

    Asserting on the spectrum handed to the fit rather than on elapsed time:
    a wall-clock bound measures the machine's load as much as the code.
    """
    from ramanchada2.protocols.calibration.calibration_model import CalibrationModel

    seen = {}
    original = CalibrationModel._derive_model_zero

    def capture(self, *args, **kwargs):
        spe = kwargs.get("spe")
        seen["points"] = len(spe.x)
        seen["span"] = float(max(spe.x)) - float(min(spe.x))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CalibrationModel, "_derive_model_zero", capture)

    recipe = get_recipe("rc2.ne_si")
    silicon = _prepared(recipe, "si", silicon_spectrum)
    engine_for_recipe(recipe).fit(
        recipe,
        {"neon": neon_spectrum.spectrum, "si": silicon},
        CalibrationContext(laser_wl_nm=532),
    )

    assert seen, "laser zeroing never ran"
    # The axis is nm by then; +/-100 cm-1 around 520 at 532 nm is a few nm.
    assert seen["span"] < 20, f"fit saw a {seen['span']:.0f} nm span -- crop gone?"
    assert seen["points"] < len(silicon.x), "the fit saw the whole spectrum"


def test_calibration_applies_to_an_unrelated_target(neon_only_fit, target_spectrum):
    """A calibration derived from neon must apply to any other spectrum."""
    _, _, fit = neon_only_fit
    out = fit.apply(target_spectrum.spectrum, spe_units="cm-1")
    assert len(out.x) == len(target_spectrum.spectrum.x)
    assert np.all(np.isfinite(out.y))


def _y_calibrated_payload():
    """A saved y-intensity calibration, as ``export_bytes`` would produce it."""
    from ramanchada2.protocols.calibration.ycalibration import (
        CertificatesDict,
        YCalibrationComponent,
    )
    from ramanchada2.spectrum import Spectrum

    certificate = CertificatesDict().get(wavelength=785, key="NIST785_SRM2241")
    reference = Spectrum(x=np.linspace(200, 3500, 60), y=np.ones(60))
    component = YCalibrationComponent(
        785, reference_spe_xcalibrated=reference, certificate=certificate
    )
    return {
        "engine": "rc2",
        "recipe": "test",
        "model": {
            "format": "ramanchada2-calmodel",
            "version": 1,
            "laser_wl": 785,
            "nonmonotonic": "drop",
            "prominence_coeff": 3,
            "components": [component.to_dict()],
        },
        "outcomes": [],
    }


def test_loaded_certificate_is_reresolved_not_trusted_from_the_file():
    """A saved profile can name a certificate; it must not be able to carry one.

    ``YCalibrationCertificate.equation``/``params`` are ``eval``'d at apply time
    with a live ``__builtins__``. If a tampered ``equation`` survives a load
    unexamined, importing and re-exporting a profile becomes a code-execution
    path. The fix re-resolves every certificate from ``CertificatesDict`` by id
    and wavelength on load, discarding whatever the file itself claims.
    """
    payload = _y_calibrated_payload()
    payload["model"]["components"][0]["certificate"]["equation"] = (
        "__import__('os').system('echo pwned') or (A0 + x*0)"
    )

    engine = Rc2Engine()
    fitted = engine.load(payload)

    restored = fitted.calmodel.components[0].ref
    assert restored.equation == (
        "A0 + A1 * x + A2 * x**2 + A3 * x**3 + A4 * x**4 + A5 * x**5"
    )

    # A re-export reflects the re-resolved certificate, not the tampered file:
    # once loaded, the in-memory model no longer carries what the file said.
    reexported = fitted.to_dict()
    assert reexported["model"]["components"][0]["certificate"]["equation"] == (
        "A0 + A1 * x + A2 * x**2 + A3 * x**3 + A4 * x**4 + A5 * x**5"
    )


def test_loaded_certificate_survives_json_round_trip():
    payload = json.loads(json.dumps(_y_calibrated_payload()))
    engine = Rc2Engine()
    fitted = engine.load(payload)
    assert fitted.calmodel.components[0].ref.id == "NIST785_SRM2241"


def test_unknown_certificate_id_is_rejected_on_load():
    payload = _y_calibrated_payload()
    payload["model"]["components"][0]["certificate"]["id"] = "not-a-real-certificate"

    engine = Rc2Engine()
    with pytest.raises(CalibrationError, match="not a known"):
        engine.load(payload)
