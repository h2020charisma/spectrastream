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

#: Categorical hues in fixed order, stepped for each surface. Validated for
#: colourblind separation against the chart surface rather than chosen by eye.
PALETTE = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#9085e9"],
}

#: Colour follows the entity, not its position in this particular chart. A
#: silicon trace stays the same colour whether it is drawn beside neon or in a
#: chart of its own -- which is what went wrong when every single-series chart
#: got the same blue.
_SLOTS: dict[str, int] = {}


def x_title(units: str | None) -> str:
    return X_TITLES.get(units or "cm-1", str(units))


def _mode() -> str:
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:  # noqa: BLE001 - theme is unavailable outside a session
        return "light"


def series_colors(labels: list[str]) -> list[str]:
    """Stable colours for these labels, in fixed palette order."""
    palette = PALETTE[_mode()]
    for label in labels:
        if label not in _SLOTS:
            _SLOTS[label] = len(_SLOTS)
    # Beyond the palette the hues would repeat; that is the point at which a
    # chart should be split rather than given invented colours.
    return [palette[_SLOTS[label] % len(palette)] for label in labels]


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
    labels = list(series)
    colors = series_colors(labels)

    # A legend for two or more traces; a single trace is named by its caption
    # and needs no key. Identity is never carried by colour alone.
    legend = alt.Legend(orient="top") if len(labels) > 1 else None
    return (
        alt.Chart(data)
        .mark_line(strokeWidth=1.6, clip=True)
        .encode(
            x=alt.X("x:Q", title=x_title, scale=alt.Scale(zero=False, nice=False)),
            y=alt.Y("y:Q", title=y_title, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N",
                title=None,
                legend=legend,
                scale=alt.Scale(domain=labels, range=colors),
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


def peak_markers(frame: pd.DataFrame, x_title: str = X_TITLE) -> alt.Chart:
    """Found peaks as marks over a spectrum, with their positions on hover."""
    return (
        alt.Chart(frame)
        .mark_point(size=70, filled=False, strokeWidth=1.6, color="#eb6834")
        .encode(
            x=alt.X("position:Q"),
            y=alt.Y("height:Q"),
            tooltip=[
                alt.Tooltip("position:Q", title=x_title, format=".3f"),
                alt.Tooltip("height:Q", title="Height", format=".4g"),
            ],
        )
    )


def show_spectrum(
    series: dict[str, tuple[np.ndarray, np.ndarray]],
    x_title: str = X_TITLE,
    y_title: str = Y_TITLE,
    height: int = 320,
    caption: str | None = None,
    peaks: pd.DataFrame | None = None,
) -> None:
    if not series:
        return
    chart = spectrum_chart(series, x_title, y_title, height)
    if peaks is not None and not peaks.empty and "position" in peaks:
        chart = chart + peak_markers(peaks, x_title)
    st.altair_chart(chart, width="stretch")
    total = sum(len(x) for x, _ in series.values())
    if caption:
        st.caption(caption)
    elif total > MAX_PLOT_POINTS:
        st.caption(
            f"Chart decimated to about {MAX_PLOT_POINTS} points for display; "
            "downloads always contain every point."
        )


def show_twin(
    left: tuple[str, tuple],
    right: tuple[str, tuple],
    x_title: str = X_TITLE,
    height: int = 280,
    caption: str | None = None,
) -> None:
    """Two traces on one x axis with independent y axes.

    For before/after of an intensity calibration, where the two differ by
    orders of magnitude: on a shared y axis one of them is pinned flat against
    the baseline and shows nothing. This is the old app's ax.twinx().
    """
    left_label, (lx, ly) = left
    right_label, (rx, ry) = right
    colors = series_colors([left_label, right_label])

    def _one(label, x, y, color, orient):
        # Each y axis is titled and coloured to match its own line: with two
        # independent scales a shared legend cannot say which axis a trace
        # belongs to, and that is the thing a reader needs.
        axis = alt.Axis(
            orient=orient,
            titleColor=color,
            labelColor=color,
            tickColor=color,
        )
        frame = spectra_frame({label: (x, y)})
        return (
            alt.Chart(frame)
            .mark_line(strokeWidth=1.6, clip=True)
            .encode(
                x=alt.X("x:Q", title=x_title, scale=alt.Scale(zero=False, nice=False)),
                y=alt.Y("y:Q", title=label, axis=axis, scale=alt.Scale(zero=False)),
                color=alt.value(color),
                tooltip=[
                    alt.Tooltip("x:Q", title=x_title, format=".2f"),
                    alt.Tooltip("y:Q", title=label, format=".4g"),
                ],
            )
        )

    chart = (
        alt.layer(
            _one(left_label, lx, ly, colors[0], "left"),
            _one(right_label, rx, ry, colors[1], "right"),
        )
        .resolve_scale(y="independent")
        .properties(height=height)
    )

    st.altair_chart(chart, width="stretch")
    if caption:
        st.caption(caption)
