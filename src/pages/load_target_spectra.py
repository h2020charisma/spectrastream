#!/usr/bin/env python3
from collections import defaultdict
from copy import deepcopy

import pandas as pd

import streamlit as st
from front_end.htmlTemplates import css

from modules.navigation_bar import navbar

from ramanchada2.protocols.calibration import CalibrationModel

from util import plot_original_x_calib_spe, process_file_spe

navbar()


st.title("Load target spectra......")

# st.set_page_config(
#     page_title="Raman spectroscopy harmonisation",
#     page_icon="./src/front_end/images/logo_charisma.jpg",
#     layout="wide",
# )

# st.write(css, unsafe_allow_html=True)


with st.sidebar:

    # st.sidebar.image("./src/front_end/images/logo_charisma.jpg")
    # st.header("AI data extractor")

    calibration_choice = st.radio(
        "Choose target spectra option",
        ["Search target spectra", "Load target spectra"],
        index=0,
    )

    if calibration_choice == "Search target spectra":
        with st.sidebar:
            existing_calibration = st.text_input("Search for target spectra in DB", "")
    else:

        # with st.form("Load target spectra"):

        # st.session_state['cache_strings']['x_calibration']
        # if calibration_choice == "X-calibration":
        uploaded_target_spec = st.file_uploader(
            "Load spectrum file", accept_multiple_files=False
        )

        if uploaded_target_spec:
            st.session_state["cache_dicts"]["target_spe"] = process_file_spe(
                [uploaded_target_spec], label="Target"
            )

            st.session_state["cache_strings"][
                "btn_load_target_spe"
            ] = "uploaded_target_spectra_btn"

# if (st.session_state["cache_strings"][
#         "btn_load_target_spe_"]):
#     print('in IF...')
#     st.session_state["cache_strings"]["x_calibration"] = \
#         st.session_state["cache_strings"]["x_calibration_"]
#     st.session_state["cache_strings"]["x_calibration_"] = None

btn_load_target_spe = st.session_state["cache_strings"]["btn_load_target_spe"]


if btn_load_target_spe == "uploaded_target_spectra_btn":
    target_spe = st.session_state["cache_dicts"]["target_spe"][0]
    ax = target_spe.plot(label="Target spe")
    fig = ax.get_figure()
    st.pyplot(fig)
    # submitted_btn_spec = st.form_submit_button("Load spectra")

    # if submitted_btn_spec:

    #     st.write('TARGET SPE loaded')
page_1_session_state = deepcopy(st.session_state)

this_int = 10
# Prominance!!!!!!
