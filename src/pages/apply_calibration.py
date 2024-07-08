#!/usr/bin/env python3
from collections import defaultdict

import pandas as pd

import streamlit as st
from front_end.htmlTemplates import css

from modules.navigation_bar import navbar

from modules.util import plot_original_x_calib_spe, process_file_spe

from ramanchada2.protocols.calibration import CalibrationModel

from modules.util import (
    simple_plot_spe
)

navbar()


# st.set_page_config(
#     page_title="Raman spectroscopy harmonisation",
#     page_icon="../front_end/images/logo_charisma.jpg",
#     layout="wide",
# )

st.write(css, unsafe_allow_html=True)


def main_page():
    with st.sidebar:

        # apply_x_calib_btn = st.button("Apply X-Calibration")

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


# main_page()

with st.sidebar:
    show_original_spe_btn = st.button("Show original Spe")

    if show_original_spe_btn:

        # if not "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]:
        #     st.write("Calibration not loaded or created...")
        # else:
        # assert "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]
        st.session_state["cache_dicts"]["page03_apply_calib"]['btn_press'] = "show_original_spe_btn"

    apply_x_calib_btn = st.button("Apply X-Calibration")

    if apply_x_calib_btn:

        # if not "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]:
        #     st.write("Calibration not loaded or created...")
        # else:
        assert "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]
        st.session_state["cache_dicts"]["page03_apply_calib"]['btn_press'] = "apply_x_calib_btn"


btn_press = None
if 'btn_press' in st.session_state["cache_dicts"]["page03_apply_calib"]:
    btn_press = st.session_state["cache_dicts"]["page03_apply_calib"]['btn_press']

target_spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]

if btn_press == "apply_x_calib_btn":

    calmodel = st.session_state["cache_dicts"]["x_calibration"]["xcalibration_model"]

    target_spe_units = target_spe.meta["units"]
    target_spe_calibrated = calmodel.apply_calibration_x(target_spe,
                                                         spe_units=target_spe_units)
    simple_plot_spe(spe=target_spe_calibrated,
                    label="X-Calibrated spe", xlabel=r"Raman shift")

elif btn_press == "show_original_spe_btn":

    simple_plot_spe(spe=target_spe,
                    label="Target spe", xlabel=r"Raman shift")

    # def apply_calibration_x(self, old_spe: Spectrum, spe_units="cm-1"):
    #     # neon calibration converts to nm
    #     # silicon calibration takes nm and converts back to cm-1 using laser zeroing
    #     new_spe = old_spe
    #     model_units = spe_units
    #     for model in self.components:
    #         # TODO: tbd find out if to convert units
    #         if model.enabled:
    #             new_spe = model.process(new_spe, model_units, convert_back=False)
    #             model_units = model.model_units
    #     return new_spe

    # x_calib_btn = st.session_state["cache_strings"]["x_calibration"]

    # if x_calib_btn == "uploaded_neon_calib_spectra_btn":
    #     st.write("Show the neon spe..")
    #     neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]

    #     simple_plot_spe(spe=neon_spe, label="Neon",
    #                     xlabel=r"Raman shift [$\mathrm{nm}$]")
