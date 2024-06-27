import streamlit as st


def navbar():
    with st.sidebar:

        st.sidebar.image("./front_end/images/logo_charisma.jpg")

        st.page_link("streamlit_app.py", label="Charisma Home Page", icon="🔥")
        st.page_link(
            "pages/load_target_spectra.py", label="1. Load target spectra", icon="🛡️"
        )
        st.page_link(
            "pages/load_or_create_calibration.py",
            label="2. Load or create calibration",
            icon="🛡️",
        )
        st.page_link(
            "pages/apply_calibration.py", label="3. Apply calibration", icon="🛡️"
        )
