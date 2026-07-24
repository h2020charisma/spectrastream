"""Interaction tests for the profile lifecycle.

Render smoke tests are not enough: creating an instrument and finding it still
absent is exactly the kind of bug that renders perfectly. These drive the real
widgets and assert on what the user would see next.

The browser-storage bridge cannot run in AppTest, so ``_answer_browser``
simulates what the component reports back -- which is the code path that makes
the difference between the library surviving a rerun and being clobbered.
"""

from streamlit.testing.v1 import AppTest

from spectrastream.profiles import InstrumentProfile, OpticalPath
from ui.localstore import COMPONENT_KEY

APP = "src/streamlit_app.py"


def _answer_browser(at, text=None, available=True):
    """Pretend the localStorage component replied with ``text``."""
    at.session_state[COMPONENT_KEY] = {
        "state": {"available": available, "text": text, "error": None}
    }
    return at


def _state(at):
    return at.session_state["spectrastream"]


def _queue_save(at, library):
    """Queue a write the way profile_store.request_save does.

    Set directly rather than by calling request_save: outside a script run
    there is no ScriptRunContext, so `st.session_state` writes go nowhere.
    """
    from ui.localstore import serialise
    from ui.profile_store import _CLEAR_KEY, _PENDING_KEY

    at.session_state[_PENDING_KEY] = serialise(library)
    if _CLEAR_KEY in at.session_state:
        del at.session_state[_CLEAR_KEY]


def _goto(at, page):
    """AppTest drives one script; run the page directly with shared state."""
    page_at = AppTest.from_file(page)
    page_at.session_state["spectrastream"] = _state(at)
    page_at.run(timeout=60)
    return page_at


def test_created_instrument_is_visible_afterwards():
    """The reported bug: create an instrument, page still says there are none."""
    at = AppTest.from_file(APP)
    _answer_browser(at, text=None)
    at.run(timeout=60)

    state = _state(at)
    state.library.upsert(InstrumentProfile(name="My rig"))

    # The save queues a write and reruns, exactly as the dialog does.
    _queue_save(at, state.library)
    at.run(timeout=60)

    assert [p.name for p in _state(at).library.profiles] == ["My rig"]

    page = _goto(at, "src/app_pages/profiles.py")
    assert not page.exception
    assert not any("No instruments yet" in i.value for i in page.info)


def test_a_stale_browser_echo_does_not_wipe_a_fresh_edit():
    """Storage always lags a save by at least one rerun. Re-reading it every
    run would silently replace what the user just entered."""
    at = AppTest.from_file(APP)
    _answer_browser(at, text=None)
    at.run(timeout=60)

    state = _state(at)
    state.library.upsert(InstrumentProfile(name="Just created"))

    # Browser still reports the pre-save contents.
    _answer_browser(at, text='{"schema_version": 2, "profiles": []}')
    at.run(timeout=60)

    assert [p.name for p in _state(at).library.profiles] == ["Just created"]


def test_a_queued_write_survives_a_run_where_the_browser_is_silent():
    """Popping the pending write and then returning early would drop the save."""
    from ui.profile_store import _PENDING_KEY

    at = AppTest.from_file(APP)
    at.run(timeout=60)  # no browser answer at all

    state = _state(at)
    state.library.upsert(InstrumentProfile(name="Pending rig"))
    _queue_save(at, state.library)

    at.run(timeout=60)
    assert _PENDING_KEY in at.session_state, "the queued write was thrown away"


def test_profiles_load_from_storage_once_then_memory_wins():
    stored = (
        '{"schema_version": 2, "profiles": [{"id": "abc", "name": "Stored rig",'
        ' "optical_paths": []}]}'
    )
    at = AppTest.from_file(APP)
    _answer_browser(at, text=stored)
    at.run(timeout=60)

    state = _state(at)
    assert [p.name for p in state.library.profiles] == ["Stored rig"]
    assert state.library_loaded

    state.library.profiles[0].name = "Renamed in memory"
    at.run(timeout=60)
    assert _state(at).library.profiles[0].name == "Renamed in memory"


def test_unavailable_storage_is_surfaced_not_silent():
    at = AppTest.from_file(APP)
    _answer_browser(at, text=None, available=False)
    at.run(timeout=60)
    assert _state(at).storage_persistent is False

    page = _goto(at, "src/app_pages/profiles.py")
    assert any("local storage" in w.value for w in page.warning)


def test_units_are_asked_alongside_the_uploader():
    """Nothing in a data file says whether x is cm-1, nm or pixels, so the
    question has to come with the file -- not after it has been plotted and
    labelled under a guess."""
    at = AppTest.from_file(APP)
    _answer_browser(at, text=None)
    at.run(timeout=60)

    page = _goto(at, "src/app_pages/convert.py")
    assert not page.exception
    assert page.file_uploader

    units = [s for s in page.selectbox if "units" in s.label.lower()]
    assert units, "the units question is missing"
    assert len(page.selectbox) == 1, "nothing else should be asked before a file"


def test_convert_page_uses_the_optical_path_wavelength(target_spectrum):
    """Bypass the uploader (AppTest cannot drive it) and check the page picks
    the wavelength up from the path rather than demanding it again."""
    at = AppTest.from_file(APP)
    _answer_browser(at, text=None)
    at.run(timeout=60)

    profile = InstrumentProfile(name="Lab rig")
    profile.add_optical_path(OpticalPath(op_id="OP1", laser_wl_nm=532))
    state = _state(at)
    state.library.upsert(profile)
    state.set_active_profile(profile.id)
    state.target = target_spectrum

    page = _goto(at, "src/app_pages/convert.py")
    assert not page.exception

    wavelength = [n for n in page.number_input if "wavelength" in n.label.lower()]
    assert wavelength, "no wavelength field rendered"
    assert wavelength[0].value == 532
    assert wavelength[0].disabled, "the path is authoritative; do not invite edits"

    # Nothing is missing, so the NeXus download is offered.
    assert any("NeXus" in b.label for b in page.download_button)


def test_calibrate_page_reaches_the_protocol_choice_for_a_real_path():
    at = AppTest.from_file(APP)
    _answer_browser(at, text=None)
    at.run(timeout=60)

    profile = InstrumentProfile(name="Lab rig")
    profile.add_optical_path(OpticalPath(op_id="OP1", laser_wl_nm=532))
    state = _state(at)
    state.library.upsert(profile)
    state.set_active_profile(profile.id)

    page = _goto(at, "src/app_pages/calibrate.py")
    assert not page.exception
    # Got past instrument and path selection to protocol selection.
    assert page.segmented_control, "no protocol chooser rendered"
    assert page.file_uploader, "no reference-spectrum uploaders rendered"
