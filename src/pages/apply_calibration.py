#!/usr/bin/env python3
from collections import defaultdict

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

import streamlit as st
from front_end.htmlTemplates import css

from modules.models import default_state_target, StateCrop, StateNormalize

from modules.navigation_bar import navbar
from modules.util import (
    apply_calibration_x,
    load_calibration_file,
    plot_original_x_calib_spe,
    process_file_spe,
    simple_plot_spe,
    update_session_state,
)
from ramanchada2.io.output.write_csv import write_csv as io_write_csv

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
        "settings"
    ]
    st.write("-----  Instrument settings -----")
    for key, value in instrument_settings.items():
        if key in [
            # "make_and_model_of_the_instrument",
            # "serial_number_of_the_instrument",
            "laser_wavelength",
        ]:
            st.sidebar.write(f"{key}: {value}")
    st.write("------------------------")


st.session_state["cache_strings"]["btn_load_target_spe"] = "uploaded_target_spectra_btn"


def load_tabs_target_spectrum():

    load_tt, crop_tt, normalize_tt = st.tabs(
        [
            "Load Target",
            # "Show Target",
            "Crop Target",  # 'Baseline corr',
            "Normalize Target",
        ]
    )

    if "target_spe" not in st.session_state["cache_dicts"]["spectrum_settings"]:
        #     state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["target_spe"]
        # else:
        # settings = default_state_target
        # settings.normalize.use_normalize = False
        st.session_state["cache_dicts"]["spectrum_settings"][
            "target_spe"
        ] = default_state_target

    # state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["target_spe"]

    with load_tt:

        # with st.form("Load target"):
        col1, col2 = st.columns(2)

        with col1:
            uploaded_target_spec = st.file_uploader(
                "Load spectrum file",
                accept_multiple_files=False,
            )
        with col2:
            units = st.selectbox(label="Select units", options=[
                                 "cm-1", "nm"], index=0)

            # upload_target_spe_btn = st.form_submit_button("Process spectrum")
        state_settings = st.session_state["cache_dicts"]["spectrum_settings"][
            "target_spe"
        ]

        if uploaded_target_spec:
            target_spe = process_file_spe(
                [uploaded_target_spec], label="Target", units=units
            )

            st.session_state["cache_dicts"]["page01_load_spe"][
                "target_spe"
            ] = target_spe

            st.session_state["cache_dicts"]["page01_load_spe"][
                "target_spe_current"
            ] = target_spe

            target_units = target_spe.meta["units"]

            target_units = "$\mathrm{cm}^{-1}$" if target_units == "cm-1" else target_units

            simple_plot_spe(
                spe=target_spe,
                label="Target",
                xlabel=r"Raman shift [{}]".format(target_units),
            )

        else:
            if "target_spe" in st.session_state["cache_dicts"]["page01_load_spe"]:
                spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]
                spe_units = spe.meta["units"]

                # st.session_state["cache_dicts"]["spectra_x_current"]["si"] = si_spe
                st.session_state["cache_dicts"]["page01_load_spe"][
                    "target_spe_current"
                ] = spe

                spe_units = "$\mathrm{cm}^{-1}$" if spe_units == "cm-1" else spe_units

                simple_plot_spe(
                    spe=spe,
                    label="Target",
                    xlabel=r"Raman shift [{}]".format(spe_units),
                )

    with crop_tt:
        if "target_spe_current" in st.session_state["cache_dicts"]["page01_load_spe"]:

            # spe = st.session_state["cache_dicts"]["page01_load_spe"][
            #     "target_spe_current"
            # ]
            spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]
            spe_units = spe.meta["units"]

            label, xlabel = "Target", r"Raman shift [{}]".format(spe_units)
            ax = spe.plot(label=label, linestyle="dashed", color="blue")
            ax.set_xlabel(xlabel)

            settings_crop = state_settings.crop

            use_crop = st.checkbox(
                key="crop_target_checkbox",
                label="Use crop",
                on_change=uploaded_target_spectra_btn(
                    "uploaded_target_spectra_btn"),
                value=settings_crop.use_crop,
            )

            # Create a form for the input fields and submit button
            with st.form(key="target_crop_form"):
                # Create three columns: two for input fields and one for the submit button
                col0, col1, col2 = st.columns([0.5, 1, 1])

                with col0:
                    st.write("")  # This is to adjust the position of the button
                    submit_crop_btn = st.form_submit_button(
                        # key="use_crop_target",
                        label="Update",
                        #   disabled=not use_crop
                    )
                with col1:
                    min_val = (
                        settings_crop.crop_min if settings_crop.crop_min else min(
                            spe.x)
                    )
                    min_val = st.number_input(
                        "Minimum Value:",
                        value=min_val,
                        format="%f",
                        key="min_val_target_crop",
                        # disabled=not use_crop
                    )
                with col2:

                    max_val = (
                        settings_crop.crop_max if settings_crop.crop_max else max(
                            spe.x)
                    )

                    max_val = st.number_input(
                        "Maximum Value:",
                        value=max_val,
                        format="%f",
                        key="max_val_target_crop",
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

            settings_crop.use_crop = use_crop
            settings_crop.crop_min = min_val
            settings_crop.crop_max = max_val

            if use_crop:
                # Save the spectrum
                st.session_state["cache_dicts"]["page01_load_spe"][
                    "target_spe_current"
                ] = spe_croped

                state_settings.crop = settings_crop

            if use_crop or submit_crop_btn:

                spe_units = spe_croped.meta["units"]

                xlabel = r"Raman shift [{}]".format(spe_units)
                ax = spe.plot(label=label, linestyle="dashed", color="blue")
                ax.set_xlabel(xlabel)

                ax = spe_croped.plot(ax=ax, label="Target crop", color="red")

            fig = ax.get_figure()
            st.pyplot(fig)

            st.session_state["cache_dicts"]["spectrum_settings"][
                "target_spe"
            ] = state_settings

    with normalize_tt:
        if "target_spe_current" in st.session_state["cache_dicts"]["page01_load_spe"]:

            spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]

            spe_units = spe.meta["units"]

            label, xlabel = "Target", r"Raman shift [{}]".format(spe_units)
            ax = spe.plot(label=label, linestyle="dashed")
            ax.set_xlabel(xlabel)
            # ax.set_ylabel("Target", color="blue")

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"][
                "target_spe"
            ]
            settings_normalize: StateNormalize = state_settings.normalize

            use_normalize = st.checkbox(
                key="target_normalize_checkbox",
                label="Use Min-max Normalization",
                on_change=uploaded_target_spectra_btn(
                    "uploaded_target_spectra_btn"),
                value=settings_normalize.use_normalize,
            )

            # normalized_spe = spe.normalize()

            # simple_plot_spe(
            #     spe=normalized_spe, label="Target normalized", xlabel=r"Raman shift"
            # )

            if use_normalize:

                # spe_current = st.session_state["cache_dicts"]["spectra_x_current"][
                #     "neon"
                # ]
                # spe_current = st.session_state["cache_dicts"]["spectra_x_last"][
                #     "neon"
                # ]
                spe_current = st.session_state["cache_dicts"]["page01_load_spe"][
                    "target_spe_current"
                ]
                normalized_spe = spe_current.normalize()

                st.session_state["cache_dicts"]["page01_load_spe"][
                    "target_spe_current"
                ] = normalized_spe

                state_settings.normalize = settings_normalize

                ax2 = ax.twinx()

                ax2 = normalized_spe.plot(
                    ax=ax2,
                    # label='Neon normalized',
                    color="red",
                    # linestyle='dashed'
                )

                ax2.set_ylabel("Intensity [a.u.]")

                red_patch = mpatches.Patch(color="blue", label="Neon")

                blue_patch = mpatches.Patch(
                    color="red", label="Target normalized")

                ax2.legend(handles=[red_patch, blue_patch])

                fig = ax2.get_figure()
                st.pyplot(fig)

            else:

                fig = ax.get_figure()
                st.pyplot(fig)

            st.session_state["cache_dicts"]["spectrum_settings"][
                "target_spe"
            ] = state_settings


