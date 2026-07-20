from collections import defaultdict
import pandas as pd
from streamlit.testing.v1 import AppTest


def _init_session_state(at: AppTest) -> AppTest:
    """Pre-populate the cache keys that init_streamlit_cache() normally sets."""
    at.session_state["cache_bools"] = defaultdict(bool)
    at.session_state["cache_strings"] = defaultdict(str)
    at.session_state["cache_numbers"] = defaultdict(float)
    at.session_state["cache_dfs"] = defaultdict(pd.DataFrame)
    at.session_state["cache_lists"] = defaultdict(list)
    cache_dicts = defaultdict(dict)
    cache_dicts["instrument_settings"] = {
        "settings": {
            "laser_wavelength": 532,
            "make_and_model_of_the_instrument": None,
            "serial_number_of_the_instrument": "",
            "device_type": None,
            "numerical_aperture": None,
            "grating": None,
            "slit": None,
        }
    }
    at.session_state["cache_dicts"] = cache_dicts
    return at


def test_app():
    at = AppTest.from_file("src/streamlit_app.py")
    at.run(timeout=30)
    assert not at.exception

def test_load_or_create_calibration():
    at = AppTest.from_file("src/pages/load_or_create_calibration.py")
    _init_session_state(at)
    at.run(timeout=30)
    assert not at.exception

def test_apply_calibration():
    at = AppTest.from_file("src/pages/apply_calibration.py")
    _init_session_state(at)
    at.run(timeout=30)
    assert not at.exception

def test_load_instrument_settings():
    at = AppTest.from_file("src/pages/load_instrument_settings.py")
    _init_session_state(at)
    at.run(timeout=30)
    assert not at.exception
