"""One typed object in session state, instead of six defaultdicts.

The previous app kept ``cache_bools``/``cache_strings``/``cache_dicts``/... and
addressed them with string keys from every page, which made it impossible to see
what state existed or who wrote it. Everything the UI needs now hangs off
``AppState``, so a reader can find it in one place.
"""

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from spectrastream.acquisition import Acquisition
from spectrastream.calibration.engines.base import FittedCalibration
from spectrastream.ingest import LoadedSpectrum
from spectrastream.profiles import InstrumentProfile, OpticalPath, ProfileLibrary

STATE_KEY = "spectrastream"


@dataclass
class CalibrationDraft:
    """A calibration being built on the calibrate page, before it is saved."""

    recipe_id: str | None = None
    inputs: dict[str, LoadedSpectrum] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    fitted: FittedCalibration | None = None
    error: str | None = None

    def clear_result(self) -> None:
        self.fitted = None
        self.error = None


@dataclass
class AppState:
    """Everything the UI remembers for one browser session."""

    library: ProfileLibrary = field(default_factory=ProfileLibrary)
    #: Set once the browser store has answered, so pages do not save an empty
    #: library over real data during the first render.
    library_loaded: bool = False
    storage_persistent: bool = True
    active_profile_id: str | None = None
    #: Which optical path of that instrument. Calibration and wavelength hang
    #: off the path, so this is the more meaningful selection of the two.
    active_optical_path_id: str | None = None
    target: LoadedSpectrum | None = None
    #: How the target spectrum was measured. Persists across page switches so
    #: a user does not retype it after wandering off to edit a profile.
    acquisition: Acquisition = field(default_factory=Acquisition)
    #: Fields prefilled from the uploaded file's own header, so the UI can say
    #: which values it guessed rather than presenting them as the user's.
    guessed_fields: set[str] = field(default_factory=set)
    guessed_laser_wl_nm: float | None = None
    draft: CalibrationDraft = field(default_factory=CalibrationDraft)

    @property
    def active_profile(self) -> InstrumentProfile | None:
        if self.active_profile_id is None:
            return None
        return self.library.get(self.active_profile_id)

    @property
    def active_optical_path(self) -> OpticalPath | None:
        """The selected optical path, defaulting to the only one if unambiguous.

        The wavelength lives here rather than on the instrument, so almost
        everything downstream wants this rather than the profile.
        """
        profile = self.active_profile
        if profile is None:
            return None
        path = profile.optical_path(self.active_optical_path_id)
        if path is not None:
            return path
        if len(profile.optical_paths) == 1:
            return profile.optical_paths[0]
        return None

    def set_active_profile(self, profile_id: str | None) -> None:
        if profile_id != self.active_profile_id:
            self.active_optical_path_id = None
        self.active_profile_id = profile_id

    def set_active_optical_path(self, path_id: str | None) -> None:
        self.active_optical_path_id = path_id


def get_state() -> AppState:
    """The single AppState for this session, created on first use."""
    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = AppState()
    return st.session_state[STATE_KEY]
