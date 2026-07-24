"""Browser-storage bridge.

The dangerous case is the first render: the component has not answered yet, and
treating "no answer" as "no profiles" would persist an empty library over the
user's real data. These tests pin that distinction and the failure reporting
around it.
"""

from streamlit.testing.v1 import AppTest

from spectrastream.profiles import InstrumentProfile, ProfileLibrary
from ui.localstore import (
    SOFT_LIMIT_BYTES,
    BrowserStoreResult,
    load_library,
    serialise,
    size_warning,
)


def test_no_answer_is_distinguishable_from_an_empty_store():
    """Both look like "no profiles"; only one is safe to write over."""
    silent = BrowserStoreResult(None)
    assert silent.answered is False

    empty = BrowserStoreResult({"available": True, "text": None})
    assert empty.answered is True
    assert empty.available is True
    assert empty.text is None


def test_unavailable_storage_is_reported():
    result = BrowserStoreResult(
        {"available": False, "text": None, "error": "SecurityError"}
    )
    assert result.answered is True
    assert result.available is False
    assert result.error == "SecurityError"


def test_round_trip_through_the_stored_text():
    library = ProfileLibrary()
    profile = InstrumentProfile(name="Lab 2", vendor="WITec", laser_wl_nm=532)
    library.upsert(profile)

    restored, problem = load_library(serialise(library))
    assert problem is None
    assert [p.name for p in restored.profiles] == ["Lab 2"]


def test_empty_storage_yields_an_empty_library():
    library, problem = load_library(None)
    assert library.profiles == []
    assert problem is None


def test_corrupt_storage_is_reported_and_left_alone():
    """Overwriting unreadable data would destroy any chance of recovering it."""
    library, problem = load_library("{not json")
    assert library.profiles == []
    assert problem is not None
    assert "left untouched" in problem


def test_size_warning_only_fires_near_the_quota():
    assert size_warning("small") is None
    assert size_warning("x" * (SOFT_LIMIT_BYTES + 1)) is not None


def test_bridge_mounts_without_error_on_the_entry_point():
    at = AppTest.from_file("src/streamlit_app.py")
    at.run(timeout=60)
    assert not at.exception


def test_library_survives_a_rerun_within_a_session():
    at = AppTest.from_file("src/streamlit_app.py")
    at.run(timeout=60)
    state = at.session_state["spectrastream"]
    state.library.upsert(InstrumentProfile(name="Persisted"))
    at.run(timeout=60)
    assert [p.name for p in at.session_state["spectrastream"].library.profiles] == [
        "Persisted"
    ]
