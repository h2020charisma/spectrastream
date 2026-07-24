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
from ui.charts import show_spectrum, x_title
from ui.state import CalibrationDraft, SlotInput

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
        scope["prominence_coeff"] = cols[2].number_input(
            "Prominence × noise",
            value=float(
                scope.get("prominence_coeff", step.params.get("prominence_coeff", 3))
            ),
            step=0.5,
            min_value=0.5,
            key=f"find_{recipe.id}_{step.id}_prom",
            help="How far above the noise a candidate must stand.",
        )
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
        scope["find_kw"] = current

        if "should_fit" in step.params:
            scope["should_fit"] = st.checkbox(
                "Fit peak shapes",
                value=bool(scope.get("should_fit", step.params["should_fit"])),
                key=f"fit_{recipe.id}_{step.id}",
                help=(
                    "Fit a profile to each candidate for a sub-pixel position "
                    "instead of taking it as found. Slower."
                ),
            )


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


def _resolve_slot(slot: SpectrumSlot, draft: CalibrationDraft) -> str | None:
    """Merge and preprocess one slot into the spectrum the engine will see.

    Called from the uploader rather than only from resolve_inputs, because the
    peak panel below needs `merged` on the *same* run the file arrives. Doing
    it later meant a freshly uploaded spectrum showed "upload a spectrum" until
    something else forced a rerun.
    """
    entry = draft.slots.get(slot.id)
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
    draft.provenance[slot.id] = [how, *applied]
    return None


def _try_peaks(
    slot: SpectrumSlot,
    recipe: RecipeSpec,
    draft: CalibrationDraft,
    laser_wl_nm: float | None,
) -> None:
    """Show what ramanchada2's fit_peaks does with the current settings.

    Finding is cheap and runs on every change; fitting is what takes time, so
    it is asked for explicitly.
    """
    entry = draft.slots.get(slot.id)
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
            key=f"prof_{recipe.id}_{slot.id}",
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
        key=f"try_{recipe.id}_{slot.id}",
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
) -> list[str]:
    """One slot: files, units, exposures, preprocessing. Returns problems."""
    problems: list[str] = []
    entry = draft.slots.setdefault(slot.id, SlotInput(units=slot.units))

    label = slot.label if slot.required else f"{slot.label} (optional)"
    uploaded = st.file_uploader(
        label,
        key=f"slot_{draft.recipe_id}_{slot.id}",
        accept_multiple_files=slot.accept_multiple,
        help=slot.help,
    )
    files = uploaded if slot.accept_multiple else ([uploaded] if uploaded else [])
    files = [f for f in files if f is not None]

    if not files:
        entry.loaded = []
        entry.merged = None
        return problems

    names = [f.name for f in files]
    if names != [item.filename for item in entry.loaded]:
        entry.loaded = []
        for handle in files:
            try:
                entry.loaded.append(
                    load_spectrum(handle.getvalue(), handle.name, units=entry.units)
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
        key=f"units_{draft.recipe_id}_{slot.id}",
    )
    if chosen_units != entry.units:
        entry.units = chosen_units
        for item in entry.loaded:
            item.units = chosen_units
        draft.clear_result()

    if len(entry.loaded) > 1:
        _exposure_inputs(slot, draft, entry)

    _preprocess_controls(slot, recipe, draft, entry)

    problem = _resolve_slot(slot, draft)
    if problem:
        problems.append(problem)

    with st.expander("Peak finding", icon=":material/graphic_eq:"):
        st.caption(
            "These apply to this material only, and no single set of values "
            "suits every instrument -- try them here and see what the fit gets."
        )
        _peak_controls(slot, recipe, draft)
        _try_peaks(slot, recipe, draft, laser_wl_nm)
    return problems


def _exposure_inputs(slot, draft: CalibrationDraft, entry: SlotInput) -> None:
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
            entry.exposures[index] = (
                row[1].number_input(
                    "Exposure (ms)",
                    value=float(entry.exposures[index] or 0.0),
                    step=100.0,
                    key=f"exp_{draft.recipe_id}_{slot.id}_{index}",
                    label_visibility="collapsed" if index else "visible",
                )
                or None
            )


