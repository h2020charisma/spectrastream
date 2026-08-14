"""Render calibration inputs from a recipe.

Nothing here knows what neon or silicon are. The uploaders, their labels, how
many files they take, how those files are combined and what preprocessing is
offered all come from the recipe, so a protocol needing entirely different
reference materials needs no UI change.
"""

from typing import Any

import streamlit as st

from spectrastream.acquisition import guess_from_metadata
from spectrastream.calibration.engines.base import explain as explain_error
from spectrastream.calibration.spec import RecipeSpec, SpectrumSlot
from spectrastream.ingest import IngestError, load_spectrum
from spectrastream.merge import MergeError, combine
from spectrastream.peaks import DEFAULT_FIND_KW, searched_axis, to_axis
from spectrastream.peaks import run as run_peaks
from spectrastream.preprocess import (
    BASELINE_METHODS,
    NORMALIZE_LABELS,
    NORMALIZE_STRATEGIES,
    SMOOTH_METHODS,
    PreprocessError,
    apply_steps,
    destroys_intensity,
)
from spectrastream.upload import files_changed
from ui.charts import show_spectrum, x_title
from ui.state import CalibrationDraft, SlotInput, entry_key, slot_id_of

UNIT_LABELS = {
    "cm-1": "Raman shift (cm⁻¹)",
    "nm": "Wavelength (nm)",
    "pixel": "Detector pixel",
}

#: Engine parameters worth exposing, with the choices the engine accepts.
TUNABLES = {
    "match_method": (
        "Peak matching",
        ["qargmin2d", "argmin2d", "cluster", "assignment", "monotonic", "dynamicp"],
        "How measured peaks are paired with reference lines.",
    ),
    "interpolator_method": (
        "Curve model",
        ["poly", "polyinverse", "pchip", "pchipinverse", "rbfinverse"],
        "How the correction between matched peaks is interpolated.",
    ),
}


def _tracked(draft: CalibrationDraft, old: Any, new: Any) -> Any:
    """Return `new`, clearing a stale fit first if it differs from `old`.

    Centralises "this control changed, so the derived result no longer
    matches its inputs" so every widget applies it the same way. `old` must
    be computed with the same default-fallback the widget's own `value=`
    uses, or a freshly-computed fit would be spuriously cleared on first
    render whenever the backing dict entry is legitimately absent.
    """
    if new != old:
        draft.clear_result()
    return new


def _finds_peaks(recipe: RecipeSpec, slot_id: str) -> bool:
    """Whether any step consuming this slot actually looks for peaks.

    A step says which of its inputs it reads peaks from when that is not all of
    them (``StepSpec.finds_peaks_in``) -- a step can derive a correction from
    reference positions alone yet still read a band apex from a laser-zeroing
    material, and showing controls on the former would imply a tuning knob that
    changes nothing.

    Falling back on the product is a guess for steps that do not declare it.
    Intensity calibration is the case it gets right: YCalibrationComponent
    resamples the measured reference and divides by the certificate's response,
    so it finds no peaks.
    """
    for step in _steps_using(recipe, slot_id):
        if step.finds_peaks_in is not None:
            if slot_id in step.finds_peaks_in:
                return True
        elif step.produces != "y_response":
            return True
    return False


def _no_peak_finding_reason(recipe: RecipeSpec, slot_id: str) -> str:
    """Why this slot has no peak-finding controls -- the two cases differ, and
    telling a user "intensity calibration does not look for peaks" about an
    x-axis anchor would be simply untrue."""
    steps = _steps_using(recipe, slot_id)
    if any(s.finds_peaks_in is not None for s in steps):
        return (
            "This calibration does not look for peaks in this material — it "
            "works from its known reference positions."
        )
    return (
        "Intensity calibration does not look for peaks — the measured "
        "reference is resampled and divided by the certificate's response."
    )


def certified_range(
    recipe: RecipeSpec, draft: CalibrationDraft, slot_id: str, laser_wl_nm
) -> tuple[float, float] | None:
    """The certificate's certified Raman-shift range, if this slot has one.

    The certificate states where it is valid; cropping to anything else is
    either discarding certified data or including uncertified data.
    """
    from ramanchada2.protocols.calibration.ycalibration import CertificatesDict

    steps = [s for s in _steps_using(recipe, slot_id) if s.action == "y_intensity"]
    if not steps or laser_wl_nm is None:
        return None
    scope = draft.params.get(steps[0].id, {})
    key = scope.get("certificate", steps[0].params.get("certificate"))
    try:
        certs = CertificatesDict().get_certificates(int(laser_wl_nm))
        cert = certs[key] if key in certs else next(iter(certs.values()))
    except (KeyError, ValueError, StopIteration):
        return None
    return tuple(cert.raman_shift) if cert.raman_shift else None