with st.sidebar:

    target_spe_btn = st.button("Target spectrum")

    if target_spe_btn:

        st.session_state["cache_dicts"]["page03_apply_calib"][
            "btn_press"
        ] = "target_spe_btn"

    # apply_x_calib_btn = st.button("Apply X-Calibration")

    with st.form("apply_calibration"):

        x_calib = st.checkbox(label="X-calibration")

        y_calib = st.checkbox(label="Y-calibration")

        apply_calib_bnt = st.form_submit_button("Apply Calibration")

        if apply_calib_bnt:
            # st.session_state["cache_bools"]["x_calib"] = x_calib
            # st.session_state["cache_bools"]["y_calib"] = y_calib

            if (
                "target_spe_current"
                not in st.session_state["cache_dicts"]["page01_load_spe"]
            ):
                st.error("Target spectrum not loaded")

            if x_calib:

                assert (
                    "xcalibration_model"
                    in st.session_state["cache_dicts"]["x_calibration"]
                )

            st.session_state["cache_bools"]["x_calib"] = x_calib

            if y_calib:

                if (
                    "ycalibration_model"
                    not in st.session_state["cache_dicts"]["y_calibration"]
                ):
                    st.error("Load Y calibration")

            st.session_state["cache_bools"]["y_calib"] = y_calib

            st.session_state["cache_dicts"]["page03_apply_calib"][
                "btn_press"
            ] = "apply_calib_btn"

    # if apply_x_calib_btn:
    #     if (
    #         "target_spe_current"
    #         not in st.session_state["cache_dicts"]["page01_load_spe"]
    #     ):
    #         st.error("Target spectrum not loaded")

    #     assert "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]
    #     st.session_state["cache_dicts"]["page03_apply_calib"][
    #         "btn_press"
    #     ] = "apply_x_calib_btn"

    # apply_y_calib_btn = st.button("Apply Y-Calibration")

    # if apply_y_calib_btn:
    #     if (
    #         "target_spe_current"
    #         not in st.session_state["cache_dicts"]["page01_load_spe"]
    #     ):
    #         st.error("Target spectrum not loaded")

    #     assert "ycalibration_model" in st.session_state["cache_dicts"]["y_calibration"]
    #     st.session_state["cache_dicts"]["page03_apply_calib"][
    #         "btn_press"
    #     ] = "apply_y_calib_btn"


