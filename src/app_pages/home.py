import streamlit as st

from ui.state import get_state

state = get_state()

st.subheader("Any spectrum in, FAIR data out")
st.markdown(
    """
    Upload a Raman spectrum in almost any vendor format and get back a
    **NeXus** file — the open, self-describing format for analytical data.
    Calibration is optional: if you have reference measurements, the axis is
    corrected before the file is written; if you do not, you still get a valid,
    shareable record.
    """
)

left, middle, right = st.columns(3)
with left:
    with st.container(border=True):
        st.markdown("#### :material/upload_file: 1 · Convert")
        st.markdown(
            "Drop in a spectrum. Download NeXus straight away — no metadata required."
        )
with middle:
    with st.container(border=True):
        st.markdown("#### :material/precision_manufacturing: 2 · Describe")
        st.markdown(
            "Optionally save an instrument profile. It stays in this browser "
            "and enriches every file you export."
        )
with right:
    with st.container(border=True):
        st.markdown("#### :material/tune: 3 · Calibrate")
        st.markdown(
            "Optionally derive a calibration from reference spectra and attach "
            "it to a profile for reuse."
        )

st.subheader("What you need")
st.markdown(
    """
    - **Nothing at all** for the NeXus floor — just a spectrum file.
    - **Reference measurements** if you want calibration. Which ones depends on
      the protocol you pick: the CHARISMA route uses a neon lamp for the shape
      of the wavenumber axis and a silicon wafer for its zero, and either can
      stand alone.
    - A **standard reference material** measurement if you also want relative
      intensity calibration.
    """
)

if state.library.profiles:
    st.caption(
        f"{len(state.library.profiles)} instrument profile(s) saved in this browser."
    )

with st.expander("About this alpha", icon=":material/info:"):
    st.markdown(
        """
        SpectraStream is a demonstrator for FAIR analytical data built on
        [ramanchada2](https://github.com/h2020charisma/ramanchada2) and the
        [CHARISMA](https://www.h2020charisma.eu/) calibration protocols. It is
        not a batch tool — for that, use ramanchada2 directly or
        [Oranchada](https://github.com/h2020charisma/oranchada).

        Instrument profiles are stored **in your browser**, not on the server.
        Clearing site data removes them, so export anything you want to keep.

        - [Report a bug](https://github.com/h2020charisma/spectrastream/issues)
        - [Discussions](https://github.com/h2020charisma/spectrastream/discussions)
        """
    )
