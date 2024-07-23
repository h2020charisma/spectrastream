#!/usr/bin/env python3
from ramanchada2.protocols.calibration import (
    CalibrationModel,
    CertificatesDict,
    LazerZeroingComponent,
    XCalibrationComponent,
    YCalibrationCertificate,
    YCalibrationComponent,
)
from ramanchada2.spectrum.baseline.baseline_rc1 import (
    baseline_als, baseline_snip)

from modules.models import (
    StateSpectrum,
    StateCrop,
    StateNormalize,
    StateBaselineCorrection,
    StatePeakFind,
    SNIPBaselineArgs, ALSBaselineArgs,
    default_state_neon, default_state_si
)
from modules.util import (
    apply_calibration_x,
    load_calibration_file,
    plot_original_x_calib_spe,
    process_file_spe,
    simple_plot_spe,
    update_session_state,
    callback_change_value
)
from pydantic import BaseModel, Field
from pydantic import BaseModel
from collections import defaultdict

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import streamlit_pydantic as sp
from front_end.htmlTemplates import css

from modules.navigation_bar import navbar

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

import warnings
# warnings.showwarning("ignore")
warnings.filterwarnings("ignore")


rpath = Path(__file__).parents[1].resolve()

# from pages.load_target_spectra import page_1_session_state, this_int

# print('END session state')
st.set_page_config(
    page_title="Raman spectroscopy harmonisation",
    page_icon=str(rpath / "front_end/images/logo_charisma.jpg"),
    # page_icon="../front_end/images/logo_charisma.jpg",
    layout="centered",
)

st.write(css, unsafe_allow_html=True)


navbar()

# print('page_1_session_state')
# print(this_int)
# print(page_1_session_state)

# print('session state BEFORE update')
# print(st.session_state)
# print('Update session state')
# update_session_state(page_1_session_state, st.session_state)
# print('session state AFTER update')
# print(st.session_state)


# st.session_state.update(page_1_session_state)

# st.session_state["cache_dicts"]["target_spe"] = st.session_state["cache_dicts"][
#     "target_spe"
# ]


# def instrument_settings_expander():
#     # st.write(type(st.session_state))
#     print("This is session state type...")
#     print(type(st.session_state))
#     with st.expander("Instrument settings", expanded=False):

#         if "instrument_settings" not in st.session_state["cache_dicts"]:
#             certificates = CertificatesDict()
#             config_certs = certificates.config_certs
#             # st.write(config_certs)
#             st.session_state["cache_dicts"]["instrument_settings"][
#                 "config_certs"
#             ] = config_certs

#         config_certs = st.session_state["cache_dicts"]["instrument_settings"][
#             "config_certs"
#         ]
#         instrument_wl = st.selectbox(
#             label="Choose wave length", options=list(config_certs.keys()), index=0
#         )

#         st.session_state["cache_dicts"]["instrument_settings"][
#             "instrument_wl"
#         ] = instrument_wl

# certs = certificates.get_certificates(wavelength=532)
# st.write(certificates.config_certs.keys())
# st.write(certs)
# ax = certs[cert].plot(ax=ax)
# st.pyplot(fig)
# 1. Use for specific SRM
# >>> cert = YCalibrationCertificate(
# ...             id="NIST785_SRM2241",
# ...             description="optical glass",
# ...             url="https://tsapps.nist.gov/srmext/certificates/2241.pdf",
# ...             wavelength=785,
# ...             params="A0 = 9.71937e-02, A1 = 2.28325e-04, A2 = -5.86762e-08, A3 = 2.16023e-10, A4 = -9.77171e-14, A5 = 1.15596e-17",
# ...             equation="A0 + A1 * x + A2 * x**2 + A3 * x**3 + A4 * x**4 + A5 * x**5",
# ...             temperature_c=(20, 25),
# ...             raman_shift=(200, 3500)
# ...         )
# ...
# >>> cert.plot()


def active_calibration_settings_expander():
    with st.expander("Active calibration settings", expanded=False):
        st.write("Set active calibration settings...")
        # value = (
        #     10
        #     if "prominence"
        #     not in st.session_state["cache_dicts"]["active_calibration_settings"]
        #     else st.session_state["cache_dicts"]["active_calibration_settings"][
        #         "prominence"
        #     ]
        # )

        # prominence = st.number_input(
        #     label="Prominence", min_value=1, max_value=15, value=value, step=1
        # )

        # st.session_state["cache_dicts"]["active_calibration_settings"][
        #     "prominence"
        # ] = prominence


def load_calibration():

    uploaded_calibration = st.file_uploader(
        "Load calibration file", accept_multiple_files=False
    )

    if uploaded_calibration:

        # load_calibration_file

        xcalibration = load_calibration_file(uploaded_calibration)
        st.session_state["cache_dicts"]["x_calibration"][
            "xcalibration_model"
        ] = xcalibration
        st.session_state["cache_strings"][
            "x_calibration"
        ] = "uploaded_x_calibration_btn"

        return xcalibration
    return None


def load_calibration_spectrum_neon():

    # with st.form("Load Neon spectrum"):
    col1, col2 = st.columns(2)

    with col1:
        uploaded_neon_spec = st.file_uploader(
            "Load spectrum file", accept_multiple_files=False,
        )
    with col2:
        units = st.selectbox(label="Select units", options=[
            "cm-1", "nm"], index=0)

    if uploaded_neon_spec:
        neon_spe = process_file_spe(
            [uploaded_neon_spec], label="Neon", units=units)
        # meta_dct = target_spe.meta
        st.session_state["cache_dicts"]["spectra_x"]["neon"] = neon_spe

        st.session_state["cache_strings"]["x_calibration"] = \
            "uploaded_neon_calib_spectra_btn"


def load_calibration_spectrum_si():

    # with st.form("Load Si spectrum"):
    col1, col2 = st.columns(2)

    with col1:
        uploaded_si_spec = st.file_uploader(
            "Load spectrum file", accept_multiple_files=False,
        )
    with col2:
        units = st.selectbox(label="Select units", options=[
            "cm-1", "nm"], index=0)

        # upload_si_spe_btn = st.form_submit_button("Load spectrum")

    if uploaded_si_spec:
        si_spe = process_file_spe([uploaded_si_spec], label="Si", units=units)
        # meta_dct = target_spe.meta
        st.session_state["cache_dicts"]["spectra_x"]["si"] = si_spe

        st.session_state["cache_strings"][
            "x_calibration"
        ] = "uploaded_si_calib_spectra_btn"


def page_call_STD1_X_Calibration():
    pass


def create_x_calibration_sidebar_expander():

    with st.expander("Create X-Calibration", expanded=False):

        # load_calibration_spectrum_neon()

        with st.form("STD1 Process"):

            page_call_STD1_X_Calibration()

        submitted_btn_st1 = st.button("Neon spectrum")
        if submitted_btn_st1:

            st.session_state["cache_strings"]["x_calibration"] = \
                "submitted_std1_btn"

        submitted_btn_derive_x = st.button(
            "Derive X-Calibration curve")

        if submitted_btn_derive_x:
            st.session_state["cache_strings"]["x_calibration"] = \
                "btn_derive_x_calibration_curve"

        submitted_btn_st2 = st.button("Si spectrum")
        if submitted_btn_st2:

            st.session_state["cache_strings"][
                "x_calibration"
            ] = "submitted_std2_btn"

        submitted_btn_lazer_zeroing = st.button("Lazer zeroing")

        if submitted_btn_lazer_zeroing:
            st.session_state["cache_strings"]["x_calibration"] = "btn_lazer_zeroing"

        import pickle

        calibration_file_name = st.text_input(
            label="Calibration file name",
            placeholder="calibration_file_name.pkl",
            value="calibration_file_name.pkl"
        )
        if "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]:
            calmodel = st.session_state["cache_dicts"]["x_calibration"][
                "xcalibration_model"
            ]
            st.download_button(
                "Download X-Calibration",
                data=pickle.dumps(calmodel),
                file_name=calibration_file_name,
            )
        # with st.form("Save X-calibration"):
        #     # st.write("Save X-calibration")
        #     calibration_file_name = st.text_input(
        #         label="Calibration file name", value="calibration_model01.pkl"
        #     )
        #     submitted_btn_save_x = st.form_submit_button("Save X-Calibration")

        #     if submitted_btn_save_x:
        #         st.session_state["cache_dicts"]["x_calibration"][
        #             "xcalibration_filename"
        #         ] = calibration_file_name

        #         st.download_button(
        #             "Download Model",
        #             data=pickle.dumps(clf),
        #             file_name=calibration_file_name,
        #         )
        #         st.session_state["cache_strings"][
        #             "x_calibration"
        #         ] = "btn_save_x_calibration"


