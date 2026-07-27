"""A reusable reference-spectrum input: upload → merge → preprocess → peaks.

The Derive page gets these controls from the recipe machinery, but the Verify
page takes reference spectra (neon for resolution, calcite, a verification
material) *outside* any recipe. This gives it the same controls — several
acquisitions HDR-merged or averaged (a stitched/multi-exposure neon is the
norm), the usual crop/baseline preprocessing, and a peak-finding preview so the
settings can be judged before a slow fit — decoupled from ``RecipeSpec``.
"""

from dataclasses import dataclass

import streamlit as st
from ramanchada2.spectrum import Spectrum

from spectrastream.ingest import IngestError, load_spectrum
from spectrastream.merge import MergeError, MergeStrategy, combine
from spectrastream.peaks import DEFAULT_FIND_KW
from spectrastream.peaks import run as run_peaks
from spectrastream.preprocess import (
    BASELINE_METHODS,
    NORMALIZE_LABELS,
    NORMALIZE_STRATEGIES,
    PreprocessError,
    PreprocessStep,
    apply_steps,
)
from ui.charts import show_spectrum, x_title
from ui.state import SlotInput

UNIT_LABELS = {
    "cm-1": "Raman shift (cm⁻¹)",
    "nm": "Wavelength (nm)",
    "pixel": "Detector pixel",
}


@dataclass
class InputResult:
    """The spectrum an input produced, and the peak-finding settings chosen."""

    spectrum: Spectrum
    units: str
    find_kw: dict
    prominence_coeff: float
    profile: str
    provenance: list[str]


def _store() -> dict[str, SlotInput]:
    return st.session_state.setdefault("_ref_inputs", {})


def _load_files(entry: SlotInput, files) -> list[str]:
    problems: list[str] = []
    names = [f.name for f in files]
    if names == [item.filename for item in entry.loaded]:
        return problems
    entry.loaded = []
    entry.peak_trial = None
    for handle in files:
        try:
            entry.loaded.append(
                load_spectrum(handle.getvalue(), handle.name, units=entry.units)
            )
        except IngestError as err:
            problems.append(str(err))
    entry.exposures = [None] * len(entry.loaded)
    return problems


def _preprocess_ui(entry: SlotInput, defaults, key: str) -> None:
    if not entry.steps:
        entry.steps = [s.model_copy(deep=True) for s in defaults]
    if not entry.steps:
        return
    low, high = entry.x_range()
    with st.expander("Preprocessing", icon=":material/tune:"):
        for i, step in enumerate(entry.steps):
            step.enabled = st.checkbox(
                step.display_label(), value=step.enabled, key=f"{key}_pp{i}"
            )
            if not step.enabled:
                continue
            if step.op == "trim":
                cols = st.columns(2)
                step.params["min"] = cols[0].number_input(
                    "From", value=float(step.params.get("min", low)), key=f"{key}_mn{i}"
                )
                step.params["max"] = cols[1].number_input(
                    "To", value=float(step.params.get("max", high)), key=f"{key}_mx{i}"
                )
            elif step.op == "baseline":
                cols = st.columns(2)
                methods = list(BASELINE_METHODS)
                cur = str(step.params.get("method", "snip"))
                step.params["method"] = cols[0].selectbox(
                    "Method",
                    options=methods,
                    index=methods.index(cur) if cur in methods else 0,
                    key=f"{key}_bm{i}",
                )
                step.params["niter"] = cols[1].number_input(
                    "Iterations",
                    value=int(step.params.get("niter", 40)),
                    step=1,
                    key=f"{key}_bn{i}",
                )
            elif step.op == "normalize":
                strategies = list(NORMALIZE_STRATEGIES)
                cur = str(step.params.get("strategy", "minmax"))
                step.params["strategy"] = st.selectbox(
                    "Strategy",
                    options=strategies,
                    index=strategies.index(cur) if cur in strategies else 0,
                    format_func=lambda s: NORMALIZE_LABELS.get(s, s),
                    key=f"{key}_ns{i}",
                )


