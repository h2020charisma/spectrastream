import os
import pickle
import tempfile

from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

import matplotlib.pyplot as plt
import pandas as pd
import ramanchada2 as rc2
import streamlit as st
from streamlit.runtime.uploaded_file_manager import DeletedFile, UploadedFile


from pydantic import BaseModel
from typing import Literal


class StateCrop(BaseModel):
    use_crop: bool = False
    crop_min: float | None = None
    crop_max: float | None = None


class StateNormalize(BaseModel):
    use_normalize: bool = False

# class StateBaseline(BaseModel):
#     use_baseline: bool = False
#     kwargs: dict = {}


class SNIPBaselineArgs(BaseModel):
    niter: int = 30


class StateSmooth(BaseModel):
    use_smooth: bool = False
    method: Literal['savgol', 'wiener', 'median',
                    'gauss', 'lowess', 'boxcar'] = 'savgol'

    savgol_window_length: int = 5
    savgol_polyorder: int = 3


class ALSBaselineArgs(BaseModel):
    niter: int = 30
    lam: float = 1e5
    p: float = 0.001
    smooth: int = 7  # PositiveOddInt(7)


class StateBaselineCorrection(BaseModel):
    use_baseline_corr: bool = False
    baseline_corr_type: Literal['AST', 'SNIP', 'MOVING_MIN'] = 'SNIP'
    args: SNIPBaselineArgs | ALSBaselineArgs = SNIPBaselineArgs()
    # baseline_corr_min: float | None = None
    # baseline_corr_max: float | None = None


class StatePeakFind(BaseModel):
    use_peak_find: bool = False
    value_prominence: float = 5.0  # neon_spe.y_noise
    value_wlen: int = 200
    value_width: int = 2
    # value_hht_chain: int = 80
    # value_sharpening: str | None = Neone  # None | hhte
    value_strategy: str | None = None  # only string

# class StateSmooth()


class StateSpectrum(BaseModel):
    crop: StateCrop
    normalize: StateNormalize | None = None
    peak_find: StatePeakFind | None = None
    baseline_corr: StateBaselineCorrection | None = None


class StateSpectrumSRMRef(BaseModel):

    crop: StateCrop = StateCrop()
    smooth: StateSmooth = StateSmooth()


default_state_srm_ref = StateSpectrumSRMRef()


default_peak_find_neon = StatePeakFind(value_sharpening=None,
                                       value_strategy='topo')

default_state_neon = StateSpectrum(crop=StateCrop(),
                                   normalize=StateNormalize(),
                                   peak_find=default_peak_find_neon)


default_peak_find_si = StatePeakFind(value_sharpening=None,
                                     value_strategy='topo')

default_state_si = StateSpectrum(crop=StateCrop(crop_min=520.45-50, crop_max=520.45+50),
                                 normalize=StateNormalize(),
                                 baseline_corr=StateBaselineCorrection(
                                     baseline_corr_type='SNIP', kwargs={'niter': 30}),
                                 peak_find=default_peak_find_si)

default_state_target = StateSpectrum(crop=StateCrop(),
                                     normalize=StateNormalize())