def create_y_calibration_sidebar_expander():
    with st.expander("Create Y-Calibration", expanded=False):

        config_certs = st.session_state["cache_dicts"]["instrument_settings"][
            "config_certs"
        ]

        settings = st.session_state["cache_dicts"]["instrument_settings"][
            "settings_mandatory"
        ]
        instrument_wl = settings.laser_wavelength

        certs_dict = config_certs[str(instrument_wl)]
        certificate_id = st.selectbox(
            label="Reference material certificate",
            options=list(certs_dict.keys()),
            index=0,
        )

        certificate_data = certs_dict[certificate_id]
        # st.write(certificate_data)

        # btn_set_instrument_wl = st.form_submit_button(
        #     "Save instrument settings")
        if st.button("Apply certificate"):

            st.session_state["cache_dicts"]["material_certificate"] = certificate_data
            # YCalibrationCertificate : certificate_data

            st.session_state["cache_strings"][
                "x_calibration"
            ] = "btn_save_material_certificate"

        with st.form("SRM experimental"):
            st.write("SRM Experimental spectrum")

            submitted_btn_srm_experimental = st.form_submit_button(
                "SRM Experimental")
            if submitted_btn_srm_experimental:
                st.session_state["cache_strings"][
                    "x_calibration"
                ] = "submitted_btn_srm_experimental"

        with st.form("Derive Y-calibration"):
            st.write("Derive Y-calibration")
            st.write("Y-calibration setup")

            submitted_btn_derive_y = st.form_submit_button("Run")

            if submitted_btn_derive_y:
                st.session_state["cache_strings"][
                    "x_calibration"
                ] = "btn_derive_y_calibration"

        with st.form("Save Y-calibration"):
            st.write("Save Y-calibration")

            submitted_btn_save_y = st.form_submit_button("Run")

            if submitted_btn_save_y:
                st.session_state["cache_strings"][
                    "x_calibration"
                ] = "btn_save_y_calibration"