def _steps_using(recipe: RecipeSpec, slot_id: str):
    return [s for s in recipe.steps if slot_id in s.inputs]


def _peak_controls(
    slot: SpectrumSlot, recipe: RecipeSpec, draft: CalibrationDraft
) -> None:
    """Peak finding for this material, beside the spectrum it applies to.

    These are per sample, not global: neon and silicon want different windows,
    which is why the VAMAS pipeline keys them by sample. Keeping them here also
    means an error advising "widen the peak window" names something visible.
    """
    steps = [
        s
        for s in _steps_using(recipe, slot.id)
        if "find_kw" in s.params or "prominence_coeff" in s.params
    ]
    if not steps:
        return

    for step in steps:
        scope = draft.params.setdefault(step.id, {})
        defaults = dict(step.params.get("find_kw") or DEFAULT_FIND_KW)
        current = dict(scope.get("find_kw") or defaults)
        old_find_kw = dict(current)

        cols = st.columns(3)
        current["wlen"] = cols[0].number_input(
            "Peak window",
            value=int(current.get("wlen", 200)),
            step=10,
            min_value=10,
            key=f"find_{recipe.id}_{step.id}_wlen",
            help=(
                "How far around a candidate its prominence is judged. Too "
                "narrow and the fit is handed groups with fewer points than it "
                "has parameters, which cannot be fitted at all."
            ),
        )
        current["width"] = cols[1].number_input(
            "Minimum width",
            value=int(current.get("width", 1)),
            step=1,
            min_value=1,
            key=f"find_{recipe.id}_{step.id}_width",
            help=(
                "Candidates narrower than this are discarded. Raise it when a "
                "fit reports a group with fewer points than parameters: it is "
                "the narrow candidates that form those groups."
            ),
        )
        old_prom = float(
            scope.get("prominence_coeff", step.params.get("prominence_coeff", 3))
        )
        new_prom = cols[2].number_input(
            "Prominence × noise",
            value=old_prom,
            step=0.5,
            min_value=0.5,
            key=f"find_{recipe.id}_{step.id}_prom",
            help="How far above the noise a candidate must stand.",
        )
        scope["prominence_coeff"] = _tracked(draft, old_prom, new_prom)
        strategies = ["topo", "bgm", "cwt"]
        chosen = str(current.get("strategy", "topo"))
        current["strategy"] = st.selectbox(
            "Finding strategy",
            options=strategies,
            index=strategies.index(chosen) if chosen in strategies else 0,
            key=f"find_{recipe.id}_{step.id}_strategy",
            help=(
                "How candidates are found: topographic prominence, a Bayesian "
                "Gaussian mixture, or continuous wavelet transform."
            ),
        )
        scope["find_kw"] = _tracked(draft, old_find_kw, current)

        if "should_fit" in step.params:
            old_should_fit = bool(scope.get("should_fit", step.params["should_fit"]))
            new_should_fit = st.checkbox(
                "Fit peak shapes",
                value=old_should_fit,
                key=f"fit_{recipe.id}_{step.id}",
                help=(
                    "Fit a profile to each candidate for a sub-pixel position "
                    "instead of taking it as found. Slower."
                ),
            )
            scope["should_fit"] = _tracked(draft, old_should_fit, new_should_fit)


#: Which peak shapes make sense per step. Neon emission lines are Gaussian;
#: the silicon band is fitted with Pearson4 by the zeroing step, with Gaussian
#: worth trying when that will not converge.
PROFILES_BY_ACTION = {
    "x_curve": ["Gaussian"],
    "laser_zero": ["Pearson4", "Gaussian"],
}


def _profiles_for(recipe: RecipeSpec, slot_id: str) -> list[str]:
    for step in _steps_using(recipe, slot_id):
        if step.action in PROFILES_BY_ACTION:
            return PROFILES_BY_ACTION[step.action]
    return ["Gaussian"]


