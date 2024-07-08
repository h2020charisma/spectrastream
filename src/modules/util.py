import os
import tempfile
from pathlib import Path
from tempfile import NamedTemporaryFile

import matplotlib.pyplot as plt
import ramanchada2 as rc2
import streamlit as st
from streamlit.runtime.uploaded_file_manager import (DeletedFile,
                                                     UploadedFile)

from collections import defaultdict
import pandas as pd
import pickle


def simple_plot_spe(spe, label, xlabel):
    # ax = spe.plot(label="Target spe")
    # fig = ax.get_figure()
    # st.pyplot(fig)
    # fig, ax = plt.subplots()
    # ax.set_xlabel(xlabel)
    ax = spe.plot(label=label)
    fig = ax.get_figure()
    # fig.set_size_inches(30, 15)
    st.pyplot(fig)


def load_calibration_file(uploaded_file: UploadedFile):  # ->
    extension = os.path.splitext(uploaded_file.name)[1][1:]
    return pickle.load(uploaded_file)

    # with tempfile.NamedTemporaryFile() as f:
    #     f.write(uploaded_file.read())
    #     f.flush()
    #     return pickle.load(f.name)


def process_file_spe(uploaded_files: list[UploadedFile], label=None, units="nm"):
    out_spe = []
    for uploaded_file in uploaded_files:
        # st.write(uploaded_file)
        # st.write(uploaded_file.name)
        # st.write(uploaded_file.type)

        extension = os.path.splitext(uploaded_file.name)[1][1:]
        # name, extension = os.path.splitext(fname)

        # # if extension == ".cha":
        # #     spe = rc2.spectrum.from_chada(fname,dataset=self.dataset)
        # # else:
        with tempfile.NamedTemporaryFile() as f:
            f.write(uploaded_file.read())
            f.flush()
            # video_function(f.name)
            # st.write(f.name)
            spe = rc2.spectrum.from_local_file(
                f.name,
                filetype=extension,
            )
            meta_dct = spe.meta.dict()["__root__"]
            meta_dct["xlabel"] = "Raman shift [cm¯¹]"
            meta_dct["Original file"] = uploaded_file.name
            meta_dct["Temporary file"] = f.name
            meta_dct["step"] = "Raw spe"
            meta_dct["label"] = str(label)
            meta_dct["units"] = units
            spe.meta = meta_dct
            out_spe.append(spe)
    return out_spe[0]


def plot_original_x_calib_spe(spe, label, legend=True):
    # neon_spe = st.session_state["cache_dicts"]['spectra_x']['neon'][0]
    # st.write(neon_spe.meta)
    # si_spe = st.session_state["cache_dicts"]['spectra_x']['si'][0]
    # st.write(si_spe.meta)
    fig, ax = plt.subplots()
    fig.set_size_inches(8, 4)

    # for ax, spe in zip(axes, spe_lst):
    spe.plot(ax=ax, label=label, fmt="b")
    # si_spe.plot(ax=ax2, label='Si', fmt='b')

    ax.set_xlabel(r"Raman shift [$\mathrm{cm}^{-1}$]")
    # ax2.set_xlabel(r'Raman shift [$\mathrm{cm}^{-1}$]')
    if not legend:
        ax.get_legend().remove()
    st.pyplot(fig, use_container_width=True)

    # return neon_spe, si_spe


def init_streamlit_cache():
    if "cache_bools" not in st.session_state:
        st.session_state["cache_bools"] = defaultdict(bool)
    if "cache_strings" not in st.session_state:
        st.session_state["cache_strings"] = defaultdict(str)
    if "cache_numbers" not in st.session_state:
        st.session_state["cache_numbers"] = defaultdict(float)
    if "cache_dfs" not in st.session_state:
        st.session_state["cache_dfs"] = defaultdict(pd.DataFrame)
    if "cache_lists" not in st.session_state:
        st.session_state["cache_lists"] = defaultdict(list)
    if "cache_dicts" not in st.session_state:
        st.session_state["cache_dicts"] = defaultdict(dict)


def update_session_state(cache_dict: dict, session_state):
    # 'cache_strings', 'cache_numbers', 'cache_dfs', 'cache_lists',
    # 'cache_dicts' in cache_dicts.keys()
    for key, item in cache_dict.items():
        assert isinstance(item, dict)
        session_state[key].update(item)
