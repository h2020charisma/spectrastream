"""Instrument profiles, stored in this browser.

A profile is the unit people recognise -- "my 532 nm rig" -- and it is what
turns a bare spectrum into a described one. Only a name is required: demanding
a serial number before someone can export a file would defeat the floor.
"""

import streamlit as st

from spectrastream.profiles import (
    InstrumentProfile,
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


@st.dialog("Instrument profile", width="large")
def edit_profile(profile: InstrumentProfile | None):
    creating = profile is None
    draft = profile or InstrumentProfile(name="")

    with st.form("profile_form"):
        name = st.text_input(
            "Name",
            value=draft.name,
            placeholder="e.g. Lab 2 WITec, 532 nm",
            help="The only required field.",
        )

        cols = st.columns(2)
        vendor = cols[0].text_input("Vendor", value=draft.vendor or "")
        model = cols[1].text_input("Model", value=draft.model or "")

        cols = st.columns(2)
        serial = cols[0].text_input("Serial number", value=draft.serial or "")
        laser = cols[1].number_input(
            "Laser wavelength (nm)",
            value=float(draft.laser_wl_nm) if draft.laser_wl_nm else 0.0,
            step=1.0,
            format="%.1f",
            help="Leave at 0 if unknown. Needed for calibration, not for export.",
        )

        with st.expander("Optical details (all optional)"):
            cols = st.columns(2)
            device_type = cols[0].text_input(
                "Device type", value=draft.device_type or ""
            )
            numerical_aperture = cols[1].text_input(
                "Numerical aperture", value=draft.numerical_aperture or ""
            )
            cols = st.columns(2)
            grating = cols[0].text_input("Grating", value=draft.grating or "")
            slit = cols[1].text_input("Slit", value=draft.slit or "")

        submitted = st.form_submit_button(
            "Create profile" if creating else "Save changes",
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
        draft.laser_wl_nm = float(laser) if laser else None
        draft.device_type = device_type.strip() or None
        draft.numerical_aperture = numerical_aperture.strip() or None
        draft.grating = grating.strip() or None
        draft.slit = slit.strip() or None

        library.upsert(draft)
        state.set_active_profile(draft.id)
        profile_store.save(state)


header = st.container(horizontal=True)
header.button(
    "New profile",
    icon=":material/add:",
    type="primary",
    on_click=lambda: edit_profile(None),
)

if not library.profiles:
    st.info(
        "No profiles yet. You do not need one to convert a spectrum — a "
        "profile just adds instrument metadata to the file, and gives "
        "calibrations somewhere to live.",
        icon=":material/precision_manufacturing:",
    )
else:
    for profile in library.profiles:
        with st.container(border=True):
            top = st.container(horizontal=True, vertical_alignment="center")
            top.markdown(f"### {profile.name}")
            if profile.id == state.active_profile_id:
                top.badge("Selected", icon=":material/check:", color="green")
            st.caption(profile.describe())

            if profile.calibrations:
                for record in profile.calibrations:
                    active = record.id == profile.active_calibration_id
                    line = st.container(horizontal=True, vertical_alignment="center")
                    line.markdown(
                        f":material/tune: **{record.label}** · "
                        f"`{record.recipe_id}` · "
                        f"{record.created:%Y-%m-%d}"
                    )
                    if active:
                        line.badge("Active", color="blue")
                    else:
                        if line.button(
                            "Use this",
                            key=f"activate_{profile.id}_{record.id}",
                        ):
                            profile.active_calibration_id = record.id
                            library.upsert(profile)
                            profile_store.save(state)
                    if line.button(
                        "",
                        icon=":material/delete:",
                        key=f"delcal_{profile.id}_{record.id}",
                        help="Remove this calibration",
                    ):
                        profile.remove_calibration(record.id)
                        library.upsert(profile)
                        profile_store.save(state)
                    if record.skipped_step_labels:
                        st.caption(
                            "Steps not applied: "
                            + ", ".join(record.skipped_step_labels)
                        )
            else:
                st.caption("No calibration attached yet.")

            actions = st.container(horizontal=True)
            actions.button(
                "Edit",
                icon=":material/edit:",
                key=f"edit_{profile.id}",
                on_click=edit_profile,
                args=(profile,),
            )
            if actions.button(
                "Select",
                icon=":material/check_circle:",
                key=f"select_{profile.id}",
                disabled=profile.id == state.active_profile_id,
            ):
                state.set_active_profile(profile.id)
                st.rerun()
            if actions.button(
                "Delete",
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
