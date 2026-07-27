"""Check a calibration's quality and characterise its resolution.

These are the CWA 18133 steps that come *after* deriving an axis: verification
(do a reference material's peaks land on their certified positions once the
calibration is applied?) and the resolution curves (sections 3-4 — spectral
distribution, pixel resolution, and the calcite/E2529 spectral resolution).

Everything here runs on a *fitted* calibration — the one just derived on the
Derive page, or one saved to an optical path — so it doubles as the place to
explore what a saved calibration actually does.
"""

import numpy as np
import pandas as pd
import streamlit as st
from ramanchada2.spectrum import Spectrum

from spectrastream.calibration import (
    MATERIAL_LABELS,
    REFERENCE_MATERIALS,
    CalibrationError,
    get_engine,
    has_relative_intensities,
    resolution_for,
    verify_against_reference,
    verify_relative_intensity,
)
from spectrastream.preprocess import PreprocessStep
from ui.charts import show_intensity_bars, show_spectrum, show_twin, x_title
from ui.inputs import reference_input
from ui.state import get_state

state = get_state()


# --- helpers ----------------------------------------------------------------


def _saved_calibrations():
    """Every saved calibration as ``(profile, optical_path, record)``."""
    out = []
    for profile in state.library.profiles:
        for path in profile.optical_paths:
            for record in path.calibrations:
                out.append((profile, path, record))
    return out


def _parse_lines(text: str) -> dict[float, float]:
    """Parse ``position:intensity`` (or ``position intensity``) pairs, one per
    line or comma-separated, into a reference dict."""
    ref: dict[float, float] = {}
    for chunk in text.replace(",", "\n").splitlines():
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.replace(":", " ").split()
        try:
            pos = float(parts[0])
            inten = float(parts[1]) if len(parts) > 1 else 1.0
        except (ValueError, IndexError):
            continue
        ref[pos] = inten
    return ref


def _mapping_traces(fitted, lo: float, hi: float, n: int = 400):
    """The calibration as a curve, in the units that make it legible.

    The composite calibration maps uncalibrated cm⁻¹ → calibrated cm⁻¹ (CWA §8);
    when a neon step is present, its cm⁻¹ → wavelength (nm) mapping is offered as
    a twin trace — the "nm vs cm⁻¹" view. Returns ``(grid, cm1, nm_or_None)`` or
    ``None`` if the calibration cannot be evaluated cleanly over the range.
    """
    grid = np.linspace(lo, hi, n)

    def _apply_x(fn) -> np.ndarray | None:
        out = fn(Spectrum(x=grid.copy(), y=np.ones_like(grid)))
        x = np.asarray(out.x, dtype=float)
        # apply drops points it cannot map monotonically; only a clean 1:1
        # result can be plotted against the input grid.
        return x if len(x) == n else None

    cm1 = _apply_x(lambda spe: fitted.apply(spe, spe_units="cm-1"))
    if cm1 is None:
        return None

    nm = None
    calmodel = getattr(fitted, "calmodel", None)
    if calmodel is not None and calmodel.components:
        first = calmodel.components[0]
        if getattr(first, "model_units", None) == "nm":
            nm = _apply_x(lambda spe: first.process(spe, "cm-1", convert_back=False))
    return grid, cm1, nm


# --- choose the calibration -------------------------------------------------

draft_fitted = state.draft.fitted
saved = _saved_calibrations()

if draft_fitted is None and not saved:
    st.info(
        "Nothing to verify yet. Derive a calibration on the **Derive calibration** "
        "page — or save one to an instrument — then come back to check its quality "
        "and resolution.",
        icon=":material/fact_check:",
    )
    st.stop()

source_options = []
if draft_fitted is not None:
    source_options.append("draft")
if saved:
    source_options.append("saved")

source = source_options[0]
if len(source_options) > 1:
    source = (
        st.segmented_control(
            "Calibration to check",
            options=source_options,
            format_func=lambda s: (
                "Current draft" if s == "draft" else "Saved calibration"
            ),
            default=source_options[0],
        )
        or source_options[0]
    )

fitted = None
laser_wl = None
reuse: dict[str, Spectrum] = {}
reuse_units: dict[str, str] = {}
provenance = ""

if source == "draft":
    fitted = draft_fitted
    reuse = state.draft.engine_inputs()
    reuse_units = state.draft.input_units()
    laser_wl = getattr(fitted, "laser_wl_nm", None)
    provenance = f"the calibration just derived with `{state.draft.recipe_id}`"
