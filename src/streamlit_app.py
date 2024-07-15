#!/usr/bin/env python3

import pandas as pd
import streamlit as st
from front_end.htmlTemplates import css

# st.set_page_config(
#     page_title="Raman spectroscopy harmonisation",
#     page_icon="./front_end/images/logo_charisma.jpg",
#     layout="wide",
# )
from modules.navigation_bar import navbar

from modules.util import (
    init_streamlit_cache,
    plot_original_x_calib_spe,
    process_file_spe,
)

from ramanchada2.protocols.calibration import CalibrationModel

# with st.sidebar:

#     st.sidebar.image("./front_end/images/logo_charisma.jpg")

# from pathlib import Path
# rpath = Path(__file__).parent.resolve()

st.title("This is the Fron Page title")

navbar()

st.write(css, unsafe_allow_html=True)

st.write("This is FRONT PAGE")


init_streamlit_cache()


def main():

    st.write("This is Main function..")


if __name__ == "__main__":
    main()
