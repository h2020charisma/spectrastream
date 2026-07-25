"""Calibration verification — the CWA quality check on the Verify page.

Uses the real Neon+Silicon calibration (``fitted_ne_si``) and the real
polystyrene fixture: after calibration, the PST peaks should sit closer to their
ASTM E1840 positions than before. The round-trip test guards that a calibration
stored as JSON and reloaded verifies identically — the pickle/JSON equivalence
the VAMAS pipeline and this app both rely on.
"""

import pytest

from spectrastream.calibration import (
    CalibrationError,
    engine_for_recipe,
    get_recipe,
    verify_against_reference,
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
    after = verify_against_reference(
        reloaded, target_spectrum.spectrum, material="PST"
    )
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