else:
    labels = {
        i: f"{p.name} · {op.op_id} · {rec.label}"
        for i, (p, op, rec) in enumerate(saved)
    }
    idx = st.selectbox(
        "Saved calibration",
        options=list(labels),
        format_func=lambda i: labels[i],
    )
    profile, path, record = saved[idx]
    try:
        fitted = get_engine(record.engine_id).load(record.model)
    except (CalibrationError, KeyError, ValueError) as err:
        st.error(f"Could not load this calibration: {err}", icon=":material/error:")
        st.stop()
    laser_wl = getattr(fitted, "laser_wl_nm", None) or record.laser_wl
    provenance = f"**{profile.name} · {path.op_id} · {record.label}**"

st.caption(f"Checking {provenance}.")


# --- what the calibration does ----------------------------------------------

st.subheader("What this calibration does")

describe = getattr(fitted, "describe", None)
corrections = getattr(fitted, "corrections", lambda: "")()
if corrections:
    st.markdown(f":material/tune: {corrections.capitalize()}.")

# The mapping curve, in real units -- not the normalized peak-matching stem.
# Range from the neon it was derived from when we have it, else a broad default.
if "neon" in reuse:
    lo, hi = float(min(reuse["neon"].x)), float(max(reuse["neon"].x))
else:
    lo, hi = 100.0, 3400.0
mapping = _mapping_traces(fitted, lo, hi)
if mapping is not None:
    grid, cm1, nm = mapping
    if nm is not None:
        show_twin(
            ("Calibrated Raman shift (cm⁻¹)", (grid, cm1)),
            ("Neon wavelength (nm)", (grid, nm)),
            x_title="Uncalibrated Raman shift (cm⁻¹)",
            caption=(
                "The calibration as a curve. Left axis: uncalibrated → calibrated "
                "Raman shift (CWA §8), cm⁻¹ throughout. Right axis: the neon step's "
                "cm⁻¹ → wavelength (nm) mapping — the nm-vs-cm⁻¹ view. The Si zero "
                "turns nm back into cm⁻¹, so the composite is cm⁻¹→cm⁻¹."
            ),
        )
    else:
        show_spectrum(
            {"Uncalibrated → calibrated (cm⁻¹)": (grid, cm1)},
            x_title="Uncalibrated Raman shift (cm⁻¹)",
            y_title="Calibrated Raman shift (cm⁻¹)",
            caption="Uncalibrated → calibrated Raman shift (CWA §8). Both axes cm⁻¹.",
        )
else:
    # Fall back to the engine's own figure when the mapping cannot be drawn.
    figure = getattr(fitted, "figure", lambda: None)()
    if figure is not None:
        st.pyplot(figure, width="stretch")

if describe is not None:
    with st.expander("Calibration detail", icon=":material/info:"):
        st.dataframe(
            pd.DataFrame(describe(), columns=["Property", "Value"]),
            width="stretch",
            hide_index=True,
        )


# --- verification -----------------------------------------------------------

st.subheader("Verify against a reference")
st.caption(
    "Measure a material with certified line positions, and see how far its peaks "
    "sit from those positions before and after the calibration is applied."
)

# Acetaminophen (APAP): the CHARISMA/VAMAS P6 *held-out* material — not one of
# CWA 18133's four calibration samples, so its bands are a genuine never-fit
# generalisation check. Positions (cm-1) from PMC4279138, cross-validated by
# Pestaner et al. 1996 (~1-2 cm-1 truth uncertainty). Offered as the default
# custom line list so that check is one click away.
ACETAMINOPHEN_LINES = "797\n858\n1236\n1324\n1560\n1611\n1649"

MATERIAL_ORDER = ["PST", "CAL", "Si", "custom"]
MATERIAL_NAMES = {**MATERIAL_LABELS, "custom": "Acetaminophen / custom lines"}
material = st.selectbox(
    "Reference material",
    options=MATERIAL_ORDER,
    format_func=lambda m: MATERIAL_NAMES[m],
)

custom_ref = None
if material == "custom":
    text = st.text_area(
        "Certified lines",
        value=ACETAMINOPHEN_LINES,
        help=(
            "One 'position:intensity' per line (intensity optional). Defaults to "
            "acetaminophen, the P6 held-out material — edit or replace it."
        ),
        height=160,
    )
    custom_ref = _parse_lines(text)