def _preprocess_controls(
    slot, recipe: RecipeSpec, draft: CalibrationDraft, entry: SlotInput
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
            key = f"pp_{draft.recipe_id}_{slot.id}_{step.op}_{index}"
            step.enabled = st.checkbox(
                step.display_label(), value=step.enabled, key=key
            )
            if not step.enabled:
                continue
            if step.op == "trim":
                low, high = entry.x_range()
                cols = st.columns(2)
                step.params["min"] = cols[0].number_input(
                    "From", value=float(step.params.get("min", low)), key=f"{key}_min"
                )
                step.params["max"] = cols[1].number_input(
                    "To", value=float(step.params.get("max", high)), key=f"{key}_max"
                )
            elif step.op == "baseline":
                cols = st.columns(2)
                methods = list(BASELINE_METHODS)
                current = str(step.params.get("method", "snip"))
                step.params["method"] = cols[0].selectbox(
                    "Method",
                    options=methods,
                    index=methods.index(current) if current in methods else 0,
                    key=f"{key}_method",
                )
                step.params["niter"] = cols[1].number_input(
                    "Iterations",
                    value=int(step.params.get("niter", 30)),
                    step=1,
                    key=f"{key}_niter",
                )
            elif step.op == "normalize":
                strategies = list(NORMALIZE_STRATEGIES)
                current = str(step.params.get("strategy", "minmax"))
                step.params["strategy"] = st.selectbox(
                    "Strategy",
                    options=strategies,
                    index=(strategies.index(current) if current in strategies else 0),
                    format_func=lambda s: NORMALIZE_LABELS.get(s, s),
                    key=f"{key}_strategy",
                    help=(
                        "Min-max rescales to 0–1; area and density normalise "
                        "the integral; the L-norms divide by a vector norm."
                    ),
                )
            elif step.op == "smooth":
                cols = st.columns(2)
                methods = list(SMOOTH_METHODS)
                current = str(step.params.get("method", "savgol"))
                step.params["method"] = cols[0].selectbox(
                    "Method",
                    options=methods,
                    index=methods.index(current) if current in methods else 0,
                    key=f"{key}_smethod",
                )
                if step.params["method"] == "savgol":
                    step.params["window_length"] = cols[1].number_input(
                        "Window",
                        value=int(step.params.get("window_length", 5)),
                        step=2,
                        min_value=3,
                        key=f"{key}_win",
                    )


def slot_uploaders(
    recipe: RecipeSpec, draft: CalibrationDraft, laser_wl_nm: float | None = None
) -> list[str]:
    """Render every slot. Returns messages for inputs that failed to load."""
    problems: list[str] = []
    for slot in recipe.slots:
        with st.container(border=True):
            problems.extend(_slot_uploader(slot, recipe, draft, laser_wl_nm))
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
    for units, slot_ids in groups.items():
        series: dict[str, Any] = {
            recipe.slot(sid).label: (
                draft.slots[sid].merged.x,
                draft.slots[sid].merged.y,
            )
            for sid in slot_ids
        }
        if len(groups) > 1:
            st.caption(f"**{UNIT_LABELS.get(units, units)}**")
        show_spectrum(series, height=260, x_title=x_title(units))
    for slot_id, notes in draft.provenance.items():
        if len(notes) > 1 or notes[0] != "single acquisition":
            st.caption(f"{recipe.slot(slot_id).label}: " + " → ".join(notes))


def step_overview(recipe: RecipeSpec, draft: CalibrationDraft) -> None:
    """Show which steps will run, before anything is fitted."""
    available = draft.available_slots()
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
            scope[name] = st.selectbox(
                title,
                options=choices,
                index=index,
                key=f"param_{recipe.id}_{step.id}_{name}",
                help=help_text,
            )


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
