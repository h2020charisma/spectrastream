"""Preprocessing of reference spectra.

The old app exposed crop/baseline/normalise/smooth as tabs per spectrum. Here
the defaults come from the recipe -- which knows what its materials need -- and
the user overrides them. What matters is that the original is never mutated and
that what ran is reported, so an altered spectrum is never presented as raw.
"""

import numpy as np
import pytest
from ramanchada2.spectrum import Spectrum

from spectrastream.preprocess import PreprocessError, PreprocessStep, apply_steps

X = np.arange(200.0, 1200.0, 1.0)


@pytest.fixture
def spectrum():
    peak = 500 * np.exp(-((X - 520) ** 2) / (2 * 5.0**2))
    slope = 0.05 * X  # a baseline worth removing
    return Spectrum(X, peak + slope + 10)


def test_disabled_steps_do_nothing(spectrum):
    out, applied = apply_steps(
        spectrum, [PreprocessStep(op="normalize", enabled=False)]
    )
    assert applied == []
    np.testing.assert_allclose(out.y, spectrum.y)


def test_steps_run_in_order_and_report_themselves(spectrum):
    out, applied = apply_steps(
        spectrum,
        [
            PreprocessStep(op="baseline", enabled=True, params={"method": "snip"}),
            PreprocessStep(op="normalize", enabled=True),
            PreprocessStep(op="trim", enabled=True, params={"min": 400, "max": 700}),
        ],
    )
    assert applied == ["Remove baseline", "Normalise", "Crop"]
    assert 400 <= min(out.x) and max(out.x) <= 700
    assert pytest.approx(1.0) == float(max(out.y))


def test_baseline_removal_flattens_the_slope(spectrum):
    out, _ = apply_steps(
        spectrum, [PreprocessStep(op="baseline", enabled=True, params={"niter": 30})]
    )
    # Away from the peak the signal should sit near zero once the slope is gone.
    off_peak = out.y[X > 900]
    assert abs(float(np.median(off_peak))) < abs(float(np.median(spectrum.y[X > 900])))


def test_the_original_is_left_alone(spectrum):
    before = np.array(spectrum.y, copy=True)
    apply_steps(spectrum, [PreprocessStep(op="normalize", enabled=True)])
    np.testing.assert_allclose(spectrum.y, before)


def test_a_crop_outside_the_data_is_reported_not_silently_empty(spectrum):
    with pytest.raises(PreprocessError, match="does not overlap"):
        apply_steps(
            spectrum,
            [
                PreprocessStep(
                    op="trim", enabled=True, params={"min": 5000, "max": 6000}
                )
            ],
        )


def test_an_unknown_method_is_named(spectrum):
    with pytest.raises(PreprocessError, match="nonsense"):
        apply_steps(
            spectrum,
            [
                PreprocessStep(
                    op="baseline", enabled=True, params={"method": "nonsense"}
                )
            ],
        )


def test_smoothing_reduces_noise(spectrum):
    noisy = Spectrum(X, spectrum.y + np.random.default_rng(0).normal(0, 20, X.shape))
    out, applied = apply_steps(
        noisy,
        [PreprocessStep(op="smooth", enabled=True, params={"method": "savgol"})],
    )
    assert applied == ["Smooth"]
    assert float(np.std(np.diff(out.y))) < float(np.std(np.diff(noisy.y)))


def test_labels_can_be_overridden_by_the_recipe():
    step = PreprocessStep(op="baseline", label="Remove baseline (SNIP)")
    assert step.display_label() == "Remove baseline (SNIP)"
    assert PreprocessStep(op="baseline").display_label() == "Remove baseline"