# The certified band this material occupies, for the crop default.
_ref_dict = (
    custom_ref if material == "custom" else REFERENCE_MATERIALS.get(material, {})
)
if _ref_dict:
    _lo, _hi = min(_ref_dict) - 100, max(_ref_dict) + 100
else:
    _lo, _hi = 0.0, 4000.0
_profiles = ("Pearson4", "Gaussian") if material == "Si" else ("Gaussian",)
_verify_pp = (
    PreprocessStep(op="trim", enabled=True, params={"min": _lo, "max": _hi}),
    PreprocessStep(op="baseline", enabled=True, params={"method": "snip", "niter": 40}),
)

# Silicon can be reused from the derivation (already merged and preprocessed);
# any other material is uploaded here with the same controls the Derive page has.
verify_spe = None
verify_units = "cm-1"
verify_find_kw = None
verify_profile = None
reuse_si = (
    material == "Si"
    and "si" in reuse
    and st.checkbox("Use the silicon from the derivation", value=True)
)
if reuse_si:
    verify_spe = reuse["si"]
    verify_units = reuse_units.get("si", "cm-1")
else:
    vin = reference_input(
        "Reference spectrum",
        "verify_material",
        accept_multiple=True,
        preprocess=_verify_pp,
        profiles=_profiles,
        peak_finding=True,
        help="A measurement of the selected material on this instrument.",
    )
    if vin is not None:
        verify_spe = vin.spectrum
        verify_units = vin.units
        verify_find_kw = vin.find_kw
        verify_profile = vin.profile

match_method = st.selectbox(
    "Peak matching",
    options=["qargmin2d", "argmin2d", "cluster", "assignment", "monotonic"],
    help="How found peaks are paired with reference lines.",
)

ready = verify_spe is not None and (material != "custom" or bool(custom_ref))
if st.button(
    "Check calibration",
    type="primary",
    icon=":material/fact_check:",
    disabled=not ready,
):
    with st.status("Fitting peaks before and after…", expanded=False) as status:
        try:
            result = verify_against_reference(
                fitted,
                verify_spe,
                material=material,
                spe_units=verify_units,
                match_method=match_method,
                ref=custom_ref,
                find_kw=verify_find_kw,
                profile=verify_profile,
                # already merged + cropped + baselined by the input control
                preprocess=False,
            )
            status.update(label="Verification complete", state="complete")
        except CalibrationError as err:
            result = None
            status.update(label="Could not verify", state="error")
            st.error(str(err), icon=":material/error:")

        # Relative-intensity verification, when the reference carries varying
        # certified intensities (polystyrene does; silicon/calcite do not).
        intensity = None
        _iref = (
            custom_ref if material == "custom" else REFERENCE_MATERIALS.get(material)
        )
        if _iref and has_relative_intensities(_iref):
            try:
                intensity = verify_relative_intensity(
                    fitted,
                    verify_spe,
                    material=material,
                    spe_units=verify_units,
                    profile=(verify_profile or "Gaussian"),
                    ref=custom_ref,
                    find_kw=verify_find_kw,
                    preprocess=False,
                )
            except CalibrationError:
                intensity = None
        st.session_state["intensity_result"] = (material, intensity)
    if result is not None:
        st.session_state["verify_result"] = (material, result)

