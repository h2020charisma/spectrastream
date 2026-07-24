"""Instruments and their optical paths, stored in this browser.

Two levels, because that is how a lab works. The instrument is the box; an
optical path is one configuration of it — wavelength, grating, objective, slit
— and one instrument commonly has several. Calibrations hang off the path, not
the instrument: a correction derived at 532 nm says nothing about a 785 nm path.

Only names are required. Demanding a serial number before someone can export a
file would defeat the point of the floor.
"""

import streamlit as st

from spectrastream.profiles import (
    InstrumentProfile,
    OpticalPath,
    export_bytes,
    import_bytes,
    merge,
)
from ui import profile_store
from ui.state import get_state

state = get_state()
library = state.library

if not state.storage_persistent:
    st.warning(
        "This browser is blocking local storage (private browsing, or a "
        "privacy setting). Profiles will work for this session but will be "
        "lost when you close the tab — use **Export** to keep them.",
        icon=":material/warning:",
    )


@st.dialog("Instrument", width="large")
def edit_profile(profile: InstrumentProfile | None):
    creating = profile is None
    draft = profile or InstrumentProfile(name="")

    with st.form("profile_form"):
        name = st.text_input(
            "Name",
            value=draft.name,
            placeholder="e.g. Lab 2 WITec",
            help="The only required field.",
        )
        cols = st.columns(2)
        vendor = cols[0].text_input("Make", value=draft.vendor or "")
        model = cols[1].text_input("Model", value=draft.model or "")
        cols = st.columns(2)
        serial = cols[0].text_input("Serial number", value=draft.serial or "")
        device_type = cols[1].text_input("Device type", value=draft.device_type or "")

        submitted = st.form_submit_button(
            "Create instrument" if creating else "Save changes",
            type="primary",
            icon=":material/save:",
        )

    if submitted:
        if not name.strip():
            st.error("A name is required.", icon=":material/error:")
            return
        draft.name = name.strip()
        draft.vendor = vendor.strip() or None
        draft.model = model.strip() or None
        draft.serial = serial.strip() or None
        draft.device_type = device_type.strip() or None

        if creating and not draft.optical_paths:
            # An instrument with no path cannot export or calibrate, so give
            # it one rather than leaving a dead end.
            draft.add_optical_path(OpticalPath(op_id="OP1"))

        library.upsert(draft)
        state.set_active_profile(draft.id)
        profile_store.save(state)


@st.dialog("Optical path", width="large")
def edit_optical_path(profile: InstrumentProfile, path: OpticalPath | None):
    creating = path is None
    draft = path or OpticalPath(op_id=profile.next_op_id())

    st.caption(
        f"A configuration of **{profile.name}**. Record one per combination of "
        "wavelength, grating and optics — each calibrates separately."
    )

    with st.form("optical_path_form"):
        cols = st.columns(2)
        op_id = cols[0].text_input(
            "Identifier",
            value=draft.op_id,
            help="How measurements cite this path, e.g. OP1.",
        )
        laser = cols[1].number_input(
            "Laser wavelength (nm)",
            value=float(draft.laser_wl_nm) if draft.laser_wl_nm else 0.0,
            step=1.0,
            format="%.2f",
            help="Needed to export NeXus and to derive a calibration.",
        )

        cols = st.columns(2)
        grating = cols[0].text_input("Grating (l/mm)", value=draft.grating or "")
        slit = cols[1].text_input("Slit size (µm)", value=draft.slit or "")
        cols = st.columns(2)
        pin_hole = cols[0].text_input("Pin hole size", value=draft.pin_hole_size or "")
        optics = cols[1].text_input(
            "Collection optics", value=draft.collection_optics or ""
        )
        cols = st.columns(2)
        fibre = cols[0].text_input(
            "Collection fibre diameter (mm)",
            value=draft.collection_fibre_diameter_mm or "",
        )
        max_power = cols[1].number_input(
            "Max laser power (mW)",
            value=float(draft.max_laser_power_mw or 0.0),
            step=1.0,
        )
        spectral_range = st.text_input(
            "Spectral range / scanning mode", value=draft.spectral_range or ""
        )
        notes = st.text_area("Notes", value=draft.notes or "", height=68)

        submitted = st.form_submit_button(
            "Add optical path" if creating else "Save changes",
            type="primary",
            icon=":material/save:",
        )

    if submitted:
        if not op_id.strip():
            st.error("An identifier is required.", icon=":material/error:")
            return
        draft.op_id = op_id.strip()
        draft.laser_wl_nm = float(laser) if laser else None
        draft.grating = grating.strip() or None
        draft.slit = slit.strip() or None
        draft.pin_hole_size = pin_hole.strip() or None
        draft.collection_optics = optics.strip() or None
        draft.collection_fibre_diameter_mm = fibre.strip() or None
        draft.max_laser_power_mw = float(max_power) if max_power else None
        draft.spectral_range = spectral_range.strip() or None
        draft.notes = notes.strip() or None

        profile.add_optical_path(draft)
        library.upsert(profile)
        state.set_active_profile(profile.id)
        state.set_active_optical_path(draft.id)
        profile_store.save(state)