btn_press = None
if "btn_press" in st.session_state["cache_dicts"]["page03_apply_calib"]:
    btn_press = st.session_state["cache_dicts"]["page03_apply_calib"]["btn_press"]

# target_spe = st.session_state["cache_dicts"]["page01_load_spe"]["target_spe"]

if btn_press == "apply_calib_btn":

    x_calib = st.session_state["cache_bools"]["x_calib"]
    y_calib = st.session_state["cache_bools"]["y_calib"]

    print(x_calib, y_calib)
    target_spe = st.session_state["cache_dicts"]["page01_load_spe"][
        "target_spe_current"
    ]

    if x_calib:
        target_spe = st.session_state["cache_dicts"]["page01_load_spe"][
            "target_spe_current"
        ]

        calmodel = st.session_state["cache_dicts"]["x_calibration"][
            "xcalibration_model"
        ]

        spe_si = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

        spe_sil_ne_calib = st.session_state["cache_dicts"]["x_calibration"][
            "spe_sil_ne_calib"
        ]

        # target_spe = st.session_state["cache_dicts"]["page01_load_spe"][
        #     "target_spe_current"
        # ]

        fig, axes = plt.subplots(3, 1, sharex=False, figsize=(12, 10))

        calmodel.plot(ax=axes[0])

        red_patch = mpatches.Patch(color="blue", label="Neon peaks")
        blue_patch = mpatches.Patch(color="red", label="Neon reference")

        axes[0].legend(handles=[red_patch, blue_patch])

        spe_si.plot(ax=axes[1], label="Si processed", color="blue")
        si_units = spe_si.meta["units"]

        si_calibrated = apply_calibration_x(calmodel, spe_si, si_units)

        si_calibrated.plot(ax=axes[1], color="orange", label="Si calibrated")
        axes[1].legend()

        si_units = "$\mathrm{cm}^{-1}$" if si_units == "cm-1" else si_units
        axes[1].set_xlabel(r"Raman shift " + si_units)
        axes[1].set_xlim(520.45 - 50, 520.45 + 50)

        # Target spectrum
        target_spe.plot(ax=axes[2], label="Target", color="blue")

        target_units = target_spe.meta["units"]
        target_calibrated = apply_calibration_x(
            calmodel, target_spe, target_units)

        target_units = "$\mathrm{cm}^{-1}$" if target_units == "cm-1" else target_units
        axes[2].set_xlabel(r"Raman shift " + target_units)

        target_calibrated.plot(
            ax=axes[2], color="orange", label="Target calibrated")

        st.pyplot(fig)

        csv = io_write_csv(target_calibrated.x, target_calibrated.y)
        str_csv = "".join(csv)
        st.download_button(
            "Download X-Calibrated spectrum (CSV)",
            data=str_csv,
            file_name="xcalibrated_spectrum.csv",
        )

        ylabel = 'Intensity [ a.u.]'
        axes[0].set_ylabel(ylabel)
        axes[1].set_ylabel(ylabel)
        axes[1].set_ylabel(ylabel)

        target_spe = target_calibrated

    if y_calib:

        ycalmodel = st.session_state["cache_dicts"]["y_calibration"][
            "ycalibration_model"
        ]
        spe_srm = st.session_state["cache_dicts"]["spectra_y_current"]["srm_ref"]

        ax = spe_srm.plot(label="SRM experimental", color="red")

        target_spe.plot(ax=ax, label="Target spectrum", color="blue")

        spe_ycalibrated = ycalmodel.process(target_spe)

        ax_twinx = ax.twinx()
        spe_ycalibrated.plot(label="Y-calibrated", color="green", ax=ax_twinx)

        blue_patch = mpatches.Patch(color="blue", label="Target spectrum")

        red_patch = mpatches.Patch(
            color="red", label="SRM experimental")

        green_patch = mpatches.Patch(color="green", label="Y-calibrated")

        ax.legend(handles=[red_patch, blue_patch], loc='upper left')
        ax_twinx.legend(handles=[green_patch], loc='upper right')

        fig = ax.get_figure()

        spe_units = target_spe.meta["units"]
        spe_units = "$\mathrm{cm}^{-1}$" if spe_units == "cm-1" else spe_units
        ax.set_xlabel(r"Raman shift " + spe_units)

        ylabel = 'Intensity [ a.u.]'
        ax.set_ylabel(ylabel)

        st.pyplot(fig)

        csv = io_write_csv(spe_ycalibrated.x, spe_ycalibrated.y)
        str_csv = "".join(csv)
        st.download_button(
            "Download Y-Calibrated spectrum (CSV)",
            data=str_csv,
            file_name="ycalibrated_spectrum.csv",
        )

elif btn_press == "target_spe_btn":

    load_tabs_target_spectrum()
