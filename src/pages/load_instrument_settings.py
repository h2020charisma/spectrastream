#!/usr/bin/env python3
from collections import defaultdict
from copy import deepcopy
from enum import Enum

from typing import Set, TypedDict

import pandas as pd

import streamlit as st
import streamlit_pydantic as sp
from front_end.htmlTemplates import css

from modules.navigation_bar import navbar

from modules.util import (
    init_streamlit_cache,
    plot_original_x_calib_spe,
    process_file_spe,
    simple_plot_spe,
    update_session_state,
)

from pydantic import BaseModel, Field, parse_obj_as, ValidationError

from ramanchada2.protocols.calibration import (
    CalibrationModel,
    CertificatesDict,
    LazerZeroingComponent,
    XCalibrationComponent,
    YCalibrationCertificate,
    YCalibrationComponent,
)


# class InstrumentsMandatory(BaseModel):
#     laser_wavelength: int = 532
#     serial_number: str | None = None
#     description: str | None = None

if "settings" in st.session_state["cache_dicts"]["instrument_settings"]:
    settings = st.session_state["cache_dicts"]["instrument_settings"]["settings"]
else:
    settings = defaultdict(str)
    settings["laser_wavelength"] = 532


class InstrumentSettings(BaseModel):
    make_and_model_of_the_instrument: str | None = settings[
        "make_and_model_of_the_instrument"
    ]
    serial_number_of_the_instrument: str = settings["serial_number_of_the_instrument"]
    laser_wavelength: int = Field(
        settings["laser_wavelength"],
        description="Units: nm",
        title="Lazer wavelength (nm)",
    )
    # serial_number: str | None = settings['serial_number']
    # description: str | None = settings['description']
    # Another
    # instrument_model: str | None = settings['instrument_model']
    device_type: str | None = settings["device_type"]
    # Optical path details
    # laser_waveletgth: str
    numerical_aperture: str | None = settings["numerical_aperture"]
    grating: str | None = settings["grating"]
    slit: str | None = settings["slit"]
    # pinhole: str | None = settings[]
    # # Acquisition parameters
    # exposure_time: str | None = settings[]
    # number_of_averages: str | None = settings[]
    # lazer_power_mw: str | None = None
    # # Optional metadata
    # number_of_datapoints: str | None = settings[]
    # temperature_in_lab: str | None = settings[]
    # humidity_in_lab: str | None = settings[]


navbar()

# if "config_certs" not in st.session_state["cache_dicts"]["instrument_settings"]:
#     certificates = CertificatesDict()
#     config_certs = certificates.config_certs

#     st.session_state["cache_dicts"]["instrument_settings"][
#         "config_certs"
#     ] = config_certs


# if "settings" not in st.session_state["cache_dicts"]["instrument_settings"]:

#     st.session_state["cache_dicts"]["instrument_settings"][
#         "settings"] = InstrumentSettings()

# if "settings_mandatory" not in st.session_state["cache_dicts"]["instrument_settings"]:

#     st.session_state["cache_dicts"]["instrument_settings"][
#         "settings_mandatory"] = InstrumentsMandatory()


st.title("Load instrument metadata")

# with st.form(key="instrument_settings_form"):
# Create three columns: two for input fields and one for the submit button


# class OtherData(BaseModel):
#     text: str
#     integer: int


# class SelectionValue(str, Enum):
#     FOO = "foo"
#     BAR = "bar"


# # class ExampleModel(BaseModel):
# #     long_text: str = Field(..., description="Unlimited text property")
# #     integer_in_range: int = Field(
# #         20,
# #         ge=10,
# #         lt=30,
# #         multiple_of=2,
# #         description="Number property with a limited range.",
# #     )
# #     single_selection: SelectionValue = Field(
# #         ..., description="Only select a single item from a set."
# #     )
# #     multi_selection: Set[SelectionValue] = Field(
# #         ..., description="Allows multiple items from a set."
# #     )
# #     single_object: OtherData = Field(
# #         ...,
# #         description="Another object embedded into this model.",
# #     )


# if True:
#     print('Delete before    ')
#     keys = [k for k in st.session_state.keys() if 'my_form' in k]

#     print('delete.....')
#     for k in keys:
#         print(k)
#         del st.session_state[k]
#     print('end delete.....')


data = sp.pydantic_input(key="my_form", model=InstrumentSettings)
if data:
    st.session_state["cache_dicts"]["instrument_settings"]["settings"] = dict(data)
# if True:
#     print('Delete AFTER ')
#     keys = [k for k in st.session_state.keys() if 'my_form' in k]

#     print('delete.....')
#     for k in keys:
#         print(k)
#         del st.session_state[k]
#     print('end delete.....')


# a = st.slider(label='choose a number', min_value=3,
#               max_value=10, key='this_slider')


# print('7777777   Session state 77777777777')
# print(st.session_state)
# print('7777777   Session state END 77777777777')

# submit_instrument_settings_btn = st.form_submit_button(
#     label="Update",
#     #   disabled=not use_crop
# )

# config_certs = st.session_state["cache_dicts"]["instrument_settings"][
#     "config_certs"
# ]

# settings = st.session_state["cache_dicts"]["instrument_settings"][
#     "settings"]


# def update_settings():
#     settings.serial_number = None
# # st.write(settings)


# col0, col1 = st.columns([0.5, 1])

# with col0:
#     st.write('Mandatory metadata')
#     # st.text_input('Wave length', value=settings.laser_waveletgth)
#     options = [int(wl) for wl in config_certs.keys()]
#     laser_wavelength = st.selectbox(
#         label="Laser wave length",
#         options=options,
#         index=options.index(settings.laser_wavelength),
#         on_change=update_settings
#     )

#     # config_certs[str(laser_wavelength)]

#     options_id = list(config_certs[str(laser_wavelength)].keys())

#     serial_number = st.selectbox(
#         label="Serial number",
#         options=options_id,
#         index=0 if settings.serial_number is None else
#         options_id.index(settings.serial_number)
#     )

# with col1:
#     st.write('Another metadata')
#     instrument_model = st.text_input(label='Instrument model')
#     device_type = st.text_input(label='Device type')

#     st.write('Optical path details')
#     numerical_aperture = st.text_input(label='Numerical aperture',
#                                        value=settings.numerical_aperture)
#     grating = st.text_input(
#         label='Grating', value=settings.grating)
#     slit = st.text_input(label='Slit', value=settings.slit)
#     pinhole = st.text_input(
#         label='Pinhole', value=settings.pinhole)

# -----------------
# settings.laser_wavelength = laser_wavelength
# settings.serial_number = serial_number

# settings.instrument_model = instrument_model
# settings.device_type = device_type
# settings.numerical_aperture = numerical_aperture
# settings.grating = grating
# settings.slit = slit
# settings.pinhole = pinhole

# # if submit_instrument_settings_btn:
# st.session_state["cache_dicts"]["instrument_settings"][
#     "settings"] = settings

# st.session_state["cache_dicts"]["instrument_settings"][
#     "settings_mandatory"] = InstrumentsMandatory(**settings.dict())
