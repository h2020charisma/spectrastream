"""Render smoke tests for the redesigned UI.

AppTest cannot drive a file uploader, so these check that every page renders
without raising -- including the empty states, which are what a first-time
visitor actually sees.
"""

import pytest
from streamlit.testing.v1 import AppTest

PAGES = [
    "src/app_pages/home.py",
    "src/app_pages/convert.py",
    "src/app_pages/calibrate.py",
    "src/app_pages/profiles.py",
]


def test_entry_point_renders():
    at = AppTest.from_file("src/streamlit_app.py")
    at.run(timeout=60)
    assert not at.exception


def test_alpha_banner_is_always_visible():
    """The caveat is a promise to users, not decoration."""
    at = AppTest.from_file("src/streamlit_app.py")
    at.run(timeout=60)
    assert any("Alpha" in w.value for w in at.warning)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_standalone(page):
    at = AppTest.from_file(page)
    at.run(timeout=60)
    assert not at.exception


def test_convert_page_invites_an_upload_before_anything_else():
    at = AppTest.from_file("src/app_pages/convert.py")
    at.run(timeout=60)
    assert not at.exception
    assert at.file_uploader, "the uploader is the entry point to the whole app"


def _seed_library(at, profile):
    at.run(timeout=60)
    state = at.session_state["spectrastream"]
    state.library.upsert(profile)
    state.set_active_profile(profile.id)
    return at


@pytest.mark.parametrize(
    "page", ["src/app_pages/profiles.py", "src/app_pages/calibrate.py"]
)
def test_pages_render_with_a_multi_path_instrument(page):
    """The case the flat model could not express: one rig, two wavelengths."""
    from spectrastream.profiles import InstrumentProfile, OpticalPath

    profile = InstrumentProfile(name="Two-line rig", vendor="WITec")
    profile.add_optical_path(OpticalPath(op_id="OP1", laser_wl_nm=532))
    profile.add_optical_path(OpticalPath(op_id="OP2", laser_wl_nm=785))

    at = _seed_library(AppTest.from_file(page), profile)
    at.run(timeout=60)
    assert not at.exception


def test_calibrate_page_stops_politely_without_an_optical_path():
    from spectrastream.profiles import InstrumentProfile

    at = _seed_library(
        AppTest.from_file("src/app_pages/calibrate.py"),
        InstrumentProfile(name="Bare instrument"),
    )
    at.run(timeout=60)
    assert not at.exception
    assert any("optical path" in w.value for w in at.warning)
