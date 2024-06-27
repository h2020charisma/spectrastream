#!/usr/bin/env python3
from collections import defaultdict

import pandas as pd

import streamlit as st
from front_end.htmlTemplates import css

from modules.navigation_bar import navbar

from ramanchada2.protocols.calibration import CalibrationModel

from util import plot_original_x_calib_spe, process_file_spe

navbar()


# st.set_page_config(
#     page_title="Raman spectroscopy harmonisation",
#     page_icon="../front_end/images/logo_charisma.jpg",
#     layout="wide",
# )

st.write(css, unsafe_allow_html=True)


def main_page():
    with st.sidebar:

        with st.expander("Instrument settings", expanded=False):
            with st.form("Set instrument wavelength"):
                # st.session_state['cache_strings']['instrument_button'] = ''
                instrument_wl = st.text_input(label="Instrument wavelength")
                # btn_set_instrument_wl =
                btn_set_instrument_wl = st.form_submit_button(
                    "Save instrument settings"
                )
                if btn_set_instrument_wl:
                    st.session_state["cache_dicts"]["instrument_settings"][
                        "wavelength"
                    ] = instrument_wl

                    # st.session_state["cache_strings"]["x_calibration"] = \
                    #                         "btn_set_instrument_wl"

            if st.button("Show instrument"):
                st.session_state["cache_strings"]["x_calibration"] = "show_instrument"

            if st.button("Select instrument"):
                st.session_state["cache_strings"]["x_calibration"] = "select_instrument"

    with st.sidebar:
        with st.expander("Active calibration settings", expanded=False):
            st.session_state["cache_strings"]["active_calibration_btn"] = ""
            if st.button("Choose settings"):
                st.session_state["cache_strings"][
                    "active_calibration_btn"
                ] = "choose_details"

    match st.session_state["cache_strings"]["active_calibration_btn"]:
        case "choose_details":
            st.write(
                "Shows all details concerning selected calibration or "
                "derived calibration which in this case is selected by default\n"
                "Note: the showed information will be context dependent \n"
                "(e.g. X or Y calibration)"  # noqa: E501
            )
        case _:
            pass


main_page()
