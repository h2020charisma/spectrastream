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
    simple_plot_spe,
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

        with st.form("Load target spectra"):

            units = st.selectbox(label="Select units", options=["cm-1", "nm"], index=0)

            uploaded_target_spec = st.file_uploader(
                "Load spectrum file", accept_multiple_files=False
            )

            upload_target_spe_btn = st.form_submit_button("Process spectrum")

        if upload_target_spe_btn and uploaded_target_spec:
            target_spe = process_file_spe(
                [uploaded_target_spec], label="Target", units=units
            )

            st.session_state["cache_dicts"]["page01_load_spe"][
                "target_spe"
            ] = target_spe

            st.session_state["cache_strings"][
                "btn_load_target_spe"
            ] = "uploaded_target_spectra_btn"


btn_load_target_spe = st.session_state["cache_strings"]["btn_load_target_spe"]


if btn_load_target_spe == "uploaded_target_spectra_btn":
    target_spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]

    load_tt, crop_tt, normalize_tt = st.tabs(
        [
            "Show Target",
            "Crop Target",  # 'Baseline corr',
            "Normalize Target",
        ]
    )

    with load_tt:
        target_spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]

        # neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
        st.session_state["cache_dicts"]["page01_load_spe"][
            "target_spe_current"
        ] = target_spe

        simple_plot_spe(spe=target_spe, label="Target", xlabel=r"Raman shift")

    with crop_tt:

        spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"]

        use_crop = st.checkbox(
            key="crop_target_checkbox",
            label="Use crop",
            on_change=uploaded_target_spectra_btn("uploaded_target_spectra_btn"),
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

        spe_croped = spe.trim_axes(method="x-axis", boundaries=(min_val, max_val))

        # st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_croped"] = spe_croped
        # st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"] = spe_croped

        simple_plot_spe(spe=spe_croped, label="Neon crop", xlabel=r"Raman shift")

        if use_crop:
            # Save the spectrum
            st.session_state["cache_dicts"]["page01_load_spe"][
                "target_spe_current"
            ] = spe_croped
            st.session_state["cache_dicts"]["page01_load_spe"][
                "target_spe_croped"
            ] = spe_croped

    with normalize_tt:

        use_normalize = st.checkbox(
            key="neon_normalize_checkbox",
            label="Use normalization",
            on_change=uploaded_target_spectra_btn("uploaded_target_spectra_btn"),
        )

        # if True:  # use_normalize:
        # st.write('normlaize tab')
        spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe_current"]

        normalized_spe = spe.normalize()

        simple_plot_spe(
            spe=normalized_spe, label="Target normalized", xlabel=r"Raman shift"
        )
        if use_normalize:
            st.session_state["cache_dicts"]["page01_load_spe"][
                "target_spe_current"
            ] = normalized_spe
            st.session_state["cache_dicts"]["page01_load_spe"][
                "target_spe_normalized"
            ] = normalized_spe

    # ax = target_spe.plot(label="Target spe {}".format(target_spe.meta["units"]))
    # fig = ax.get_figure()
    # st.pyplot(fig)