stored = st.session_state.get("verify_result")
result = stored[1] if stored and stored[0] == material else None
if result is not None and verify_spe is not None:
    cols = st.columns(3)
    before = result.mean_before
    after = result.mean_after
    delta = (
        f"{after - before:+.3f}" if (before is not None and after is not None) else None
    )
    cols[0].metric(
        "Mean |Δ| before",
        f"{before:.3f} cm⁻¹" if before is not None else "—",
    )
    cols[1].metric(
        "Mean |Δ| after",
        f"{after:.3f} cm⁻¹" if after is not None else "—",
        delta=delta,
        delta_color="inverse",
    )
    cols[2].metric("Peaks matched", result.n_matched)

    if result.improved is True:
        st.success(
            "The calibration moved these peaks closer to their certified positions.",
            icon=":material/trending_down:",
        )
    elif result.improved is False:
        st.warning(
            "These peaks did not get closer to their certified positions — worth a "
            "look at the crop, units, and which material this is.",
            icon=":material/warning:",
        )

    show_twin(
        ("As measured", result.as_measured),
        ("Calibrated", result.calibrated),
        x_title=x_title("cm-1"),
        reference_lines=sorted(result.reference),
        caption=(
            "Baseline-removed, before and after calibration, on independent y "
            "axes (an intensity calibration rescales the calibrated trace). "
            "Dashed rules mark the certified reference positions."
        ),
    )
    with st.expander("Matched peaks", icon=":material/table_view:"):
        st.dataframe(result.matched, width="stretch", hide_index=True)

    xm, ym = result.as_measured
    xc, yc = result.calibrated
    spectra_df = pd.DataFrame(
        {
            "stage": ["as_measured"] * len(xm) + ["calibrated"] * len(xc),
            "raman_shift_cm-1": np.concatenate([xm, xc]),
            "intensity": np.concatenate([ym, yc]),
        }
    )
    dl = st.container(horizontal=True)
    dl.download_button(
        "Peak deviations (CSV)",
        data=result.matched.to_csv(index=False),
        file_name=f"{material}_peak_deviations.csv",
        mime="text/csv",
        icon=":material/download:",
    )
    dl.download_button(
        "Spectra as measured + calibrated (CSV)",
        data=spectra_df.to_csv(index=False),
        file_name=f"{material}_spectra.csv",
        mime="text/csv",
        icon=":material/download:",
    )


# --- relative intensity -----------------------------------------------------

istored = st.session_state.get("intensity_result")
intensity = istored[1] if istored and istored[0] == material else None
if intensity is not None and verify_spe is not None:
    st.subheader("Relative intensity")
    if not intensity.intensity_corrected:
        st.caption(
            "This calibration has no intensity (y) correction, so the measured "
            "relative intensities are shown against the reference but should not "
            "be expected to move."
        )
    cols = st.columns(3)
    ib, ia = intensity.mean_before, intensity.mean_after
    idelta = f"{ia - ib:+.1f}" if (ib is not None and ia is not None) else None
    cols[0].metric("Mean |ΔI| before", f"{ib:.1f}" if ib is not None else "—")
    cols[1].metric(
        "Mean |ΔI| after",
        f"{ia:.1f}" if ia is not None else "—",
        delta=idelta,
        delta_color="inverse",
    )
    cols[2].metric("Peaks matched", intensity.n_matched)

    if intensity.intensity_corrected and intensity.improved is True:
        st.success(
            "The intensity calibration brought the relative intensities closer "
            "to the certified values.",
            icon=":material/trending_down:",
        )

    show_intensity_bars(
        intensity.table,
        caption=(
            "Relative peak intensities, each normalised to 100 at the strongest "
            "line: certified reference vs as-measured vs calibrated."
        ),
    )
    with st.expander("Relative intensity table", icon=":material/table_view:"):
        st.dataframe(intensity.table, width="stretch", hide_index=True)
    st.download_button(
        "Relative intensities (CSV)",
        data=intensity.table.to_csv(index=False),
        file_name=f"{material}_relative_intensity.csv",
        mime="text/csv",
        icon=":material/download:",
    )


# --- resolution -------------------------------------------------------------

st.subheader("Resolution curves")
st.caption(
    "CWA 18133 sections 3-4: the spectral distribution (cm⁻¹ per pixel), the "
    "neon-FWHM pixel-resolution curve, and — with a calcite spectrum — the "
    "ASTM E2529 spectral resolution."
)

if getattr(fitted, "calmodel", None) is None:
    st.info(
        "Resolution needs the ramanchada2 calibration model, which this "
        "calibration does not expose.",
        icon=":material/info:",
    )
