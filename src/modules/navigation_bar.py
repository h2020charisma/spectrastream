from pathlib import Path

import streamlit as st

rpath = Path(__file__).parents[1].resolve()

page_icon = str(rpath / "front_end/images/logo_charisma.jpg")


def navbar():
    with st.sidebar:

        st.sidebar.image(page_icon)

        st.page_link("streamlit_app.py", label="Charisma Home Page", icon="🔥")
        st.page_link(
            "pages/load_target_spectra.py", label="Load target spectra", icon="🛡️"
        )
        st.page_link(
            "pages/load_or_create_calibration.py",
            label="Load or create calibration",
            icon="🛡️",
        )
        st.page_link("pages/apply_calibration.py",
                     label="Apply calibration", icon="🛡️")
