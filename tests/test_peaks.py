"""A crop bound has to land on the same axis as the spectrum it crops.

``convert_bound`` exists because a certified band is always authored in cm-1,
but the spectrum it crops may be uploaded in nm or pixels -- it must convert a
single number exactly the way ``to_axis`` converts a whole spectrum.
"""

import numpy as np
import pytest
from ramanchada2.spectrum import Spectrum

from spectrastream.peaks import convert_bound, to_axis


def test_convert_bound_matches_to_axis_on_a_single_point():
    spe = Spectrum(x=np.array([500.0]), y=np.array([1.0]))
    converted = to_axis(spe, "cm-1", "nm", 532.0)
    assert convert_bound(500.0, "cm-1", "nm", 532.0) == pytest.approx(converted.x[0])


def test_convert_bound_is_the_identity_with_no_wavelength():
    assert convert_bound(500.0, "cm-1", "nm", None) == 500.0


def test_convert_bound_is_the_identity_for_matching_units():
    assert convert_bound(500.0, "cm-1", "cm-1", 532.0) == 500.0


def test_convert_bound_round_trips_through_nm_and_back():
    nm = convert_bound(500.0, "cm-1", "nm", 532.0)
    back = convert_bound(nm, "nm", "cm-1", 532.0)
    assert back == pytest.approx(500.0)