def process_x_calibration_neon_creation():

    load_tn, crop_tn, normalize_tn, peakfind_tn, peakfit_tn = st.tabs(
        [
            "Load [Ne]",
            # "Show [Ne]",
            "Crop [Ne]",  # 'Baseline corr',
            "Normalize [Ne]",
            "Peak find [Ne]",
            "Peak fitting [Ne]",
        ]
    )

    if "neon" in st.session_state["cache_dicts"]["spectrum_settings"]:
        state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["neon"]
    else:
        st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = default_state_neon

    state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["neon"]

    print("State settings Neon start..")
    print(state_settings)
    print('------ END ------')

    with load_tn:
        load_calibration_spectrum_neon()

        if "neon" in st.session_state["cache_dicts"]["spectra_x"]:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
            spe_units = neon_spe.meta["units"]

            st.session_state["cache_dicts"]["spectra_x_current"]["neon"] = neon_spe

            simple_plot_spe(
                spe=neon_spe, label="Neon", xlabel=r"Raman shift [{}]".format(spe_units)
            )

    with crop_tn:

        if "neon" in st.session_state["cache_dicts"]["spectra_x"]:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
            spe_units = neon_spe.meta["units"]

            label, xlabel = "Neon", r"Raman shift [{}]".format(spe_units)
            ax = neon_spe.plot(label=label, linestyle='dashed', color='blue')
            ax.set_xlabel(xlabel)

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["neon"]
            print('state_settings in the beginning of crop')
            print(state_settings)
            print('--- == end == ----')
            settings_crop: StateCrop = state_settings.crop

            col1_up, col2_up = st.columns([1, 1])
            with col1_up:

                # callback_change_value(
                #     key="crop_neon_checkbox", value=settings_crop.use_crop)

                use_crop = st.checkbox(
                    key="crop_neon_checkbox",
                    label="Use crop",
                    value=settings_crop.use_crop,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )
            with col2_up:
                set_default_btn = st.button(
                    key='crop_neon_default_btn',
                    label='Default Settings', help='Reset default values of all settings',

                )

            if set_default_btn:
                state_settings.crop = default_state_neon.crop
                st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = state_settings
                settings_crop: StateCrop = state_settings.crop

            # Create a form for the input fields and submit button
            with st.form(key="neon_crop_form"):
                # Create three columns: two for input fields and one for the submit button
                spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

                col0, col1, col2 = st.columns([0.5, 1, 1])

                with col0:
                    # This is to adjust the position of the button
                    st.write("")
                    submit_neon_crop_btn = st.form_submit_button(
                        label="Update",
                        #   disabled=not use_crop
                    )

                with col1:
                    min_val = settings_crop.crop_min if settings_crop.crop_min \
                        else min(spe.x)
                    print('Min val: ', min_val)

                    if set_default_btn:
                        callback_change_value('min_crop_input', min_val)
                    # callback_change_value('min_crop_input', min_val)

                    min_val = st.number_input(
                        "Minimum Value:",

                        value=min_val,
                        format="%f",
                        key="min_crop_input"
                        # disabled=not use_crop
                    )
                with col2:
                    max_val = settings_crop.crop_max if settings_crop.crop_max \
                        else max(spe.x)
                    print('Max val: ', max_val)

                    if set_default_btn:
                        callback_change_value('max_crop_input', max_val)
                    # callback_change_value('max_crop_input', max_val)

                    max_val = st.number_input(
                        "Maximum Value:",
                        value=max_val,
                        format="%f",
                        key="max_crop_input"
                        # disabled=not use_crop
                    )

            # Check if the form is submitted
            # if True:  # submit_neon_crop_btn:
            if min_val > max_val:
                st.error("Minimum value cannot be greater than Maximum value.")
            # else:

            update_x_calibration_btn("submitted_std1_btn")
            # st.success(f"Range set from {min_val} to {max_val}")
            settings_crop.use_crop = use_crop
            settings_crop.crop_min = min_val
            settings_crop.crop_max = max_val

            if submit_neon_crop_btn:
                spe_croped = spe.trim_axes(
                    method="x-axis", boundaries=(min_val, max_val))

            if use_crop:
                # if not submit_neon_crop_btn:
                spe_croped = spe.trim_axes(
                    method="x-axis", boundaries=(min_val, max_val))
                st.session_state["cache_dicts"]["spectra_x_current"]["neon"] = spe_croped
                st.session_state["cache_dicts"]["spectra_x_crop"]["neon"] = spe_croped

            if use_crop or submit_neon_crop_btn:
                ax = spe_croped.plot(ax=ax, label="Neon crop", color='red')

            fig = ax.get_figure()
            st.pyplot(fig)

            st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = state_settings

    with normalize_tn:

        if "neon" in st.session_state["cache_dicts"]["spectra_x"]:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
            spe_units = neon_spe.meta["units"]

            label, xlabel = "Neon", r"Raman shift [{}]".format(spe_units)
            ax = neon_spe.plot(label=label, linestyle='dashed')
            ax.set_xlabel(xlabel)
            ax.set_ylabel('Neon', color='blue')

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["neon"]
            print('State_settings')
            print(state_settings)

            settings_normalize: StateNormalize = state_settings.normalize

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key='normalize_neon_default_btn',
                    label='Default Settings', help='Reset default values of all settings',
                )

                if set_default_btn:

                    state_settings.normalize = default_state_neon.normalize
                    st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = state_settings
                    settings_normalize: StateCrop = state_settings.normalize

            with col1_up:

                if set_default_btn:

                    callback_change_value(
                        'normalize_neon_checkbox', settings_normalize.use_normalize)

                use_normalize = st.checkbox(
                    key="normalize_neon_checkbox",
                    label="Use Normalize",
                    value=settings_normalize.use_normalize,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )

            if use_normalize:

                spe_current = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

                neon_normalized_spe = spe_current.normalize()

                st.session_state["cache_dicts"]["spectra_x_normalized"][
                    "neon"
                ] = neon_normalized_spe

                st.session_state["cache_dicts"]["spectra_x_current"][
                    "neon"
                ] = neon_normalized_spe

                ax2 = ax.twinx()

                ax2 = neon_normalized_spe.plot(
                    ax=ax2,
                    # label='Neon normalized',
                    color='red',
                    # linestyle='dashed'
                )
                ax2.set_ylabel('Neon normalized', color='red'
                               )

                red_patch = mpatches.Patch(
                    color='blue', label='Neon')

                blue_patch = mpatches.Patch(
                    color='red', label='Neon normalized')

                ax2.legend(handles=[red_patch, blue_patch])

                fig = ax2.get_figure()
                st.pyplot(fig)

            else:

                fig = ax.get_figure()
                st.pyplot(fig)

            print('Set Normalize End')
            print(settings_normalize)

            settings_normalize.use_normalize = use_normalize
            state_settings.normalize = settings_normalize
            st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = state_settings

    with peakfind_tn:

        if "neon" in st.session_state["cache_dicts"]["spectra_x"]:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
            spe_units = neon_spe.meta["units"]

            label, xlabel = "Neon", r"Raman shift [{}]".format(spe_units)

            fig, axs = plt.subplots(2, 1, sharex=True, figsize=(12, 10))

            ax = neon_spe.plot(ax=axs[0], label=label, linestyle='dashed')
            ax.set_xlabel(xlabel)
            # ax.set_ylabel('Neon', color='blue')

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["neon"]
            print('State_settings')
            print(state_settings)

            settings_peak_find: StatePeakFind = state_settings.peak_find

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key='peakfind_neon_default_btn',
                    label='Default Settings',
                    help='Reset default values of all settings',
                )

                if set_default_btn:

                    state_settings.peak_find = default_state_neon.peak_find
                    st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = state_settings
                    settings_peak_find: StatePeakFind = state_settings.peak_find

                    callback_change_value(
                        'neon_peak_find_checkbox', settings_peak_find.use_peak_find)

                    callback_change_value(
                        'window_length_neon', settings_peak_find.value_wlen)

                    callback_change_value(
                        'width_neon', settings_peak_find.value_width)
                    callback_change_value(
                        'hht_chain_neon', settings_peak_find.value_hht_chain)
                    callback_change_value(
                        'sharpening_neon', settings_peak_find.value_sharpening)
                    callback_change_value(
                        'prominence_neon', settings_peak_find.value_prominence)
                    callback_change_value(
                        'strategy_neon', settings_peak_find.value_strategy)

            with col1_up:

                # if set_default_btn:

                # callback_change_value(
                #     'neon_peak_find_checkbox', settings_peak_find.use_peak_find)

                use_peak_find = st.checkbox(
                    key="neon_peak_find_checkbox",
                    label="Use Peak find",
                    value=settings_peak_find.use_peak_find,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )

            # if use_peak_find:

                # spe_current = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

            neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

            # Create a form for the input fields and submit button
            with st.form(key="neon_peakfind_form"):

                col0, col1, col2, col3 = st.columns(4)
                with col0:
                    st.write("")  # This is to adjust the position of the button
                    submit_find_peaks_neon_btn = st.form_submit_button(
                        # key='update_findpeaks_neon',
                        label="Update",
                        on_click=update_x_calibration_btn("submitted_std1_btn"),
                    )
                with col1:
                    wlen = st.number_input(
                        key='window_length_neon',
                        label="window length",
                        min_value=10,
                        max_value=800,
                        value=settings_peak_find.value_wlen,
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )
                    width = st.number_input(
                        key='width_neon',
                        label="width",
                        min_value=1,
                        max_value=10,
                        value=settings_peak_find.value_width,
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )
                with col2:
                    hht_chain = st.number_input(
                        key='hht_chain_neon',
                        label="hht_chain[int]",
                        min_value=10,
                        max_value=150,
                        value=settings_peak_find.value_hht_chain,
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )
                    options_sharpening = ["hht", None]
                    sharpening = st.selectbox(
                        key='sharpening_neon',
                        label="sharpening",
                        options=options_sharpening,
                        index=options_sharpening.index(
                            settings_peak_find.value_sharpening),
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )
                with col3:

                    prominence = st.number_input(
                        key='prominence_neon',
                        label="prominence",
                        min_value=0.0,
                        max_value=500.0,
                        value=settings_peak_find.value_prominence,
                        step=0.001,
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )

                    options_strategy = [
                        "topo", "bayesian_gaussian_mixture", "bgm", "cwt"]

                    # st.write(value_strategy)
                    strategy = st.selectbox(
                        key='strategy_neon',
                        label="strategy",
                        options=options_strategy,
                        index=options_strategy.index(
                            settings_peak_find.value_strategy),
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )

            kwargs = {
                "wlen": wlen,
                "width": width,
                "hht_chain": [hht_chain],
                "prominence": prominence * neon_spe.y_noise,
                "sharpening": sharpening,
                "strategy": strategy,
            }

            if use_peak_find or submit_find_peaks_neon_btn:

                neon_peak_candidates = neon_spe.find_peak_multipeak(
                    **kwargs)

                # fig, ax = plt.subplots()

                neon_peak_candidates.plot(
                    ax=axs[1], fmt=":", label="Neon peaks")
                axs[1].set_xlabel(xlabel)
                fig = axs[1].get_figure()

            if use_peak_find:
                st.session_state["cache_dicts"]["spectra_x_peak_candidates"]["neon"] = \
                    neon_peak_candidates

                st.session_state["cache_dicts"]["spectra_x_current"][
                    "neon_kwargs_find_peak"
                ] = kwargs

            st.pyplot(fig)

            settings_peak_find.use_peak_find = use_peak_find
            settings_peak_find.value_hht_chain = hht_chain
            settings_peak_find.value_prominence = prominence
            settings_peak_find.value_sharpening = sharpening
            settings_peak_find.value_wlen = wlen
            settings_peak_find.value_width = width
            settings_peak_find.value_strategy = strategy

            state_settings.peak_find = settings_peak_find

    ################
    with peakfit_tn:
        if "spectra_x_current" in st.session_state["cache_dicts"]:

            use_peakfit = st.checkbox(
                key="neon_peak_fit_checkbox",
                label="Use Peak find",
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )

            with st.form(key="neon_peakfit_form"):

                # if use_peakfit:
                col0, col1 = st.columns(2)
                with col0:
                    submit_neon_fitpeaks_btn = st.form_submit_button(
                        label="Update",
                        on_click=update_x_calibration_btn("submitted_std1_btn"),
                    )
                with col1:
                    profile = st.selectbox(
                        label="Profile",
                        options=[
                            "Gaussian",
                            "Moffat",
                            "Lorentzian",
                            "Voigt",
                            "PseudoVoigt",
                            "Pearson4",
                            "Pearson7",
                        ],
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )

                # neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

                if ("neon" in st.session_state["cache_dicts"]["spectra_x_peak_candidates"] and
                   "neon" in st.session_state["cache_dicts"]["spectra_x_current"]):
                    neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

                    neon_peak_candidates = \
                        st.session_state["cache_dicts"]["spectra_x_peak_candidates"]["neon"]

                    assert isinstance(use_peakfit, bool), use_peakfit

                    fitres = neon_spe.fit_peak_multimodel(
                        profile=profile, candidates=neon_peak_candidates, no_fit=not use_peakfit
                    )

                # fig, ax = plt.subplots(figsize=(30, 15))
                    fig, ax = plt.subplots()

                    neon_spe.plot(ax=ax, fmt=":", label="Neon")
                    fitres.plot(
                        ax=ax,
                        peak_candidate_groups=neon_peak_candidates,
                        individual_peaks=True,
                        label=None,
                    )
                    st.pyplot(fig)

                    if use_peakfit:
                        st.session_state["cache_dicts"]["spectra_x_current"][
                            "neon_kwargs_fit_peak"
                        ] = {
                            "profile": profile,
                            "no_fit": not use_peakfit,
                        }

                        st.session_state["cache_dicts"]["spectra_x_peak_fitres"][
                            "neon"
                        ] = fitres


