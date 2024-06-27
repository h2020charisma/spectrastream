#!/usr/bin/env python3
from collections import defaultdict

import pandas as pd

import streamlit as st
from front_end.htmlTemplates import css

# st.set_page_config(
#     page_title="Raman spectroscopy harmonisation",
#     page_icon="./front_end/images/logo_charisma.jpg",
#     layout="wide",
# )
from modules.navigation_bar import navbar

from ramanchada2.protocols.calibration import CalibrationModel

from util import plot_original_x_calib_spe, process_file_spe

# with st.sidebar:

#     st.sidebar.image("./front_end/images/logo_charisma.jpg")


navbar()

st.write(css, unsafe_allow_html=True)


def page_SEARCH_or_UPLOAD_spectra():
    query_spectra = st.session_state["cache_strings"]["query_spectra"]
    # st.write('Query spectra...')
    st.write(query_spectra)
    st.session_state["cache_dicts"]["input_files"] = {
        "STD1": "Standard 1 spectra loaded",
        "STD2": "Standard 2 spectra loaded",
    }
    st.write("HERE IS THE SPECTRA SEARCHED RESULTS...")


def page_init_X_Calibration():
    input_files_dict = st.session_state["cache_dicts"]["input_files"]
    if not input_files_dict:
        st.write("You have not choosen spectra to process...")
    else:
        st.write("Process Spectra files")


def page_call_STD1_X_Calibration():
    # if st.session_state.cache_bools["submitted_std1_btn"] == True:
    #     st.write(
    #         "Graph with matched Neon (standard 1) peak "
    #         "for deriving the calibration curve..."
    #     )
    pass


def page_call_STD2_X_Calibration():

    if st.session_state.cache_bools["submitted_std2_btn"]:
        st.write("Graph: Lazer zeroing step using Si (standard 2)...")


# st.set_page_config(
#     page_title="Raman spectroscopy harmonisation",
#     page_icon="./front_end/images/logo_charisma.jpg",
#     layout="wide",
# )


