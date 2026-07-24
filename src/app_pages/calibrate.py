"""Derive a calibration and attach it to an instrument profile.

The whole page is generated from the selected recipe: which reference spectra
to ask for, which steps will run, and which of them can be skipped. Swapping in
a protocol that needs different materials -- or a different engine entirely --
changes the YAML, not this file.
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
from ui.recipe_form import parameter_controls, slot_uploaders, step_overview
from ui.state import get_state

state = get_state()
draft = state.draft
profile = state.active_profile

# --- which instrument -------------------------------------------------------

if not state.library.profiles:
    st.info(
        "Calibration is derived **for an instrument**, so it needs a profile "
        "to belong to. Create one on the Instruments page — a name is enough.",
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

if profile.laser_wl_nm is None:
    st.warning(
        f"**{profile.name}** has no laser wavelength recorded. Most protocols "
        "need one to look up reference lines — add it on the Instruments page.",
        icon=":material/warning:",
    )

# --- which protocol ---------------------------------------------------------

recipes = [r for r in all_recipes() if r.supports_wavelength(profile.laser_wl_nm)]
if not recipes:
    st.error(
        f"No calibration protocol supports {profile.laser_wl_nm:g} nm.",
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
    draft.inputs.clear()
    draft.params.clear()
    draft.clear_result()

recipe = get_recipe(draft.recipe_id)
st.caption(recipe.description.strip())

# --- reference spectra, straight from the recipe ----------------------------

st.subheader("Reference spectra")
for problem in slot_uploaders(recipe, draft):
    st.error(problem, icon=":material/error:")

if draft.inputs:
    show_spectrum(
        {
            f"{recipe.slot(sid).label}": (loaded.spectrum.x, loaded.spectrum.y)
            for sid, loaded in draft.inputs.items()
        },
        height=260,
    )

st.subheader("Steps")
step_overview(recipe, draft)

with st.expander("Advanced settings", icon=":material/tune:"):
    parameter_controls(recipe, draft)

# --- fit --------------------------------------------------------------------

missing = recipe.missing_required_slots(set(draft.inputs))
if st.button(
    "Derive calibration",
    type="primary",
    icon=":material/play_arrow:",
    disabled=bool(missing),
):
    engine = engine_for_recipe(recipe)
    context = CalibrationContext(
        laser_wl_nm=profile.laser_wl_nm,
        instrument=profile.instrument_metadata(),
    )
    with st.status("Deriving calibration…", expanded=False) as status:
        try:
            draft.fitted = engine.fit(
                recipe,
                {sid: loaded.spectrum for sid, loaded in draft.inputs.items()},
                context,
                params=draft.params,
            )
            draft.error = None
            status.update(label="Calibration derived", state="complete")
        except CalibrationError as err:
            draft.fitted = None
            draft.error = str(err)
            status.update(label="Could not derive a calibration", state="error")

if missing:
    names = ", ".join(recipe.slot(s).label for s in missing)
    st.caption(f"Waiting for: {names}")

if draft.error:
    st.error(draft.error, icon=":material/error:")

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
primary = next(iter(draft.inputs.values()), None)
if primary is not None:
    corrected = fitted.apply(primary.spectrum, spe_units=primary.units)
    show_spectrum(
        {
            "Before": (primary.spectrum.x, primary.spectrum.y),
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

st.subheader("Save to instrument")
with st.form("save_calibration"):
    default_label = f"{recipe.label} · {len(profile.calibrations) + 1}"
    label = st.text_input("Label", value=default_label)
    notes = st.text_area("Notes (optional)", value="", height=80)
    saved = st.form_submit_button(
        f"Save to {profile.name}", type="primary", icon=":material/save:"
    )

if saved:
    record = CalibrationRecord(
        label=label.strip() or default_label,
        recipe_id=recipe.id,
        engine_id=fitted.engine_id,
        laser_wl_nm=profile.laser_wl_nm,
        sources=[
            SourceFile(slot=sid, filename=loaded.filename, sha256=loaded.sha256)
            for sid, loaded in draft.inputs.items()
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
    profile.add_calibration(record)
    state.library.upsert(profile)
    st.toast(f"Saved to {profile.name}", icon=":material/check_circle:")
    profile_store.save(state)
