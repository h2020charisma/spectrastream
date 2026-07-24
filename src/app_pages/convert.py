"""The floor: upload a spectrum, download NeXus.

Everything on this page beyond the uploader is optional. The download button is
live the moment a file parses, before any profile is chosen or any calibration
applied -- the value proposition is that this never fails to return something
useful.
"""

import streamlit as st
from ramanchada2.io.output.write_csv import write_csv as io_write_csv

from spectrastream.calibration import CalibrationError, get_engine
from spectrastream.ingest import IngestError, load_spectrum
from spectrastream.nexus import nexus_filename, spectrum_to_nexus
from ui.charts import show_spectrum
from ui.state import get_state

state = get_state()

uploaded = st.file_uploader(
    "Spectrum file",
    accept_multiple_files=False,
    help="Any format ramanchada2 can read: .spc, .txt, .csv, .wdf, .cha and more.",
)

if uploaded is not None:
    payload = uploaded.getvalue()
    already = state.target
    if already is None or already.filename != uploaded.name:
        try:
            state.target = load_spectrum(payload, uploaded.name)
        except IngestError as err:
            state.target = None
            st.error(str(err), icon=":material/error:")

target = state.target

if target is None:
    st.info(
        "Upload a spectrum to begin. Nothing else is required — you can "
        "download a NeXus file straight away.",
        icon=":material/upload:",
    )
    st.stop()


# --- what was loaded -------------------------------------------------------

low, high = target.x_range
meta_cols = st.columns(4)
meta_cols[0].metric("Points", f"{target.n_points:,}")
meta_cols[1].metric("Range", f"{low:,.0f}–{high:,.0f}")
meta_cols[2].metric("Format", target.filetype.upper())
meta_cols[3].metric("Fields read", len(target.source_metadata))


# --- optional instrument profile -------------------------------------------

profiles = state.library.profiles
options: list[str | None] = [None] + [p.id for p in profiles]
current = state.active_profile_id if state.active_profile_id in options else None

selected = st.selectbox(
    "Instrument profile (optional)",
    options=options,
    index=options.index(current),
    format_func=lambda pid: (
        "No profile — export without instrument metadata"
        if pid is None
        else f"{state.library.get(pid).name} · {state.library.get(pid).describe()}"
    ),
    help="Profiles add instrument metadata to the file and can carry a calibration.",
)
state.set_active_profile(selected)
profile = state.active_profile

if not profiles:
    st.caption(
        "No instrument profiles yet. The export below works without one — "
        "add one on the Instruments page to enrich it."
    )


# --- optional calibration ---------------------------------------------------

calibration_record = None
calibrated = None
apply_calibration = False

if profile is not None and profile.calibrations:
    labels = {c.id: c.label for c in profile.calibrations}
    default_id = profile.active_calibration_id or profile.calibrations[-1].id
    ids = list(labels)
    chosen_id = st.selectbox(
        "Calibration",
        options=[None] + ids,
        index=ids.index(default_id) + 1,
        format_func=lambda cid: "Do not calibrate" if cid is None else labels[cid],
    )
    if chosen_id is not None:
        calibration_record = profile.calibration(chosen_id)
        apply_calibration = True
elif profile is not None:
    st.caption(
        "This profile has no calibration yet — the file will carry its "
        "metadata but an uncorrected axis."
    )

if apply_calibration and calibration_record is not None:
    try:
        engine = get_engine(calibration_record.engine_id)
        fitted = engine.load(calibration_record.model)
        calibrated = fitted.apply(target.spectrum, spe_units=target.units)
    except (CalibrationError, KeyError, ValueError) as err:
        calibrated = None
        calibration_record = None
        st.error(
            f"Could not apply this calibration: {err}. Exporting the "
            "uncalibrated spectrum instead.",
            icon=":material/warning:",
        )


# --- chart ------------------------------------------------------------------

if calibrated is not None:
    show_spectrum(
        {
            "As measured": (target.spectrum.x, target.spectrum.y),
            "Calibrated": (calibrated.x, calibrated.y),
        }
    )
else:
    show_spectrum({target.filename: (target.spectrum.x, target.spectrum.y)})


# --- downloads --------------------------------------------------------------

st.subheader("Download")

export_spectrum = calibrated if calibrated is not None else target.spectrum
sample_name = st.text_input(
    "Sample name (optional)",
    value="",
    placeholder="e.g. polystyrene",
    help="Recorded in the NeXus file. Left blank it is exported as 'unknown'.",
)

try:
    nexus_bytes = spectrum_to_nexus(
        export_spectrum,
        profile=profile,
        calibration=calibration_record,
        sample=sample_name or None,
        original_filename=target.filename,
        units=target.units,
        source_metadata=target.source_metadata,
    )
except Exception as err:  # noqa: BLE001 - the floor must explain itself
    nexus_bytes = None
    st.error(f"NeXus export failed: {err}", icon=":material/error:")

buttons = st.container(horizontal=True)
if nexus_bytes is not None:
    buttons.download_button(
        "Download NeXus",
        data=nexus_bytes,
        file_name=nexus_filename(target.filename),
        mime="application/x-hdf5",
        icon=":material/download:",
        type="primary",
    )
buttons.download_button(
    "Download CSV",
    data="".join(io_write_csv(export_spectrum.x, export_spectrum.y)),
    file_name=f"{nexus_filename(target.filename)[:-4]}.csv",
    mime="text/csv",
    icon=":material/download:",
)

if calibrated is None:
    st.caption(
        "Exported without calibration — still a valid, shareable NeXus record."
    )
else:
    st.caption(f"Exported with calibration “{calibration_record.label}” applied.")

with st.expander("Metadata read from the file", icon=":material/description:"):
    if target.source_metadata:
        st.json(target.source_metadata, expanded=False)
    else:
        st.caption(
            "This format carried no metadata. That is fine — the export works "
            "regardless; a profile is the way to add it."
        )
