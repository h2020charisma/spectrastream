#!/usr/bin/env python3
from collections import defaultdict
from copy import deepcopy

import pandas as pd

from typing import TypedDict

from pydantic import BaseModel


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

from ramanchada2.protocols.calibration import (
    CalibrationModel,
    CertificatesDict,
    LazerZeroingComponent,
    XCalibrationComponent,
    YCalibrationCertificate,
    YCalibrationComponent,
)

from ramanchada2.protocols.calibration import CalibrationModel


class InstrumentsMandatory(BaseModel):
    laser_wavelength: int = 532
    serial_number: str | None = None
    description: str | None = None


class InstrumentSettings(InstrumentsMandatory):
    laser_wavelength: int = 532
    serial_number: str | None = None
    description: str | None = None
    # Another
    instrument_model: str | None = None
    device_type: str | None = None
    # Optical path details
    # laser_waveletgth: str
    numerical_aperture: str | None = None
    grating: str | None = None
    slit: str | None = None
    pinhole: str | None = None
    # Acquisition parameters
    exposure_time: str | None = None
    number_of_averages: str | None = None
    lazer_power_mw: str | None = None
    # Optional metadata
    number_of_datapoints: str | None = None
    temperature_in_lab: str | None = None
    humidity_in_lab: str | None = None


navbar()

if "config_certs" not in st.session_state["cache_dicts"]["instrument_settings"]:
    certificates = CertificatesDict()
    config_certs = certificates.config_certs

    st.session_state["cache_dicts"]["instrument_settings"][
        "config_certs"
    ] = config_certs


if "settings" not in st.session_state["cache_dicts"]["instrument_settings"]:

    st.session_state["cache_dicts"]["instrument_settings"][
        "settings"] = InstrumentSettings()

if "settings_mandatory" not in st.session_state["cache_dicts"]["instrument_settings"]:

    st.session_state["cache_dicts"]["instrument_settings"][
        "settings_mandatory"] = InstrumentsMandatory()


st.title("Load instrument metadata")

# with st.form(key="instrument_settings_form"):
# Create three columns: two for input fields and one for the submit button

# submit_instrument_settings_btn = st.form_submit_button(
#     label="Update",
#     #   disabled=not use_crop
# )

config_certs = st.session_state["cache_dicts"]["instrument_settings"][
    "config_certs"
]

settings = st.session_state["cache_dicts"]["instrument_settings"][
    "settings"]


def update_settings():
    settings.serial_number = None
# st.write(settings)


col0, col1 = st.columns([0.5, 1])

with col0:
    st.write('Mandatory metadata')
    # st.text_input('Wave length', value=settings.laser_waveletgth)
    options = [int(wl) for wl in config_certs.keys()]
    laser_wavelength = st.selectbox(
        label="Laser wave length",
        options=options,
        index=options.index(settings.laser_wavelength),
        on_change=update_settings
    )

    # config_certs[str(laser_wavelength)]

    options_id = list(config_certs[str(laser_wavelength)].keys())

    serial_number = st.selectbox(
        label="Serial number",
        options=options_id,
        index=0 if settings.serial_number is None else
        options_id.index(settings.serial_number)
    )

with col1:
    st.write('Another metadata')
    instrument_model = st.text_input(label='Instrument model')
    device_type = st.text_input(label='Device type')

    st.write('Optical path details')
    numerical_aperture = st.text_input(label='Numerical aperture',
                                       value=settings.numerical_aperture)
    grating = st.text_input(
        label='Grating', value=settings.grating)
    slit = st.text_input(label='Slit', value=settings.slit)
    pinhole = st.text_input(
        label='Pinhole', value=settings.pinhole)

# -----------------
settings.laser_wavelength = laser_wavelength
settings.serial_number = serial_number

settings.instrument_model = instrument_model
settings.device_type = device_type
settings.numerical_aperture = numerical_aperture
settings.grating = grating
settings.slit = slit
settings.pinhole = pinhole

# if submit_instrument_settings_btn:
st.session_state["cache_dicts"]["instrument_settings"][
    "settings"] = settings

st.session_state["cache_dicts"]["instrument_settings"][
    "settings_mandatory"] = InstrumentsMandatory(**settings.dict())