def _peak_settings(recipe: RecipeSpec, draft: CalibrationDraft, slot_id: str):
    """The peak-finding settings in force for a slot: (find_kw, coeff, fit)."""
    steps = _steps_using(recipe, slot_id)
    if not steps:
        return None, 3.0, False
    step = steps[0]
    scope = draft.params.get(step.id, {})
    find_kw = scope.get("find_kw") or step.params.get("find_kw") or DEFAULT_FIND_KW
    coeff = float(scope.get("prominence_coeff", step.params.get("prominence_coeff", 3)))
    should_fit = bool(scope.get("should_fit", step.params.get("should_fit", False)))
    return dict(find_kw), coeff, should_fit


def _resolve_slot(
    slot: SpectrumSlot, draft: CalibrationDraft, key: str | None = None
) -> str | None:
    """Merge and preprocess one slot into the spectrum the engine will see.

    Called from the uploader rather than only from resolve_inputs, because the
    peak panel below needs `merged` on the *same* run the file arrives. Doing
    it later meant a freshly uploaded spectrum showed "upload a spectrum" until
    something else forced a rerun.
    """
    key = key or slot.id
    entry = draft.slots.get(key)
    if entry is None or not entry.loaded:
        if entry is not None:
            entry.merged = None
        return None

    try:
        merged, how = combine(
            [item.spectrum for item in entry.loaded],
            entry.exposures,
            strategy=slot.merge,
        )
    except MergeError as err:
        entry.merged = None
        return f"{slot.label}: {err}"

    try:
        merged, applied = apply_steps(merged, entry.steps_for(slot))
    except PreprocessError as err:
        entry.merged = None
        return f"{slot.label}: {err}"

    entry.merged = merged
    draft.provenance[key] = [how, *applied]
    return None


def _try_peaks(
    slot: SpectrumSlot,
    recipe: RecipeSpec,
    draft: CalibrationDraft,
    laser_wl_nm: float | None,
    key: str | None = None,
) -> None:
    """Show what ramanchada2's fit_peaks does with the current settings.

    Finding is cheap and runs on every change; fitting is what takes time, so
    it is asked for explicitly.
    """
    key = key or slot.id
    entry = draft.slots.get(key)
    if entry is None or entry.merged is None:
        st.caption("Upload a spectrum to try peak finding.")
        return

    find_kw, coeff, _ = _peak_settings(recipe, draft, slot.id)
    steps = _steps_using(recipe, slot.id)
    action = steps[0].action if steps else "x_curve"
    profiles = _profiles_for(recipe, slot.id)
    profile = (
        profiles[0]
        if len(profiles) == 1
        else st.selectbox(
            "Peak profile",
            options=profiles,
            index=0,
            key=f"prof_{recipe.id}_{key}",
        )
    )

    # The neon curve searches in nm, because that is where it matches its
    # reference lines. Showing the cm-1 axis would show peaks at positions the
    # calibration never uses.
    units = searched_axis(action, entry.units)
    working = to_axis(entry.merged, entry.units, units, laser_wl_nm)

    _, found, error = run_peaks(working, find_kw, coeff, profile, should_fit=False)
    if error:
        st.error(f"Peak finding fails here: {error}", icon=":material/error:")
        hint = explain_error(Exception(error))
        if hint:
            st.caption(hint)
        return

    if units != entry.units:
        st.caption(
            f"Searched in {UNIT_LABELS.get(units, units)} — where this step "
            "matches its reference lines."
        )
    st.caption(f"**{len(found)} peaks found.**")
    show_spectrum(
        {slot.label: (working.x, working.y)},
        height=260,
        x_title=x_title(units),
        peaks=found,
        caption="Circles mark what this step will match against its references.",
    )

    if st.button(
        "Fit these peaks",
        key=f"try_{recipe.id}_{key}",
        icon=":material/play_arrow:",
        help="Fitting every candidate is slow — seconds to minutes.",
    ):
        with st.spinner(f"Fitting {len(found)} peaks…"):
            table, _, fit_error = run_peaks(
                working, find_kw, coeff, profile, should_fit=True
            )
        entry.peak_trial = (table, fit_error, True)

    trial = getattr(entry, "peak_trial", None)
    if trial is None:
        st.dataframe(found, width="stretch", height=180)
        return
    table, fit_error, _ = trial

    if fit_error:
        st.error(f"Fitting fails: {fit_error}", icon=":material/error:")
        hint = explain_error(Exception(fit_error))
        if hint:
            st.caption(hint)
        return

    st.success(f"{len(table)} peaks fitted.", icon=":material/check_circle:")
    st.dataframe(table, width="stretch", height=180)


