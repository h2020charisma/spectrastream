"""Derive a calibration and attach it to an optical path.

Everything below the path selector is generated from the chosen recipe: which
reference spectra to ask for, which steps will run, and which can be skipped.
Swapping in a protocol that needs different materials -- or a different engine
entirely -- changes the YAML, not this file.

A calibration attaches to an optical path rather than to the instrument,
because that is the level at which it is valid: change the grating and the
correction changes; change the wavelength and even the reference lines differ.
"""

import streamlit as st

from spectrastream.calibration import (
    CalibrationContext,
    CalibrationError,
    all_recipes,
    engine_for_recipe,
    get_recipe,
)
from spectrastream.profiles import CalibrationRecord, SourceFile
from ui import profile_store
from ui.charts import show_spectrum
from ui.recipe_form import (
    certificate_control,
    parameter_controls,
    preview,
    resolve_inputs,
    slot_uploaders,
    step_overview,
)
from ui.state import get_state

state = get_state()
draft = state.draft
profile = state.active_profile

# --- which instrument -------------------------------------------------------

if not state.library.profiles:
    st.info(
        "A calibration belongs to an **optical path**, so it needs one to "
        "attach to. Create an instrument on the Instruments page — a name is "
        "enough to start.",
        icon=":material/precision_manufacturing:",
    )
    st.stop()

profile_ids = [p.id for p in state.library.profiles]
chosen = st.selectbox(
    "Instrument",
    options=profile_ids,
    index=(
        profile_ids.index(state.active_profile_id)
        if state.active_profile_id in profile_ids
        else 0
    ),
    format_func=lambda pid: state.library.get(pid).name,
)
state.set_active_profile(chosen)
profile = state.active_profile

if not profile.optical_paths:
    st.warning(
        f"**{profile.name}** has no optical path yet. Add one on the "
        "Instruments page — the wavelength and optics a calibration depends on "
        "live there, not on the instrument.",
        icon=":material/warning:",
    )
    st.stop()

# A calibration is only valid for one configuration: change the grating and the
# correction changes, change the wavelength and even the reference lines do.
path_ids = [p.id for p in profile.optical_paths]
chosen_path = st.selectbox(
    "Optical path",
    options=path_ids,
    index=(
        path_ids.index(state.active_optical_path_id)
        if state.active_optical_path_id in path_ids
        else 0
    ),
    format_func=lambda pid: (
        f"{profile.optical_path(pid).op_id} · {profile.optical_path(pid).describe()}"
    ),
)
state.set_active_optical_path(chosen_path)
optical_path = profile.optical_path(chosen_path)

if optical_path.laser_wl_nm is None:
    st.warning(
        f"Optical path **{optical_path.op_id}** has no laser wavelength. Most "
        "protocols need one to look up reference lines — add it on the "
        "Instruments page.",
        icon=":material/warning:",
    )

# --- which protocol ---------------------------------------------------------

recipes = [r for r in all_recipes() if r.supports_wavelength(optical_path.laser_wl_nm)]
if not recipes:
    st.error(
        f"No calibration protocol supports {optical_path.laser_wl_nm:g} nm.",
        icon=":material/error:",
    )
    st.stop()

recipe_ids = [r.id for r in recipes]
labels = {r.id: r.label for r in recipes}
selected_id = st.segmented_control(
    "Protocol",
    options=recipe_ids,
    format_func=lambda rid: labels[rid],
    default=draft.recipe_id if draft.recipe_id in recipe_ids else recipe_ids[0],
)
if selected_id is None:
    selected_id = recipe_ids[0]
if selected_id != draft.recipe_id:
    draft.recipe_id = selected_id
    draft.reset()

recipe = get_recipe(draft.recipe_id)
st.caption(recipe.description.strip())

# --- reference spectra, straight from the recipe ----------------------------

st.subheader("Reference spectra")
for problem in slot_uploaders(recipe, draft):
    st.error(problem, icon=":material/error:")

# Merge and preprocess now, so the plot shows what the engine will receive
# rather than what was uploaded.
for problem in resolve_inputs(recipe, draft):
    st.error(problem, icon=":material/error:")
preview(recipe, draft)

st.subheader("Steps")
step_overview(recipe, draft)

with st.expander("Advanced settings", icon=":material/tune:"):
    certificate_control(recipe, draft, optical_path.laser_wl_nm)
    parameter_controls(recipe, draft)

# --- fit --------------------------------------------------------------------

