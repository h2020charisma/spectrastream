#!/usr/bin/env python3
import warnings
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import ramanchada2.misc.constants as rc2const
import streamlit as st
from ramanchada2.protocols.calibration.calibration_model import CalibrationModel
from ramanchada2.protocols.calibration.xcalibration import (
    LazerZeroingComponent,
    XCalibrationComponent,
)
from ramanchada2.protocols.calibration.ycalibration import (
    CertificatesDict,
    YCalibrationCertificate,
    YCalibrationComponent,
)
from ramanchada2.spectrum.baseline.baseline_rc1 import baseline_als, baseline_snip

from front_end.htmlTemplates import css
from modules.models import (
    ALSBaselineArgs,
    SNIPBaselineArgs,
    StateBaselineCorrection,
    StateCrop,
    StateNormalize,
    StatePeakFind,
    StateSmooth,
    default_state_neon,
    default_state_si,
    default_state_srm_ref,
)
from modules.navigation_bar import navbar
from modules.util import (
    apply_calibration_x,
    callback_change_value,
    load_calibration_file,
    process_file_spe,
    simple_plot_spe,
)

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


def material_settings_expander():

    # with st.expander("Material settings", expanded=False):

    if "config_certs" not in st.session_state["cache_dicts"]["material_settings"]:
        certificates = CertificatesDict()
        config_certs = certificates.config_certs
        # st.write(config_certs)
        st.session_state["cache_dicts"]["material_settings"]["config_certs"] = (
            config_certs
        )

    config_certs = st.session_state["cache_dicts"]["material_settings"]["config_certs"]
    instrument_wl = st.selectbox(
        label="Choose wavelength", options=list(config_certs.keys()), index=0
    )

    st.session_state["cache_dicts"]["material_settings"]["instrument_wl"] = (
        instrument_wl
    )


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
# ...             params=(
# ...                 "A0 = 9.71937e-02, A1 = 2.28325e-04, "
# ...                 "A2 = -5.86762e-08, A3 = 2.16023e-10, "
# ...                 "A4 = -9.77171e-14, A5 = 1.15596e-17"
# ...             ),
# ...             equation=(
# ...                 "A0 + A1 * x + A2 * x**2 + A3 * x**3 + "
# ...                 "A4 * x**4 + A5 * x**5"
# ...             ),
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
        st.session_state["cache_dicts"]["x_calibration"]["xcalibration_model"] = (
            xcalibration
        )
        st.session_state["cache_strings"]["x_calibration"] = (
            "uploaded_x_calibration_btn"
        )

        return xcalibration
    return None


def load_calibration_spectrum_neon():

    # with st.form("Load Neon spectrum"):
    col1_load_n, col2_load_n = st.columns(2)

    with col1_load_n:
        uploaded_neon_spec = st.file_uploader(
            key="upload_neon",
            label="Load Neon spectrum file",
            accept_multiple_files=False,
        )
    with col2_load_n:
        units = st.selectbox(
            key="units_select_neon",
            label="Select units",
            options=["cm-1", "nm"],
            index=0,
        )

    if uploaded_neon_spec:
        neon_spe = process_file_spe([uploaded_neon_spec], label="Neon", units=units)
        # meta_dct = target_spe.meta
        st.session_state["cache_dicts"]["spectra_x"]["neon"] = neon_spe

        # st.session_state["cache_strings"]["x_calibration"] = \
        #     "uploaded_neon_calib_spectra_btn"


def load_calibration_spectrum_si():

    # with st.form("Load Si spectrum"):
    col1, col2 = st.columns(2)

    with col1:
        uploaded_si_spec = st.file_uploader(
            key="upload_si",
            label="Load Si spectrum file",
            accept_multiple_files=False,
        )
    with col2:
        units = st.selectbox(
            key="units_select_si", label="Select units", options=["cm-1", "nm"], index=0
        )

        # upload_si_spe_btn = st.form_submit_button("Load spectrum")

    if uploaded_si_spec:
        si_spe = process_file_spe([uploaded_si_spec], label="Si", units=units)
        # meta_dct = target_spe.meta
        st.session_state["cache_dicts"]["spectra_x"]["si"] = si_spe

        # st.session_state["cache_strings"][
        #     "x_calibration"
        # ] = "uploaded_si_calib_spectra_btn"


def load_calibration_spectrum_srm_ref():

    col1, col2 = st.columns(2)

    with col1:
        uploaded_srm_spec = st.file_uploader(
            key="upload_srm_ref",
            label="Load Reference spectrum",
            accept_multiple_files=False,
        )
    with col2:
        units = st.selectbox(
            key="units_select_srm_ref",
            label="Select units",
            options=["cm-1", "nm"],
            index=0,
        )

        # upload_si_spe_btn = st.form_submit_button("Load spectrum")

    if uploaded_srm_spec:
        si_spe = process_file_spe([uploaded_srm_spec], label="Si", units=units)
        # meta_dct = target_spe.meta
        st.session_state["cache_dicts"]["spectra_y"]["srm_ref"] = si_spe


# def page_call_STD1_X_Calibration():
#     pass