def _slot_uploader(
    slot: SpectrumSlot,
    recipe: RecipeSpec,
    draft: CalibrationDraft,
    laser_wl_nm: float | None,
    key: str | None = None,
) -> list[str]:
    """One slot -- or one entry of a repeatable slot: files, units, exposures,
    preprocessing. Returns problems.

    ``key`` addresses the draft entry and the widgets; it differs from
    ``slot.id`` only for a repeatable slot, whose entries each hold a different
    material. Recipe lookups still use ``slot.id``, since every entry of a slot
    shares the same recipe definition.
    """
    problems: list[str] = []
    key = key or slot.id
    entry = draft.slots.setdefault(key, SlotInput(units=slot.units))

    label = slot.label if slot.required else f"{slot.label} (optional)"
    uploaded = st.file_uploader(
        label,
        key=f"slot_{draft.recipe_id}_{key}",
        accept_multiple_files=slot.accept_multiple,
        help=slot.help,
    )
    files = uploaded if slot.accept_multiple else ([uploaded] if uploaded else [])
    files = [f for f in files if f is not None]

    if not files:
        entry.loaded = []
        entry.merged = None
        return problems

    payloads = [f.getvalue() for f in files]
    if files_changed(payloads, entry.loaded):
        entry.loaded = []
        for handle, payload in zip(files, payloads, strict=True):
            try:
                entry.loaded.append(
                    load_spectrum(payload, handle.name, units=entry.units)
                )
            except IngestError as err:
                problems.append(str(err))
        # Exposure times are needed to HDR-merge; the file often states them.
        entry.exposures = []
        for item in entry.loaded:
            guessed, _ = guess_from_metadata(item.source_metadata)
            entry.exposures.append(guessed.get("integration_time_ms"))
        draft.clear_result()

    if not entry.loaded:
        return problems

    # Units: a bare data file does not say whether x is cm-1, nm or pixels.
    unit_options = list(UNIT_LABELS)
    chosen_units = st.selectbox(
        "X axis units",
        options=unit_options,
        index=unit_options.index(entry.units) if entry.units in unit_options else 0,
        format_func=lambda u: UNIT_LABELS[u],
        key=f"units_{draft.recipe_id}_{key}",
    )
    if chosen_units != entry.units:
        entry.units = chosen_units
        for item in entry.loaded:
            item.units = chosen_units
        draft.clear_result()

    _material_controls(slot, recipe, draft, entry, key)

    if len(entry.loaded) > 1:
        _exposure_inputs(slot, draft, entry, key)

    _preprocess_controls(slot, recipe, draft, entry, laser_wl_nm, key)

    problem = _resolve_slot(slot, draft, key)
    if problem:
        problems.append(problem)

    # The certificate belongs beside the spectrum it describes, not in a
    # settings panel further down the page.
    _certificate_control(slot, recipe, draft, laser_wl_nm, key)

    if not _finds_peaks(recipe, slot.id):
        st.caption(_no_peak_finding_reason(recipe, slot.id))
        _show_slot(slot, draft, key)
        return problems

    # Controls fold away; the spectrum and its peaks stay visible, because
    # seeing them is the whole point of tuning the controls.
    with st.expander("Peak finding settings", icon=":material/graphic_eq:"):
        st.caption(
            "These apply to this material only, and no single set of values "
            "suits every instrument."
        )
        _peak_controls(slot, recipe, draft)
    _try_peaks(slot, recipe, draft, laser_wl_nm, key)
    return problems


#: A material name that appears in no known-materials list -- st.selectbox needs a
#: sentinel value distinct from any real material name to represent "something else".
_CUSTOM_MATERIAL = "__custom__"


@st.cache_data(ttl=300, show_spinner=False)
def _known_materials_cached(algorithm_id: str) -> list[dict]:
    """Cached wrapper over the engine's fetch -- called on every rerun a slot with an
    open material renders, and the list changes only when the service's own reference
    tables do."""
    from spectrastream.calibration.engines.remote import fetch_materials

    return fetch_materials(algorithm_id)