def __process_x_calibration_si_creation():

    load_ts, crop_ts, baseline_ts, normalize_ts, peakfind_ts, peakfit_ts = st.tabs(
        [
            "Load [Si]",
            # "Show [Ne]",
            "Crop [Si]",  # 'Baseline corr',
            "Baseline corr [Si]",
            "Normalize [Si]",
            "Peak find [Si]",
            "Peak fitting [Si]",
        ]
    )

    if "si" in st.session_state["cache_dicts"]["spectrum_settings"]:
        state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
    else:
        st.session_state["cache_dicts"]["spectrum_settings"]["si"] = default_state_si

    state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]

    print("State settings si start..")
    print(state_settings)
    print('------ END ------')

    with load_ts:
        load_calibration_spectrum_si()

        if "si" in st.session_state["cache_dicts"]["spectra_x"]:
            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            st.session_state["cache_dicts"]["spectra_x_current"]["si"] = si_spe

            simple_plot_spe(
                spe=si_spe, label="Neon", xlabel=r"Raman shift [{}]".format(spe_units)
            )

    with crop_ts:

        if "si" in st.session_state["cache_dicts"]["spectra_x"]:
            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            label, xlabel = "Si", r"Raman shift [{}]".format(spe_units)
            ax = si_spe.plot(label=label, linestyle='dashed', color='blue')
            ax.set_xlabel(xlabel)

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
            print('state_settings in the beginning of crop')
            print(state_settings)
            print('--- == end == ----')
            settings_crop: StateCrop = state_settings.crop

            col1_up, col2_up = st.columns([1, 1])
            with col1_up:

                # callback_change_value(
                #     key="crop_si_checkbox", value=settings_crop.use_crop)

                use_crop = st.checkbox(
                    key="crop_si_checkbox",
                    label="Use crop",
                    value=settings_crop.use_crop,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )
            with col2_up:
                set_default_btn = st.button(
                    key='crop_si_default_btn',
                    label='Default Settings', help='Reset default values of all settings',

                )

            if set_default_btn:
                state_settings.crop = default_state_si.crop
                st.session_state["cache_dicts"]["spectrum_settings"]["si"] = state_settings
                settings_crop: StateCrop = state_settings.crop

            # Create a form for the input fields and submit button
            with st.form(key="si_crop_form"):
                # Create three columns: two for input fields and one for the submit button
                spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

                col0, col1, col2 = st.columns([0.5, 1, 1])

                with col0:
                    # This is to adjust the position of the button
                    st.write("")
                    submit_si_crop_btn = st.form_submit_button(
                        label="Update",
                        # on_click=update_x_calibration_btn("submitted_std2_btn")
                        #   disabled=not use_crop
                    )

                with col1:
                    min_val = settings_crop.crop_min if settings_crop.crop_min \
                        else min(spe.x)
                    print('Min val: ', min_val)

                    if set_default_btn:
                        callback_change_value('min_crop_input', min_val)
                    # callback_change_value('min_crop_input', min_val)

                    min_val = st.number_input(
                        "Minimum Value:",

                        value=min_val,
                        format="%f",
                        key="min_crop_input"
                        # disabled=not use_crop
                    )
                with col2:
                    max_val = settings_crop.crop_max if settings_crop.crop_max \
                        else max(spe.x)
                    print('Max val: ', max_val)

                    if set_default_btn:
                        callback_change_value('max_crop_input', max_val)
                    # callback_change_value('max_crop_input', max_val)

                    max_val = st.number_input(
                        "Maximum Value:",
                        value=max_val,
                        format="%f",
                        key="max_crop_input"
                        # disabled=not use_crop
                    )

            # Check if the form is submitted
            # if True:  # submit_si_crop_btn:
            if min_val > max_val:
                st.error("Minimum value cannot be greater than Maximum value.")
            # else:

            # update_x_calibration_btn("submitted_std2_btn")
            # st.success(f"Range set from {min_val} to {max_val}")
            settings_crop.use_crop = use_crop
            settings_crop.crop_min = min_val
            settings_crop.crop_max = max_val

            if submit_si_crop_btn:
                spe_croped = spe.trim_axes(
                    method="x-axis", boundaries=(min_val, max_val))

            if use_crop:
                # if not submit_si_crop_btn:
                spe_croped = spe.trim_axes(
                    method="x-axis", boundaries=(min_val, max_val))
                st.session_state["cache_dicts"]["spectra_x_current"]["si"] = spe_croped
                st.session_state["cache_dicts"]["spectra_x_crop"]["si"] = spe_croped

            if use_crop or submit_si_crop_btn:
                ax = spe_croped.plot(ax=ax, label="Si crop", color='red')

            fig = ax.get_figure()
            st.pyplot(fig)

            st.session_state["cache_dicts"]["spectrum_settings"]["si"] = state_settings

    with baseline_ts:
        #######
        if ("si" in st.session_state["cache_dicts"]["spectra_x"] and
                "si" in st.session_state["cache_dicts"]["spectra_x_current"]):

            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            label, xlabel = "Si", r"Raman shift [{}]".format(spe_units)
            ax = si_spe.plot(label=label, linestyle='dashed')
            ax.set_xlabel(xlabel)
            ax.set_ylabel('Si', color='blue')

            si_spe_current = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
            print('State_settings')
            print(state_settings)

            settings_baseline: StateBaselineCorrection = state_settings.baseline_corr

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key='baseline_si_default_btn',
                    label='Default Settings', help='Reset default values of all settings',
                )

                if set_default_btn:

                    state_settings.baseline_corr = default_state_si.baseline_corr
                    st.session_state["cache_dicts"]["spectrum_settings"]["si"] = state_settings
                    settings_baseline: StateBaselineCorrection = state_settings.baseline_corr

            with col1_up:

                if set_default_btn:

                    callback_change_value(
                        'baseline_si_checkbox', settings_baseline.use_baseline_corr)

                use_baseline = st.checkbox(
                    key="baseline_si_checkbox",
                    label="Use Baseline",
                    value=settings_baseline.use_baseline_corr,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )

            # Create a form for the input fields and submit button
            with st.form(key="si_baseline_form"):
                # Create three columns: two for input fields and one for the submit button
                spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

                col0, col1, col2 = st.columns([0.5, 1, 1])

                with col0:
                    # This is to adjust the position of the button
                    st.write("")
                    submit_si_baseline_btn = st.form_submit_button(
                        label="Update",
                        #   disabled=not use_crop
                    )

                with col1:

                    # min_val = settings_crop.crop_min if settings_crop.crop_min \
                    #     else min(spe.x)
                    # print('Min val: ', min_val)
                    baseline_current = settings_baseline.baseline_corr_type
                    if set_default_btn:
                        callback_change_value(
                            'select_baseline_si', baseline_current)

                    # callback_change_value('min_crop_input', min_val)
                    options = ['SNIP', 'ALS',
                               #    'MOVING_MING'
                               ]
                    baseline_current = settings_baseline.baseline_corr_type

                    baseline_corr = st.selectbox(label='Select baseline correction', key='select_baseline_si',
                                                 options=options, index=options.index(
                                                     baseline_current),
                                                 #  on_change=callback_change_value, args=('baseline_corr_args', baseline_current)
                                                 )

                with col2:
                    if baseline_corr == 'SNIP':
                        baseline_corr_class = SNIPBaselineArgs
                    elif baseline_corr == 'ALS':
                        baseline_corr_class = ALSBaselineArgs
                    else:
                        st.error("Choose SNIP or ALS")

                    st.write("")
                    with st.expander(label="Baseline correction settings"):
                        input_data = sp.pydantic_input(
                            "Baseline correction settings", baseline_corr_class)

                        # input_data = input_data.dict()
                        niter = input_data['niter']
                        # st.write(niter)
                        args = baseline_corr_class(**input_data)
                        # st.write(args)
                        # st.write(type(input_data))

                if submit_si_baseline_btn or use_baseline:
                    if baseline_corr == 'SNIP':
                        si_spe_baseline = si_spe_current
                        si_spe_baseline.y = si_spe_current.y - baseline_snip(
                            si_spe_current.y, niter=input_data['niter'])

                    elif baseline_corr == 'ALS':

                        si_spe_baseline = si_spe_current
                        si_spe_baseline.y = si_spe_current.y - baseline_als(
                            si_spe_current.y, **input_data)

                        # si_spe_baseline = si_spe_current - \
                        #     baseline_als(si_spe_current, **input_data)

                    else:
                        st.error("Choose SNIP or ALS")

                    ax = si_spe_baseline.plot(
                        ax=ax, label="Si baseline correction", color='red')

                    # fig = ax.get_figure()
                    # st.pyplot(fig)

                    if use_baseline:
                        # if not submit_si_crop_btn:
                        st.session_state["cache_dicts"]["spectra_x_current"]["si"] = si_spe_baseline
                        st.session_state["cache_dicts"]["spectra_x_baseline"]["si"] = si_spe_baseline

                    # if use_crop or submit_si_crop_btn:
                    #     ax = spe_croped.plot(ax=ax, label="Si crop", color='red')

            fig = ax.get_figure()
            st.pyplot(fig)

            settings_baseline.use_baseline_corr = use_baseline
            settings_baseline.baseline_corr_type = baseline_corr
            settings_baseline.args = args
            state_settings.baseline_corr = settings_baseline

            st.session_state["cache_dicts"]["spectrum_settings"]["si"] = state_settings

            # si_spe_current - si_spe_current.
            # st.write(input_data)
            # st.write(type(input_data))
            # if use_normalize:

            # use_baseline_corr = st.checkbox(
            #     label="Use baseline correction",
            #     on_change=update_x_calibration_btn("submitted_std2_btn"),
            # )

            # st.session_state["cache_dicts"]["spectra_x_use_baseline_corr"][
            #     "si"
            # ] = use_baseline_corr

            # moving_min_val = st.slider(
            #     label="Moving min",
            #     min_value=1,
            #     max_value=10,
            #     value=2,
            #     on_change=update_x_calibration_btn("submitted_std2_btn"),
            #     disabled=(not use_baseline_corr),
            # )

            # spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]
            # # st.session_state["cache_dicts"]['spectra_x']['neon']
            #   si_spe_current - si_spe_current.
            # baseline_corr_spe = spe - spe.moving_minimum(moving_min_val)

            # st.session_state["cache_dicts"]["spectra_x_baseline_corr"][
            #     "si"
            # ] = baseline_corr_spe

            # if use_baseline_corr:
            #     st.session_state["cache_dicts"]["spectra_x_current"][
            #         "si"
            #     ] = baseline_corr_spe

            # simple_plot_spe(
            #     spe=baseline_corr_spe,
            #     label="Si",
            #     xlabel=r"Raman shift [{}]".format(spe_units),
            # )

            ######
    with normalize_ts:

        if "si" in st.session_state["cache_dicts"]["spectra_x"]:
            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            label, xlabel = "Si", r"Raman shift [{}]".format(spe_units)
            ax = si_spe.plot(label=label, linestyle='dashed')
            ax.set_xlabel(xlabel)
            ax.set_ylabel('Si', color='blue')

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
            print('State_settings')
            print(state_settings)

            settings_normalize: StateNormalize = state_settings.normalize

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key='normalize_si_default_btn',
                    label='Default Settings', help='Reset default values of all settings',
                )

                if set_default_btn:

                    state_settings.normalize = default_state_si.normalize
                    st.session_state["cache_dicts"]["spectrum_settings"]["si"] = state_settings
                    settings_normalize: StateCrop = state_settings.normalize

            with col1_up:

                if set_default_btn:

                    callback_change_value(
                        'normalize_si_checkbox', settings_normalize.use_normalize)

                use_normalize = st.checkbox(
                    key="normalize_si_checkbox",
                    label="Use Normalize",
                    value=settings_normalize.use_normalize,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )

            if use_normalize:

                spe_current = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

                si_normalized_spe = spe_current.normalize()

                st.session_state["cache_dicts"]["spectra_x_normalized"][
                    "si"
                ] = si_normalized_spe

                st.session_state["cache_dicts"]["spectra_x_current"][
                    "si"
                ] = si_normalized_spe

                ax2 = ax.twinx()

                ax2 = si_normalized_spe.plot(
                    ax=ax2,
                    # label='si normalized',
                    color='red',
                    # linestyle='dashed'
                )
                ax2.set_ylabel('Si normalized', color='red'
                               )

                red_patch = mpatches.Patch(
                    color='blue', label='Si')

                blue_patch = mpatches.Patch(
                    color='red', label='Si normalized')

                ax2.legend(handles=[red_patch, blue_patch])

                fig = ax2.get_figure()
                st.pyplot(fig)

            else:

                fig = ax.get_figure()
                st.pyplot(fig)

            print('Set Normalize End')
            print(settings_normalize)

            settings_normalize.use_normalize = use_normalize
            state_settings.normalize = settings_normalize
            st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = state_settings

    with peakfind_ts:

        if "si" in st.session_state["cache_dicts"]["spectra_x"]:
            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            label, xlabel = "Si", r"Raman shift [{}]".format(spe_units)

            fig, axs = plt.subplots(2, 1, sharex=True, figsize=(12, 10))

            ax = si_spe.plot(ax=axs[0], label=label, linestyle='dashed')
            ax.set_xlabel(xlabel)
            # ax.set_ylabel('si', color='blue')

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
            print('State_settings')
            print(state_settings)

            settings_peak_find: StatePeakFind = state_settings.peak_find

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key='peakfind_si_default_btn',
                    label='Default Settings',
                    help='Reset default values of all settings',
                )

                if set_default_btn:

                    state_settings.peak_find = default_state_si.peak_find
                    st.session_state["cache_dicts"]["spectrum_settings"]["si"] = state_settings
                    settings_peak_find: StatePeakFind = state_settings.peak_find

                    callback_change_value(
                        'si_peak_find_checkbox', settings_peak_find.use_peak_find)

                    callback_change_value(
                        'window_length_si', settings_peak_find.value_wlen)

                    callback_change_value(
                        'width_si', settings_peak_find.value_width)
                    callback_change_value(
                        'hht_chain_si', settings_peak_find.value_hht_chain)
                    callback_change_value(
                        'sharpening_si', settings_peak_find.value_sharpening)
                    callback_change_value(
                        'prominence_si', settings_peak_find.value_prominence)
                    callback_change_value(
                        'strategy_si', settings_peak_find.value_strategy)

            with col1_up:

                # if set_default_btn:

                # callback_change_value(
                #     'si_peak_find_checkbox', settings_peak_find.use_peak_find)

                use_peak_find = st.checkbox(
                    key="si_peak_find_checkbox",
                    label="Use Peak find",
                    value=settings_peak_find.use_peak_find,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )

            # if use_peak_find:

                # spe_current = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

            si_spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

            # Create a form for the input fields and submit button
            with st.form(key="si_peakfind_form"):

                col0, col1, col2, col3 = st.columns(4)
                with col0:
                    st.write("")  # This is to adjust the position of the button
                    submit_find_peaks_si_btn = st.form_submit_button(
                        # key='update_findpeaks_si',
                        label="Update",
                        on_click=update_x_calibration_btn("submitted_std2_btn"),
                    )
                with col1:
                    wlen = st.number_input(
                        key='window_length_si',
                        label="window length",
                        min_value=10,
                        max_value=800,
                        value=settings_peak_find.value_wlen,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                    width = st.number_input(
                        key='width_si',
                        label="width",
                        min_value=1,
                        max_value=10,
                        value=settings_peak_find.value_width,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                with col2:
                    hht_chain = st.number_input(
                        key='hht_chain_si',
                        label="hht_chain[int]",
                        min_value=10,
                        max_value=150,
                        value=settings_peak_find.value_hht_chain,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                    options_sharpening = ["hht", None]
                    sharpening = st.selectbox(
                        key='sharpening_si',
                        label="sharpening",
                        options=options_sharpening,
                        index=options_sharpening.index(
                            settings_peak_find.value_sharpening),
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                with col3:

                    prominence = st.number_input(
                        key='prominence_si',
                        label="prominence",
                        min_value=0.0,
                        max_value=500.0,
                        value=settings_peak_find.value_prominence,
                        step=0.001,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )

                    options_strategy = [
                        "topo", "bayesian_gaussian_mixture", "bgm", "cwt"]

                    # st.write(value_strategy)
                    strategy = st.selectbox(
                        key='strategy_si',
                        label="strategy",
                        options=options_strategy,
                        index=options_strategy.index(
                            settings_peak_find.value_strategy),
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )

            kwargs = {
                "wlen": wlen,
                "width": width,
                "hht_chain": [hht_chain],
                "prominence": prominence * si_spe.y_noise,
                "sharpening": sharpening,
                "strategy": strategy,
            }

            if use_peak_find or submit_find_peaks_si_btn:

                si_peak_candidates = si_spe.find_peak_multipeak(
                    **kwargs)

                # fig, ax = plt.subplots()

                si_peak_candidates.plot(
                    ax=axs[1], fmt=":", label="Si peaks")
                axs[1].set_xlabel(xlabel)
                fig = axs[1].get_figure()

            if use_peak_find:
                st.session_state["cache_dicts"]["spectra_x_peak_candidates"]["si"] = \
                    si_peak_candidates

                st.session_state["cache_dicts"]["spectra_x_current"][
                    "si_kwargs_find_peak"
                ] = kwargs

            st.pyplot(fig)

            # st.session_state["cache_dicts"]["spectra_x_peak_candidates"][
            #     "si"
            # ] = si_peak_candidates

            settings_peak_find.use_peak_find = use_peak_find
            settings_peak_find.value_hht_chain = hht_chain
            settings_peak_find.value_prominence = prominence
            settings_peak_find.value_sharpening = sharpening
            settings_peak_find.value_wlen = wlen
            settings_peak_find.value_width = width
            settings_peak_find.value_strategy = strategy

            state_settings.peak_find = settings_peak_find

    ################
    with peakfit_ts:
        if "si" in st.session_state["cache_dicts"]["spectra_x_current"]:

            use_peakfit = st.checkbox(
                key="si_peak_fit_checkbox",
                label="Use Peak find",
                on_change=update_x_calibration_btn("submitted_std2_btn"),
            )

            with st.form(key="si_peakfit_form"):

                # if use_peakfit:
                col0, col1 = st.columns(2)
                with col0:
                    submit_si_fitpeaks_btn = st.form_submit_button(
                        label="Update",
                        on_click=update_x_calibration_btn("submitted_std2_btn"),
                    )
                with col1:
                    profile = st.selectbox(
                        label="Profile",
                        options=[
                            "Pearson4",
                            "Gaussian",
                            "Moffat",
                            "Lorentzian",
                            "Voigt",
                            "PseudoVoigt",
                            "Pearson7",
                        ],
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )

                si_spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]
                if "si" in st.session_state["cache_dicts"][
                        "spectra_x_peak_candidates"]:

                    si_peak_candidates = st.session_state["cache_dicts"][
                        "spectra_x_peak_candidates"]["si"]

                    assert isinstance(use_peakfit, bool), use_peakfit

                    fitres = si_spe.fit_peak_multimodel(
                        profile=profile, candidates=si_peak_candidates, no_fit=not use_peakfit
                    )

                    # fig, ax = plt.subplots(figsize=(30, 15))
                    fig, ax = plt.subplots()

                    si_spe.plot(ax=ax, fmt=":", label="Si")
                    fitres.plot(
                        ax=ax,
                        peak_candidate_groups=si_peak_candidates,
                        individual_peaks=True,
                        label=None,
                    )
                    # st.pyplot(fig)

                    if use_peakfit:
                        st.session_state["cache_dicts"]["spectra_x_current"][
                            "si_kwargs_fit_peak"
                        ] = {
                            "profile": profile,
                            "no_fit": not use_peakfit,
                        }

                        st.session_state["cache_dicts"]["spectra_x_peak_fitres"][
                            "si"
                        ] = fitres


def process_x_calibration_si_creation():
    # load_calibration_spectrum_si
    material = "si"
    ###############################################
    # st.write(' in elif x_calib_btn std2')
    load_tss, crop_tns, baseline_tns, normalize_tss, peakfind_tss, peakfit_tss = (
        st.tabs(
            ["Load [Si]",
                # "Show [Si]",
                "Crop [Si]",
                "Baseline corr [Si]",
                "Normalize [Si]",
                "Peak find [Si]",
                "Peak fitting [Si]",
             ]
        )
    )

    with load_tss:

        load_calibration_spectrum_si()

    # with show_tss:
        if material in st.session_state["cache_dicts"]["spectra_x"]:
            spe = st.session_state["cache_dicts"]["spectra_x"][material]
            spe_units = spe.meta["units"]

            st.session_state["cache_dicts"]["spectra_x_current"][material] = spe

            simple_plot_spe(
                spe=spe, label="Si", xlabel=r"Raman shift [{}]".format(spe_units)
            )

    with crop_tns:
        #########
        if material in st.session_state["cache_dicts"]["spectra_x_current"]:
            spe = st.session_state["cache_dicts"]["spectra_x_current"][material]

            use_crop = st.checkbox(
                key='use_crop_checkbox_si',
                label="Use crop",
                # value=settings.crop.use_crop,
                on_change=update_x_calibration_btn("submitted_std2_btn"),
            )

            # Create a form for the input fields and submit button
            with st.form(key="si_crop_form"):
                # Create three columns: two for input fields and one for the submit button
                col0, col1, col2 = st.columns([0.5, 1, 1])

                with col0:
                    st.write("")  # This is to adjust the position of the button
                    submit_si_crop_btn = st.form_submit_button(
                        label="Update",
                        #   disabled=not use_crop
                    )
                with col1:
                    min_val = st.number_input(
                        "Minimum Value:",
                        value=520.45 - 50,  # min(spe.x),
                        format="%f",
                        # disabled=not use_crop
                    )
                with col2:
                    max_val = st.number_input(
                        "Maximum Value:",
                        value=520.45 + 50,  # max(spe.x),
                        format="%f",
                        # disabled=not use_crop
                    )

            # Check if the form is submitted
            # if submit_si_crop_btn:  # submit_neon_crop_btn:
            if min_val > max_val:
                st.error("Minimum value cannot be greater than Maximum value.")
            # else:
            update_x_calibration_btn("submitted_std2_btn")
            # st.success(f"Range set from {min_val} to {max_val}")

            spe_croped = spe.trim_axes(
                method="x-axis", boundaries=(min_val, max_val))

            simple_plot_spe(
                spe=spe_croped,
                label="Si crop",
                xlabel=r"Raman shift [{}]".format(spe_units),
            )

            if use_crop:  # and submit_si_crop_btn:
                if material in st.session_state["cache_dicts"]["spectra_x_current"]:
                    st.session_state["cache_dicts"]["spectra_x_current"][material] = spe_croped
                    st.session_state["cache_dicts"]["spectra_x_crop"][material] = spe_croped

        with baseline_tns:
            if material in st.session_state["cache_dicts"]["spectra_x_current"]:
                use_baseline_corr = st.checkbox(
                    label="Use baseline correction",
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )

                st.session_state["cache_dicts"]["spectra_x_use_baseline_corr"][
                    "si"
                ] = use_baseline_corr

                moving_min_val = st.slider(
                    label="Moving min",
                    min_value=1,
                    max_value=10,
                    value=2,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                    disabled=(not use_baseline_corr),
                )

                spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]
                # st.session_state["cache_dicts"]['spectra_x']['neon']
                baseline_corr_spe = spe - spe.moving_minimum(moving_min_val)
                st.session_state["cache_dicts"]["spectra_x_baseline_corr"][
                    "si"
                ] = baseline_corr_spe

                if use_baseline_corr:
                    st.session_state["cache_dicts"]["spectra_x_current"][
                        "si"
                    ] = baseline_corr_spe

                simple_plot_spe(
                    spe=baseline_corr_spe,
                    label="Si",
                    xlabel=r"Raman shift [{}]".format(spe_units),
                )

    with normalize_tss:
        if material in st.session_state["cache_dicts"]["spectra_x_current"]:
            use_normalize = st.checkbox(
                key="si_normalize_checkbox",
                label="Use normalization",
                on_change=update_x_calibration_btn("submitted_std2_btn"),
            )

            # if True:  # use_normalize:
            # st.write('normlaize tab')
            spe = st.session_state["cache_dicts"]["spectra_x_current"][material]

            normalized_spe = spe.normalize()

            simple_plot_spe(
                spe=normalized_spe,
                label="Si normalized",
                xlabel=r"Raman shift [{}]".format(spe_units),
            )
            if use_normalize:
                st.session_state["cache_dicts"]["spectra_x_normalized"][
                    material
                ] = normalized_spe
                st.session_state["cache_dicts"]["spectra_x_current"][
                    material
                ] = normalized_spe

    with peakfind_tss:
        if material in st.session_state["cache_dicts"]["spectra_x_current"]:
            use_peakfind = st.checkbox(
                key="neon_peak_find_checkbox",
                label="Use Peak find",
                on_change=update_x_calibration_btn("submitted_std2_btn"),
            )

            # st.write('Peak find')
            spe = st.session_state["cache_dicts"]["spectra_x_current"][material]

            # Create a form for the input fields and submit button
            with st.form(key="si_peakfind_form"):

                if (
                    "si_widgetsvals_find_peak"
                    not in st.session_state["cache_dicts"]["spectra_x_current"]
                ):
                    print("inside si_kwargs find peak MISSING")
                    # NB! value_prominance --> spe.y_noise does not find any peaks for 633 nm
                    value_prominence = 5.0  # spe.y_noise,  # 0.0  # neon_spe.y_noise
                    value_wlen = 200
                    value_width = 2
                    value_hht_chain = 80
                    value_sharpening = None
                    value_strategy = "topo"
                else:
                    print("inside si kwargs find peak")
                    args = st.session_state["cache_dicts"]["spectra_x_current"][
                        "si_widgetsvals_find_peak"
                    ]
                    value_prominence = args["prominence"]
                    value_wlen = args["wlen"]
                    value_width = args["width"]
                    value_hht_chain = args["hht_chain"]
                    value_sharpening = args["sharpening"]
                    value_strategy = args["strategy"]

                col0, col1, col2, col3 = st.columns(4)
                with col0:
                    st.write("")  # This is to adjust the position of the button
                    submit_find_peaks_si_btn = st.form_submit_button(
                        # key='update_findpeaks_si',
                        label="Update",
                        on_click=update_x_calibration_btn("submitted_std2_btn"),
                    )
                with col1:
                    wlen = st.number_input(
                        label="window length",
                        min_value=10,
                        max_value=800,
                        value=value_wlen,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                    width = st.number_input(
                        label="width",
                        min_value=1,
                        max_value=10,
                        value=value_width,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                with col2:
                    hht_chain = st.number_input(
                        label="hht_chain[int]",
                        min_value=10,
                        max_value=150,
                        value=value_hht_chain,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                    options_sharpening = ["hht", None]
                    sharpening = st.selectbox(
                        label="sharpening",
                        options=options_sharpening,
                        index=options_sharpening.index(value_sharpening),
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                with col3:
                    print(value_prominence)
                    prominence = st.number_input(
                        label="prominence",
                        min_value=0.0,
                        max_value=1000.0,
                        value=value_prominence,
                        step=0.5,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )

                    options_strategy = [
                        "topo", "bayesian_gaussian_mixture", "bgm", "cwt"]

                    # st.write(value_strategy)
                    strategy = st.selectbox(
                        label="strategy",
                        options=options_strategy,
                        index=options_strategy.index(value_strategy),
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )

                # if submit_find_peaks_neon_btn:
                # args = {
                #     "wlen": wlen,
                #     "width": width,
                #     "hht_chain": hht_chain,
                #     "prominence": prominence,
                #     "sharpening": sharpening,
                #     "strategy": strategy,
                # }
                kwargs = {
                    "wlen": wlen,
                    "width": width,
                    "hht_chain": [hht_chain],
                    "prominence": prominence * spe.y_noise,
                    "sharpening": sharpening,
                    "strategy": strategy,
                }

                peak_candidates = spe.find_peak_multipeak(**kwargs)

                # fig, ax = plt.subplots(figsize=(30, 12))
                fig, ax = plt.subplots()

                peak_candidates.plot(ax=ax, fmt=":", label="Si")
                ax.set_label("Raman shift [{}]".format(spe_units))
                st.pyplot(fig)

                st.session_state["cache_dicts"]["spectra_x_peak_candidates"][
                    "si"
                ] = peak_candidates

                st.session_state["cache_dicts"]["spectra_x_current"][
                    "si_widgetsvals_find_peak"
                ] = args
                if True:  # use_peakfind:

                    st.session_state["cache_dicts"]["spectra_x_current"][
                        "si_kwargs_find_peak"
                    ] = kwargs

    ################

    with peakfit_tss:
        if material in st.session_state["cache_dicts"]["spectra_x_current"]:
            use_peakfit = st.checkbox(
                key="si_peak_fit_checkbox",
                label="Use Peak find",
                on_change=update_x_calibration_btn("submitted_std2_btn"),
            )

            with st.form(key="si_peakfit_form"):

                # if use_peakfit:
                col0, col1 = st.columns(2)
                with col0:
                    submit_si_fitpeaks_btn = st.form_submit_button(
                        label="Update",
                        on_click=update_x_calibration_btn("submitted_std2_btn"),
                    )

                with col1:
                    profile = st.selectbox(
                        label="Profile",
                        options=[
                            "Pearson4",
                            "Gaussian",
                            "Moffat",
                            "Lorentzian",
                            "Voigt",
                            "PseudoVoigt",
                            "Pearson7",
                        ],
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )

                # if submit_sifitpeaks_btn:
                # st.session_state["cache_dicts"]["spectra_x_current"]["si_kwargs_fit_peak"] = {
                #     "profile": profile,
                #     "no_fit": no_fit,
                # }
                spe = st.session_state["cache_dicts"]["spectra_x_current"][material]
                peak_candidates = st.session_state["cache_dicts"][
                    "spectra_x_peak_candidates"
                ][material]

                assert isinstance(use_peakfit, bool), use_peakfit

                print("--966---")
                print(profile)
                print(peak_candidates)
                print(not use_peakfit)

                fitres = spe.fit_peak_multimodel(
                    profile=profile, candidates=peak_candidates, no_fit=not use_peakfit
                )

                # fig, ax = plt.subplots(figsize=(30, 15))
                fig, ax = plt.subplots()

                spe.plot(ax=ax, fmt=":", label="Si")
                fitres.plot(
                    ax=ax,
                    peak_candidate_groups=peak_candidates,
                    individual_peaks=True,
                    label=None,
                )
                ax.set_label("Raman shift [{}]".format(spe_units))
                st.pyplot(fig)

                if use_peakfit:
                    st.session_state["cache_dicts"]["spectra_x_current"][
                        "si_kwargs_fit_peak"
                    ] = {
                        "profile": profile,
                        "no_fit": not use_peakfit,
                    }

                    st.session_state["cache_dicts"]["spectra_x_peak_fitres"][
                        material
                    ] = fitres


#############


def update_x_calibration_btn(value):
    def update_x_calibraiton_val():
        st.session_state["cache_strings"]["x_calibration_"] = value

    return update_x_calibraiton_val


instruments_mandatory = st.session_state["cache_dicts"]["instrument_settings"][
    "settings_mandatory"]

with st.sidebar:

    # st.sidebar.image("./src/front_end/images/logo_charisma.jpg")
    # st.header("AI data extractor")
    calibration_choice_ = st.session_state["cache_strings"].get(
        "calibration_choice", "Load Calibration"
    )

    calibration_choices = ["Load Calibration", "Create Calibration"]
    assert calibration_choice_ in calibration_choices, (
        calibration_choice_,
        calibration_choices,
    )

    st.write(instruments_mandatory)

    calibration_choice = st.radio(
        "Choose calibration option",
        calibration_choices,
        index=calibration_choices.index(calibration_choice_),
    )

    st.session_state["cache_strings"]["calibration_choice"] = calibration_choice

if calibration_choice == "Load Calibration":
    with st.sidebar:
        # existing_calibration = st.text_input(
        #     "Search for existing calibration", "")

        calmodel = load_calibration()


else:
    with st.sidebar:

        # st.session_state["cache_dicts"]["x_calibration"] = ""

        # instrument_settings_expander()

        # active_calibration_settings_expander()

        create_x_calibration_sidebar_expander()

        create_y_calibration_sidebar_expander()


if st.session_state["cache_strings"]["x_calibration_"]:
    print("in IF...")
    st.session_state["cache_strings"]["x_calibration"] = st.session_state[
        "cache_strings"
    ]["x_calibration_"]
    st.session_state["cache_strings"]["x_calibration_"] = None

x_calib_btn = st.session_state["cache_strings"]["x_calibration"]


# if x_calib_btn == "uploaded_neon_calib_spectra_btn":
# # st.write("Show the neon spe..")
# neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
# st.session_state["cache_dicts"]["spectra_x_current"]["neon"] = neon_spe
# spe_units = neon_spe.meta["units"]
# simple_plot_spe(
#     spe=neon_spe, label="Neon", xlabel=r"Raman shift [{}]".format(spe_units)
# )
if x_calib_btn == "uploaded_x_calibration_btn":

    xcalibration_model = st.session_state["cache_dicts"]["x_calibration"][
        "xcalibration_model"
    ]

    fig, ax = plt.subplots(1, 1, sharex=False, figsize=(12, 10))

    xcalibration_model.plot(ax=ax)

    red_patch = mpatches.Patch(color='blue', label='Neon peaks')
    blue_patch = mpatches.Patch(color='red', label='Neon reference')

    ax.legend(handles=[red_patch, blue_patch])

    st.pyplot(fig)

    # ax = xcalibration_model.plot()
    # fig = ax.get_figure()
    # fig.set_size_inches(40, 25)
    # st.pyplot(fig)

elif x_calib_btn == "uploaded_si_calib_spectra_btn":
    # st.write("Show the Si spe...")
    si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]

    st.session_state["cache_dicts"]["spectra_x_current"]["si"] = si_spe
    spe_units = si_spe.meta["units"]
    simple_plot_spe(
        spe=si_spe, label="Si", xlabel=r"Raman shift [{}]".format(spe_units)
    )

elif x_calib_btn == "submitted_std1_btn":
    # st.write(' in elif x_calib_btn std1')
    process_x_calibration_neon_creation()

elif x_calib_btn == "submitted_std2_btn":

    __process_x_calibration_si_creation()
    ###################################################

elif x_calib_btn == "btn_derive_x_calibration_curve":

    neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

    settings = st.session_state["cache_dicts"]["instrument_settings"][
        "settings_mandatory"
    ]
    laser_wl = settings.laser_wavelength

    # laser_wl = st.session_state["cache_dicts"]["instrument_settings"]["instrument_wl"]

    calmodel = CalibrationModel(laser_wl)

    find_kw_neon = {}
    if "neon_kwargs_find_peak" in st.session_state["cache_dicts"]["spectra_x_current"]:
        find_kw_neon = st.session_state["cache_dicts"]["spectra_x_current"][
            "neon_kwargs_find_peak"
        ]

    # find_kw = {"prominence": neon_spe.y_noise * prominence,
    #            "wlen": laser_wl, "width":  self.kw_findpeak_width}
    fit_kw_neon = {}
    if "neon_kwargs_fit_peak" in st.session_state["cache_dicts"]["spectra_x_current"]:
        fit_kw_neon = st.session_state["cache_dicts"]["spectra_x_current"][
            "neon_kwargs_fit_peak"
        ]

    from ramanchada2.spectrum import Spectrum

    ref_spe = calmodel.neon_wl[int(laser_wl)]

    calibration_component_neon: XCalibrationComponent = calmodel.derive_model_curve(
        spe=neon_spe,
        ref=ref_spe,  # neon_spe,
        spe_units=neon_spe.meta["units"],
        ref_units="nm",
        find_kw=find_kw_neon,
        fit_peaks_kw=fit_kw_neon,
        should_fit=False,
        name="Neon calibration",
    )

    st.session_state["cache_dicts"]["x_calibration"]["xcalibration_model"] = calmodel

    st.session_state["cache_dicts"]["x_calibration"][
        "xcalibration_component_neon"
    ] = calibration_component_neon

    fig, ax = plt.subplots(1, 1, sharex=False, figsize=(12, 10))

    calmodel.plot(ax=ax)

    red_patch = mpatches.Patch(color='blue', label='Neon peaks')
    blue_patch = mpatches.Patch(color='red', label='Neon reference')

    ax.legend(handles=[red_patch, blue_patch])

    st.pyplot(fig)

elif x_calib_btn == "btn_lazer_zeroing":

    if not "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]:
        st.error("First derive calibration model: CalibrationModel(laser_wl)")
    else:
        calmodel = st.session_state["cache_dicts"]["x_calibration"][
            "xcalibration_model"
        ]

    if (
        not "xcalibration_component_neon"
        in st.session_state["cache_dicts"]["x_calibration"]
    ):
        st.error("First save xcalibration component Neon")
    else:
        calibration_component = st.session_state["cache_dicts"]["x_calibration"][
            "xcalibration_component_neon"
        ]

    si_spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

    spe_si_new = calibration_component.process(
        si_spe, si_spe.meta["units"], convert_back=False
    )

    find_kw_si = {}
    if "si_kwargs_find_peak" in st.session_state["cache_dicts"]["spectra_x_current"]:
        find_kw_si = st.session_state["cache_dicts"]["spectra_x_current"][
            "si_kwargs_find_peak"
        ]
    fit_kw_si = {}
    if "si_kwargs_fit_peak" in st.session_state["cache_dicts"]["spectra_x_current"]:
        fit_kw_si = st.session_state["cache_dicts"]["spectra_x_current"][
            "si_kwargs_fit_peak"
        ]

    print("find_kw_si ", find_kw_si)
    print("fit_kw_si ", fit_kw_si)

    spe_sil_ne_calib = spe_si_new

    st.session_state["cache_dicts"]["x_calibration"][
        "spe_sil_ne_calib"
    ] = spe_sil_ne_calib

    # ref={520.45: 1}, spe_units="nm", ref_units=ref_sil_units,
    ref_sil_units = "cm-1"

    # ref_spe
    lazer_zeroing_component_si: LazerZeroingComponent = calmodel.derive_model_zero(
        spe_sil_ne_calib,
        ref={520.45: 1},
        spe_units="nm",
        ref_units=ref_sil_units,
        find_kw=find_kw_si,
        # fit_peaks_kw=fit_kw_si,
    )

    st.session_state["cache_dicts"]["x_calibration"][
        "xcalibration_component_si"
    ] = lazer_zeroing_component_si

    st.session_state["cache_dicts"]["x_calibration"]["xcalibration_model"] = calmodel

    spe_si = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

    fig, axes = plt.subplots(2, 1, sharex=False, figsize=(12, 10))

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

    st.pyplot(fig)


# elif x_calib_btn == "plot_xcalibration_model_btn":
#     pass
    # calmodel = st.session_state["cache_dicts"]["x_calibration"]["xcalibration_model"]

    # spe_si = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

    # spe_sil_ne_calib = st.session_state["cache_dicts"]["x_calibration"][
    #     "spe_sil_ne_calib"
    # ]

    # # target_spe = st.session_state["cache_dicts"]["page01_load_spe"][
    # #     "target_spe_current"
    # # ]

    # fig, axes = plt.subplots(2, 1, sharex=False, figsize=(12, 10))

    # calmodel.plot(ax=axes[0])
    # # axes[0].legend(['Neon peaks', 'referent Neon peaks'])

    # # spe_sil_ne_calib.plot(ax=axes[1], label='processed')
    # spe_si.plot(ax=axes[1], label="Si processed", color="blue")
    # si_units = spe_si.meta["units"]

    # si_calibrated = apply_calibration_x(calmodel, spe_si, si_units)

    # si_calibrated.plot(ax=axes[1], color="orange", label="Si calibrated")
    # axes[1].legend()
    # axes[1].set_xlabel(r"Raman shift " + si_units)
    # axes[1].set_xlim(520.45 - 50, 520.45 + 50)

    # st.pyplot(fig)

elif x_calib_btn == "btn_save_x_calibration":
    st.write("SAVE X-Calibraiton")

    if not "xcalibration_model" in st.session_state["cache_dicts"]["x_calibration"]:
        st.write("First derive calibration")
    else:

        xcalibration_filename = st.session_state["cache_dicts"]["x_calibration"][
            "xcalibration_filename"
        ]
        calmodel = st.session_state["cache_dicts"]["x_calibration"][
            "xcalibration_model"
        ]
        # './data/calibration_model01.pkl'
        path = str(rpath / "data" / xcalibration_filename)
        calmodel.save(path)

        st.write("Saved X-calibration model in ",
                 "./data/" + xcalibration_filename)


elif x_calib_btn == "btn_save_material_certificate":

    certificate_data: YCalibrationCertificate = st.session_state["cache_dicts"][
        "material_certificate"
    ]
    # st.write(certificate_data)
    # st.write(type(certificate_data))
    ax = certificate_data.plot()
    fig = ax.get_figure()
    st.pyplot(fig)

elif x_calib_btn == "uploaded_x_calibration_btn":
    calmodel = st.session_state["cache_dicts"]["x_calibration"]["xcalibration_model"]
    ax = calmodel.plot()
    fig = ax.get_figure()
    fig.set_size_inches(40, 25)
    st.pyplot(fig)

elif x_calib_btn == "btn_save_y_calibration":

    ycertificate_data: YCalibrationCertificate = st.session_state["cache_dicts"][
        "instrument_settings"
    ]["certificate_data"]
    reference_spe_xcalibrated = st.session_state["cache_dicts"]["spectra_x_current"][
        "neon"
    ]

    laser_wl = ycertificate_data.wavelength

    st.write(ycertificate_data)
    st.write(type(ycertificate_data))
    ax = ycertificate_data.plot()
    fig = ax.get_figure()
    st.pyplot(fig)

    y_calibration = YCalibrationComponent(
        laser_wl,
        reference_spe_xcalibrated=reference_spe_xcalibrated,
        certificate=ycertificate_data,
    )

    y_calib_string = """>>> laser_wl = 785
        >>> ycert = YCalibrationCertificate.load(wavelength=785, key="SRM2241")
        theoretical from certificate / experimental from file spe
        >>> ycal = YCalibrationComponent(laser_wl, reference_spe_xcalibrated=spe_srm,certificate=ycert)
        >>> fig, ax = plt.subplots(1, 1, figsize=(15,4))
        >>> spe_srm.plot(ax=ax)
        >>> spe_to_correct.plot(ax=ax)
        >>> spe_ycalibrated = ycal.process(spe_to_correct)
        >>> spe_ycalibrated.plot(label="y-calibrated",color="green",ax=ax.twinx())


        !!!NB  Give the option to reverse X-Y Calibration to think about it!!!

        !!! Think about save / load Y-calibration - to be developed!
        """

    """
    NB! Signal to noise ratio to be added - (Enrique)
    NB! Dark background - to be extracted

    """
    st.write(y_calib_string)
else:
    pass

# main_page()
