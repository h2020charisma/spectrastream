#!/usr/bin/env python3
from collections import defaultdict

import pandas as pd

import streamlit as st
from front_end.htmlTemplates import css
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from modules.navigation_bar import navbar

from modules.util import (
    apply_calibration_x,
    load_calibration_file,
    plot_original_x_calib_spe,
    process_file_spe,
    simple_plot_spe,
    update_session_state,
)

from ramanchada2.protocols.calibration import CalibrationModel

navbar()


st.write(css, unsafe_allow_html=True)


def uploaded_target_spectra_btn(value):
    # btn_load_target_spe = st.session_state["cache_strings"]["btn_load_target_spe"]
    def uploaded_target_spectra_btn_val():
        st.session_state["cache_strings"]["btn_load_target_spe"] = value

    return uploaded_target_spectra_btn_val


with st.sidebar:

    # st.sidebar.image("./src/front_end/images/logo_charisma.jpg")
    # st.header("AI data extractor")
    target_spe_choices = ["Search target spectrum", "Load target spectrum"]

    def set_target_spe_choice_change():

        spe_choice = st.session_state["cache_strings"]["target_spe_choice"]
        assert spe_choice in target_spe_choices, (
            spe_choice, target_spe_choices)
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

    if "settings" not in st.session_state["cache_dicts"]["instrument_settings"]:
        st.error("Set Instrument settings first")

    instrument_settings = st.session_state["cache_dicts"]["instrument_settings"][
        "settings"]
    st.write('-----  Instrument settings -----')
    for key, value in instrument_settings.items():
        if key in ['make_and_model_of_the_instrument', 'serial_number_of_the_instrument', 'laser_wavelength']:
            st.sidebar.write(f"{key}: {value}")
        # st.write(instrument_settings)
    st.write('------------------------')

    # target_spe_choice = st.radio(
    #     "Choose target spectrum option",
    #     target_spe_choices,
    #     index=target_spe_choices.index(target_spe_choice_),
    #     on_change=set_target_spe_choice_change(),
    # )

    # st.session_state["cache_strings"]["target_spe_choice"] = target_spe_choice

    # if target_spe_choice == "Search target spectrum":
    #     with st.sidebar:
    #         existing_calibration = st.text_input(
    #             "Search for target spectra in DB", "")

    # else:

    #     st.session_state["cache_strings"][
    #         "btn_load_target_spe"
    #     ] = "uploaded_target_spectra_btn"

st.session_state["cache_strings"][
    "btn_load_target_spe"
] = "uploaded_target_spectra_btn"


def load_tabs_target_spectrum():

    load_tt, show_spec_tt, crop_tt, normalize_tt = st.tabs(
        ["Load Target",
            "Show Target",
            "Crop Target",  # 'Baseline corr',
            "Normalize Target",
         ]
    )

    with load_tt:

        with st.form("Load target"):
            col1, col2 = st.columns(2)

            with col1:
                uploaded_target_spec = st.file_uploader(
                    "Load spectrum file", accept_multiple_files=False,
                )
            with col2:
                units = st.selectbox(label="Select units", options=[
                    "cm-1", "nm"], index=0)

            upload_target_spe_btn = st.form_submit_button("Process spectrum")

        if upload_target_spe_btn and uploaded_target_spec:
            target_spe = process_file_spe(
                [uploaded_target_spec], label="Target", units=units
            )

            st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"] = target_spe

            st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"] = target_spe

    with show_spec_tt:
        if "target_spe_current" in st.session_state["cache_dicts"]["page01_load_spe"]:
            target_spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"]

            target_units = target_spe.meta['units']

            simple_plot_spe(spe=target_spe, label="Target",
                            xlabel=r"Raman shift [{}]".format(target_units))

    with crop_tt:
        if "target_spe_current" in st.session_state["cache_dicts"]["page01_load_spe"]:

            spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"]

            use_crop = st.checkbox(
                key="crop_target_checkbox",
                label="Use crop",
                on_change=uploaded_target_spectra_btn(
                    "uploaded_target_spectra_btn"),
            )

            # Create a form for the input fields and submit button
            with st.form(key="target_crop_form"):
                # Create three columns: two for input fields and one for the submit button
                col0, col1, col2 = st.columns([0.5, 1, 1])

                with col0:
                    st.write("")  # This is to adjust the position of the button
                    submit_crop_btn = st.form_submit_button(
                        label="Update",
                        #   disabled=not use_crop
                    )
                with col1:
                    min_val = st.number_input(
                        "Minimum Value:",
                        value=min(spe.x),
                        format="%f",
                        # disabled=not use_crop
                    )
                with col2:
                    max_val = st.number_input(
                        "Maximum Value:",
                        value=max(spe.x),
                        format="%f",
                        # disabled=not use_crop
                    )

            # Check if the form is submitted
            # if True:  # submit_neon_crop_btn:
            if min_val > max_val:
                st.error("Minimum value cannot be greater than Maximum value.")
            # else:
            uploaded_target_spectra_btn("uploaded_target_spectra_btn")
            # st.success(f"Range set from {min_val} to {max_val}")

            spe_croped = spe.trim_axes(
                method="x-axis", boundaries=(min_val, max_val))

            simple_plot_spe(spe=spe_croped, label="Neon crop",
                            xlabel=r"Raman shift")

            st.session_state["cache_dicts"]["page01_load_spe"][
                "target_spe_croped"
            ] = spe_croped

            if use_crop:
                # Save the spectrum
                st.session_state["cache_dicts"]["page01_load_spe"][
                    "target_spe_current"
                ] = spe_croped

    with normalize_tt:
        if "target_spe_current" in st.session_state["cache_dicts"]["page01_load_spe"]:

            use_normalize = st.checkbox(
                key="neon_normalize_checkbox",
                label="Use normalization",
                on_change=uploaded_target_spectra_btn(
                    "uploaded_target_spectra_btn"),
            )

            spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"]

            normalized_spe = spe.normalize()

            simple_plot_spe(
                spe=normalized_spe, label="Target normalized", xlabel=r"Raman shift"
            )

            st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_normalized"] = \
                normalized_spe

            if use_normalize:
                st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"] = \
                    normalized_spe