def _material_controls(
    slot: SpectrumSlot,
    recipe: RecipeSpec,
    draft: CalibrationDraft,
    entry: SlotInput,
    key: str,
) -> None:
    """Which reference material this entry holds, and its certified positions.

    Only for slots the recipe leaves open: a protocol that accepts any material
    cannot name it in advance, so the user does. Known materials -- the ones
    the service already holds a table for -- come from the service itself
    (GET /v1/algorithms/{id}/materials) as a dropdown, the same shape as the
    Verify page's REFERENCE_MATERIALS selector; anything else is entered as
    positions directly, same as Verify's "custom lines" option.
    """
    known = (
        _known_materials_cached(recipe.algorithm_id or "") if recipe.algorithm_id else []
    )
    if slot.material_required and not known:
        # Silent here is worse than silent in the log: a dropdown with nothing in it
        # but "Something else..." looks broken, not empty, unless it says why.
        st.caption(
            ":orange[Could not reach the calibration service for its known-materials "
            "list — every material will need to be entered by name below.]"
        )

    if slot.material_required:
        options = [m["name"] for m in known] + [_CUSTOM_MATERIAL]
        current = entry.material if entry.material in options else _CUSTOM_MATERIAL
        chosen = st.selectbox(
            "Reference material",
            options=options,
            index=options.index(current),
            format_func=lambda m: "Something else…" if m == _CUSTOM_MATERIAL else m,
            key=f"mat_{draft.recipe_id}_{key}",
            help=(
                "The material this spectrum is of, matched against the "
                "calibration service's own reference tables. Choose "
                "“Something else…” for a material it does not "
                "already know, and give its positions below."
            ),
        )
        if chosen == _CUSTOM_MATERIAL:
            # entry.material is only ever a real name or None here -- once a known
            # material is chosen it stops being an "unknown name" to prefill from.
            prefill = entry.material if entry.material not in options else ""
            material = st.text_input(
                "Material name",
                value=prefill or "",
                key=f"matname_{draft.recipe_id}_{key}",
            ).strip()
        else:
            material = chosen
        if material != (entry.material or ""):
            entry.material = material or None
            draft.clear_result()

    if not slot.accepts_reference_peaks:
        return

    # The material this slot actually resolves to -- named by the recipe when it is
    # fixed, chosen above when it is not -- so the caption below can say exactly whose
    # table applies instead of leaving "the service's own table" unspecified.
    resolved_material = slot.material or entry.material
    by_name = {m["name"]: m for m in known}
    known_peaks = (by_name.get(resolved_material) or {}).get("reference_peaks")

    if resolved_material and known_peaks and not entry.reference_peaks:
        st.caption(
            f"Using {resolved_material}’s known positions from the calibration "
            f"service ({len(known_peaks)} lines). Override them below if needed."
        )
    elif resolved_material and not known_peaks:
        st.caption(
            f"The calibration service has no known positions for "
            f"{resolved_material!r} — supply them below, or nothing will anchor "
            "this material."
        )

    with st.expander(
        "Reference peak positions",
        icon=":material/straighten:",
        expanded=bool(resolved_material) and not known_peaks,
    ):
        st.caption(
            "Certified positions for this material, one per line as "
            "`position` or `position, relative intensity`. Leave empty to use "
            f"the value above -- {resolved_material}'s table on the calibration "
            "service -- as-is."
            if resolved_material
            else "Certified positions for this material, one per line as "
            "`position` or `position, relative intensity`."
        )
        text = st.text_area(
            "Positions (cm⁻¹)",
            value=_peaks_to_text(entry.reference_peaks),
            key=f"refpk_{draft.recipe_id}_{key}",
            height=120,
            label_visibility="collapsed",
        )
        parsed, error = _parse_reference_peaks(text)
        if error:
            st.error(error, icon=":material/error:")
        elif parsed != entry.reference_peaks:
            entry.reference_peaks = parsed
            draft.clear_result()


def _peaks_to_text(peaks: dict[float, float] | None) -> str:
    if not peaks:
        return ""
    return "\n".join(f"{pos:g}, {weight:g}" for pos, weight in sorted(peaks.items()))


def _parse_reference_peaks(
    text: str,
) -> tuple[dict[float, float] | None, str | None]:
    """``{position: relative intensity}`` from one entry per line.

    Intensity is optional and defaults to 1.0 -- most certified tables give
    positions only, and a table of equal weights is exactly that.
    """
    peaks: dict[float, float] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p for p in line.replace(",", " ").split() if p]
        try:
            position = float(parts[0])
            weight = float(parts[1]) if len(parts) > 1 else 1.0
        except (ValueError, IndexError):
            return None, f"Line {lineno} is not a position: {raw.strip()!r}"
        if len(parts) > 2:
            return None, f"Line {lineno} has more than a position and intensity"
        peaks[position] = weight
    return (peaks or None), None


