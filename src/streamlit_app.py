import pandas as pd
from collections import defaultdict
from front_end.htmlTemplates import css

import streamlit as st
# import extra_streamlit_components as stx


st.set_page_config(page_title="Raman spectroscopy harmonisation",
                    page_icon = "./src/front_end/images/logo_charisma.jpg",
                    layout='wide')

st.write(css, unsafe_allow_html=True)


def page_SEARCH_or_UPLOAD_spectra():
    query_spectra = st.session_state['cache_strings']['query_spectra'] 
    # st.write('Query spectra...')
    st.write(query_spectra)
    st.session_state['cache_dicts']['input_files'] = {'STD1': 'Standard 1 spectra loaded',
                                                      'STD2': 'Standard 2 spectra loaded'}
    st.write("HERE IS THE SPECTRA SEARCHED RESULTS...")

def page_init_X_Calibration():
    input_files_dict = st.session_state['cache_dicts']['input_files']
    if not input_files_dict:
        st.write('You have not choosen spectra to process...')
    else:
        st.write('Process Spectra files')

def page_call_STD1_X_Calibration():
    if st.session_state.cache_bools['submitted_std1_btn'] == True:
        st.write('Graph with matched Neon (standard 1) peak for deriving the calibration curve...')

def page_call_STD2_X_Calibration():

    if st.session_state.cache_bools['submitted_std2_btn']:
        st.write('Graph: Lazer zeroing step using Si (standard 2)...')
    
def main():

    st.markdown("### Raman spectroscopy harmonisation")

    delta_max = 0.3

    if "cache_bools" not in st.session_state:
        st.session_state['cache_bools'] = defaultdict(bool)
    if "cache_strings" not in st.session_state:
        st.session_state['cache_strings'] = defaultdict(bool)
    if "cache_numbers" not in st.session_state:
        st.session_state['cache_numbers'] = defaultdict(float)
    if "cache_dfs" not in st.session_state:
        st.session_state['cache_dfs'] = defaultdict(pd.DataFrame)
  
    if "cache_dicts" not in st.session_state:
        st.session_state['cache_dicts'] = defaultdict(dict)


    with st.sidebar:

        st.sidebar.image("./src/front_end/images/logo_charisma.jpg")
        # st.header("AI data extractor")


        with st.expander("Search for or upload spectra files", expanded=True):
            with st.form('Choose Spectra'):
            
                query_spectra = st.text_input("Search for spectrum", "")
                st.session_state['cache_strings']['query_spectra'] = query_spectra.strip()
               
                uploaded_pdf = st.file_uploader("Upload JSON spectra file", accept_multiple_files=False)
                st.session_state['cache_dicts']['input_files'].update({'PDF': [uploaded_pdf]})                
    
                submitted_btn = st.form_submit_button("Load spectra")
                if submitted_btn:
                  
                    st.session_state.cache_bools['submitted_btn'] = True


        with st.expander("X-Calibration", expanded=False):
            
            page_init_X_Calibration()

            with st.form('STD1 Process'):
                st.write('STD1 setup....')

                submitted_btn = st.form_submit_button("STD1 process")
                if submitted_btn:
                    st.session_state.cache_bools['submitted_std1_btn'] = True
                    page_call_STD1_X_Calibration()

            with st.form('STD2 Process'):
                st.write('STD2 setup....')

                submitted_btn = st.form_submit_button("STD2 process")
                if submitted_btn:
                    st.session_state.cache_bools['submitted_std2_btn'] = True
                    page_call_STD2_X_Calibration()


            with st.form("Execute X-Calibration"):
                # choices = st.multiselect("Select fields to extract", ["RT[min]", "Width[min]", "Area,%", "Area"])
                st.write('Setup for the X-Calibration')
                submitted_btn = st.form_submit_button("Run")
                if submitted_btn:
                    st.write("X-Calibration is executing...")
                    page_call_STD1_X_Calibration()
                    page_call_STD2_X_Calibration()
                    st.write("X-Calibration has FINISHED...")                    
                    st.session_state.cache_bools['run_X_Calibration_btn'] = True
                    # page_SEARCH_or_UPLOAD_spectra()

        with st.expander("Y-Calibration", expanded=False):

           st.write('Y-Calibration')

    # if st.session_state.cache_bools['submitted_btn']:
    #     page_SEARCH_or_UPLOAD_spectra()



if __name__ == "__main__":
    main()

