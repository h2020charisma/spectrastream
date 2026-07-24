"""Render calibration inputs from a recipe.

Nothing here knows what neon or silicon are. The uploaders, their labels, their
help text and which of them are mandatory all come from the recipe, so adding a
protocol that needs entirely different reference materials needs no UI change.
"""

import streamlit as st

from spectrastream.calibration.spec import RecipeSpec
from spectrastream.ingest import IngestError, load_spectrum
from ui.state import CalibrationDraft

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


def slot_uploaders(recipe: RecipeSpec, draft: CalibrationDraft) -> list[str]:
    """One uploader per slot. Returns messages for files that failed to load."""
    problems: list[str] = []

    for slot in recipe.slots:
        label = slot.label if slot.required else f"{slot.label} (optional)"
        uploaded = st.file_uploader(
            label,
            key=f"slot_{recipe.id}_{slot.id}",
            accept_multiple_files=False,
            help=slot.help,
        )
        if uploaded is None:
            draft.inputs.pop(slot.id, None)
            continue

        existing = draft.inputs.get(slot.id)
        if existing is not None and existing.filename == uploaded.name:
            continue
        try:
            draft.inputs[slot.id] = load_spectrum(
                uploaded.getvalue(), uploaded.name, units=slot.units
            )
            draft.clear_result()
        except IngestError as err:
            draft.inputs.pop(slot.id, None)
            problems.append(str(err))

    return problems


def step_overview(recipe: RecipeSpec, draft: CalibrationDraft) -> None:
    """Show which steps will run, before anything is fitted."""
    available = set(draft.inputs)
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
    """Per-step overrides for the parameters an engine exposes."""
    for step in recipe.steps:
        tunable = {k: v for k, v in step.params.items() if k in TUNABLES}
        if not tunable:
            continue
        st.markdown(f"**{step.label}**")
        scope = draft.params.setdefault(step.id, {})
        for name, current in tunable.items():
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