def _show_slot(
    slot: SpectrumSlot, draft: CalibrationDraft, key: str | None = None
) -> None:
    """The spectrum as the engine will receive it."""
    entry = draft.slots.get(key or slot.id)
    if entry is None or entry.merged is None:
        return
    show_spectrum(
        {entry.material or slot.label: (entry.merged.x, entry.merged.y)},
        height=240,
        x_title=x_title(entry.units),
    )


def _certificate_control(
    slot: SpectrumSlot,
    recipe: RecipeSpec,
    draft: CalibrationDraft,
    laser_wl_nm: float | None,
    key: str | None = None,
) -> None:
    """Which certified material this spectrum is, beside its upload."""
    from ramanchada2.protocols.calibration.ycalibration import CertificatesDict

    steps = [s for s in _steps_using(recipe, slot.id) if s.action == "y_intensity"]
    if not steps or laser_wl_nm is None:
        return
    try:
        available = list(CertificatesDict().get_certificates(int(laser_wl_nm)))
    except (KeyError, ValueError):
        available = []
    if not available:
        st.caption(f":orange[No intensity certificate exists for {laser_wl_nm:g} nm.]")
        return

    for step in steps:
        scope = draft.params.setdefault(step.id, {})
        current = scope.get("certificate", step.params.get("certificate"))
        chosen = st.selectbox(
            "Reference material certificate",
            options=available,
            index=available.index(current) if current in available else 0,
            key=f"cert_{recipe.id}_{step.id}",
            help="Which certified material this measured spectrum is.",
        )
        scope["certificate"] = _tracked(draft, current, chosen)


def _exposure_inputs(
    slot, draft: CalibrationDraft, entry: SlotInput, key: str | None = None
) -> None:
    """Exposure per file, so different exposures can be HDR-merged."""
    with st.expander(
        f"{len(entry.loaded)} acquisitions — how to combine them",
        icon=":material/layers:",
        expanded=True,
    ):
        st.caption(
            "Different exposure times are HDR-merged, so strong lines come "
            "from the short exposures that did not saturate and weak ones from "
            "the long exposures that could see them. Equal exposures are "
            "averaged instead."
        )
        for index, item in enumerate(entry.loaded):
            row = st.columns([2, 1])
            row[0].caption(item.filename)
            old = entry.exposures[index]
            new = (
                row[1].number_input(
                    "Exposure (ms)",
                    value=float(old or 0.0),
                    step=100.0,
                    key=f"exp_{draft.recipe_id}_{key or slot.id}_{index}",
                    label_visibility="collapsed" if index else "visible",
                )
                or None
            )
            entry.exposures[index] = _tracked(draft, old, new)


