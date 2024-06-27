#!/usr/bin/env python3
from collections import defaultdict

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from front_end.htmlTemplates import css

from modules.navigation_bar import navbar

from ramanchada2.protocols.calibration import (
    CalibrationModel,
    CertificatesDict,
    YCalibrationCertificate,
    YCalibrationComponent,
)

from util import plot_original_x_calib_spe, process_file_spe

from pages.load_target_spectra import page_1_session_state, this_int

navbar()

print(this_int)
print(page_1_session_state)


# st.set_page_config(
#     page_title="Raman spectroscopy harmonisation",
#     page_icon="../front_end/images/logo_charisma.jpg",
#     layout="wide",
# )

st.write(css, unsafe_allow_html=True)

st.session_state.update(page_1_session_state)

st.session_state["cache_dicts"]["target_spe"] = st.session_state["cache_dicts"][
    "target_spe"
]


def instrument_settings_expander():

    with st.expander("Instrument settings", expanded=False):

        if "instrument_settings" not in st.session_state["cache_dicts"]:
            certificates = CertificatesDict()
            config_certs = certificates.config_certs
            st.write(config_certs)
            st.session_state["cache_dicts"]["instrument_settings"][
                "config_certs"
            ] = config_certs

        config_certs = st.session_state["cache_dicts"]["instrument_settings"][
            "config_certs"
        ]
        instrument_wl = st.selectbox(
            label="Choose wave length", options=list(config_certs.keys()), index=0
        )

        st.session_state["cache_dicts"]["instrument_settings"][
            "instrument_wl"
        ] = instrument_wl

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
        value = (
            10
            if "prominence"
            not in st.session_state["cache_dicts"]["active_calibration_settings"]
            else st.session_state["cache_dicts"]["active_calibration_settings"][
                "prominence"
            ]
        )

        prominence = st.number_input(
            label="Prominence", min_value=1, max_value=15, value=value, step=1
        )

        st.session_state["cache_dicts"]["active_calibration_settings"][
            "prominence"
        ] = prominence


def load_calibration_spectra_expander():

    uploaded_neon_spec = st.file_uploader(
        "Load Neon spectra file", accept_multiple_files=False
    )
    if uploaded_neon_spec:
        st.session_state["cache_dicts"]["spectra_x"]["neon"] = process_file_spe(
            [uploaded_neon_spec], label="Neon"
        )

        st.session_state["cache_strings"][
            "x_calibration"
        ] = "uploaded_neon_calib_spectra_btn"

    ###########################################
    uploaded_si_spec = st.file_uploader(
        "Load Si spectra file", accept_multiple_files=False
    )
    if uploaded_si_spec:
        st.session_state["cache_dicts"]["spectra_x"]["si"] = process_file_spe(
            [uploaded_si_spec], label="Si"
        )

        st.session_state["cache_strings"][
            "x_calibration"
        ] = "uploaded_si_calib_spectra_btn"


def create_x_calibration_sidebar_expander():

    with st.expander("Create X-Calibration", expanded=False):

        load_calibration_spectra_expander()

        with st.form("STD1 Process"):

            submitted_btn_st1 = st.form_submit_button("Process Neon spe")
            if submitted_btn_st1:
                st.session_state["cache_strings"][
                    "x_calibration"
                ] = "submitted_std1_btn"

                # page_call_STD1_X_Calibration()

        with st.form("STD2 Process"):
            # st.write("Si STD2 setup....")

            submitted_btn_st2 = st.form_submit_button("Process Si spe")
            if submitted_btn_st2:
                # st.session_state.cache_bools['submitted_std2_btn'] = True
                st.session_state["cache_strings"][
                    "x_calibration"
                ] = "submitted_std2_btn"
                # page_call_STD2_X_Calibration()

        with st.form("Derive X-calibration"):
            # st.write("Derive X-calibration")
            # st.write("X-calibration setup")

            submitted_btn_derive_x = st.form_submit_button("Derive X-Calibration")

            if submitted_btn_derive_x:
                st.session_state["cache_strings"][
                    "x_calibration"
                ] = "btn_derive_x_calibration"

        with st.form("Save X-calibration"):
            # st.write("Save X-calibration")

            submitted_btn_save_x = st.form_submit_button("Save X-Calibration")

            if submitted_btn_save_x:
                st.session_state["cache_strings"][
                    "x_calibration"
                ] = "btn_save_x_calibration"


