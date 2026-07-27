"""Calibration verification — the CWA quality check on the Verify page.

Uses the real Neon+Silicon calibration (``fitted_ne_si``) and the real
polystyrene fixture: after calibration, the PST peaks should sit closer to their
ASTM E1840 positions than before. The round-trip test guards that a calibration
stored as JSON and reloaded verifies identically — the pickle/JSON equivalence
the VAMAS pipeline and this app both rely on.
"""

import pytest

from spectrastream.calibration import (
    REFERENCE_MATERIALS,
    CalibrationError,
    engine_for_recipe,
    get_recipe,
    has_relative_intensities,
    verify_against_reference,
    verify_relative_intensity,
)


def _engine():
    return engine_for_recipe(get_recipe("rc2.ne_si"))


def test_verify_pst_moves_peaks_toward_reference(fitted_ne_si, target_spectrum):
    result = verify_against_reference(
        fitted_ne_si, target_spectrum.spectrum, material="PST"
    )
    assert result.n_matched > 0
    assert result.mean_before is not None and result.mean_after is not None
    # the whole point of the calibration: the peaks end up closer to the
    # certified positions than they started
    assert result.mean_after <= result.mean_before
    assert result.improved is True


def test_verify_round_trips_through_json(fitted_ne_si, target_spectrum):
    reloaded = _engine().load(fitted_ne_si.to_dict())
    before = verify_against_reference(
        fitted_ne_si, target_spectrum.spectrum, material="PST"
    )
    after = verify_against_reference(reloaded, target_spectrum.spectrum, material="PST")
    assert after.mean_after == pytest.approx(before.mean_after)
    assert after.n_matched == before.n_matched


def test_custom_lines_are_honoured(fitted_ne_si, target_spectrum):
    result = verify_against_reference(
        fitted_ne_si,
        target_spectrum.spectrum,
        material="custom",
        ref={1001.4: 100, 1602.3: 28},
    )
    assert result.n_matched > 0


def test_unknown_material_is_rejected(fitted_ne_si, target_spectrum):
    with pytest.raises(CalibrationError):
        verify_against_reference(
            fitted_ne_si, target_spectrum.spectrum, material="unobtainium"
        )


def test_has_relative_intensities():
    # polystyrene (ASTM E1840) has varying certified intensities...
    assert has_relative_intensities(REFERENCE_MATERIALS["PST"])
    # ...calcite's table lists every line as 1.0 (no relative comparison), and
    # silicon is a single band
    assert not has_relative_intensities(REFERENCE_MATERIALS["CAL"])
    assert not has_relative_intensities(REFERENCE_MATERIALS["Si"])


def test_relative_intensity_reports_a_table(fitted_ne_si, target_spectrum):
    result = verify_relative_intensity(
        fitted_ne_si, target_spectrum.spectrum, material="PST"
    )
    assert result.n_matched > 0
    assert {"position_cm-1", "reference", "as_measured", "calibrated"} <= set(
        result.table.columns
    )
    # every reference line row carries its certified intensity, normalised to
    # 100 at the strongest line
    assert result.table["reference"].max() == pytest.approx(100.0)
    assert result.mean_before is not None
    # this calibration (rc2.ne_si) has no y-step, so intensity is not corrected
    assert result.intensity_corrected is False


def test_relative_intensity_rejects_a_flat_reference(fitted_ne_si, silicon_spectrum):
    with pytest.raises(CalibrationError):
        verify_relative_intensity(fitted_ne_si, silicon_spectrum, material="Si")