else:
    neon_spe = None
    neon_units = "cm-1"
    neon_find_kw = None
    neon_coeff = 3.0
    reuse_neon = "neon" in reuse and st.checkbox(
        "Use the neon from the derivation", value=True, key="reuse_neon"
    )
    if reuse_neon:
        neon_spe = reuse["neon"]
        neon_units = reuse_units.get("neon", "cm-1")
    else:
        neon_pp = (
            PreprocessStep(
                op="baseline", enabled=True, params={"method": "snip", "niter": 40}
            ),
            PreprocessStep(op="trim", enabled=False),
        )
        nin = reference_input(
            "Neon spectrum",
            "res_neon",
            accept_multiple=True,
            preprocess=neon_pp,
            profiles=("Gaussian",),
            peak_finding=True,
            help="Several exposures are HDR-merged (stitched), as in derivation.",
        )
        if nin is not None:
            neon_spe = nin.spectrum
            neon_units = nin.units
            neon_find_kw = nin.find_kw
            neon_coeff = nin.prominence_coeff

    cin = reference_input(
        "Calcite spectrum (optional)",
        "res_calcite",
        accept_multiple=True,
        preprocess=(PreprocessStep(op="trim", enabled=False),),
        peak_finding=False,
        help="Adds the ASTM E2529 spectral-resolution curve.",
    )
    calcite_spe = cin.spectrum if cin is not None else None
    calcite_units = cin.units if cin is not None else "cm-1"
    calcite_find_kw = cin.find_kw if cin is not None else None

    if st.button(
        "Compute resolution",
        type="primary",
        icon=":material/insights:",
        disabled=neon_spe is None,
    ):
        with st.status("Fitting neon peaks and curves…", expanded=False) as status:
            try:
                res = resolution_for(
                    fitted,
                    neon_spe,
                    neon_units=neon_units,
                    calcite_spe=calcite_spe,
                    calcite_units=calcite_units,
                    find_kw=neon_find_kw,
                    prominence_coeff=neon_coeff,
                    calcite_find_kw=calcite_find_kw,
                )
                status.update(label="Resolution computed", state="complete")
            except Exception as err:  # noqa: BLE001 - reported, not swallowed
                res = None
                status.update(label="Could not compute resolution", state="error")
                st.error(f"Resolution failed: {err}", icon=":material/error:")
        st.session_state["resolution_result"] = res

    res = st.session_state.get("resolution_result")
    if res is not None:
        figure = res.figure()
        if figure is not None:
            st.pyplot(figure, width="stretch")

        cols = st.columns(4)
        cols[0].metric("Neon peaks", res.n_neon_peaks)
        cols[1].metric(
            "Spectral resolution",
            f"{res.spectral_resolution:.2f} cm⁻¹" if res.spectral_resolution else "—",
        )
        cols[2].metric(
            "Max neon FWHM",
            f"{res.max_neon_fwhm_nm:.3f} nm" if res.max_neon_fwhm_nm else "—",
            help=(
                "Neon FWHM converted to nm — the quantity the 0.8 nm CWA "
                "boundary is tested against (the pixel-resolution curve itself "
                "is shown in cm⁻¹)."
            ),
        )
        boundary = "—"
        if res.within_cwa_boundary is True:
            boundary = "yes"
        elif res.within_cwa_boundary is False:
            boundary = "no"
        cols[3].metric(
            "Within CWA boundary",
            boundary,
            help="CWA 18133 Table 1: max neon FWHM below 0.8 nm.",
        )

        if res.uniform_grid:
            st.warning(
                "This spectrum is on a vendor-resampled uniform grid, so the "
                "spectral distribution shows the export grid, not detector pixels.",
                icon=":material/grid_on:",
            )
        if res.sres_plausible is False:
            st.warning(
                "The calcite fit is implausible (its E2529 resolution falls below "
                "the neon-derived instrument function), so the rescale was not "
                "applied and no spectral-resolution curve is drawn.",
                icon=":material/warning:",
            )
        for note in res.notes:
            st.caption(note)

        curves_df = pd.DataFrame(
            {
                "raman_shift_cm-1": res.raman_shift,
                "spectral_distribution_cm-1_per_pixel": res.sped,
                "pixel_resolution_fwhm_cm-1": res.pixel_res,
                "spectral_resolution_fwhm_cm-1": res.spectral_res,
                "sped_sres": res.sped_sres,
            }
        )
        dl = st.container(horizontal=True)
        dl.download_button(
            "Resolution curves (CSV)",
            data=curves_df.to_csv(index=False),
            file_name="resolution_curves.csv",
            mime="text/csv",
            icon=":material/download:",
        )
        if not res.neon_peaks.empty:
            dl.download_button(
                "Neon peaks (CSV)",
                data=res.neon_peaks.to_csv(index=False),
                file_name="neon_peaks.csv",
                mime="text/csv",
                icon=":material/download:",
            )

        if not res.neon_peaks.empty:
            with st.expander("Fitted neon peaks", icon=":material/table_view:"):
                st.dataframe(res.neon_peaks, width="stretch", hide_index=True)