with st.sidebar:

    target_spe_btn = st.button("Target spectrum")

    if target_spe_btn:

        st.session_state["cache_dicts"]["page03_apply_calib"]["btn_press"] = \
            "target_spe_btn"

    apply_x_calib_btn = st.button("Apply X-Calibration")

    if apply_x_calib_btn:
        if 'target_spe_current' not in st.session_state["cache_dicts"]["page01_load_spe"]:
            st.error('Target spectrum not loaded')

        assert "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]
        st.session_state["cache_dicts"]["page03_apply_calib"][
            "btn_press"
        ] = "apply_x_calib_btn"


btn_press = None
if "btn_press" in st.session_state["cache_dicts"]["page03_apply_calib"]:
    btn_press = st.session_state["cache_dicts"]["page03_apply_calib"]["btn_press"]

# target_spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]

if btn_press == "apply_x_calib_btn":

    from matplotlib import pyplot as plt

    target_spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"]

    calmodel = st.session_state["cache_dicts"]["x_calibration"]["xcalibration_model"]

    spe_si = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

    spe_sil_ne_calib = st.session_state["cache_dicts"]["x_calibration"][
        "spe_sil_ne_calib"
    ]

    target_spe = st.session_state["cache_dicts"]["page01_load_spe"][
        "target_spe_current"
    ]

    fig, axes = plt.subplots(3, 1, sharex=False, figsize=(12, 10))

    calmodel.plot(ax=axes[0])

    red_patch = mpatches.Patch(color='blue', label='Neon peaks')
    blue_patch = mpatches.Patch(color='red', label='Neon reference')

    axes[0].legend(handles=[red_patch, blue_patch])

    spe_si.plot(ax=axes[1], label="Si processed", color="blue")
    si_units = spe_si.meta["units"]

    si_calibrated = apply_calibration_x(calmodel, spe_si, si_units)

    si_calibrated.plot(ax=axes[1], color="orange", label="Si calibrated")
    axes[1].legend()
    axes[1].set_xlabel(r"Raman shift " + si_units)
    axes[1].set_xlim(520.45 - 50, 520.45 + 50)

    # Target spectrum
    target_spe.plot(ax=axes[2], label="Target", color="blue")

    target_units = target_spe.meta["units"]
    target_calibrated = apply_calibration_x(calmodel, target_spe, target_units)

    axes[2].set_xlabel(r"Raman shift " + target_units)

    target_calibrated.plot(
        ax=axes[2], color="orange", label="Target calibrated")

    st.pyplot(fig)


elif btn_press == "target_spe_btn":

    load_tabs_target_spectrum()