missing = recipe.missing_required_slots(draft.available_slots())
if st.button(
    "Derive calibration",
    type="primary",
    icon=":material/play_arrow:",
    disabled=bool(missing),
):
    engine = engine_for_recipe(recipe)
    context = CalibrationContext(
        laser_wl_nm=optical_path.laser_wl_nm,
        instrument={**profile.instrument_metadata(), **optical_path.metadata()},
        # Each slot carries the units the user declared for it; a neon lamp in
        # nm alongside a silicon wafer in cm-1 is perfectly ordinary.
        input_units=draft.input_units(),
    )
    with st.status("Deriving calibration…", expanded=False) as status:
        try:
            draft.fitted = engine.fit(
                recipe, draft.engine_inputs(), context, params=draft.params
            )
            draft.error = None
            draft.detail = None
            status.update(label="Calibration derived", state="complete")
        except CalibrationError as err:
            draft.fitted = None
            draft.error = str(err)
            draft.detail = getattr(err, "detail", None)
            status.update(label="Could not derive a calibration", state="error")

if missing:
    names = ", ".join(recipe.slot(s).label for s in missing)
    st.caption(f"Waiting for: {names}")

if draft.error:
    st.error(draft.error, icon=":material/error:")
    if draft.detail:
        with st.expander("Technical detail", icon=":material/bug_report:"):
            st.code(draft.detail)

# --- results ----------------------------------------------------------------

fitted = draft.fitted
if fitted is None:
    st.stop()

st.subheader("Result")
for outcome in fitted.outcomes():
    if outcome.status == "applied":
        st.markdown(
            f":material/check_circle: **{outcome.label}** — :gray[{outcome.detail}]"
        )
    elif outcome.status == "skipped":
        st.markdown(
            f":material/remove_circle_outline: {outcome.label} — "
            f":gray[skipped, {outcome.detail}]"
        )
    else:
        st.markdown(f":material/error: {outcome.label} — :red[{outcome.detail}]")

# Show the effect on whichever reference spectrum drove the first step.
primary_id = next(iter(draft.available_slots()), None)
if primary_id is not None:
    entry = draft.slots[primary_id]
    corrected = fitted.apply(entry.merged, spe_units=entry.units)
    show_spectrum(
        {
            "Before": (entry.merged.x, entry.merged.y),
            "After": (corrected.x, corrected.y),
        },
        height=280,
        caption="Effect of the calibration on the reference spectrum it came from.",
    )

with st.expander("Diagnostics", icon=":material/query_stats:"):
    diagnostics = fitted.diagnostics()
    if not diagnostics:
        st.caption("This engine reported no diagnostics.")
    for diagnostic in diagnostics:
        st.markdown(f"**{diagnostic.label}** — {diagnostic.text or ''}")
        if diagnostic.table is not None and not diagnostic.table.empty:
            st.dataframe(diagnostic.table, width="stretch", height=220)
        if diagnostic.curve is not None:
            xs, ys = diagnostic.curve
            show_spectrum({diagnostic.label: (xs, ys)}, height=200)

# --- save -------------------------------------------------------------------

st.subheader("Save to optical path")
with st.form("save_calibration"):
    default_label = f"{recipe.label} · {len(optical_path.calibrations) + 1}"
    label = st.text_input("Label", value=default_label)
    notes = st.text_area("Notes (optional)", value="", height=80)
    saved = st.form_submit_button(
        f"Save to {profile.name} · {optical_path.op_id}",
        type="primary",
        icon=":material/save:",
    )

if saved:
    record = CalibrationRecord(
        label=label.strip() or default_label,
        recipe_id=recipe.id,
        engine_id=fitted.engine_id,
        laser_wl_nm=optical_path.laser_wl_nm,
        sources=[
            SourceFile(slot=sid, filename=item.filename, sha256=item.sha256)
            for sid, item in draft.source_files()
        ],
        model=fitted.to_dict(),
        steps=[
            {
                "step_id": o.step_id,
                "label": o.label,
                "status": o.status,
                "detail": o.detail,
            }
            for o in fitted.outcomes()
        ],
        notes=notes.strip(),
    )
    optical_path.add_calibration(record)
    profile.add_optical_path(optical_path)
    state.library.upsert(profile)
    st.toast(
        f"Saved to {profile.name} · {optical_path.op_id}",
        icon=":material/check_circle:",
    )
    profile_store.save(state)