header = st.container(horizontal=True)
header.button(
    "New instrument",
    icon=":material/add:",
    type="primary",
    on_click=lambda: edit_profile(None),
)

if not library.profiles:
    st.info(
        "No instruments yet. You do not need one to convert a spectrum — an "
        "instrument just records metadata for the file, and gives optical "
        "paths and their calibrations somewhere to live.",
        icon=":material/precision_manufacturing:",
    )

for profile in library.profiles:
    with st.container(border=True):
        top = st.container(horizontal=True, vertical_alignment="center")
        top.markdown(f"### {profile.name}")
        if profile.id == state.active_profile_id:
            top.badge("Selected", icon=":material/check:", color="green")
        st.caption(profile.describe())

        if not profile.optical_paths:
            st.caption(
                ":orange[No optical path recorded — needed to export NeXus "
                "and to calibrate.]"
            )

        for path in profile.optical_paths:
            with st.container(border=True):
                line = st.container(horizontal=True, vertical_alignment="center")
                line.markdown(f"**{path.op_id}**")
                line.caption(path.describe())
                if path.laser_wl_nm is None:
                    line.badge("No wavelength", color="orange")

                for record in path.calibrations:
                    row = st.container(horizontal=True, vertical_alignment="center")
                    row.markdown(
                        f":material/tune: {record.label} · "
                        f"`{record.recipe_id}` · {record.created:%Y-%m-%d}"
                    )
                    if record.id == path.active_calibration_id:
                        row.badge("Active", color="blue")
                    elif row.button("Use this", key=f"act_{path.id}_{record.id}"):
                        path.active_calibration_id = record.id
                        library.upsert(profile)
                        profile_store.save(state)
                    if row.button(
                        "",
                        icon=":material/delete:",
                        key=f"delcal_{path.id}_{record.id}",
                        help="Remove this calibration",
                    ):
                        path.remove_calibration(record.id)
                        library.upsert(profile)
                        profile_store.save(state)
                    if record.skipped_step_labels:
                        st.caption(
                            "Steps not applied: "
                            + ", ".join(record.skipped_step_labels)
                        )

                path_actions = st.container(horizontal=True)
                path_actions.button(
                    "Edit path",
                    icon=":material/edit:",
                    key=f"editop_{path.id}",
                    on_click=edit_optical_path,
                    args=(profile, path),
                )
                if path_actions.button(
                    "Select",
                    icon=":material/check_circle:",
                    key=f"selop_{path.id}",
                    disabled=(
                        profile.id == state.active_profile_id
                        and path.id == state.active_optical_path_id
                    ),
                ):
                    state.set_active_profile(profile.id)
                    state.set_active_optical_path(path.id)
                    st.rerun()
                if path_actions.button(
                    "Delete path",
                    icon=":material/delete:",
                    key=f"delop_{path.id}",
                ):
                    profile.remove_optical_path(path.id)
                    library.upsert(profile)
                    profile_store.save(state)

        actions = st.container(horizontal=True)
        actions.button(
            "Add optical path",
            icon=":material/add:",
            key=f"addop_{profile.id}",
            on_click=edit_optical_path,
            args=(profile, None),
        )
        actions.button(
            "Edit instrument",
            icon=":material/edit:",
            key=f"edit_{profile.id}",
            on_click=edit_profile,
            args=(profile,),
        )
        if actions.button(
            "Delete instrument",
            icon=":material/delete:",
            key=f"delete_{profile.id}",
        ):
            library.remove(profile.id)
            if state.active_profile_id == profile.id:
                state.set_active_profile(None)
            profile_store.save(state)


st.subheader("Backup")
st.caption(
    "Profiles live in this browser only. Clearing site data removes them, and "
    "they do not follow you to another machine — export to keep a copy."
)

backup = st.container(horizontal=True)
backup.download_button(
    "Export profiles",
    data=export_bytes(library),
    file_name="spectrastream-profiles.json",
    mime="application/json",
    icon=":material/download:",
    disabled=not library.profiles,
)

imported = st.file_uploader(
    "Import profiles",
    type=["json"],
    help="Merges into what is already here. Profiles with the same id are replaced.",
)
if imported is not None:
    try:
        incoming = import_bytes(imported.getvalue())
    except (ValueError, UnicodeDecodeError) as err:
        st.error(f"Could not read that file: {err}", icon=":material/error:")
    else:
        added, replaced = merge(library, incoming.profiles)
        st.success(
            f"Imported {added} new and updated {replaced} existing profile(s).",
            icon=":material/check_circle:",
        )
        profile_store.save(state)
