"""Reading what the file already told us.

Guessing is worth doing because vendor headers frequently carry the laser
wavelength and integration time -- the very fields we would otherwise make the
contributor retype. It is only ever a suggestion: headers go stale, and the
person in front of the instrument is the authority.
"""

from datetime import date, datetime, time

from spectrastream.acquisition import Acquisition, guess_from_metadata


def test_nothing_to_guess_from_is_not_an_error():
    fields, laser_wl = guess_from_metadata(None)
    assert fields == {}
    assert laser_wl is None

    fields, laser_wl = guess_from_metadata({})
    assert fields == {}
    assert laser_wl is None


def test_laser_wavelength_is_read_from_a_real_header(neon_spectrum):
    """The BWTek text format states it outright, so asking again is rude."""
    _, laser_wl = guess_from_metadata(neon_spectrum.source_metadata)
    assert laser_wl is not None
    assert 531 < laser_wl < 533


def test_misspelled_vendor_keys_are_matched(neon_spectrum):
    """The file really does say "intigration times(ms)"."""
    fields, _ = guess_from_metadata(neon_spectrum.source_metadata)
    assert fields["integration_time_ms"] == 5.0


def test_datetime_headers_split_into_date_and_time():
    fields, _ = guess_from_metadata({"Date": datetime(2022, 3, 17, 8, 46, 42)})
    assert fields["measured_on"] == date(2022, 3, 17)
    assert fields["measured_at"] == time(8, 46)


def test_guessed_values_are_valid_acquisition_fields(neon_spectrum):
    """Whatever guessing produces must construct without further massaging."""
    fields, _ = guess_from_metadata(neon_spectrum.source_metadata)
    acq = Acquisition(**fields)
    assert acq.integration_time_ms == 5.0


def test_zero_and_blank_headers_are_ignored():
    """A zero integration time is a placeholder, not a measurement."""
    fields, laser_wl = guess_from_metadata(
        {"laser_wavelength": 0, "integration time": "", "temperature": None}
    )
    assert fields == {}
    assert laser_wl is None


def test_keys_are_matched_case_and_space_insensitively():
    fields, laser_wl = guess_from_metadata(
        {"  Laser Wavelength  ": "785", "Integration Time": "1000"}
    )
    assert laser_wl == 785.0
    assert fields["integration_time_ms"] == 1000.0


def test_optical_path_id_is_recorded_for_the_measurement():
    """OP is the optical path, and one instrument commonly has several."""
    meta = Acquisition(op_id="OP2").as_metadata()
    assert meta["op_id"] == "OP2"


def test_units_always_survive_into_the_metadata():
    assert Acquisition(units="nm").as_metadata()["x_axis_units"] == "nm"
