"""Spectrum charts.

Altair rather than matplotlib: a Raman spectrum is something people want to zoom
into, and the old app redrew a static PNG on every rerun. Vega charts pan and
zoom client-side, so exploring costs no server round trips.
"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

#: Above this, the chart is decimated for display. Raman spectra routinely run
#: to tens of thousands of points and Vega chokes long before the science does.
MAX_PLOT_POINTS = 6000

#: Axis titles per unit. Labelling a nm or pixel axis "Raman shift" would be a
#: quiet lie, and the units are exactly what a reader needs to judge the plot.
X_TITLES = {
    "cm-1": "Raman shift (cm⁻¹)",
    "nm": "Wavelength (nm)",
    "pixel": "Detector pixel",
}
X_TITLE = X_TITLES["cm-1"]
Y_TITLE = "Intensity (a.u.)"


def x_title(units: str | None) -> str:
    return X_TITLES.get(units or "cm-1", str(units))


def _decimate(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(x) <= MAX_PLOT_POINTS:
        return x, y
    step = int(np.ceil(len(x) / MAX_PLOT_POINTS))
    return x[::step], y[::step]


def spectra_frame(series: dict[str, tuple[np.ndarray, np.ndarray]]) -> pd.DataFrame:
    """Long-form frame for a set of named traces."""
    frames = []
    for label, (x, y) in series.items():
        xs, ys = _decimate(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
        frames.append(pd.DataFrame({"x": xs, "y": ys, "series": label}))
    if not frames:
        return pd.DataFrame({"x": [], "y": [], "series": []})
    return pd.concat(frames, ignore_index=True)


def spectrum_chart(
    series: dict[str, tuple[np.ndarray, np.ndarray]],
    x_title: str = X_TITLE,
    y_title: str = Y_TITLE,
    height: int = 320,
) -> alt.Chart:
    """An interactive line chart of one or more spectra."""
    data = spectra_frame(series)
    single = len(series) <= 1
    return (
        alt.Chart(data)
        .mark_line(strokeWidth=1.2, clip=True)
        .encode(
            x=alt.X("x:Q", title=x_title, scale=alt.Scale(zero=False, nice=False)),
            y=alt.Y("y:Q", title=y_title, scale=alt.Scale(zero=False)),
            color=(
                alt.value("#4c78a8")
                if single
                else alt.Color("series:N", title=None, legend=alt.Legend(orient="top"))
            ),
            tooltip=[
                alt.Tooltip("series:N", title="Trace"),
                alt.Tooltip("x:Q", title=x_title, format=".2f"),
                alt.Tooltip("y:Q", title=y_title, format=".4g"),
            ],
        )
        .properties(height=height)
        .interactive(bind_y=False)
    )


def show_spectrum(
    series: dict[str, tuple[np.ndarray, np.ndarray]],
    x_title: str = X_TITLE,
    y_title: str = Y_TITLE,
    height: int = 320,
    caption: str | None = None,
) -> None:
    if not series:
        return
    st.altair_chart(spectrum_chart(series, x_title, y_title, height), width="stretch")
    total = sum(len(x) for x, _ in series.values())
    if caption:
        st.caption(caption)
    elif total > MAX_PLOT_POINTS:
        st.caption(
            f"Chart decimated to about {MAX_PLOT_POINTS} points for display; "
            "downloads always contain every point."
        )
