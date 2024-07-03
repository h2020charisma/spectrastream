#!/usr/bin/env python3
from collections import defaultdict
from copy import deepcopy

import pandas as pd

import streamlit as st
from front_end.htmlTemplates import css

from modules.navigation_bar import navbar

from modules.util import (
    init_streamlit_cache,
    plot_original_x_calib_spe,
    process_file_spe,
    update_session_state,
)

from ramanchada2.protocols.calibration import CalibrationModel

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
    target_spe_choices = ["Search target spectrum", "Load target spectrum"]

    def set_target_spe_choice_change():

        spe_choice = st.session_state["cache_strings"]["target_spe_choice"]
        assert spe_choice in target_spe_choices, (spe_choice, target_spe_choices)
        if spe_choice == "Search target spectrum":
            set_spe_choice = "Load target spectrum"
        else:  # spe_choice == 'Load target spectrum':
            set_spe_choice = "Search target spectrum"

        st.session_state["cache_strings"]["target_spe_choice"] = set_spe_choice

    if "target_spe_choice" not in st.session_state["cache_strings"]:
        st.session_state["cache_strings"][
            "target_spe_choice"
        ] = "Search target spectrum"

    target_spe_choice_ = st.session_state["cache_strings"]["target_spe_choice"]

    assert target_spe_choice_ in target_spe_choices, (
        target_spe_choice_,
        target_spe_choices,
    )

    target_spe_choice = st.radio(
        "Choose target spectrum option",
        target_spe_choices,
        index=target_spe_choices.index(target_spe_choice_),
        on_change=set_target_spe_choice_change(),
    )

    st.session_state["cache_strings"]["target_spe_choice"] = target_spe_choice

    if target_spe_choice == "Search target spectrum":
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
            st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"] = (
                process_file_spe([uploaded_target_spec], label="Target")
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
    target_spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]
    ax = target_spe.plot(label="Target spe")
    fig = ax.get_figure()
    st.pyplot(fig)
    # submitted_btn_spec = st.form_submit_button("Load spectra")

    # if submitted_btn_spec:

#     #     st.write('TARGET SPE loaded')
# page_1_session_state = {}

# page_1_session_state['cache_dicts'] = deepcopy(
#     st.session_state['cache_dicts'])

this_int = 10
# Prominance!!!!!!
