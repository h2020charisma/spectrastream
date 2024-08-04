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

st.title("SpectraStream- Your Gateway to Harmonized Raman Spectra")

navbar()

st.write(css, unsafe_allow_html=True)

# st.write("This is FRONT PAGE")


init_streamlit_cache()

# str_write = """
# **Acknowledgements** \n
# This project has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement 952921 CHARISMA

# Support info
# Ideaconsult Ltd.
# www.ideaconsult.net
# email: support@ideaconsult.net"""

# st.write(str_write)


# def main():

#     st.write("This is Main function..")


# if __name__ == "__main__":
#     main()

str_markdown = """
Welcome to **SpectraStream**, a user-friendly app designed to simplify the process of generating harmonized Raman spectra, based on [CHARISMA](https://www.h2020charisma.eu/) calibration protocols.

## Purpose and Functionality

### Ultimate Goal

The ultimate goal of **SpectraStream** is to empower users to generate harmonized spectra effortlessly. By leveraging CHARISMA developed [ramanchada2](https://github.com/h2020charisma/ramanchada2) library in the background, **SpectraStream** ensures that even users with minimal technical knowledge can achieve accurate and consistent results.

### Key Features

#### Ideal User Profile

If you have reference materials, your samples, and a Raman system, you're all set to benefit from SpectraStream  and  [CHARISMA](https://www.h2020charisma.eu/) calibration protocols. Here's what you need to do:

- Measure Reference Materials: Collect spectra from reference materials - Neon and Silicon for x-calibration;  LED or NIST reference materials for relative intensity calibration.
- Measure Your Samples: Collect spectra from your samples.

#### Easy-to-Use Web Interface

- Upload Reference Spectra: Upload the spectra of your reference materials to the CHARISMA website. Associate these spectra with your specific Raman system and configuration to create a unique system profile. This profile acts as the harmonizer tool for your setup.  Derive the calibration and download the calibration file.

- Upload Sample Spectra: Upload the spectra of your samples.

- Receive Harmonized Spectra: SpectraStream processes your data and provides harmonized spectra.

## Application Interface

Spectra Stream app offers several options to guide you through the process:

### Specify Instrument Settings

Record your Raman system settings (this is used to associate the calibration profile with the instrument )

### Load or Create Calibration

#### Create Calibration

##### X Calibration

- Load a Neon spectrum to create a calibration curve.
- Laser Zeroing: Load a Silicon spectrum to perform laser zeroing.
- Save Calibration: Download your calibration file for future use.

##### Y Calibration

- Select standard reference material  certificate (NIST or LED)
- Load a measured spectrum of the standard reference material

#### Load Calibration

From Local File: Load a previously saved calibration file.

### Apply Calibration

- Load Target Spectrum: Upload the spectrum you wish to calibrate.
- Apply Calibration: Apply the calibration to your target spectrum.

## Spectrum Processing Tools

All spectrum upload options come with integrated tools to process Raman spectra:

- Crop: Trim the spectrum to focus on relevant data.
- Baseline Removal: Remove background.
- Normalize (optional): Standardize the spectrum for consistent comparison.
- Peak Find and Fit: Find and Fit peaks

## Advanced users

SpectraStream is a demonstration and does not support batch mode.  For advanced users, consider [RamanChada2](https://github.com/h2020charisma/ramanchada2) Python library and [Oranchada](https://github.com/h2020charisma/oranchada) user interface (an [Orange](https://orangedatamining.com/) add-on) .
"""

st.markdown(str_markdown)
