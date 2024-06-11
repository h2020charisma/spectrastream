import pandas as pd
from collections import defaultdict
from front_end.htmlTemplates import css

import streamlit as st

# import extra_streamlit_components as stx


st.set_page_config(
    page_title="Raman spectroscopy harmonisation",
    page_icon="./src/front_end/images/logo_charisma.jpg",
    layout="wide",
)

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

        st.sidebar.image("./src/front_end/images/logo_charisma.jpg")
        # st.header("AI data extractor")

        st.session_state["cache_dicts"]["x_calibration"] = ""

        with st.expander("Load/Search spectra files", expanded=False):

            with st.form("Choose Spectra"):
                query_spectra = st.text_input("Search for existing spectrum", "")
                st.session_state["cache_strings"][
                    "query_spectra"
                ] = query_spectra.strip()

                submitted_btn_search_spec = st.form_submit_button("Run")
                # st.session_state['cache_dicts']['submitted_btn_upload_spec'] = ''

                if submitted_btn_search_spec:

                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_btn_search_spec"

            with st.form("Load Spectra"):

                uploaded_spec = st.file_uploader(
                    "Load spectra file", accept_multiple_files=False
                )  # noqa: E501
                st.session_state["cache_dicts"]["input_files"].update(
                    {"SPEC": [uploaded_spec]}
                )

                submitted_btn_spec = st.form_submit_button("Load spectra")

                if submitted_btn_spec:

                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_btn_spec"

        with st.expander("Instrument settings", expanded=False):

            # st.session_state['cache_strings']['instrument_button'] = ''

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

    with st.sidebar:
        with st.expander("Load Calibration", expanded=False):
            with st.form("Load Calibration"):

                uploaded_calibration = st.file_uploader(
                    "Load Calibration", accept_multiple_files=False
                )
                st.session_state["cache_dicts"]["input_files"].update(
                    {"calibration": [uploaded_calibration]}
                )

                submitted_btn_load_calibration = st.form_submit_button(
                    "Submit calibration"
                )
                if submitted_btn_load_calibration:

                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "load_calibration"

    with st.sidebar:
        with st.expander("Search Calibration", expanded=False):

            with st.form("Search Calibration"):
                st.write("Search Calibration....")

                x_calib_search = st.text_input("Search for existing spectrum", "")
                st.session_state["cache_strings"][
                    "x_calibration_search"
                ] = x_calib_search.strip()

                submitted_btn_calibration_search = st.form_submit_button("Run")
                if submitted_btn_calibration_search:
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_btn_calibration_search"

                    page_call_STD1_X_Calibration()

    with st.sidebar:
        with st.expander("Create X-Calibration", expanded=False):

            with st.form("STD1 Process"):
                st.write("Neon STD1 setup....")

                submitted_btn_st1 = st.form_submit_button("Neon process")
                if submitted_btn_st1:
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_std1_btn"

                    page_call_STD1_X_Calibration()

            with st.form("STD2 Process"):
                st.write("Si STD2 setup....")

                submitted_btn_st2 = st.form_submit_button("Si process")
                if submitted_btn_st2:
                    # st.session_state.cache_bools['submitted_std2_btn'] = True
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "submitted_std2_btn"
                    page_call_STD2_X_Calibration()

            with st.form("Derive X-calibration"):
                st.write("Derive X-calibration")
                st.write("X-calibration setup")

                submitted_btn_derive_x = st.form_submit_button("Run")

                if submitted_btn_derive_x:
                    st.session_state["cache_strings"][
                        "x_calibration"
                    ] = "btn_derive_x_calibration"

            with st.form("Save X-calibration"):
                st.write("Save X-calibration")

                submitted_btn_save_x = st.form_submit_button("Run")

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

    match st.session_state["cache_strings"]["x_calibration"]:
        case "submitted_btn_search_spec":
            plc_x_calibration.image("src/data/images/screenshot_search_spectra01.png")
            # plc_x_calibration.write(st.session_state['cache_strings']['query_spectra'])

        case "submitted_btn_calibration_search":
            # plc_x_calibration.write(st.session_state['cache_strings']['x_calibration_search'])

            plc_x_calibration.image(
                "src/data/images/screenshot_search_x_calibration01.png"
            )
            # plc_x_calibration.write('src/data/images/screenshot_search_x_calibration01.png')

        case "show_instrument":
            plc_x_calibration.write(
                "Show Instrument  (e.g. Instrument recognized from Spectrum  metadata)"
            )
        case "select_instrument":
            plc_x_calibration.write("Select / search an instrument")

        case "load_calibration":
            plc_x_calibration.write(
                "Select user specified path and load calibration from file"
            )

        case "submitted_std1_btn":
            # st.write(st.session_state['cache_strings']['x_calibration_search'])
            plc_x_calibration.image(
                "src/data/images/screenshot_create_x_calibration01.png"
            )
            # plc_x_calibration.write('src/data/images/screenshot_create_x_calibration01.png')

        case "submitted_std2_btn":
            # st.write(st.session_state['cache_strings']['x_calibration_search'])
            plc_x_calibration.image(
                "src/data/images/screenshot_create_x_calibration01.png"
            )
            # plc_x_calibration.write('src/data/images/screenshot_create_x_calibration01.png')

        case "btn_derive_x_calibration":

            plc_x_calibration.image(
                "src/data/images/screenshot_derive_x_calibration01.png"
            )
            # plc_x_calibration.write('src/data/images/screenshot_derive_x_calibration01.png')
        case "btn_save_x_calibration":

            plc_x_calibration.image(
                "src/data/images/screenshot_save_x_calibration01.png"
            )

        case "submitted_btn_srm_experimental":
            # st.write(st.session_state['cache_strings']['x_calibration_search'])
            plc_x_calibration.image(
                "src/data/images/screenshot_srm_experimental_y_calibration01.png"
            )
            # plc_x_calibration.write('src/data/images/screenshot_create_x_calibration01.png')

        case "submitted_btn_srm_theoretical":
            # st.write(st.session_state['cache_strings']['x_calibration_search'])
            plc_x_calibration.image(
                "src/data/images/screenshot_srm_theoretical_y_calibration01.png"
            )
            # plc_x_calibration.write('src/data/images/screenshot_create_x_calibration01.png')

        case "btn_derive_y_calibration":

            plc_x_calibration.image(
                "src/data/images/screenshot_derive_y_calibration01.png"
            )
            # plc_x_calibration.write('src/data/images/screenshot_derive_x_calibration01.png')
        case "btn_save_y_calibration":

            plc_x_calibration.image(
                "src/data/images/screenshot_save_x_calibration01.png"
            )

        case _:
            pass

            # with st.form("Execute X-Calibration"):
            # st.write('Setup for the X-Calibration')
            # submitted_btn_run_x_cal = st.form_submit_button("Run")

    # if submitted_btn_run_x_cal:
    #     # with st.subheader:
    #     st.write("X-Calibration is executing...")
    #     page_call_STD1_X_Calibration()
    #     page_call_STD2_X_Calibration()
    #     st.write("X-Calibration has FINISHED...")
    #     st.session_state.cache_bools['run_X_Calibration_btn'] = True
    # page_SEARCH_or_UPLOAD_spectra()
    # with st.sidebar:
    #     with st.expander("Y-Calibration", expanded=False):
    #         st.write('Y-Calibration')

    # if st.session_state.cache_bools['submitted_btn']:
    #     page_SEARCH_or_UPLOAD_spectra()


if __name__ == "__main__":
    main()
