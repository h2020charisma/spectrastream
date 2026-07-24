#!/usr/bin/env python3
"""SpectraStream entry point.

Declares navigation and the state every page shares. Page bodies live in
``app_pages/`` as plain scripts; anything reusable belongs in ``ui/`` (Streamlit)
or ``spectrastream/`` (framework-independent).
"""

import streamlit as st

st.set_page_config(
    page_title="SpectraStream",
    page_icon=":material/linear_scale:",
    layout="wide",
)

from ui.state import get_state  # noqa: E402  - must follow set_page_config

state = get_state()

pages = [
    st.Page(
        "app_pages/home.py",
        title="Home",
        icon=":material/home:",
        default=True,
    ),
    st.Page(
        "app_pages/convert.py",
        title="Convert",
        icon=":material/upload_file:",
    ),
    st.Page(
        "app_pages/calibrate.py",
        title="Calibrate",
        icon=":material/tune:",
    ),
    st.Page(
        "app_pages/profiles.py",
        title="Instruments",
        icon=":material/precision_manufacturing:",
    ),
]

page = st.navigation(pages, position="top")

st.title(f"{page.icon} {page.title}")
st.warning(
    "Alpha — results are indicative. Check anything you intend to publish.",
    icon=":material/science:",
)

page.run()