def create_y_calibration_sidebar_expander():
    with st.expander("Create Y-Calibration", expanded=False):

        config_certs = st.session_state["cache_dicts"]["instrument_settings"][
            "config_certs"
        ]

        instrument_wl = st.session_state["cache_dicts"]["instrument_settings"][
            "instrument_wl"
        ]
        certs_dict = config_certs[instrument_wl]
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

            submitted_btn_srm_experimental = st.form_submit_button("SRM Experimental")
            if submitted_btn_srm_experimental:
                st.session_state["cache_strings"][
                    "x_calibration"
                ] = "submitted_btn_srm_experimental"

                # page_call_STD1_X_Calibration()

        # with st.form("SRM theoretical"):
        #     st.write("SRM Theoretical spectrum")

        #     submitted_btn_srm_theoretical = st.form_submit_button(
        #         "SRM Theoretical")
        #     if submitted_btn_srm_theoretical:
        #         st.session_state["cache_strings"][
        #             "x_calibration"
        #         ] = "submitted_btn_srm_theoretical"

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
            "Load spe",
            "Crop",  # 'Baseline corr',
            "Normalize",
            "Peak find",
            "Peak fitting",
        ]
    )

    with load_tn:
        neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"][0]
        st.session_state["cache_dicts"]["spectra_x_current"]["neon"] = neon_spe

        fig, ax = plt.subplots(figsize=(30, 15))
        neon_spe.plot(ax=ax, label="Neon")
        st.pyplot(fig)
        # plot_original_x_calib_spe(
        #     neon_spe, label=neon_spe.meta['label'])
    with crop_tn:
        spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
        (left_val, right_val) = st.slider(
            "Select range of X axis",
            min(spe.x),
            max(spe.x),
            (min(spe.x), max(spe.x)),
            on_change=update_x_calibration_btn("submitted_std2_btn"),
        )
        # st.write(left_val, right_val)
        spe = spe.trim_axes(method="x-axis", boundaries=(left_val, right_val))
        st.session_state["cache_dicts"]["spectra_x_current"]["neon"] = spe
        st.session_state["cache_dicts"]["spectra_x_crop"]["neon"] = spe

        fig, ax = plt.subplots(figsize=(30, 15))
        spe.plot(ax=ax, label="Neon")
        st.pyplot(fig)

    with normalize_tn:
        # st.write('normlaize tab')
        neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

        neon_normalized_spe = neon_spe.normalize()
        st.session_state["cache_dicts"]["spectra_x_normalized"][
            "neon"
        ] = neon_normalized_spe
        st.session_state["cache_dicts"]["spectra_x_current"][
            "neon"
        ] = neon_normalized_spe

        fig, ax = plt.subplots(figsize=(30, 15))
        neon_normalized_spe.plot(ax=ax)
        st.pyplot(fig)
        # plot_original_x_calib_spe(neon_normalized_spe,
        #                           label=neon_normalized_spe.meta['label'])
    with peakfind_tn:
        # st.write('Peak find')
        neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

        # st.write('neon spe y noise')
        # st.write(neon_spe.y_noise)

        if (
            "neon_kwargs_find_peak"
            not in st.session_state["cache_dicts"]["spectra_x_current"]
        ):

            value_prominence = neon_spe.y_noise
            value_wlen = 200
            value_width = 2
            value_hht_chain = 80
            value_sharpening = None
            value_strategy = "topo"
        else:
            kwargs = st.session_state["cache_dicts"]["spectra_x_current"][
                "neon_kwargs_find_peak"
            ]
            value_prominence = kwargs["prominence"]
            value_wlen = kwargs["wlen"]
            value_width = kwargs["width"]
            value_hht_chain = kwargs["hht_chain"][0]
            value_sharpening = kwargs["sharpening"]
            value_strategy = kwargs["strategy"]

        col1, col2, col3 = st.columns(3)
        with col1:
            wlen = st.number_input(
                label="window length",
                min_value=10,
                max_value=800,
                value=value_wlen,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
            width = st.number_input(
                label="width",
                min_value=1,
                max_value=10,
                value=value_width,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
        with col2:
            hht_chain = st.number_input(
                label="hht_chain[int]",
                min_value=10,
                max_value=150,
                value=value_hht_chain,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
            options_sharpening = ["hht", None]
            sharpening = st.selectbox(
                label="sharpening",
                options=options_sharpening,
                index=options_sharpening.index(value_sharpening),
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
        with col3:

            prominence = st.number_input(
                label="prominence",
                min_value=0.0,
                max_value=10.0,
                value=value_prominence,
                step=0.001,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )

            options_strategy = ["topo", "bayesian_gaussian_mixture", "bgm", "cwt"]

            # st.write(value_strategy)
            strategy = st.selectbox(
                label="strategy",
                options=options_strategy,
                index=options_strategy.index(value_strategy),
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )

        kwargs = {
            "wlen": wlen,
            "width": width,
            "hht_chain": [hht_chain],
            "prominence": prominence,
            "sharpening": sharpening,
            "strategy": strategy,
        }

        st.session_state["cache_dicts"]["spectra_x_current"][
            "neon_kwargs_find_peak"
        ] = kwargs

        neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
        neon_peak_candidates = neon_spe.find_peak_multipeak(**kwargs)

        st.session_state["cache_dicts"]["spectra_x_peak_candidates"][
            "neon"
        ] = neon_peak_candidates

        fig, ax = plt.subplots(figsize=(30, 10))
        neon_peak_candidates.plot(ax=ax, fmt=":", label="Neon")

        st.pyplot(fig)

    with peakfit_tn:

        col1, col2, col3 = st.columns(3)
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
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
            no_fit = st.selectbox(
                label="No fit",
                options=[True, False],
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )

        st.session_state["cache_dicts"]["spectra_x_current"]["neon_kwargs_fit_peak"] = {
            "profile": profile,
            "no_fit": no_fit,
        }
        neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
        neon_peak_candidates = st.session_state["cache_dicts"][
            "spectra_x_peak_candidates"
        ]["neon"]
        fitres = neon_spe.fit_peak_multimodel(
            profile=profile, candidates=neon_peak_candidates, no_fit=True
        )

        fig, ax = plt.subplots(figsize=(30, 15))
        neon_spe.plot(ax=ax, fmt=":", label="Neon")
        fitres.plot(
            ax=ax,
            peak_candidate_groups=neon_peak_candidates,
            individual_peaks=True,
            label=None,
        )
        st.pyplot(fig)


def process_x_calibration_si_creation():
    material = "si"
    ###############################################
    # st.write(' in elif x_calib_btn std2')
    load_ts, crop_tn, baseline_tn, normalize_ts, peakfind_ts, peakfit_ts = st.tabs(
        ["Load spe", "Crop", "Baseline corr", "Normalize", "Peak find", "Peak fitting"]
    )

    with load_ts:
        spe = st.session_state["cache_dicts"]["spectra_x"][material][0]
        st.session_state["cache_dicts"]["spectra_x_current"][material] = spe

        fig, ax = plt.subplots(figsize=(30, 15))
        spe.plot(ax=ax, label="Si")
        st.pyplot(fig)

    with crop_tn:
        spe = st.session_state["cache_dicts"]["spectra_x_current"][material]
        (left_val, right_val) = st.slider(
            "Select range of X axis",
            min(spe.x),
            max(spe.x),
            (min(spe.x), max(spe.x)),
            on_change=update_x_calibration_btn("submitted_std2_btn"),
        )
        st.write(left_val, right_val)
        spe = spe.trim_axes(method="x-axis", boundaries=(left_val, right_val))
        st.session_state["cache_dicts"]["spectra_x_current"][material] = spe
        st.session_state["cache_dicts"]["spectra_x_crop"][material] = spe

        fig, ax = plt.subplots(figsize=(30, 15))
        spe.plot(ax=ax, label="Si")
        st.pyplot(fig)

    with baseline_tn:
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
        # st.session_state["cache_dicts"]['spectra_x']['neon'][0]
        baseline_corr_spe = spe - spe.moving_minimum(moving_min_val)
        st.session_state["cache_dicts"]["spectra_x_baseline_corr"][
            "si"
        ] = baseline_corr_spe
        if use_baseline_corr:
            st.session_state["cache_dicts"]["spectra_x_current"][
                "si"
            ] = baseline_corr_spe
        # plot_original_x_calib_spe(neon_baseline_corr_spe,
        #                           label=neon_baseline_corr_spe.meta['label'])
        fig, ax = plt.subplots(figsize=(30, 12))
        baseline_corr_spe.plot(ax=ax, label="Si")
        st.pyplot(fig)

    with normalize_ts:
        # st.write('normlaize tab')
        spe = st.session_state["cache_dicts"]["spectra_x_current"][material]

        normalized_spe = spe.normalize()
        st.session_state["cache_dicts"]["spectra_x_normalized"][
            material
        ] = normalized_spe
        st.session_state["cache_dicts"]["spectra_x_current"][material] = normalized_spe

        fig, ax = plt.subplots(figsize=(30, 15))

        normalized_spe.plot(ax=ax, label="Si")
        st.pyplot(fig)

    with peakfind_ts:

        spe = st.session_state["cache_dicts"]["spectra_x_current"][material]

        if (
            "si_kwargs_find_peak"
            not in st.session_state["cache_dicts"]["spectra_x_current"]
        ):

            value_prominence = spe.y_noise
            value_wlen = 200
            value_width = 2
            value_hht_chain = 80
            value_sharpening = None
            value_strategy = "topo"
        else:
            kwargs = st.session_state["cache_dicts"]["spectra_x_current"][
                "si_kwargs_find_peak"
            ]
            value_prominence = kwargs["prominence"]
            value_wlen = kwargs["wlen"]
            value_width = kwargs["width"]
            value_hht_chain = kwargs["hht_chain"][0]
            value_sharpening = kwargs["sharpening"]
            value_strategy = kwargs["strategy"]

        col1, col2, col3 = st.columns(3)
        with col1:
            wlen = st.number_input(
                label="window length",
                min_value=10,
                max_value=800,
                value=value_wlen,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
            width = st.number_input(
                label="width",
                min_value=1,
                max_value=10,
                value=value_width,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
        with col2:
            hht_chain = st.number_input(
                label="hht_chain[int]",
                min_value=10,
                max_value=150,
                value=value_hht_chain,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
            options_sharpening = ["hht", None]
            sharpening = st.selectbox(
                label="sharpening",
                options=options_sharpening,
                index=options_sharpening.index(value_sharpening),
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )
        with col3:

            prominence = st.number_input(
                label="prominence",
                min_value=0.0,
                max_value=10.0,
                value=value_prominence,
                step=0.001,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )

            options_strategy = ["topo", "bayesian_gaussian_mixture", "bgm", "cwt"]

            # st.write(value_strategy)
            strategy = st.selectbox(
                label="strategy",
                options=options_strategy,
                index=options_strategy.index(value_strategy),
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )

        kwargs = {
            "wlen": wlen,
            "width": width,
            "hht_chain": [hht_chain],
            "prominence": prominence,
            "sharpening": sharpening,
            "strategy": strategy,
        }

        st.session_state["cache_dicts"]["spectra_x_current"][
            "si_kwargs_find_peak"
        ] = kwargs

        # neon_spe = st.session_state["cache_dicts"]['spectra_x_current']['neon']
        # neon_peak_candidates = neon_spe.find_peak_multipeak(
        #     **kwargs)

        # st.session_state["cache_dicts"]['spectra_x_peak_candidates']['neon'] = \
        #     neon_peak_candidates

        spe = st.session_state["cache_dicts"]["spectra_x_current"][material]
        peak_candidates = spe.find_peak_multipeak(**kwargs)

        st.session_state["cache_dicts"]["spectra_x_peak_candidates"][
            material
        ] = peak_candidates

        fig, ax = plt.subplots(figsize=(30, 10))
        peak_candidates.plot(ax=ax, fmt=":", label="Si")

        st.pyplot(fig)

    with peakfit_ts:
        col1, col2, col3 = st.columns(3)
        with col1:

            profile = st.selectbox(
                label="Profile",
                options=[
                    "Pearson7",
                    "Gaussian",
                    "Moffat",
                    "Lorentzian",
                    "Voigt",
                    "PseudoVoigt",
                    "Pearson4",
                ],
                index=0,
                on_change=update_x_calibration_btn("submitted_std2_btn"),
            )
        spe = st.session_state["cache_dicts"]["spectra_x_current"][material]
        peak_candidates = st.session_state["cache_dicts"]["spectra_x_peak_candidates"][
            material
        ]
        fitres = spe.fit_peak_multimodel(
            profile=profile, candidates=peak_candidates, no_fit=True
        )

        fig, ax = plt.subplots(figsize=(30, 15))
        spe.plot(ax=ax, fmt=":", label="Si")
        fitres.plot(
            ax=ax,
            peak_candidate_groups=peak_candidates,
            individual_peaks=True,
            label=None,
        )
        st.pyplot(fig)


def simple_plot_spe(spe, label, xlabel):
    fig, ax = plt.subplots()
    fig.set_size_inches(30, 15)
    ax.set_xlabel(xlabel)
    spe.plot(ax=ax, label=label)
    st.pyplot(fig)


def update_x_calibration_btn(value):
    def update_x_calibraiton_val():
        st.session_state["cache_strings"]["x_calibration_"] = value
        # print('in update_x_calibration_val')
        # print(' ini...', st.session_state["cache_strings"]["x_calibration_"])

    return update_x_calibraiton_val
    # print('inside update x calib')
    # print()
    # st.session_state["cache_strings"]["x_calibration_"] = "submitted_std1_btn"


with st.sidebar:

    # st.sidebar.image("./src/front_end/images/logo_charisma.jpg")
    # st.header("AI data extractor")

    calibration_choice = st.radio(
        "Choose calibration option",
        ["Load/Search Calibration", "Create Calibration"],
        index=0,
    )

if calibration_choice == "Load/Search Calibration":
    with st.sidebar:
        existing_calibration = st.text_input("Search for existing calibration", "")
else:
    with st.sidebar:

        st.session_state["cache_dicts"]["x_calibration"] = ""

        instrument_settings_expander()

        active_calibration_settings_expander()

        create_x_calibration_sidebar_expander()

        create_y_calibration_sidebar_expander()


if st.session_state["cache_strings"]["x_calibration_"]:
    print("in IF...")
    st.session_state["cache_strings"]["x_calibration"] = st.session_state[
        "cache_strings"
    ]["x_calibration_"]
    st.session_state["cache_strings"]["x_calibration_"] = None

x_calib_btn = st.session_state["cache_strings"]["x_calibration"]


if x_calib_btn == "uploaded_neon_calib_spectra_btn":

    neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"][0]

    simple_plot_spe(spe=neon_spe, label="Neon", xlabel=r"Raman shift [$\mathrm{nm}$]")

elif x_calib_btn == "uploaded_si_calib_spectra_btn":
    si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"][0]

    simple_plot_spe(spe=si_spe, label="Si", xlabel=r"Raman shift [$\mathrm{cm}^{-1}$]")
    # fig, ax = plt.subplots()
    # fig.set_size_inches(30, 15)
    # ax.set_xlabel(xlabel)
    # si_spe.plot(ax=ax, label='Si')
    # st.pyplot(fig)

elif x_calib_btn == "submitted_std1_btn":
    # st.write(' in elif x_calib_btn std1')
    process_x_calibration_neon_creation()

elif x_calib_btn == "submitted_std2_btn":

    process_x_calibration_si_creation()
    ###################################################

elif x_calib_btn == "btn_derive_x_calibration":
    neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
    si_spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

    laser_wl = st.session_state["cache_dicts"]["instrument_settings"]["instrument_wl"]
    # ycertificate_data: YCalibrationCertificate = \
    #     st.session_state["cache_dicts"]['instrument_settings'
    #                                     ]['certificate_data']
    # laser_wl = ycertificate_data.wavelength

    # prominence = st.session_state["cache_dicts"]["active_calibration_settings"
    #                                              ]["prominence"]

    calmodel = CalibrationModel(laser_wl)

    find_kw_neon = st.session_state["cache_dicts"]["spectra_x_current"][
        "neon_kwargs_find_peak"
    ]
    # find_kw = {"prominence": neon_spe.y_noise * prominence,
    #            "wlen": laser_wl, "width":  self.kw_findpeak_width}
    fit_kw_neon = st.session_state["cache_dicts"]["spectra_x_current"][
        "neon_kwargs_fit_peak"
    ]

    target_spe = st.session_state["cache_dicts"]["target_spe"][0]
    ref_neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

    from ramanchada2.protocols.calibration import XCalibrationComponent

    calibration_component_neon: XCalibrationComponent = calmodel.derive_model_curve(
        spe=target_spe,
        ref=ref_neon_spe,  # neon_spe,
        # laser_wl,
        spe_units="cm-1",
        ref_units="cm-1",
        find_kw=find_kw_neon,
        fit_peaks_kw=fit_kw_neon,
        should_fit=False,
        name="Neon calibration",
    )

    spe_si_new = calibration_component_neon.process(
        si_spe, spe_units="nm", convert_back=False
    )

    find_kw_si = st.session_state["cache_dicts"]["spectra_x_current"][
        "si_kwargs_find_peak"
    ]
    fit_kw_si = st.session_state["cache_dicts"]["spectra_x_current"][
        "si_kwargs_fit_peak"
    ]

    lazer_zeroing_component_si = calmodel.derive_model_zero(
        spe=target_spe,
        ref=spe_si_new,
        spe_units="cm-1",
        ref_units="nm",
        find_kw=find_kw_si,
        fit_peaks_kw=fit_kw_si,
    )

    ax = calmodel.plot()
    fig = ax.get_figure()
    st.pyplot(fig)
    # !!! Save the calmodel !!! and use in the Ycalibration

    # target_spe = st.session_state["cache_dicts"]['spectra_x']['target'][0]
    st.write("DERIVING MODEL...")
    # calmodel = CalibrationModel()
    # find_kw = {"prominence": spe_neon.y_noise * calmodel.prominence_coeff,
    #            "wlen": self.kw_findpeak_wlen, "width":  self.kw_findpeak_width}
    # model_neon = calmodel.derive_model_curve(
    #         spe_neon, laser_wl,
    #         spe_units=spe_neon_units, ref_units=ref_neon_units,
    #         find_kw={},
    #         fit_peaks_kw={}, should_fit=False, name="Neon calibration")
    # spe_sil_ne_calib = model_neon.process(spe_sil, spe_units=spe_sil_units, convert_back=False)
    # find_kw = {"prominence": spe_sil_ne_calib.y_noise * 10, "wlen": 200, "width":  1}

    # model_si = self.derive_model_zero(
    #         spe_sil_ne_calib, ref={520.45: 1}, spe_units="nm", ref_units=ref_sil_units, find_kw=find_kw,
    #         fit_peaks_kw={}, should_fit=True, name="Si laser zeroing")

    # return (model_neon, model_si)
    # calmodel = CalibrationModel()
    # calmodel.prominence_coeff = self.kw_findpeak_prominence
    # print("derive_model_curve")
    # find_kw = {"prominence": spe_neon.y_noise * calmodel.prominence_coeff,
    #            "wlen": self.kw_findpeak_wlen, "width":  self.kw_findpeak_width}

    # model_neon = calmodel.derive_model_curve(spe_neon,calmodel.neon_wl[laser_wl],spe_units="cm-1",ref_units="nm",find_kw=find_kw,fit_peaks_kw={},should_fit = self.ne_should_fit,name="Neon calibration")
    # plc_x_calibration.image(
    #     "src/data/images/screenshot_derive_x_calibration01.png"
    # )
    # plc_x_calibration.write(
    #     'src/data/images/screenshot_derive_x_calibration01.png')
elif x_calib_btn == "btn_save_x_calibration":
    st.write("SAVE X-Calibraiton")
    # plc_x_calibration.image(
    #     "src/data/images/screenshot_save_x_calibration01.png"
    # )
    #   should_fit = True, name = "Si laser zeroing")
    """ !NB!
#    1.  remove the theoretical button --> it will be the drop down with the reference material
    before the experimental SRM button (it will use the same material!)

    2. wlen --> this is window length!!! not wave length!!!  CHECK lazer_wl, and other wl how are used!

 #   3. Add Crop for Neon too -- and for the one we apply calibration (target spe too)

    4.  Add units for the spectra - to be choosen by the user (bellow Upload spectra)


    """
elif x_calib_btn == "btn_save_material_certificate":

    certificate_data: YCalibrationCertificate = st.session_state["cache_dicts"][
        "material_certificate"
    ]
    # st.write(certificate_data)
    # st.write(type(certificate_data))
    ax = certificate_data.plot()
    fig = ax.get_figure()
    st.pyplot(fig)

elif x_calib_btn == "btn_save_y_calibration":

    ycertificate_data: YCalibrationCertificate = st.session_state["cache_dicts"][
        "instrument_settings"
    ]["certificate_data"]
    reference_spe_xcalibrated = neon_spe = st.session_state["cache_dicts"][
        "spectra_x_current"
    ]["neon"]
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