def main():

    st.markdown("### Raman spectroscopy harmonisation")

    if "cache_bools" not in st.session_state:
        st.session_state["cache_bools"] = defaultdict(bool)
    if "cache_strings" not in st.session_state:
        st.session_state["cache_strings"] = defaultdict(str)
    if "cache_numbers" not in st.session_state:
        st.session_state["cache_numbers"] = defaultdict(float)
    if "cache_dfs" not in st.session_state:
        st.session_state["cache_dfs"] = defaultdict(pd.DataFrame)

    if "cache_dicts" not in st.session_state:
        st.session_state["cache_dicts"] = defaultdict(dict)

    plc_x_calibration = st.empty()

    with st.sidebar:

        # st.sidebar.image("./src/front_end/images/logo_charisma.jpg")
        # st.header("AI data extractor")

        st.session_state["cache_dicts"]["x_calibration"] = ""

        with st.expander("Load spectra files", expanded=False):

            # with st.form("Choose Spectra"):
            #     query_spectra = st.text_input(
            #         "Search for existing spectrum", "")
            #     st.session_state["cache_strings"][
            #         "query_spectra"
            #     ] = query_spectra.strip()

            #     submitted_btn_search_spec = st.form_submit_button("Run")
            #     # st.session_state['cache_dicts']['submitted_btn_upload_spec'] = ''

            #     if submitted_btn_search_spec:

            #         st.session_state["cache_strings"][
            #             "x_calibration"
            #         ] = "submitted_btn_search_spec"

            calibration_choice = st.radio(
                "Choose option",
                ["X-calibration", "Y-calibration"],
                index=None,
            )

            with st.form("Load Spectra"):

                # st.session_state['cache_strings']['x_calibration']
                if calibration_choice == "X-calibration":
                    uploaded_neon_spec = st.file_uploader(
                        "Load Neon spectra file", accept_multiple_files=False
                    )

                    uploaded_si_spec = st.file_uploader(
                        "Load Si spectra file", accept_multiple_files=False
                    )

                    # st.session_state["cache_strings"]["x_calibration"] = ""

                # st.write(calibration_choice)
                submitted_btn_spec = st.form_submit_button("Load spectra")

                if submitted_btn_spec:
                    if calibration_choice == "X-calibration":
                        # st.write('Calib: ', calibration_choice)

                        st.session_state["cache_dicts"]["spectra_x"]["neon"] = (
                            process_file_spe([uploaded_neon_spec], label="Neon")
                        )

                        st.session_state["cache_dicts"]["spectra_x"]["si"] = (
                            process_file_spe([uploaded_si_spec], label="Si")
                        )
                    # st.session_state["cache_strings"]["x_calibration"]
                    # st.write("SUBMIT LOAD")
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_btn_x_spec_upload"

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

    # st.write(st.session_state['cache_dicts']['spectra_x'])

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

    # with st.sidebar:
    #     with st.expander("Load Calibration", expanded=False):
    #         with st.form("Load Calibration"):

    #             uploaded_calibration = st.file_uploader(
    #                 "Load Calibration", accept_multiple_files=False
    #             )
    #             # st.session_state["cache_dicts"]["input_files"].update(
    #             #     {"calibration": [uploaded_calibration]}
    #             # )

    #             st.session_state["cache_strings"][
    #                 "load_calibration"
    #             ] = ""

    #             submitted_btn_load_calibration = st.form_submit_button(
    #                 "Submit calibration"
    #             )
    #             if submitted_btn_load_calibration:

    #                 st.session_state["cache_strings"][
    #                     "x_calibration"
    #                 ] = "load_calibration"

    # with st.sidebar:
    #     with st.expander("Search Calibration", expanded=False):

    #         with st.form("Search Calibration"):
    #             st.write("Search Calibration....")

    #             x_calib_search = st.text_input(
    #                 "Search for existing spectrum", "")
    #             st.session_state["cache_strings"][
    #                 "x_calibration_search"
    #             ] = x_calib_search.strip()

    #             submitted_btn_calibration_search = st.form_submit_button("Run")
    #             if submitted_btn_calibration_search:
    #                 st.session_state["cache_strings"][
    #                     "x_calibration"
    #                 ] = "submitted_btn_calibration_search"

    #                 page_call_STD1_X_Calibration()

    with st.sidebar:
        with st.expander("Create X-Calibration", expanded=False):

            with st.form("STD1 Process"):
                # st.write("Neon STD1 setup....")

                # if (st.session_state["cache_strings"][
                #         "x_calibration_"] == "submitted_std1_btn_"):
                # st.session_state["cache_strings"][
                #     "x_calibration"
                # ] = ""

                submitted_btn_st1 = st.form_submit_button("Process Neon spe")
                if submitted_btn_st1:
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_std1_btn"

                    page_call_STD1_X_Calibration()

            with st.form("STD2 Process"):
                # st.write("Si STD2 setup....")

                submitted_btn_st2 = st.form_submit_button("Process Si spe")
                if submitted_btn_st2:
                    # st.session_state.cache_bools['submitted_std2_btn'] = True
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_std2_btn"
                    page_call_STD2_X_Calibration()

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

    with st.sidebar:
        with st.expander("Create Y-Calibration", expanded=False):

            # st.session_state['cache_strings']['x_calibration'] = st.radio(
            #     "Choose option",
            #     ["Search X-calibration", "Create X-calibration"],
            #     index=None,
            # )

            with st.form("SRM experimental"):
                st.write("SRM Experimental spectrum")

                submitted_btn_srm_experimental = st.form_submit_button(
                    "SRM Experimental"
                )
                if submitted_btn_srm_experimental:
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_btn_srm_experimental"

                    # page_call_STD1_X_Calibration()

            with st.form("SRM theoretical"):
                st.write("SRM Theoretical spectrum")

                submitted_btn_srm_theoretical = st.form_submit_button("SRM Theoretical")
                if submitted_btn_srm_theoretical:
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_btn_srm_theoretical"

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

    import matplotlib.pyplot as plt

    if st.session_state["cache_strings"]["x_calibration_"]:
        print("in IF...")
        st.session_state["cache_strings"]["x_calibration"] = st.session_state[
            "cache_strings"
        ]["x_calibration_"]
        st.session_state["cache_strings"]["x_calibration_"] = None

    x_calib_btn = st.session_state["cache_strings"]["x_calibration"]
    # st.write("x_calib_btn")
    # st.write(x_calib_btn)

    # print('x_calibration_')
    # print(st.session_state["cache_strings"]["x_calibration_"])
    # print('x_calibration')
    # print(st.session_state["cache_strings"]["x_calibration"])

    if x_calib_btn == "submitted_btn_x_spec_upload":
        # st.write("LOAD Spectra..")
        neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"][0]
        # plot_original_x_calib_spe(neon_spe, neon_spe.meta['label'])
        si_spe = st.session_state["cache_dicts"]["spectra_x"]["si"][0]
        # plot_original_x_calib_spe(si_spe, neon_spe.meta['label'])
        fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
        fig.set_size_inches(30, 16)
        ax2.set_xlabel(r"Raman shift [$\mathrm{cm}^{-1}$]")
        neon_spe.plot(ax=ax1, label="Neon")
        si_spe.plot(ax=ax2, label="Si")
        st.pyplot(fig)

    elif x_calib_btn == "submitted_btn_search_spec":
        plc_x_calibration.image("src/data/images/screenshot_search_spectra01.png")
        # plc_x_calibration.write(st.session_state['cache_strings']['query_spectra'])

    elif x_calib_btn == "submitted_btn_calibration_search":
        # plc_x_calibration.write(st.session_state['cache_strings']['x_calibration_search'])

        plc_x_calibration.image("src/data/images/screenshot_search_x_calibration01.png")
        # plc_x_calibration.write('src/data/images/screenshot_search_x_calibration01.png')

    elif x_calib_btn == "show_instrument":
        plc_x_calibration.write(
            "Show Instrument  (e.g. Instrument recognized from Spectrum  metadata)"
        )
    elif x_calib_btn == "select_instrument":
        plc_x_calibration.write("Select / search an instrument")

    elif x_calib_btn == "load_calibration":
        plc_x_calibration.write(
            "Select user specified path and load calibration from file"
        )

    elif x_calib_btn == "submitted_std1_btn":
        # st.write(' in elif x_calib_btn std1')
        load_tn, baseline_tn, normalize_tn, peakfind_tn, peakfit_tn = st.tabs(
            ["Load spe", "Baseline corr", "Normalize", "Peak find", "Peak fitting"]
        )
        with load_tn:
            neon_spe = st.session_state["cache_dicts"]["spectra_x"]["neon"][0]
            st.session_state["cache_dicts"]["spectra_x_current"]["neon"] = neon_spe

            fig, ax = plt.subplots(figsize=(30, 15))
            neon_spe.plot(ax=ax, label="Neon")
            st.pyplot(fig)
            # plot_original_x_calib_spe(
            #     neon_spe, label=neon_spe.meta['label'])

        # st.write(st.session_state['cache_strings']['x_calibration_search'])
        with baseline_tn:
            use_baseline_corr = st.checkbox(
                label="Use baseline correction",
                on_change=update_x_calibration_btn("submitted_std1_btn"),
            )

            st.session_state["cache_dicts"]["spectra_x_use_baseline_corr"][
                "neon"
            ] = use_baseline_corr

            moving_min_val = st.slider(
                label="Moving min",
                min_value=1,
                max_value=10,
                value=2,
                on_change=update_x_calibration_btn("submitted_std1_btn"),
                disabled=(not use_baseline_corr),
            )

            neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
            # st.session_state["cache_dicts"]['spectra_x']['neon'][0]
            neon_baseline_corr_spe = neon_spe - neon_spe.moving_minimum(moving_min_val)
            st.session_state["cache_dicts"]["spectra_x_baseline_corr"][
                "neon"
            ] = neon_baseline_corr_spe
            if use_baseline_corr:
                st.session_state["cache_dicts"]["spectra_x_current"][
                    "neon"
                ] = neon_baseline_corr_spe
            # plot_original_x_calib_spe(neon_baseline_corr_spe,
            #                           label=neon_baseline_corr_spe.meta['label'])
            fig, ax = plt.subplots(figsize=(30, 12))
            neon_baseline_corr_spe.plot(ax=ax)
            st.pyplot(fig)
            # si_spe = st.session_state["cache_dicts"]['spectra_x']['si'][0]
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
            col1, col2, col3 = st.columns(3)
            with col1:
                wlen = st.number_input(
                    label="wlen",
                    min_value=10,
                    max_value=800,
                    value=200,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )
                width = st.number_input(
                    label="width",
                    min_value=1,
                    max_value=10,
                    value=2,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )
            with col2:
                hht_chain = st.number_input(
                    label="hht_chain[int]",
                    min_value=10,
                    max_value=150,
                    value=80,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )
            with col3:
                sharpening = st.selectbox(
                    label="sharpening",
                    options=["hht", None],
                    index=1,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )
                strategy = st.selectbox(
                    label="strategy",
                    options=["topo", "bayesian_gaussian_mixture", "bgm", "cwt"],
                    index=0,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )
            kwargs = {
                "wlen": wlen,
                "width": width,
                "hht_chain": [hht_chain],
                "sharpening": sharpening,
                "strategy": strategy,
            }
            neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
            neon_peak_candidates = neon_spe.find_peak_multipeak(**kwargs)

            st.session_state["cache_dicts"]["spectra_x_peak_candidates"][
                "neon"
            ] = neon_peak_candidates

            fig, ax = plt.subplots(figsize=(30, 10))
            neon_peak_candidates.plot(ax=ax, fmt=":")

            st.pyplot(fig)

        with peakfit_tn:
            col1, col2, col3 = st.columns(3)
            with col1:
                profile = st.selectbox(
                    label="Profile",
                    options=[
                        "Moffat",
                        "Gaussian",
                        "Lorentzian",
                        "Voigt",
                        "PseudoVoigt",
                        "Pearson4",
                        "Pearson7",
                    ],
                    index=0,
                    on_change=update_x_calibration_btn("submitted_std1_btn"),
                )
            neon_spe = st.session_state["cache_dicts"]["spectra_x_current"]["neon"]
            neon_peak_candidates = st.session_state["cache_dicts"][
                "spectra_x_peak_candidates"
            ]["neon"]
            fitres = neon_spe.fit_peak_multimodel(
                profile=profile, candidates=neon_peak_candidates, no_fit=True
            )

            fig, ax = plt.subplots(figsize=(30, 15))
            neon_spe.plot(ax=ax, fmt=":")
            fitres.plot(
                ax=ax,
                peak_candidate_groups=neon_peak_candidates,
                individual_peaks=True,
                label=None,
            )
            st.pyplot(fig)

    elif x_calib_btn == "submitted_std2_btn":

        material = "si"
        ###############################################
        # st.write(' in elif x_calib_btn std2')
        load_ts, normalize_ts, peakfind_ts, peakfit_ts = st.tabs(
            ["Load spe", "Normalize", "Peak find", "Peak fitting"]  # 'Baseline corr',
        )
        with load_ts:
            spe = st.session_state["cache_dicts"]["spectra_x"][material][0]
            st.session_state["cache_dicts"]["spectra_x_current"][material] = spe

            fig, ax = plt.subplots(figsize=(30, 15))
            spe.plot(ax=ax, label="Si")
            st.pyplot(fig)

        with normalize_ts:
            # st.write('normlaize tab')
            spe = st.session_state["cache_dicts"]["spectra_x_current"][material]

            normalized_spe = spe.normalize()
            st.session_state["cache_dicts"]["spectra_x_normalized"][
                material
            ] = normalized_spe
            st.session_state["cache_dicts"]["spectra_x_current"][
                material
            ] = normalized_spe

            fig, ax = plt.subplots(figsize=(30, 15))

            normalized_spe.plot(ax=ax, label="Si")
            st.pyplot(fig)

        with peakfind_ts:
            # st.write('Peak find')
            col1, col2 = st.columns(2)
            with col1:
                wlen = st.number_input(
                    label="wlen",
                    min_value=10,
                    max_value=800,
                    value=200,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )
                width = st.number_input(
                    label="width",
                    min_value=1,
                    max_value=10,
                    value=2,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )
                hht_chain = st.number_input(
                    label="hht_chain[int]",
                    min_value=10,
                    max_value=150,
                    value=80,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )
            with col2:
                sharpening = st.selectbox(
                    label="sharpening",
                    options=["hht", None],
                    index=1,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )
                strategy = st.selectbox(
                    label="strategy",
                    options=["topo", "bayesian_gaussian_mixture", "bgm", "cwt"],
                    index=0,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )
            kwargs = {
                "wlen": wlen,
                "width": width,
                "hht_chain": [hht_chain],
                "sharpening": sharpening,
                "strategy": strategy,
            }
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
                        "Moffat",
                        "Gaussian",
                        "Lorentzian",
                        "Voigt",
                        "PseudoVoigt",
                        "Pearson4",
                        "Pearson7",
                    ],
                    index=0,
                    on_change=update_x_calibration_btn("submitted_std2_btn"),
                )
            spe = st.session_state["cache_dicts"]["spectra_x_current"][material]
            peak_candidates = st.session_state["cache_dicts"][
                "spectra_x_peak_candidates"
            ][material]
            fitres = spe.fit_peak_multimodel(
                profile=profile, candidates=peak_candidates, no_fit=True
            )

            fig, ax = plt.subplots(figsize=(30, 15))
            spe.plot(ax=ax, fmt=":")
            fitres.plot(
                ax=ax,
                peak_candidate_groups=peak_candidates,
                individual_peaks=True,
                label=None,
            )
            st.pyplot(fig)

        ###################################################

    elif x_calib_btn == "btn_derive_x_calibration":
        st.write("DERIVING MODEL...")
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

    elif x_calib_btn == "submitted_btn_srm_experimental":
        # st.write(st.session_state['cache_strings']['x_calibration_search'])
        plc_x_calibration.image(
            "src/data/images/screenshot_srm_experimental_y_calibration01.png"
        )
        # plc_x_calibration.write('src/data/images/screenshot_create_x_calibration01.png')

    elif x_calib_btn == "submitted_btn_srm_theoretical":
        # st.write(st.session_state['cache_strings']['x_calibration_search'])
        plc_x_calibration.image(
            "src/data/images/screenshot_srm_theoretical_y_calibration01.png"
        )
        # plc_x_calibration.write('src/data/images/screenshot_create_x_calibration01.png')
    else:
        pass
        #  "btn_derive_y_calibration":

        #     plc_x_calibration.image(
        #         "src/data/images/screenshot_derive_y_calibration01.png"
        #     )
        #     # plc_x_calibration.write('src/data/images/screenshot_derive_x_calibration01.png')
        # case "btn_save_y_calibration":

        #     plc_x_calibration.image(
        #         "src/data/images/screenshot_save_x_calibration01.png"
        #     )

        # case _:
        #     pass

        # with st.form("Execute X-Calibration"):
        # st.write('Setup for the X-Calibration')
        # submitted_btn_run_x_cal = st.form_submit_button("Run")


def update_x_calibration_btn(value):
    def update_x_calibraiton_val():
        st.session_state["cache_strings"]["x_calibration_"] = value
        # print('in update_x_calibration_val')
        # print(' ini...', st.session_state["cache_strings"]["x_calibration_"])

    return update_x_calibraiton_val
    # print('inside update x calib')
    # print()
    # st.session_state["cache_strings"]["x_calibration_"] = "submitted_std1_btn"


if __name__ == "__main__":
    main()