def _preprocess_controls(
    slot,
    recipe: RecipeSpec,
    draft: CalibrationDraft,
    entry: SlotInput,
    laser_wl_nm: float | None = None,
    key: str | None = None,
) -> None:
    """Toggles and parameters for the preprocessing this recipe offers."""
    if not slot.preprocess:
        return

    steps = entry.steps_for(slot)
    # Intensity calibration compares measured counts against a certified
    # response, so anything that rescales the measurement makes the comparison
    # meaningless. Peak-position steps do not care.
    intensity_step = any(
        s.produces == "y_response" for s in _steps_using(recipe, slot.id)
    )
    with st.expander("Preprocessing", icon=":material/tune:"):
        if intensity_step:
            offenders = destroys_intensity(steps)
            if offenders:
                st.warning(
                    f"**{', '.join(offenders)}** rescales the intensities, and "
                    "this spectrum is used for intensity calibration — which "
                    "compares measured counts against a certified response. "
                    "Turn it off, or the correction will be meaningless.",
                    icon=":material/warning:",
                )
        for index, step in enumerate(steps):
            widget_key = f"pp_{draft.recipe_id}_{key or slot.id}_{step.op}_{index}"
            old_enabled = step.enabled
            step.enabled = st.checkbox(
                step.display_label(), value=step.enabled, key=widget_key
            )
            if step.enabled != old_enabled:
                draft.clear_result()
            if not step.enabled:
                continue
            if step.op == "trim":
                low, high = entry.x_range()
                certified = certified_range(recipe, draft, slot.id, laser_wl_nm)
                if certified:
                    low, high = certified
                    st.caption(
                        f"Certified range {low:g}–{high:g} cm⁻¹ — the "
                        "certificate is only valid here."
                    )
                cols = st.columns(2)
                old_min = step.params.get("min", low)
                new_min = cols[0].number_input(
                    "From", value=float(old_min), key=f"{widget_key}_min"
                )
                step.params["min"] = _tracked(draft, old_min, new_min)
                old_max = step.params.get("max", high)
                new_max = cols[1].number_input(
                    "To", value=float(old_max), key=f"{widget_key}_max"
                )
                step.params["max"] = _tracked(draft, old_max, new_max)
            elif step.op == "baseline":
                cols = st.columns(2)
                methods = list(BASELINE_METHODS)
                current = str(step.params.get("method", "snip"))
                chosen_method = cols[0].selectbox(
                    "Method",
                    options=methods,
                    index=methods.index(current) if current in methods else 0,
                    key=f"{widget_key}_method",
                )
                step.params["method"] = _tracked(draft, current, chosen_method)
                old_niter = step.params.get("niter", 30)
                new_niter = cols[1].number_input(
                    "Iterations",
                    value=int(old_niter),
                    step=1,
                    key=f"{widget_key}_niter",
                )
                step.params["niter"] = _tracked(draft, old_niter, new_niter)
            elif step.op == "normalize":
                strategies = list(NORMALIZE_STRATEGIES)
                current = str(step.params.get("strategy", "minmax"))
                chosen_strategy = st.selectbox(
                    "Strategy",
                    options=strategies,
                    index=(strategies.index(current) if current in strategies else 0),
                    format_func=lambda s: NORMALIZE_LABELS.get(s, s),
                    key=f"{widget_key}_strategy",
                    help=(
                        "Min-max rescales to 0–1; area and density normalise "
                        "the integral; the L-norms divide by a vector norm."
                    ),
                )
                step.params["strategy"] = _tracked(draft, current, chosen_strategy)
            elif step.op == "smooth":
                cols = st.columns(2)
                methods = list(SMOOTH_METHODS)
                current = str(step.params.get("method", "savgol"))
                chosen_method = cols[0].selectbox(
                    "Method",
                    options=methods,
                    index=methods.index(current) if current in methods else 0,
                    key=f"{widget_key}_smethod",
                )
                step.params["method"] = _tracked(draft, current, chosen_method)
                if step.params["method"] == "savgol":
                    old_window = step.params.get("window_length", 5)
                    new_window = cols[1].number_input(
                        "Window",
                        value=int(old_window),
                        step=2,
                        min_value=3,
                        key=f"{widget_key}_win",
                    )
                    step.params["window_length"] = _tracked(
                        draft, old_window, new_window
                    )


def slot_uploaders(
    recipe: RecipeSpec, draft: CalibrationDraft, laser_wl_nm: float | None = None
) -> list[str]:
    """Render every slot. Returns messages for inputs that failed to load."""
    problems: list[str] = []
    for slot in recipe.slots:
        if not slot.repeatable:
            with st.container(border=True):
                problems.extend(_slot_uploader(slot, recipe, draft, laser_wl_nm))
            continue

        # A repeatable slot is filled once per material. Entries are never
        # combined with each other -- only the acquisitions within one are --
        # so each renders as its own independent uploader.
        count = draft.entry_counts.setdefault(slot.id, 1)
        for index in range(count):
            with st.container(border=True):
                key = entry_key(slot.id, index)
                st.caption(f"{slot.label} {index + 1} of {count}")
                problems.extend(
                    _slot_uploader(slot, recipe, draft, laser_wl_nm, key=key)
                )
        cols = st.columns(2)
        if cols[0].button(
            "Add another material",
            key=f"add_{draft.recipe_id}_{slot.id}",
            icon=":material/add:",
        ):
            draft.entry_counts[slot.id] = count + 1
            st.rerun()
        if count > 1 and cols[1].button(
            "Remove last",
            key=f"del_{draft.recipe_id}_{slot.id}",
            icon=":material/remove:",
        ):
            draft.slots.pop(entry_key(slot.id, count - 1), None)
            draft.entry_counts[slot.id] = count - 1
            draft.clear_result()
            st.rerun()
    return problems


def resolve_inputs(recipe: RecipeSpec, draft: CalibrationDraft) -> list[str]:
    """Ensure every slot has been merged and preprocessed.

    The uploaders already resolve each slot as it renders; this catches any
    that did not (a slot whose uploader was not reached) and returns whatever
    went wrong.
    """
    problems = []
    for slot in recipe.slots:
        entry = draft.slots.get(slot.id)
        if entry is None or not entry.loaded or entry.merged is not None:
            continue
        problem = _resolve_slot(slot, draft)
        if problem:
            problems.append(problem)
    return problems


