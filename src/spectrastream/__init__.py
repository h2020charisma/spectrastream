"""Framework-independent core for SpectraStream.

Nothing in this package may import ``streamlit`` -- the UI layer lives in
``ui/`` and ``app_pages/``. Keeping the boundary strict is what allows the core
to be unit tested, reused from a notebook, and eventually served from something
other than Streamlit.
"""

__version__ = "0.2.0"