def create_x_calibration_sidebar_expander():

    with st.expander("Create X-Calibration", expanded=False):
        # load_calibration_spectrum_neon()

        # with st.form("STD1 Process"):

        #     page_call_STD1_X_Calibration()

        submitted_btn_st1 = st.button("1. Neon spectrum")

        if submitted_btn_st1:
            st.session_state["cache_strings"]["x_calibration"] = "submitted_std1_btn"

        submitted_btn_derive_x = st.button("2. Derive X-Calibration curve")

        if submitted_btn_derive_x:
            st.session_state["cache_strings"]["x_calibration"] = (
                "btn_derive_x_calibration_curve"
            )

        submitted_btn_st2 = st.button("3. Si spectrum")
        if submitted_btn_st2:
            st.session_state["cache_strings"]["x_calibration"] = "submitted_std2_btn"

        submitted_btn_lazer_zeroing = st.button(
            "4. Lazer zeroing",
            # disabled=st.session_state["cache_bools"].get(
            #     "disable_lazer_zeroing", True
            # ),
        )

        # st.session_state['cache_bools']['disable_lazer_zeroing'] = True
        if submitted_btn_lazer_zeroing:
            # st.session_state['cache_bools']['disable_lazer_zeroing'] = True
            st.session_state["cache_strings"]["x_calibration"] = "btn_lazer_zeroing"

        import pickle

        calibration_file_name = st.text_input(
            label="Calibration file name",
            placeholder="xcalibration_file_name.pkl",
            value="calibration_file_name.pkl",
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


def create_y_calibration_sidebar_expander():
    expander = st.expander("Create Y-Calibration", expanded=False)
    with expander:
        # st.error("Under development!")
        # material_settings_expander()

        if "config_certs" not in st.session_state["cache_dicts"]["material_settings"]:
            certificates = CertificatesDict()
            config_certs = certificates.config_certs

            st.session_state["cache_dicts"]["material_settings"]["config_certs"] = (
                config_certs
            )

        config_certs = st.session_state["cache_dicts"]["material_settings"][
            "config_certs"
        ]

        settings = st.session_state["cache_dicts"]["instrument_settings"]["settings"]
        instrument_wl = settings["laser_wavelength"]
        st.text("Wavelength: {}".format(instrument_wl))

        certs_dict = config_certs[str(instrument_wl)]
        certificate_id = st.selectbox(
            label="Reference material certificate",
            options=list(certs_dict.keys()),
            index=0,
            on_change=update_x_calibration_btn("btn_save_material_certificate"),
        )

        certificate_data = certs_dict[certificate_id]
        st.session_state["cache_dicts"]["y_calib"]["material_certificate"] = (
            certificate_data
        )
        # st.write(certificate_data)

        # st.session_state["cache_strings"]["x_calibration"] = (
        #     "btn_save_material_certificate"
        # )

        submitted_btn_srm_experimental = st.button("SRM Experimental")
        if submitted_btn_srm_experimental:
            st.session_state["cache_strings"]["x_calibration"] = (
                "submitted_btn_srm_experimental"
            )

        derive_y_calibration_btn = st.button(
            key="derive_y_calibration_btn", label="Derive Y-calibration"
        )
        if derive_y_calibration_btn:
            st.session_state["cache_strings"]["x_calibration"] = (
                "btn_derive_y_calibration"
            )

            if "settings" not in st.session_state["cache_dicts"]["instrument_settings"]:
                st.error("Set laser wavelength from Instrument settings page")

            instrument_settings = st.session_state["cache_dicts"][
                "instrument_settings"
            ]["settings"]

            lazer_wavelength = instrument_settings["laser_wavelength"]

            ycertificate_data: YCalibrationCertificate = st.session_state[
                "cache_dicts"
            ]["y_calib"]["material_certificate"]

            spe_srm = st.session_state["cache_dicts"]["spectra_y_current"]["srm_ref"]

            ycal = YCalibrationComponent(
                laser_wl=lazer_wavelength,
                reference_spe_xcalibrated=spe_srm,
                certificate=ycertificate_data,
            )

            st.session_state["cache_dicts"]["y_calibration"]["ycalibration_model"] = (
                ycal
            )

        import pickle

        calibration_file_name = st.text_input(
            label="Calibration file name",
            placeholder="ycalibration_file_name.pkl",
            value="ycalibration_file_name.pkl",
        )
        if (
            "ycalibration_model" in st.session_state["cache_dicts"]["y_calibration"]
            and "y_calibration" in st.session_state["cache_dicts"]
        ):
            calmodel = st.session_state["cache_dicts"]["y_calibration"][
                "ycalibration_model"
            ]
            st.download_button(
                "Download Y-Calibration",
                data=pickle.dumps(calmodel),
                file_name=calibration_file_name,
            )
        # st.write('expander:')
        # st.write(type(expander.expanded))
        # if (
        #     expander.expanded
        #     and not derive_y_calibration_btn
        #     and not submitted_btn_srm_experimental
        # ):
        #     st.session_state["cache_strings"]["x_calibration"] = (
        #         "btn_save_material_certificate"
        #     )


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

    if "neon" not in st.session_state["cache_dicts"]["use"]:
        # state_settings = st.session_state["cache_dicts"]["spectrum_settings"][
        #     "neon"
        # ]
        # else:
        st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = (
            default_state_neon
        )

    state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["neon"]

    # print("State settings Neon start..")
    # print(state_settings)
    # print('------ END ------')
    print("BEFORE TABS NEON")

    with load_tn:
        load_calibration_spectrum_neon()

        if "neon" in st.session_state["cache_dicts"]["spectra_x"]:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
            spe_units = neon_spe.meta["units"]

            st.session_state["cache_dicts"]["spectra_x_current"]["neon"] = neon_spe
            st.session_state["cache_dicts"]["spectra_x_last"]["neon"] = neon_spe

            simple_plot_spe(
                spe=neon_spe, label="Neon", xlabel=r"Raman shift [{}]".format(spe_units)
            )

    with crop_tn:
        if "neon" in st.session_state["cache_dicts"]["spectra_x"]:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
            spe_units = neon_spe.meta["units"]

            label, xlabel = "Neon", r"Raman shift [{}]".format(spe_units)
            ax = neon_spe.plot(label=label, linestyle="dashed", color="blue")
            ax.set_xlabel(xlabel)

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"][
                "neon"
            ]

            # print('state_settings in the beginning of crop')
            # print(state_settings)
            # print('--- == end == ----')
            settings_crop: StateCrop = state_settings.crop

            col1_upn, col2_upn = st.columns([1, 1])
            with col1_upn:
                # callback_change_value(
                #     key="crop_neon_checkbox", value=settings_crop.use_crop)

                use_crop = st.checkbox(
                    key="crop_neon_checkbox",
                    label="Use crop",
                    value=settings_crop.use_crop,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )
            with col2_upn:
                set_default_btn = st.button(
                    key="crop_neon_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

            if set_default_btn:
                state_settings.crop = default_state_neon.crop
                st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = (
                    state_settings
                )
                settings_crop: StateCrop = state_settings.crop

            # Create a form for the input fields and submit button
            with st.form(key="neon_crop_form"):
                # Create two input columns and one submit-button column.
                # spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
                spe = st.session_state["cache_dicts"]["spectra_x_last"]["neon"]

                col0, col1, col2 = st.columns([0.5, 1, 1])

                with col0:
                    # This is to adjust the position of the button
                    st.write("")
                    submit_crop_btn = st.form_submit_button(
                        label="Update",
                        #   disabled=not use_crop
                    )

                with col1:
                    min_val = (
                        settings_crop.crop_min if settings_crop.crop_min else min(spe.x)
                    )
                    print("Min val: ", min_val)

                    if set_default_btn:
                        callback_change_value("min_crop_input_neon", min_val)
                    # callback_change_value('min_crop_input', min_val)

                    min_val = st.number_input(
                        "Minimum Value:",
                        value=min_val,
                        format="%f",
                        key="min_crop_input_neon",
                        # disabled=not use_crop
                    )
                with col2:
                    max_val = (
                        settings_crop.crop_max if settings_crop.crop_max else max(spe.x)
                    )
                    # print('Max val: ', max_val)

                    if set_default_btn:
                        callback_change_value("max_crop_input_neon", max_val)
                    # callback_change_value('max_crop_input', max_val)

                    max_val = st.number_input(
                        "Maximum Value:",
                        value=max_val,
                        format="%f",
                        key="max_crop_input",
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

            # if submit_crop_btn:
            # spe_croped = spe.trim_axes(
            #     method="x-axis", boundaries=(min_val, max_val)
            # )

            if use_crop or submit_crop_btn:
                # if not submit_neon_crop_btn:
                spe_croped = spe.trim_axes(
                    method="x-axis", boundaries=(min_val, max_val)
                )
                # st.session_state["cache_dicts"]["spectra_x_current"][
                #     "neon"
                # ] = spe_croped
                # st.session_state["cache_dicts"]["spectra_x_last"]["neon"] = spe_croped

                # st.session_state["cache_dicts"]["spectra_x_crop"]["neon"] = spe_croped
                state_settings.crop = settings_crop

                # if use_crop or submit_neon_crop_btn:
                ax = spe_croped.plot(ax=ax, label="Neon crop", color="red")

            if submit_crop_btn:
                st.session_state["cache_dicts"]["spectra_x_last"]["neon"] = spe_croped

                st.session_state["cache_dicts"]["spectra_x_crop"]["neon"] = spe_croped

            fig = ax.get_figure()
            st.pyplot(fig)

            st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = (
                state_settings
            )

    with normalize_tn:
        if "neon" in st.session_state["cache_dicts"]["spectra_x"]:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
            spe_units = neon_spe.meta["units"]

            label, xlabel = "Neon", r"Raman shift [{}]".format(spe_units)
            ax = neon_spe.plot(label=label, linestyle="dashed")
            ax.set_xlabel(xlabel)
            # ax.set_ylabel("Neon", color="blue")

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"][
                "neon"
            ]
            # print('State_settings')
            # print(state_settings)

            settings_normalize: StateNormalize = state_settings.normalize

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key="normalize_neon_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

                if set_default_btn:
                    state_settings.normalize = default_state_neon.normalize
                    st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = (
                        state_settings
                    )
                    settings_normalize: StateCrop = state_settings.normalize

            with col1_up:
                if set_default_btn:
                    callback_change_value(
                        "normalize_neon_checkbox", settings_normalize.use_normalize
                    )

                use_normalize = st.checkbox(
                    key="normalize_neon_checkbox",
                    label="Use Min-max Normalization",
                    value=settings_normalize.use_normalize,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )

            if use_normalize:
                # spe_current = st.session_state["cache_dicts"]["spectra_x_current"][
                #     "neon"
                # ]
                spe_current = st.session_state["cache_dicts"]["spectra_x_last"]["neon"]

                neon_normalized_spe = spe_current.normalize()

                st.session_state["cache_dicts"]["spectra_x_normalized"]["neon"] = (
                    neon_normalized_spe
                )

                # st.session_state["cache_dicts"]["spectra_x_current"][
                #     "neon"
                # ] = neon_normalized_spe
                st.session_state["cache_dicts"]["spectra_x_last"]["neon"] = (
                    neon_normalized_spe
                )

                ax2 = ax.twinx()

                ax2 = neon_normalized_spe.plot(
                    ax=ax2,
                    # label='Neon normalized',
                    color="red",
                    # linestyle='dashed'
                )
                # ax2.set_ylabel("Neon normalized", color="red")

                red_patch = mpatches.Patch(color="blue", label="Neon")

                blue_patch = mpatches.Patch(color="red", label="Neon normalized")

                ax2.legend(handles=[red_patch, blue_patch])

                fig = ax2.get_figure()
                st.pyplot(fig)

            else:
                fig = ax.get_figure()
                st.pyplot(fig)

            print("Set Normalize End")
            print(settings_normalize)

            settings_normalize.use_normalize = use_normalize
            state_settings.normalize = settings_normalize
            st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = (
                state_settings
            )

    with peakfind_tn:
        if "neon" in st.session_state["cache_dicts"]["spectra_x"]:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"]
            spe_units = neon_spe.meta["units"]

            label, xlabel = "Neon", r"Raman shift [{}]".format(spe_units)

            fig, axs = plt.subplots(2, 1, sharex=True, figsize=(12, 10))

            ax = neon_spe.plot(ax=axs[0], label=label, linestyle="dashed")
            ax.set_xlabel(xlabel)
            # ax.set_ylabel('Neon', color='blue')

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"][
                "neon"
            ]
            print("State_settings")
            print(state_settings)

            settings_peak_find: StatePeakFind = state_settings.peak_find

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key="peakfind_neon_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

                if set_default_btn:
                    state_settings.peak_find = default_state_neon.peak_find
                    st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = (
                        state_settings
                    )
                    settings_peak_find: StatePeakFind = state_settings.peak_find

                    callback_change_value(
                        "neon_peak_find_checkbox", settings_peak_find.use_peak_find
                    )

                    callback_change_value(
                        "window_length_neon", settings_peak_find.value_wlen
                    )

                    callback_change_value("width_neon", settings_peak_find.value_width)
                    # callback_change_value(
                    #     "hht_chain_neon", settings_peak_find.value_hht_chain
                    # )
                    # callback_change_value(
                    #     "sharpening_neon", settings_peak_find.value_sharpening
                    # )
                    callback_change_value(
                        "prominence_neon", settings_peak_find.value_prominence
                    )
                    callback_change_value(
                        "strategy_neon", settings_peak_find.value_strategy
                    )

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

            # neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
            neon_spe = st.session_state["cache_dicts"]["spectra_x_last"]["neon"]

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
                        key="window_length_neon",
                        label="window length",
                        min_value=10,
                        max_value=800,
                        value=settings_peak_find.value_wlen,
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )
                    width = st.number_input(
                        key="width_neon",
                        label="width",
                        min_value=1,
                        max_value=10,
                        value=settings_peak_find.value_width,
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )
                # with col2:
                #     hht_chain = st.number_input(
                #         key="hht_chain_neon",
                #         label="hht_chain[int]",
                #         min_value=10,
                #         max_value=150,
                #         value=settings_peak_find.value_hht_chain,
                #         # on_change=update_x_calibration_btn("submitted_std1_btn"),
                #     )
                #     options_sharpening = ["hht", None]
                #     sharpening = st.selectbox(
                #         key="sharpening_neon",
                #         label="sharpening",
                #         options=options_sharpening,
                #         index=options_sharpening.index(
                #             settings_peak_find.value_sharpening
                #         ),
                #         # on_change=update_x_calibration_btn("submitted_std1_btn"),
                #     )
                with col2:
                    # NB: HHT CHain and SHARPENING --> To remove!!!
                    prominence = st.number_input(
                        key="prominence_neon",
                        label="prominence",
                        min_value=0.0,
                        max_value=500.0,
                        value=settings_peak_find.value_prominence,
                        step=0.001,
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )

                    options_strategy = [
                        "topo",
                        # "bayesian_gaussian_mixture",
                        "bgm",
                        # "cwt",
                    ]

                    # st.write(value_strategy)
                    strategy = st.selectbox(
                        key="strategy_neon",
                        label="strategy",
                        options=options_strategy,
                        index=options_strategy.index(settings_peak_find.value_strategy),
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )

            kwargs = {
                "wlen": wlen,
                "width": width,
                # "hht_chain": [hht_chain],
                "prominence": prominence * neon_spe.y_noise,  # .y_noise_MAD
                # "sharpening": sharpening,
                "strategy": strategy,
            }

            if use_peak_find or submit_find_peaks_neon_btn:
                neon_peak_candidates = neon_spe.find_peak_multipeak(**kwargs)

                # fig, ax = plt.subplots()

                neon_peak_candidates.plot(ax=axs[1], fmt=":", label="Neon peaks")
                axs[1].set_xlabel(xlabel)
                fig = axs[1].get_figure()

                st.download_button(
                    "Download Peaks found (JSON)",
                    data=neon_peak_candidates.json(),
                    file_name="neon_peaks_found.json",
                )

            if use_peak_find:
                st.session_state["cache_dicts"]["spectra_x_peak_candidates"]["neon"] = (
                    neon_peak_candidates
                )

                st.session_state["cache_dicts"]["spectra_x_current"][
                    "neon_kwargs_find_peak"
                ] = kwargs

            st.pyplot(fig)

            settings_peak_find.use_peak_find = use_peak_find
            # settings_peak_find.value_hht_chain = hht_chain
            settings_peak_find.value_prominence = prominence
            # settings_peak_find.value_sharpening = sharpening
            settings_peak_find.value_wlen = wlen
            settings_peak_find.value_width = width
            settings_peak_find.value_strategy = strategy

            state_settings.peak_find = settings_peak_find

    ################
    with peakfit_tn:
        if "spectra_x_last" in st.session_state["cache_dicts"]:
            use_peakfit = st.checkbox(
                key="neon_peak_fit_checkbox",
                label="Use Peak fit",
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )

            with st.form(key="neon_peakfit_form"):
                # if use_peakfit:
                col0, col1 = st.columns(2)
                with col0:
                    st.form_submit_button(
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

                # neon_spe = st.session_state["cache_dicts"][
                #     "spectra_x_current"
                # ]["neon"]

                if (
                    "neon"
                    in st.session_state["cache_dicts"]["spectra_x_peak_candidates"]
                    and "neon" in st.session_state["cache_dicts"]["spectra_x_last"]
                ):
                    # neon_spe = st.session_state["cache_dicts"]["spectra_x_current"][
                    #     "neon"
                    # ]
                    neon_spe = st.session_state["cache_dicts"]["spectra_x_last"]["neon"]

                    neon_peak_candidates = st.session_state["cache_dicts"][
                        "spectra_x_peak_candidates"
                    ]["neon"]

                    assert isinstance(use_peakfit, bool), use_peakfit

                    fitres = neon_spe.fit_peak_multimodel(
                        profile=profile,
                        candidates=neon_peak_candidates,
                        no_fit=not use_peakfit,
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

    if (
        "spectra_x_last" in st.session_state["cache_dicts"]
        and "neon" in st.session_state["cache_dicts"]["spectra_x_last"]
    ):
        st.session_state["cache_dicts"]["spectra_x_current"]["neon"] = st.session_state[
            "cache_dicts"
        ]["spectra_x_last"]["neon"]


def process_x_calibration_si_creation():

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

    # print("State settings si start..")
    # print(state_settings)
    # print('------ END ------')
    import time

    print("BEFORE TABS SI, --- time: {} ---------".format(time.strftime("%X %x %Z")))

    with load_ts:
        print("IN LOAD SI")

        load_calibration_spectrum_si()

        if "si" in st.session_state["cache_dicts"]["spectra_x"]:
            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            # st.session_state["cache_dicts"]["spectra_x_current"]["si"] = si_spe
            st.session_state["cache_dicts"]["spectra_x_last"]["si"] = st.session_state[
                "cache_dicts"
            ]["spectra_x"]["si"]
            simple_plot_spe(
                spe=si_spe, label="Si", xlabel=r"Raman shift [{}]".format(spe_units)
            )

    with crop_ts:
        print("IN CROP SI")
        if "si" in st.session_state["cache_dicts"]["spectra_x"]:
            print("INSIDE IF CROP")
            # st.session_state["cache_dicts"]["spectra_x"]["si"]
            si_spe = st.session_state["cache_dicts"]["spectra_x_last"]["si"]
            spe_units = si_spe.meta["units"]

            label, xlabel = "Si", r"Raman shift [{}]".format(spe_units)
            ax = si_spe.plot(label=label, linestyle="dashed", color="blue")
            ax.set_xlabel(xlabel)

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
            # print('state_settings in the beginning of crop')
            # print(state_settings)
            # print('--- == end == ----')
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
                    key="crop_si_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

            if set_default_btn:
                state_settings.crop = default_state_si.crop
                st.session_state["cache_dicts"]["spectrum_settings"]["si"] = (
                    state_settings
                )
                settings_crop: StateCrop = state_settings.crop

            # Create a form for the input fields and submit button
            with st.form(key="si_crop_form"):
                # Create two input columns and one submit-button column.
                # spe = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

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
                    min_val = (
                        settings_crop.crop_min
                        if settings_crop.crop_min
                        else min(spe_si.x)
                    )
                    print("Min val: ", min_val)

                    if set_default_btn:
                        callback_change_value("min_crop_input", min_val)
                    # callback_change_value('min_crop_input', min_val)

                    min_val = st.number_input(
                        "Minimum Value:",
                        value=min_val,
                        format="%f",
                        key="min_crop_input",
                        # disabled=not use_crop
                    )
                with col2:
                    max_val = (
                        settings_crop.crop_max
                        if settings_crop.crop_max
                        else max(spe_si.x)
                    )
                    print("Max val: ", max_val)

                    if set_default_btn:
                        callback_change_value("max_crop_input", max_val)
                    # callback_change_value('max_crop_input', max_val)

                    max_val = st.number_input(
                        "Maximum Value:",
                        value=max_val,
                        format="%f",
                        key="max_crop_input",
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

            # spe_croped = si_spe

            # if submit_si_crop_btn:

            spe_croped = si_spe.trim_axes(
                method="x-axis", boundaries=(min_val, max_val)
            )

            if use_crop:
                state_settings.crop = settings_crop
                st.session_state["cache_dicts"]["spectra_x_last"]["si"] = spe_croped
            else:
                st.session_state["cache_dicts"]["spectra_x_last"]["si"] = (
                    st.session_state["cache_dicts"]["spectra_x"]["si"]
                )

            if use_crop or submit_si_crop_btn:
                ax = spe_croped.plot(ax=ax, label="Si crop", color="red")

            fig = ax.get_figure()
            st.pyplot(fig)

            st.session_state["cache_dicts"]["spectrum_settings"]["si"] = state_settings

    with baseline_ts:
        print(" IN BASELINE ")

        #######
        if (
            "si" in st.session_state["cache_dicts"]["spectra_x"]
            and "si" in st.session_state["cache_dicts"]["spectra_x_last"]
        ):
            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            label, xlabel = "Si", r"Raman shift [{}]".format(spe_units)
            ax = si_spe.plot(label=label, linestyle="dashed")
            ax.set_xlabel(xlabel)
            # ax.set_ylabel("Si", color="blue")

            si_spe_current = st.session_state["cache_dicts"]["spectra_x_last"]["si"]

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
            # print("State_settings")
            # print(state_settings)

            settings_baseline: StateBaselineCorrection = state_settings.baseline_corr

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key="baseline_si_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

                if set_default_btn:
                    state_settings.baseline_corr = default_state_si.baseline_corr
                    st.session_state["cache_dicts"]["spectrum_settings"]["si"] = (
                        state_settings
                    )
                    settings_baseline: StateBaselineCorrection = (
                        state_settings.baseline_corr
                    )

            with col1_up:
                if set_default_btn:
                    callback_change_value(
                        "baseline_si_checkbox", settings_baseline.use_baseline_corr
                    )

                use_baseline = st.checkbox(
                    key="baseline_si_checkbox",
                    label="Use Baseline",
                    value=settings_baseline.use_baseline_corr,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )

            # Create a form for the input fields and submit button
            with st.form(key="si_baseline_form"):
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
                        callback_change_value("select_baseline_si", baseline_current)

                    # callback_change_value('min_crop_input', min_val)
                    options = [
                        "SNIP",
                        "ALS",
                        #    'MOVING_MING'
                    ]
                    baseline_current = settings_baseline.baseline_corr_type

                    baseline_corr = st.selectbox(
                        label="Select baseline correction",
                        key="select_baseline_si",
                        options=options,
                        index=options.index(baseline_current),
                        # on_change=callback_change_value,
                        # args=("baseline_corr_args", baseline_current),
                    )

                with col2:
                    if baseline_corr == "SNIP":
                        baseline_corr_class = SNIPBaselineArgs
                    elif baseline_corr == "ALS":
                        baseline_corr_class = ALSBaselineArgs
                    else:
                        st.error("Choose SNIP or ALS")

                    st.write("")
                    with st.expander(label="Baseline correction settings"):
                        if set_default_btn:
                            keys = [
                                k
                                for k in st.session_state.keys()
                                if "Baseline correction settings"
                            ]
                            for key in keys:
                                del st.session_state[key]

                        if baseline_corr == "SNIP":
                            niter = st.number_input(
                                "niter",
                                min_value=1,
                                value=30,
                                step=1,
                                key="baseline_snip_niter",
                            )
                            input_data = {"niter": int(niter)}
                        elif baseline_corr == "ALS":
                            niter = st.number_input(
                                "niter",
                                min_value=1,
                                value=30,
                                step=1,
                                key="baseline_als_niter",
                            )
                            lam = st.number_input(
                                "lam", min_value=0.0, value=1e5, key="baseline_als_lam"
                            )
                            p = st.number_input(
                                "p",
                                min_value=0.0,
                                max_value=1.0,
                                value=0.001,
                                format="%f",
                                key="baseline_als_p",
                            )
                            smooth = st.number_input(
                                "smooth",
                                min_value=1,
                                value=7,
                                step=2,
                                key="baseline_als_smooth",
                            )
                            input_data = {
                                "niter": int(niter),
                                "lam": float(lam),
                                "p": float(p),
                                "smooth": int(smooth),
                            }
                        else:
                            input_data = {"niter": 30}

                        niter = input_data["niter"]

                        args = baseline_corr_class(**input_data)

                if submit_si_baseline_btn or use_baseline:
                    if baseline_corr == "SNIP":
                        si_spe_baseline = si_spe_current
                        si_spe_baseline.y = si_spe_current.y - baseline_snip(
                            si_spe_current.y, niter=input_data["niter"]
                        )

                    elif baseline_corr == "ALS":
                        si_spe_baseline = si_spe_current
                        si_spe_baseline.y = si_spe_current.y - baseline_als(
                            si_spe_current.y, **input_data
                        )

                        # si_spe_baseline = si_spe_current - \
                        #     baseline_als(si_spe_current, **input_data)

                    else:
                        st.error("Choose SNIP or ALS")

                    ax = si_spe_baseline.plot(
                        ax=ax, label="Si baseline correction", color="red"
                    )

                    settings_baseline.use_baseline_corr = use_baseline
                    settings_baseline.baseline_corr_type = baseline_corr
                    settings_baseline.args = args
                    # fig = ax.get_figure()
                    # st.pyplot(fig)
                    # st.session_state["cache_dicts"]["spectra_x_baseline"][
                    #     "si"
                    # ] = si_spe_current

                if use_baseline:
                    state_settings.baseline_corr = settings_baseline
                    st.session_state["cache_dicts"]["spectra_x_last"]["si"] = (
                        si_spe_baseline
                    )

                    # if use_crop or submit_si_crop_btn:
                    #     ax = spe_croped.plot(ax=ax, label="Si crop", color='red')

            fig = ax.get_figure()
            st.pyplot(fig)

            # settings_baseline.use_baseline_corr = use_baseline
            # settings_baseline.baseline_corr_type = baseline_corr
            # settings_baseline.args = args
            # state_settings.baseline_corr = settings_baseline

            st.session_state["cache_dicts"]["spectrum_settings"]["si"] = state_settings

            ######
    with normalize_ts:
        print("IN NORMALIZE")

        if "si" in st.session_state["cache_dicts"]["spectra_x"]:
            assert "si" in st.session_state["cache_dicts"]["spectra_x_last"]

            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            label, xlabel = "Si", r"Raman shift [{}]".format(spe_units)
            ax = si_spe.plot(label=label, linestyle="dashed")
            ax.set_xlabel(xlabel)
            # ax.set_ylabel("Si", color="blue")

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
            # print("State_settings")
            # print(state_settings)

            settings_normalize: StateNormalize = state_settings.normalize

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key="normalize_si_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

                if set_default_btn:
                    state_settings.normalize = default_state_si.normalize
                    st.session_state["cache_dicts"]["spectrum_settings"]["si"] = (
                        state_settings
                    )
                    settings_normalize: StateCrop = state_settings.normalize

            with col1_up:
                if set_default_btn:
                    callback_change_value(
                        "normalize_si_checkbox", settings_normalize.use_normalize
                    )

                use_normalize = st.checkbox(
                    key="normalize_si_checkbox",
                    label="Use Min-max Normalization",
                    value=settings_normalize.use_normalize,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )

            # st.session_state["cache_dicts"]["spectra_x_last"]["si"] = si_spe

            if use_normalize:
                spe_current = st.session_state["cache_dicts"]["spectra_x_last"]["si"]

                si_normalized_spe = spe_current.normalize()

                st.session_state["cache_dicts"]["spectra_x_last"]["si"] = (
                    si_normalized_spe
                )

                # st.session_state["cache_dicts"]["spectra_x_current"][
                #     "si"
                # ] = si_normalized_spe

                ax2 = ax.twinx()

                ax2 = si_normalized_spe.plot(
                    ax=ax2,
                    # label='si normalized',
                    color="red",
                    # linestyle='dashed'
                )
                # ax2.set_ylabel("Si normalized", color="red")

                red_patch = mpatches.Patch(color="blue", label="Si")

                blue_patch = mpatches.Patch(color="red", label="Si normalized")

                ax2.legend(handles=[red_patch, blue_patch])

                fig = ax2.get_figure()
                st.pyplot(fig)

                settings_normalize.use_normalize = use_normalize
                state_settings.normalize = settings_normalize

            else:
                fig = ax.get_figure()
                st.pyplot(fig)

            # print("Set Normalize End")
            # print(settings_normalize)

            # settings_normalize.use_normalize = use_normalize
            # state_settings.normalize = settings_normalize
            st.session_state["cache_dicts"]["spectrum_settings"]["neon"] = (
                state_settings
            )

    with peakfind_ts:
        print("IN PEAKFIND")
        if "si" in st.session_state["cache_dicts"]["spectra_x"]:
            si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"]
            spe_units = si_spe.meta["units"]

            label, xlabel = "Si", r"Raman shift [{}]".format(spe_units)

            fig, axs = plt.subplots(2, 1, sharex=True, figsize=(12, 10))

            ax = si_spe.plot(ax=axs[0], label=label, linestyle="dashed")
            ax.set_xlabel(xlabel)
            # ax.set_ylabel('si', color='blue')

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["si"]
            # print("State_settings")
            # print(state_settings)

            settings_peak_find: StatePeakFind = state_settings.peak_find

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key="peakfind_si_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

                if set_default_btn:
                    state_settings.peak_find = default_state_si.peak_find
                    st.session_state["cache_dicts"]["spectrum_settings"]["si"] = (
                        state_settings
                    )
                    settings_peak_find: StatePeakFind = state_settings.peak_find

                    callback_change_value(
                        "si_peak_find_checkbox", settings_peak_find.use_peak_find
                    )

                    callback_change_value(
                        "window_length_si", settings_peak_find.value_wlen
                    )

                    callback_change_value("width_si", settings_peak_find.value_width)
                    # callback_change_value(
                    #     "hht_chain_si", settings_peak_find.value_hht_chain
                    # )
                    # callback_change_value(
                    #     "sharpening_si", settings_peak_find.value_sharpening
                    # )
                    callback_change_value(
                        "prominence_si", settings_peak_find.value_prominence
                    )
                    callback_change_value(
                        "strategy_si", settings_peak_find.value_strategy
                    )

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

            si_spe = st.session_state["cache_dicts"]["spectra_x_last"]["si"]

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
                        key="window_length_si",
                        label="window length",
                        min_value=10,
                        max_value=800,
                        value=settings_peak_find.value_wlen,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                    width = st.number_input(
                        key="width_si",
                        label="width",
                        min_value=1,
                        max_value=10,
                        value=settings_peak_find.value_width,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )
                # with col2:
                #     hht_chain = st.number_input(
                #         key="hht_chain_si",
                #         label="hht_chain[int]",
                #         min_value=10,
                #         max_value=150,
                #         value=settings_peak_find.value_hht_chain,
                #         # on_change=update_x_calibration_btn("submitted_std2_btn"),
                #     )
                #     options_sharpening = ["hht", None]
                #     sharpening = st.selectbox(
                #         key="sharpening_si",
                #         label="sharpening",
                #         options=options_sharpening,
                #         index=options_sharpening.index(
                #             settings_peak_find.value_sharpening
                #         ),
                #         # on_change=update_x_calibration_btn("submitted_std2_btn"),
                #     )
                with col2:
                    prominence = st.number_input(
                        key="prominence_si",
                        label="prominence",
                        min_value=0.0,
                        max_value=500.0,
                        value=settings_peak_find.value_prominence,
                        step=0.001,
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )

                    options_strategy = [
                        "topo",
                        # "bayesian_gaussian_mixture",
                        "bgm",
                        # "cwt",
                    ]

                    # st.write(value_strategy)
                    strategy = st.selectbox(
                        key="strategy_si",
                        label="strategy",
                        options=options_strategy,
                        index=options_strategy.index(settings_peak_find.value_strategy),
                        # on_change=update_x_calibration_btn("submitted_std2_btn"),
                    )

            kwargs = {
                "wlen": wlen,
                "width": width,
                # "hht_chain": [hht_chain],
                "prominence": prominence * si_spe.y_noise,
                # "sharpening": sharpening,
                "strategy": strategy,
            }

            if use_peak_find or submit_find_peaks_si_btn:
                si_peak_candidates = si_spe.find_peak_multipeak(**kwargs)

                # fig, ax = plt.subplots()

                si_peak_candidates.plot(ax=axs[1], fmt=":", label="Si peaks")
                axs[1].set_xlabel(xlabel)
                fig = axs[1].get_figure()

                st.download_button(
                    "Download Peaks found (JSON)",
                    data=si_peak_candidates.json(),
                    file_name="si_peaks_found.json",
                )

            if use_peak_find:
                st.session_state["cache_dicts"]["spectra_x_peak_candidates"]["si"] = (
                    si_peak_candidates
                )

                st.session_state["cache_dicts"]["spectra_x_current"][
                    "si_kwargs_find_peak"
                ] = kwargs

            st.pyplot(fig)

            # st.session_state["cache_dicts"]["spectra_x_peak_candidates"][
            #     "si"
            # ] = si_peak_candidates

            settings_peak_find.use_peak_find = use_peak_find
            # settings_peak_find.value_hht_chain = hht_chain
            settings_peak_find.value_prominence = prominence
            # settings_peak_find.value_sharpening = sharpening
            settings_peak_find.value_wlen = wlen
            settings_peak_find.value_width = width
            settings_peak_find.value_strategy = strategy

            state_settings.peak_find = settings_peak_find

    ################
    # NB!  NB to enable fit visualization!
    # NB (Use .... to have hint everywhere!!!)
    with peakfit_ts:
        print("IN PEAKFIT")
        if (
            "spectra_x_last" in st.session_state["cache_dicts"]
            and "si" in st.session_state["cache_dicts"]["spectra_x_last"]
        ):
            use_peakfit = st.checkbox(
                key="neon_peak_fit_checkbox",
                label="Use Peak fit",
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
                        # on_change=update_x_calibration_btn("submitted_std1_btn"),
                    )

                if (
                    submit_si_fitpeaks_btn
                    and "si"
                    in st.session_state["cache_dicts"]["spectra_x_peak_candidates"]
                    and "si" in st.session_state["cache_dicts"]["spectra_x_last"]
                ):
                    si_spe = st.session_state["cache_dicts"]["spectra_x_last"]["si"]

                    si_peak_candidates = st.session_state["cache_dicts"][
                        "spectra_x_peak_candidates"
                    ]["si"]

                    assert isinstance(use_peakfit, bool), use_peakfit

                    fitres = si_spe.fit_peak_multimodel(
                        profile=profile,
                        candidates=si_peak_candidates,
                        no_fit=not use_peakfit,
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
                    st.pyplot(fig)

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

    if (
        "spectra_x_last" in st.session_state["cache_dicts"]
        and "si" in st.session_state["cache_dicts"]["spectra_x_last"]
    ):
        st.session_state["cache_dicts"]["spectra_x_current"]["si"] = st.session_state[
            "cache_dicts"
        ]["spectra_x_last"]["si"]

    # st.session_state["cache_dicts"]["spectra_x_current"]["si"] = \
    #     st.session_state["cache_dicts"]["spectra_x_last"]["si"]


def upload_y_calibration_ref_spe():

    load_srm, crop_srm, smooth_srm = st.tabs(
        [
            "Load [Ref]",
            "Crop [Ref]",  # 'Baseline corr',
            "Smooth [Ref]",
        ]
    )

    if "srm_ref" in st.session_state["cache_dicts"]["spectrum_settings"]:
        state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["srm_ref"]
    else:
        st.session_state["cache_dicts"]["spectrum_settings"]["srm_ref"] = (
            default_state_srm_ref
        )

    state_settings = st.session_state["cache_dicts"]["spectrum_settings"]["srm_ref"]

    # print("State settings si start..")
    # print(state_settings)
    # print('------ END ------')
    import time

    print(
        "BEFORE TABS SRM REF, --- time: {} ---------".format(time.strftime("%X %x %Z"))
    )

    with load_srm:
        print("IN LOAD SRM REF")

        load_calibration_spectrum_srm_ref()

        if "srm_ref" in st.session_state["cache_dicts"]["spectra_y"]:
            srm_spe = st.session_state["cache_dicts"]["spectra_y"]["srm_ref"]
            spe_units = srm_spe.meta["units"]

            # st.session_state["cache_dicts"]["spectra_x_current"]["si"] = si_spe
            st.session_state["cache_dicts"]["spectra_y_last"]["srm_ref"] = (
                st.session_state["cache_dicts"]["spectra_y"]["srm_ref"]
            )
            simple_plot_spe(
                spe=srm_spe,
                label="Reference spectrum",
                xlabel=r"Raman shift [{}]".format(spe_units),
            )

    with crop_srm:
        print("IN CROP SRM REF")
        if "srm_ref" in st.session_state["cache_dicts"]["spectra_y"]:
            print("INSIDE IF CROP SRM REF")
            # st.session_state["cache_dicts"]["spectra_y"]["si"]
            srm_spe = st.session_state["cache_dicts"]["spectra_y_last"]["srm_ref"]
            spe_units = srm_spe.meta["units"]

            label, xlabel = "Reference spectrum", r"Raman shift [{}]".format(spe_units)
            ax = srm_spe.plot(label=label, linestyle="dashed", color="blue")
            ax.set_xlabel(xlabel)

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"][
                "srm_ref"
            ]

            # print('state_settings in the beginning of crop')
            # print(state_settings)
            # print('--- == end == ----')
            settings_crop: StateCrop = state_settings.crop

            col1_upn, col2_upn = st.columns([1, 1])
            with col1_upn:
                # callback_change_value(
                #     key="crop_neon_checkbox", value=settings_crop.use_crop)

                use_crop = st.checkbox(
                    key="crop_neon_checkbox",
                    label="Use crop",
                    value=settings_crop.use_crop,
                    on_change=update_x_calibration_btn(
                        "submitted_btn_srm_experimental"
                    ),
                )
            with col2_upn:
                set_default_btn = st.button(
                    key="crop_neon_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

            if set_default_btn:
                state_settings.crop = default_state_srm_ref.crop
                st.session_state["cache_dicts"]["spectrum_settings"]["srm_ref"] = (
                    state_settings
                )
                settings_crop: StateCrop = state_settings.crop

            # Create a form for the input fields and submit button
            with st.form(key="srm_crop_form"):
                # Create two input columns and one submit-button column.
                # spe = st.session_state["cache_dicts"]["spectra_y_current"]["neon"]
                spe = st.session_state["cache_dicts"]["spectra_y_last"]["srm_ref"]

                col0, col1, col2 = st.columns([0.5, 1, 1])

                with col0:
                    # This is to adjust the position of the button
                    st.write("")
                    submit_neon_crop_btn = st.form_submit_button(
                        label="Update",
                        #   disabled=not use_crop
                    )

                with col1:
                    min_val = (
                        settings_crop.crop_min if settings_crop.crop_min else min(spe.x)
                    )
                    print("Min val: ", min_val)

                    if set_default_btn:
                        callback_change_value("min_crop_input_srm", min_val)
                    # callback_change_value('min_crop_input', min_val)

                    min_val = st.number_input(
                        "Minimum Value:",
                        value=min_val,
                        format="%f",
                        key="min_crop_input_srm",
                        # disabled=not use_crop
                    )
                with col2:
                    max_val = (
                        settings_crop.crop_max if settings_crop.crop_max else max(spe.x)
                    )
                    # print('Max val: ', max_val)

                    if set_default_btn:
                        callback_change_value("max_crop_input_srm", max_val)
                    # callback_change_value('max_crop_input', max_val)

                    max_val = st.number_input(
                        "Maximum Value:",
                        value=max_val,
                        format="%f",
                        key="max_crop_input_srm",
                        # disabled=not use_crop
                    )

            # Check if the form is submitted
            # if True:  # submit_neon_crop_btn:
            if min_val > max_val:
                st.error("Minimum value cannot be greater than Maximum value.")
            # else:

            update_x_calibration_btn("submitted_btn_srm_experimental")
            # st.success(f"Range set from {min_val} to {max_val}")
            settings_crop.use_crop = use_crop
            settings_crop.crop_min = min_val
            settings_crop.crop_max = max_val

            if submit_neon_crop_btn:
                spe_croped = spe.trim_axes(
                    method="x-axis", boundaries=(min_val, max_val)
                )

            if use_crop:
                # if not submit_neon_crop_btn:
                spe_croped = spe.trim_axes(
                    method="x-axis", boundaries=(min_val, max_val)
                )
                # st.session_state["cache_dicts"]["spectra_y_current"][
                #     "neon"
                # ] = spe_croped
                st.session_state["cache_dicts"]["spectra_y_last"]["srm_ref"] = (
                    spe_croped
                )

                st.session_state["cache_dicts"]["spectra_y_crop"]["srm_ref"] = (
                    spe_croped
                )
                state_settings.crop = settings_crop

            if use_crop or submit_neon_crop_btn:
                ax = spe_croped.plot(ax=ax, label="Ref crop", color="red")

            fig = ax.get_figure()
            st.pyplot(fig)

            st.session_state["cache_dicts"]["spectrum_settings"]["srm_ref"] = (
                state_settings
            )

    with smooth_srm:
        print("IN NORMALIZE")

        if "srm_ref" in st.session_state["cache_dicts"]["spectra_y"]:
            assert "srm_ref" in st.session_state["cache_dicts"]["spectra_y_last"]

            srm_spe = st.session_state["cache_dicts"]["spectra_y"]["srm_ref"]
            spe_units = srm_spe.meta["units"]

            label, xlabel = "Reference spectrum", r"Raman shift [{}]".format(spe_units)
            ax = srm_spe.plot(label=label, linestyle="dashed", color="blue")
            ax.set_xlabel(xlabel)
            # ax.set_ylabel("Si", color="blue")

            state_settings = st.session_state["cache_dicts"]["spectrum_settings"][
                "srm_ref"
            ]

            settings_smooth: StateSmooth = state_settings.smooth

            col1_up, col2_up = st.columns([1, 1])

            with col2_up:
                set_default_btn = st.button(
                    key="smooth_srm_default_btn",
                    label="Reset Settings",
                    help="Reset default values of all settings",
                )

                if set_default_btn:
                    state_settings.smooth = default_state_srm_ref.smooth

                    st.session_state["cache_dicts"]["spectrum_settings"]["srm_ref"] = (
                        state_settings
                    )
                    settings_smooth: StateSmooth = state_settings.smooth

            with col1_up:
                if set_default_btn:
                    callback_change_value(
                        "smooth_srm_checkbox", settings_smooth.use_smooth
                    )
                print("settings smooth: ")
                print(settings_smooth)

                use_smooth = st.checkbox(
                    key="smooth_srm_checkbox",
                    label="Use Smoothing",
                    value=settings_smooth.use_smooth,
                    on_change=update_x_calibration_btn(
                        "submitted_btn_srm_experimental"
                    ),
                )
                method_options = [
                    "savgol",
                    "wiener",
                    "median",
                    "gauss",
                    "lowess",
                    "boxcar",
                ]

            with st.form("srm_ref_form"):
                col0, col1, col3 = st.columns([1, 2, 2])

                with col0:
                    # This is to adjust the position of the button
                    st.write("")
                    btn_update_srm_form = st.form_submit_button(
                        label="Update",
                        #   disabled=not use_crop
                    )

                with col1:
                    index_method = method_options.index(settings_smooth.method)

                    if set_default_btn:
                        index_method = method_options.index(settings_smooth.method)
                        callback_change_value(
                            "select_box_srm_method", default_state_srm_ref.smooth.method
                        )

                    method = st.selectbox(
                        label="Select method (and Update)",
                        key="select_box_srm_method",
                        options=method_options,
                        index=index_method,
                    )
                kwargs = {}
                with col3:
                    # st.write(method)
                    if method == "savgol":
                        # st.write('savgolll')
                        col_window_l, col_polyorder = st.columns([1, 1])
                        with col_window_l:
                            savgol_window_length = st.number_input(
                                label="window length",
                                min_value=2,
                                max_value=31,
                                value=settings_smooth.savgol_window_length,
                            )

                            # st.write('savgol')
                        with col_polyorder:
                            savgol_polyorder = st.number_input(
                                label="polyorder",
                                min_value=1,
                                max_value=7,
                                value=settings_smooth.savgol_polyorder,
                            )
                        kwargs = {
                            "window_length": savgol_window_length,
                            "polyorder": savgol_polyorder,
                        }

            if btn_update_srm_form or use_smooth:
                spe_smooth = srm_spe.smoothing_RC1(method=method, **kwargs)

                if use_smooth:
                    st.session_state["cache_dicts"]["spectra_y_last"]["srm_ref"] = (
                        spe_smooth
                    )

                ax2 = ax.twinx()

                ax2 = spe_smooth.plot(
                    ax=ax2,
                    color="red",
                )

                red_patch = mpatches.Patch(color="blue", label="Reference spectrum")

                blue_patch = mpatches.Patch(color="red", label="Ref smooth")

                ax2.legend(handles=[red_patch, blue_patch])

                fig = ax2.get_figure()
                st.pyplot(fig)

                settings_smooth.use_smooth = use_smooth
                state_settings.smooth = settings_smooth

            else:
                fig = ax.get_figure()
                st.pyplot(fig)

            state_settings.smooth = settings_smooth

            st.session_state["cache_dicts"]["spectrum_settings"]["srm_ref"] = (
                state_settings
            )

    if (
        "spectra_y_last" in st.session_state["cache_dicts"]
        and "srm_ref" in st.session_state["cache_dicts"]["spectra_y_last"]
    ):
        st.session_state["cache_dicts"]["spectra_y_current"]["srm_ref"] = (
            st.session_state["cache_dicts"]["spectra_y_last"]["srm_ref"]
        )


def update_x_calibration_btn(value):
    def update_x_calibraiton_val():
        st.session_state["cache_strings"]["x_calibration_"] = value

    return update_x_calibraiton_val


with st.sidebar:
    # st.sidebar.image("./src/front_end/images/logo_charisma.jpg")
    # st.header("AI data extractor")
    calibration_choice_ = st.session_state["cache_strings"].get(
        "calibration_choice", "Create Calibration"
    )

    calibration_choices = ["Load Calibration", "Create Calibration"]
    assert calibration_choice_ in calibration_choices, (
        calibration_choice_,
        calibration_choices,
    )

    # if (
    #     "settings"
    #     not in st.session_state["cache_dicts"]["instrument_settings"]
    # ):
    #     st.error("Set Instrument settings first")

    instrument_settings = st.session_state["cache_dicts"]["instrument_settings"].get(
        "settings", None
    )
    if instrument_settings is None:
        st.error("ERROR: Set Instrument settings first")
    else:
        st.write("-----  Instrument settings -----")
        for key, value in instrument_settings.items():
            if key in [
                # "make_and_model_of_the_instrument",
                # "serial_number_of_the_instrument",
                "laser_wavelength",
            ]:
                st.sidebar.write(f"{key}: {value}")
            # st.write(instrument_settings)
        st.write("------------------------")

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
        create_x_calibration_sidebar_expander()

        create_y_calibration_sidebar_expander()


if st.session_state["cache_strings"]["x_calibration_"]:
    print("in IF...")
    st.session_state["cache_strings"]["x_calibration"] = st.session_state[
        "cache_strings"
    ]["x_calibration_"]
    st.session_state["cache_strings"]["x_calibration_"] = None

x_calib_btn = st.session_state["cache_strings"]["x_calibration"]


if x_calib_btn == "uploaded_x_calibration_btn":
    xcalibration_model = st.session_state["cache_dicts"]["x_calibration"][
        "xcalibration_model"
    ]

    fig, ax = plt.subplots(1, 1, sharex=False, figsize=(12, 10))

    xcalibration_model.plot(ax=ax)

    red_patch = mpatches.Patch(color="blue", label="Neon peaks")
    blue_patch = mpatches.Patch(color="red", label="Neon reference")

    ax.legend(handles=[red_patch, blue_patch])

    st.pyplot(fig)


elif x_calib_btn == "submitted_std1_btn":
    # st.write(' in elif x_calib_btn std1')
    process_x_calibration_neon_creation()

elif x_calib_btn == "submitted_std2_btn":
    process_x_calibration_si_creation()
    ###################################################

elif x_calib_btn in ["btn_derive_x_calibration_curve", "btn_lazer_zeroing"]:
    neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]

    settings = st.session_state["cache_dicts"]["instrument_settings"]["settings"]
    laser_wl = settings["laser_wavelength"]

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

    ref_spe = rc2const.NEON_WL[laser_wl]

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

    st.session_state["cache_dicts"]["x_calibration"]["xcalibration_component_neon"] = (
        calibration_component_neon
    )

    if x_calib_btn == "btn_derive_x_calibration_curve":
        fig, ax = plt.subplots(1, 1, sharex=False, figsize=(12, 10))

        calmodel.plot(ax=ax)

        red_patch = mpatches.Patch(color="blue", label="Neon peaks")
        blue_patch = mpatches.Patch(color="red", label="Neon reference")

        ax.legend(handles=[red_patch, blue_patch])

        st.pyplot(fig)

    elif x_calib_btn == "btn_lazer_zeroing":
        if "xcalibration_model" not in st.session_state["cache_dicts"]["x_calibration"]:
            st.error("First derive calibration model: CalibrationModel(laser_wl)")
        else:
            calmodel = st.session_state["cache_dicts"]["x_calibration"][
                "xcalibration_model"
            ]

        if (
            "xcalibration_component_neon"
            not in st.session_state["cache_dicts"]["x_calibration"]
        ):
            st.error("First save xcalibration component Neon")
        else:
            calibration_component = st.session_state["cache_dicts"]["x_calibration"][
                "xcalibration_component_neon"
            ]

        find_kw_si = {}
        if (
            "si_kwargs_find_peak"
            in st.session_state["cache_dicts"]["spectra_x_current"]
        ):
            find_kw_si = st.session_state["cache_dicts"]["spectra_x_current"][
                "si_kwargs_find_peak"
            ]
        fit_kw_si = {}
        if "si_kwargs_fit_peak" in st.session_state["cache_dicts"]["spectra_x_current"]:
            fit_kw_si = st.session_state["cache_dicts"]["spectra_x_current"][
                "si_kwargs_fit_peak"
            ]

        spe_si = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

        si_not_processed: bool = st.session_state["cache_bools"]["si_not_processed"]

        # if si_not_processed:
        spe_si_new = calibration_component.process(
            spe_si, spe_si.meta["units"], convert_back=False
        )

        # print("find_kw_si ", find_kw_si)
        # print("fit_kw_si ", fit_kw_si)

        spe_sil_ne_calib = spe_si_new

        st.session_state["cache_dicts"]["x_calibration"]["spe_sil_ne_calib"] = (
            spe_sil_ne_calib
        )

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
        st.session_state["cache_dicts"]["x_calibration"]["xcalibration_model"] = (
            calmodel
        )

        # else:

        #     calmodel = st.session_state["cache_dicts"]["x_calibration"][
        #         "xcalibration_model"
        #     ]

        #     st.session_state["cache_bools"]["si_not_processed"] = False

        # spe_si = st.session_state["cache_dicts"]["spectra_x_current"]["si"]

        fig, axes = plt.subplots(2, 1, sharex=False, figsize=(12, 10))

        calmodel.plot(ax=axes[0])

        red_patch = mpatches.Patch(color="blue", label="Neon peaks")
        blue_patch = mpatches.Patch(color="red", label="Neon reference")

        axes[0].legend(handles=[red_patch, blue_patch])

        spe_si.plot(ax=axes[1], label="Si processed", color="blue")
        si_units = spe_si.meta["units"]

        si_calibrated = apply_calibration_x(calmodel, spe_si, si_units)

        si_calibrated.plot(ax=axes[1], color="orange", label="Si calibrated")
        axes[1].legend()
        axes[1].set_xlabel(r"Raman shift " + si_units)
        axes[1].set_xlim(520.45 - 50, 520.45 + 50)

        st.pyplot(fig)


elif x_calib_btn == "btn_save_x_calibration":
    st.write("SAVE X-Calibraiton")

    if "xcalibration_model" not in st.session_state["cache_dicts"]["x_calibration"]:
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

        st.write("Saved X-calibration model in ", "./data/" + xcalibration_filename)


elif x_calib_btn == "btn_save_material_certificate":
    certificate_data: YCalibrationCertificate = st.session_state["cache_dicts"][
        "y_calib"
    ]["material_certificate"]
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


elif x_calib_btn == "submitted_btn_srm_experimental":
    upload_y_calibration_ref_spe()

    # reference_spe_xcalibrated = st.session_state["cache_dicts"]["spectra_x_current"][
    #     "neon"
    # ]
elif x_calib_btn == "btn_derive_y_calibration":
    # laser_wl = ycertificate_data.wavelength
    # if "settings" not in st.session_state["cache_dicts"]["instrument_settings"]:
    #     st.error("Set laser wavelength from Instrument settings page")

    # instrument_settings = st.session_state["cache_dicts"]["instrument_settings"][
    #     "settings"]

    # lazer_wavelength = instrument_settings["laser_wavelength"]

    # ycertificate_data: YCalibrationCertificate = st.session_state[
    #     "cache_dicts"]["y_calib"]["material_certificate"]

    # spe_srm = st.session_state["cache_dicts"]["spectra_y_current"]["srm_ref"]

    # ycal = YCalibrationComponent(laser_wl=lazer_wavelength,
    #                              reference_spe_xcalibrated=spe_srm,
    #                              certificate=ycertificate_data)

    # st.session_state["cache_dicts"]["y_calibration"]["ycalibration_model"]

    ycalmodel = st.session_state["cache_dicts"]["y_calibration"]["ycalibration_model"]
    spe_srm_original = st.session_state["cache_dicts"]["spectra_y"]["srm_ref"]
    spe_srm = st.session_state["cache_dicts"]["spectra_y_current"]["srm_ref"]

    # with st.form("derive_y_calibration"):
    # col_srm, col1, col2 = st.columns([1, 1, 1])
    # with col_srm:
    # btn_download_srm = st.button("Download SRM Experimental")

    # fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    ax = spe_srm_original.plot(label="Reference original", color="blue")

    ax = spe_srm.plot(ax=ax, label="Reference spectrum", color="red")

    ax.legend(loc="upper left")

    certificate_data: YCalibrationCertificate = st.session_state["cache_dicts"][
        "y_calib"
    ]["material_certificate"]

    ax_twin = ax.twinx()
    ax = certificate_data.plot(
        # label="Theoretical spectrum",
        color="green",
        ax=ax_twin,
    )
    ax_twin.legend(loc="upper right")

    fig = ax.get_figure()
    st.pyplot(fig)

    # st.write("Y Calibration component derived")

    y_calib_string = """>>> laser_wl = 785
        >>> ycert = YCalibrationCertificate.load(wavelength=785, key="SRM2241")
        theoretical from certificate / experimental from file spe
        >>> ycal = YCalibrationComponent(
        ...     laser_wl,
        ...     reference_spe_xcalibrated=spe_srm,
        ...     certificate=ycert,
        ... )
        >>> fig, ax = plt.subplots(1, 1, figsize=(15,4))
        >>> spe_srm.plot(ax=ax)
        >>> spe_to_correct.plot(ax=ax)
        >>> spe_ycalibrated = ycal.process(spe_to_correct)
        >>> spe_ycalibrated.plot(label="y-calibrated",color="green",ax=ax.twinx())


        !!!NB  Give the option to reverse X-Y Calibration to think about it!!!

        !!! Think about save / load Y-calibration - to be developed!
        """

    nb_str = """
    NB! Signal to noise ratio to be added - (Enrique)
    NB! Dark background - to be extracted

    """
    # st.write(y_calib_string)
else:
    pass

# main_page()