def _peak_ui(entry: SlotInput, profiles, key: str) -> tuple[dict, float, str]:
    """Peak-finding controls + a preview, returning (find_kw, coeff, profile)."""
    with st.expander("Peak finding", icon=":material/graphic_eq:"):
        cols = st.columns(3)
        find_kw = dict(DEFAULT_FIND_KW)
        find_kw["wlen"] = cols[0].number_input(
            "Peak window", value=200, step=10, min_value=10, key=f"{key}_wlen"
        )
        find_kw["width"] = cols[1].number_input(
            "Minimum width", value=1, step=1, min_value=1, key=f"{key}_width"
        )
        coeff = cols[2].number_input(
            "Prominence × noise",
            value=3.0,
            step=0.5,
            min_value=0.5,
            key=f"{key}_prom",
        )
        profile = (
            profiles[0]
            if len(profiles) == 1
            else st.selectbox("Peak profile", options=list(profiles), key=f"{key}_prof")
        )
        if st.checkbox("Preview found peaks", key=f"{key}_prev"):
            _, found, error = run_peaks(
                entry.merged, find_kw, coeff, profile, should_fit=False
            )
            if error:
                st.error(f"Peak finding fails: {error}", icon=":material/error:")
            else:
                st.caption(f"**{len(found)} peaks found** with these settings.")
                show_spectrum(
                    {"spectrum": (entry.merged.x, entry.merged.y)},
                    height=240,
                    x_title=x_title(entry.units),
                    peaks=found,
                )
    return find_kw, float(coeff), profile


def reference_input(
    label: str,
    key: str,
    *,
    accept_multiple: bool = True,
    merge_strategy: MergeStrategy = "auto",
    preprocess: tuple[PreprocessStep, ...] = (),
    profiles: tuple[str, ...] = ("Gaussian",),
    peak_finding: bool = True,
    units_default: str = "cm-1",
    help: str | None = None,
) -> InputResult | None:
    """Upload one or more acquisitions and return the merged, preprocessed
    spectrum plus the peak-finding settings chosen for it, or ``None``.

    Several files are HDR-merged when their exposures differ and averaged when
    they match — the "stitching" a multi-exposure neon needs. Preprocessing and
    peak-finding are the same controls the Derive page offers.
    """
    entry = _store().setdefault(key, SlotInput(units=units_default))

    uploaded = st.file_uploader(
        label, key=f"{key}_up", accept_multiple_files=accept_multiple, help=help
    )
    files = uploaded if accept_multiple else ([uploaded] if uploaded else [])
    files = [f for f in files if f is not None]
    if not files:
        entry.loaded = []
        entry.merged = None
        return None

    for problem in _load_files(entry, files):
        st.error(problem, icon=":material/error:")
    if not entry.loaded:
        return None

    unit_options = list(UNIT_LABELS)
    chosen = st.selectbox(
        "X axis units",
        options=unit_options,
        index=unit_options.index(entry.units) if entry.units in unit_options else 0,
        format_func=lambda u: UNIT_LABELS[u],
        key=f"{key}_units",
    )
    if chosen != entry.units:
        entry.units = chosen
        for item in entry.loaded:
            item.units = chosen

    if len(entry.loaded) > 1:
        with st.expander(
            f"{len(entry.loaded)} acquisitions — exposures", icon=":material/layers:"
        ):
            st.caption("Different exposure times are HDR-merged; equal ones averaged.")
            for i, item in enumerate(entry.loaded):
                row = st.columns([2, 1])
                row[0].caption(item.filename)
                entry.exposures[i] = (
                    row[1].number_input(
                        "Exposure (ms)",
                        value=float(entry.exposures[i] or 0.0),
                        step=100.0,
                        key=f"{key}_exp{i}",
                        label_visibility="collapsed" if i else "visible",
                    )
                    or None
                )

    try:
        merged, how = combine(
            [item.spectrum for item in entry.loaded],
            entry.exposures,
            strategy=merge_strategy,
        )
    except MergeError as err:
        st.error(f"{err}", icon=":material/error:")
        return None

    _preprocess_ui(entry, preprocess, key)
    try:
        merged, applied = apply_steps(merged, entry.steps)
    except PreprocessError as err:
        st.error(f"{err}", icon=":material/error:")
        return None
    entry.merged = merged
    provenance = [how, *applied]

    find_kw, coeff, profile = (dict(DEFAULT_FIND_KW), 3.0, profiles[0])
    if peak_finding:
        find_kw, coeff, profile = _peak_ui(entry, profiles, key)

    return InputResult(merged, entry.units, find_kw, coeff, profile, provenance)
