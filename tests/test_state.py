"""The calibration draft's optical-path scoping.

A fitted result is only meaningful for the optical path it was derived on --
its wavelength and instrument context came from whichever path was active at
fit time. Switching to a different path afterwards must not let a stale fit
be saved under, or compared against, the wrong one.
"""

from ui.state import CalibrationDraft


def test_a_fit_survives_while_its_optical_path_stays_selected():
    draft = CalibrationDraft(fitted=object(), derived_optical_path_id="A")
    draft.invalidate_if_stale("A")
    assert draft.fitted is not None
    assert draft.derived_optical_path_id == "A"


def test_a_fit_is_cleared_once_a_different_optical_path_is_selected():
    draft = CalibrationDraft(fitted=object(), derived_optical_path_id="A")
    draft.invalidate_if_stale("B")
    assert draft.fitted is None
    assert draft.derived_optical_path_id is None


def test_invalidate_is_a_no_op_with_nothing_fitted_yet():
    """Selecting a path before deriving anything must not trip the guard."""
    draft = CalibrationDraft()
    draft.invalidate_if_stale("A")
    assert draft.fitted is None


def test_clear_result_resets_the_derived_path_too():
    draft = CalibrationDraft(fitted=object(), derived_optical_path_id="A")
    draft.clear_result()
    assert draft.fitted is None
    assert draft.derived_optical_path_id is None