def preview(recipe: RecipeSpec, draft: CalibrationDraft) -> None:
    """Show what the engine will actually receive, not what was uploaded.

    One chart per unit system. A neon spectrum in nm and a silicon one in cm-1
    share no x axis, and drawing them together under a single label would be a
    plot nobody can read -- the numbers do not mean the same thing.
    """
    groups = draft.unit_groups()
    for units, keys in groups.items():
        # A repeatable slot's entries share one label but hold different materials, so
        # the series label is the entry's material where it has one -- falling back to
        # the slot label only distinguishes entries when there is just one of them.
        series: dict[str, Any] = {
            _series_label(recipe, draft, key): (
                draft.slots[key].merged.x,
                draft.slots[key].merged.y,
            )
            for key in keys
        }
        if len(groups) > 1:
            st.caption(f"**{UNIT_LABELS.get(units, units)}**")
        show_spectrum(series, height=260, x_title=x_title(units))
    for key, notes in draft.provenance.items():
        if len(notes) > 1 or notes[0] != "single acquisition":
            st.caption(f"{_series_label(recipe, draft, key)}: " + " → ".join(notes))


def _series_label(recipe: RecipeSpec, draft: CalibrationDraft, key: str) -> str:
    entry = draft.slots.get(key)
    if entry is not None and entry.material:
        return entry.material
    label = recipe.slot(key).label
    return label if key == slot_id_of(key) else f"{label} ({key})"


def step_overview(recipe: RecipeSpec, draft: CalibrationDraft) -> None:
    """Show which steps will run, before anything is fitted."""
    # A repeatable slot's available entries are keyed "anchor#0", "anchor#1", ... -- any
    # one of them present counts as the plain slot id "anchor" being satisfied.
    available = {slot_id_of(s) for s in draft.available_slots()}
    for step in recipe.steps:
        missing = [s for s in step.inputs if s not in available]
        if not missing:
            st.markdown(f":material/check_circle: **{step.label}**")
        elif step.optional:
            names = ", ".join(recipe.slot(s).label for s in missing)
            st.markdown(
                f":material/remove_circle_outline: {step.label} — "
                f":gray[will be skipped, no {names}]"
            )
        else:
            names = ", ".join(recipe.slot(s).label for s in missing)
            st.markdown(f":material/error: {step.label} — :red[needs {names}]")


def parameter_controls(recipe: RecipeSpec, draft: CalibrationDraft) -> None:
    """Per-step overrides for the parameters an engine exposes.

    Peak finding is tuned per instrument in the VAMAS pipeline, so the same
    levers are offered here rather than buried in the recipe. Without them, an
    error message advising "raise the prominence" names something the user
    cannot reach.
    """
    for step in recipe.steps:
        if not any(k in TUNABLES for k in step.params):
            continue

        st.markdown(f"**{step.label}**")
        scope = draft.params.setdefault(step.id, {})

        for name, current in step.params.items():
            if name not in TUNABLES:
                continue
            title, choices, help_text = TUNABLES[name]
            value = scope.get(name, current)
            index = choices.index(value) if value in choices else 0
            chosen = st.selectbox(
                title,
                options=choices,
                index=index,
                key=f"param_{recipe.id}_{step.id}_{name}",
                help=help_text,
            )
            scope[name] = _tracked(draft, value, chosen)


def certificate_control(
    recipe: RecipeSpec, draft: CalibrationDraft, laser_wl_nm: float | None
) -> None:
    """Choose which standard reference material certificate to calibrate against.

    There are several per wavelength -- NIST SRM glasses and calibrated LED
    sources -- and they are not interchangeable: the response function is
    specific to the material in front of the instrument.
    """
    from ramanchada2.protocols.calibration.ycalibration import CertificatesDict

    y_steps = [s for s in recipe.steps if s.action == "y_intensity"]
    if not y_steps or laser_wl_nm is None:
        return

    try:
        available = list(CertificatesDict().get_certificates(int(laser_wl_nm)))
    except (KeyError, ValueError):
        available = []
    if not available:
        st.caption(
            f":orange[No intensity-calibration certificate is available for "
            f"{laser_wl_nm:g} nm.]"
        )
        return

    for step in y_steps:
        scope = draft.params.setdefault(step.id, {})
        current = scope.get("certificate", step.params.get("certificate"))
        scope["certificate"] = st.selectbox(
            "Reference material certificate",
            options=available,
            index=available.index(current) if current in available else 0,
            key=f"cert_{recipe.id}_{step.id}",
            help="Which certified material the measured reference spectrum is.",
        )
