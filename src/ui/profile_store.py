"""Keeps AppState.library and browser storage in step.

Mounted once per run from the entry point, so every page sees a hydrated
library. The ordering rule that matters: never write until the browser has
answered at least once, otherwise the first render would persist an empty
library over the user's real profiles.
"""

import streamlit as st

from spectrastream.profiles import ProfileLibrary
from ui import localstore
from ui.state import AppState

_PENDING_KEY = "spectrastream_pending_write"
_CLEAR_KEY = "spectrastream_pending_clear"


def request_save(library: ProfileLibrary) -> None:
    """Queue the library to be written on the next run.

    The write is queued rather than performed because the bridge is mounted at
    the top of the script: by the time a page callback edits a profile, this
    run's component has already been instantiated and mutating its state would
    raise.
    """
    st.session_state[_PENDING_KEY] = localstore.serialise(library)
    st.session_state.pop(_CLEAR_KEY, None)


def request_clear() -> None:
    st.session_state[_CLEAR_KEY] = True
    st.session_state.pop(_PENDING_KEY, None)


def sync(state: AppState) -> None:
    """Mount the bridge and reconcile it with ``state.library``."""
    pending = st.session_state.pop(_PENDING_KEY, None)
    clear = bool(st.session_state.pop(_CLEAR_KEY, False))

    result = localstore.sync(pending_write=pending, clear=clear)

    if not result.answered:
        # First render: the browser has not reported yet. Leave the in-memory
        # library alone and wait for the rerun the component will trigger.
        return

    state.storage_persistent = result.available

    if not result.available:
        if not state.library_loaded:
            state.library_loaded = True
        return

    if clear:
        state.library = ProfileLibrary()
        state.library_loaded = True
        return

    if pending is not None:
        # We just wrote; the echo is our own text. Trust the in-memory copy.
        state.library_loaded = True
        return

    library, problem = localstore.load_library(result.text)
    if problem and not st.session_state.get("spectrastream_load_warned"):
        st.session_state["spectrastream_load_warned"] = True
        st.warning(problem, icon=":material/warning:")
    state.library = library
    state.library_loaded = True


def save(state: AppState) -> None:
    """Persist the current library and rerun so the write actually happens."""
    request_save(state.library)
    st.rerun()
