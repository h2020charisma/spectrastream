"""Apply a calibration to a spectrum and export it.

This is where a derived calibration gets *used*: pick the instrument and
optical path, choose one of its saved calibrations, and it is applied to the
uploaded spectrum before export. Deriving one happens on the other page.


Two things are required and everything else is optional. The axis units and the
excitation wavelength are not metadata *about* the data -- they are what makes
the numbers mean anything, and a record missing them cannot be compared with
anything else. No profile, no calibration and no other field is needed.

Optional fields follow the CHARISMA/VAMAS Raman reporting template, so a
spectrum described here carries the same facts as one described for a
round-robin.
"""

import pandas as pd
import streamlit as st
from ramanchada2.io.output.write_csv import write_csv as io_write_csv

from spectrastream.acquisition import (
    BACKGROUND_CHOICES,
    UNIT_LABELS,
    Acquisition,
    guess_from_metadata,
)
from spectrastream.calibration import CalibrationError, get_engine
from spectrastream.cwa import CwaExportError, export_x_files, x_calibration_model
from spectrastream.ingest import IngestError, load_spectrum
from spectrastream.nexus import missing_minimum, nexus_filename, spectrum_to_nexus
from spectrastream.preprocess import (
    BASELINE_METHODS,
    PreprocessError,
    PreprocessStep,
    apply_steps,
)
from ui.charts import show_spectrum, show_twin, x_title
from ui.state import get_state

state = get_state()

upload_row = st.columns([2, 1])
uploaded = upload_row[0].file_uploader(
    "Spectrum file",
    accept_multiple_files=False,
    help="Any format ramanchada2 can read: .spc, .txt, .csv, .wdf, .cha and more.",
)

# Asked here, not further down: nothing in a bare data file says whether its x
# axis is Raman shift, wavelength or detector pixels, and guessing would mean
# plotting and exporting it under the wrong label.
unit_options = list(UNIT_LABELS)
state.acquisition.units = upload_row[1].selectbox(
    "X axis units",
    options=unit_options,
    index=unit_options.index(state.acquisition.units)
    if state.acquisition.units in unit_options
    else 0,
    format_func=lambda u: UNIT_LABELS[u],
    help="What the numbers on the x axis actually are.",
)

if uploaded is None:
    # Removing the file removes the spectrum: leaving the old one on screen
    # would show a plot and offer downloads for a file no longer chosen.
    state.target = None
    state.guessed_fields = set()
    state.guessed_laser_wl_nm = None
else:
    payload = uploaded.getvalue()
    already = state.target
    if already is None or already.filename != uploaded.name:
        try:
            state.target = load_spectrum(payload, uploaded.name)
        except IngestError as err:
            state.target = None
            st.error(str(err), icon=":material/error:")
        else:
            # Prefill from whatever the file already told us. These are
            # suggestions shown in editable fields, not commitments -- a header
            # can be stale, and the contributor is the one who knows.
            fields, guessed_wl = guess_from_metadata(state.target.source_metadata)
            # Keep the units the user just chose: they describe the file, and
            # rebuilding the acquisition from guesses would silently reset them.
            fields.setdefault("units", state.acquisition.units)
            state.acquisition = Acquisition(**fields)
            state.guessed_fields = set(fields) | (
                {"laser_wl_nm"} if guessed_wl else set()
            )
            state.guessed_laser_wl_nm = guessed_wl

st.caption(
    "Any format ramanchada2 reads becomes a NeXus file. A calibration and an "
    "instrument profile make the record richer, but neither is required — "
    "converting alone is the point."
)

target = state.target

if target is None:
    st.info(
        "Upload a spectrum to begin. All you need beyond the file itself is "
        "its x axis units and the laser wavelength.",
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


# --- optional preprocessing -------------------------------------------------

if not state.target_steps:
    state.target_steps = [
        PreprocessStep(op="trim", enabled=False),
        PreprocessStep(op="baseline", enabled=False, params={"method": "snip"}),
    ]

with st.expander("Preprocess this spectrum", icon=":material/tune:"):
    st.caption(
        "Optional, and applied before calibration and export. Cropping and "
        "baseline removal are the usual ones."
    )
    for index, step in enumerate(state.target_steps):
        step.enabled = st.checkbox(
            step.display_label(), value=step.enabled, key=f"tgt_{index}"
        )
        if not step.enabled:
            continue
        if step.op == "trim":
            cols = st.columns(2)
            step.params["min"] = cols[0].number_input(
                "From", value=float(step.params.get("min", low)), key=f"tgt_min{index}"
            )
            step.params["max"] = cols[1].number_input(
                "To", value=float(step.params.get("max", high)), key=f"tgt_max{index}"
            )
        elif step.op == "baseline":
            cols = st.columns(2)
            methods = list(BASELINE_METHODS)
            current = str(step.params.get("method", "snip"))
            step.params["method"] = cols[0].selectbox(
                "Method",
                options=methods,
                index=methods.index(current) if current in methods else 0,
                key=f"tgt_bl{index}",
            )
            step.params["niter"] = cols[1].number_input(
                "Iterations",
                value=int(step.params.get("niter", 30)),
                step=1,
                key=f"tgt_ni{index}",
            )

try:
    working_spectrum, target_applied = apply_steps(target.spectrum, state.target_steps)
except PreprocessError as err:
    working_spectrum, target_applied = target.spectrum, []
    st.error(str(err), icon=":material/error:")
if target_applied:
    st.caption("Applied: " + " → ".join(target_applied))


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

# Which configuration of that instrument. The wavelength and the calibration
# both belong to the path, so this choice matters more than the instrument.
if profile is not None and len(profile.optical_paths) > 1:
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
            f"{profile.optical_path(pid).op_id} · "
            f"{profile.optical_path(pid).describe()}"
        ),
        help="One instrument, several configurations — each calibrates separately.",
    )
    state.set_active_optical_path(chosen_path)
elif profile is not None and not profile.optical_paths:
    st.caption(
        f"**{profile.name}** has no optical path recorded yet — add one on the "
        "Instruments page to carry its wavelength and optics."
    )

optical_path = state.active_optical_path


# --- optional calibration ---------------------------------------------------

calibration_record = None
calibrated = None
fitted = None
apply_calibration = False

st.subheader("Apply a calibration")
if optical_path is not None and optical_path.calibrations:
    labels = {c.id: c.label for c in optical_path.calibrations}
    default_id = optical_path.active_calibration_id or optical_path.calibrations[-1].id
    ids = list(labels)
    chosen_id = st.selectbox(
        "Calibration",
        options=[None] + ids,
        index=ids.index(default_id) + 1,
        format_func=lambda cid: "Do not calibrate" if cid is None else labels[cid],
    )
    if chosen_id is not None:
        calibration_record = optical_path.calibration(chosen_id)
        apply_calibration = True
elif optical_path is not None:
    st.caption(
        f"Optical path {optical_path.op_id} has no calibration yet — derive "
        "one on the Derive calibration page, or export with an uncorrected "
        "axis."
    )
else:
    st.caption(
        "Select an instrument and optical path above to apply one of its "
        "calibrations. Without one the spectrum is exported uncorrected."
    )

if apply_calibration and calibration_record is not None:
    try:
        engine = get_engine(calibration_record.engine_id)
        fitted = engine.load(calibration_record.model)
        # The preprocessed spectrum, not the raw one: otherwise cropping
        # and baseline removal would be discarded the moment a calibration
        # was applied, which is worse than not offering them.
        calibrated = fitted.apply(working_spectrum, spe_units=state.acquisition.units)
    except (CalibrationError, KeyError, ValueError) as err:
        calibrated = None
        calibration_record = None
        st.error(
            f"Could not apply this calibration: {err}. Exporting the "
            "uncalibrated spectrum instead.",
            icon=":material/warning:",
        )


if fitted is not None and calibration_record is not None:
    with st.expander("Explore this calibration", icon=":material/search:"):
        st.caption(
            f"Derived {calibration_record.created:%Y-%m-%d} with "
            f"`{calibration_record.recipe_id}`."
        )
        describe = getattr(fitted, "describe", None)
        if describe is not None:
            st.dataframe(
                pd.DataFrame(describe(), columns=["Property", "Value"]),
                width="stretch",
                hide_index=True,
            )
        figure = getattr(fitted, "figure", None)
        if figure is not None:
            drawn = figure()
            if drawn is not None:
                st.pyplot(drawn, width="stretch")
        for source in calibration_record.sources:
            st.caption(f"{source.slot}: {source.filename}")


# --- chart ------------------------------------------------------------------

axis_units = state.acquisition.units
if calibrated is not None:
    corrections = getattr(fitted, "corrections", lambda: "calibrated")()
    show_twin(
        ("As measured", (working_spectrum.x, working_spectrum.y)),
        (corrections.capitalize(), (calibrated.x, calibrated.y)),
        x_title=x_title(axis_units),
        caption=f"Left axis as measured, right axis {corrections}.",
    )
else:
    show_spectrum(
        {target.filename: (working_spectrum.x, working_spectrum.y)},
        x_title=x_title(axis_units),
    )


# --- how it was measured ----------------------------------------------------

st.subheader("Measurement")
st.caption(
    "Two of these are not optional: the units say whether the numbers are "
    "Raman shifts or wavelengths, and the excitation wavelength is what lets "
    "anyone convert between them or compare your record with another. The "
    "rest follow the CHARISMA/VAMAS reporting template — fill in what you know."
)

acq = state.acquisition

if state.guessed_fields:
    st.caption(
        ":material/auto_awesome: Prefilled from the file's own header: "
        f"{', '.join(sorted(f.replace('_', ' ') for f in state.guessed_fields))}. "
        "Check and correct anything that looks wrong — headers go stale."
    )

core = st.columns(3)
core[0].text_input(
    "X axis units",
    value=UNIT_LABELS[acq.units],
    disabled=True,
    help="Set with the file uploader above.",
)

# The optical path is authoritative when one is chosen -- the wavelength is a
# property of the path, not the instrument. Otherwise fall back to what the
# file claimed, and let the user override.
path_wl = optical_path.laser_wl_nm if optical_path else None
prefill_wl = path_wl if path_wl is not None else state.guessed_laser_wl_nm
laser_wl = core[1].number_input(
    "Laser wavelength (nm)",
    value=float(prefill_wl) if prefill_wl else 0.0,
    step=1.0,
    format="%.2f",
    help=(
        "Taken from the selected optical path, otherwise read from the file if "
        "it says. Record it on the optical path to stop retyping it."
    ),
    disabled=path_wl is not None,
)
acq.sample = (
    core[2].text_input("Sample", value=acq.sample or "", placeholder="e.g. polystyrene")
    or None
)

with st.expander("More measurement detail (optional)", icon=":material/notes:"):
    row = st.columns(3)
    acq.op_id = (
        row[0].text_input(
            "Optical path ID",
            value=acq.op_id or "",
            help=(
                "Which optical path was used. One instrument often has "
                "several — different grating, objective or slit — and each "
                "calibrates differently."
            ),
        )
        or None
    )
    acq.integration_time_ms = (
        row[1].number_input(
            "Integration time (ms)",
            value=float(acq.integration_time_ms or 0.0),
            step=100.0,
        )
        or None
    )
    acq.power_meter_mw = (
        row[2].number_input(
            "Power at sample (mW)", value=float(acq.power_meter_mw or 0.0), step=0.1
        )
        or None
    )

    row = st.columns(3)
    acq.laser_power_percent = (
        row[0].number_input(
            "Laser power (%)", value=float(acq.laser_power_percent or 0.0), step=1.0
        )
        or None
    )
    acq.temperature_c = (
        row[1].number_input(
            "Temperature (°C)", value=float(acq.temperature_c or 0.0), step=1.0
        )
        or None
    )
    acq.background = (
        row[2].selectbox("Background", options=[None] + BACKGROUND_CHOICES) or None
    )

effective_wl = path_wl if path_wl is not None else (laser_wl or None)
missing = missing_minimum(optical_path, effective_wl)


# --- downloads --------------------------------------------------------------

st.subheader("Download")

export_spectrum = calibrated if calibrated is not None else working_spectrum
nexus_bytes = None

if missing:
    st.info(
        f"Add the {' and '.join(missing)} to export NeXus. Everything else on "
        "this page is optional.",
        icon=":material/edit_note:",
    )
else:
    try:
        nexus_bytes = spectrum_to_nexus(
            export_spectrum,
            profile=profile,
            optical_path=optical_path,
            calibration=calibration_record,
            original_filename=target.filename,
            acquisition=acq,
            laser_wl_nm=effective_wl,
            source_metadata=target.source_metadata,
            extra_metadata=(
                {"preprocessing": " -> ".join(target_applied)}
                if target_applied
                else None
            ),
        )
    except Exception as err:  # noqa: BLE001 - the floor must explain itself
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
    st.caption("Exported without calibration — still a valid, shareable NeXus record.")
else:
    st.caption(f"Exported with calibration “{calibration_record.label}” applied.")

    # The interoperable form of the calibration itself: a curve of points plus
    # metadata that reads without ramanchada2, per CWA 18133:2024 section 8.
    calmodel = x_calibration_model(fitted)
    if calmodel is not None:
        try:
            csv_text, json_text = export_x_files(
                calmodel,
                spectral_range=target.x_range,
                metadata={
                    "instrument": profile.describe() if profile else "",
                    "profile": profile.name if profile else "",
                    "recipe": calibration_record.recipe_id,
                },
            )
        except CwaExportError:
            pass
        else:
            with st.expander(
                "Calibration file (CWA 18133 §8)", icon=":material/description:"
            ):
                st.caption(
                    "The calibration itself, as a curve of points plus "
                    "metadata — readable without ramanchada2."
                )
                cwa = st.container(horizontal=True)
                cwa.download_button(
                    "Curve (CSV)",
                    data=csv_text,
                    file_name="calibration.csv",
                    mime="text/csv",
                    icon=":material/download:",
                )
                cwa.download_button(
                    "Metadata (JSON)",
                    data=json_text,
                    file_name="calibration.json",
                    mime="application/json",
                    icon=":material/download:",
                )

with st.expander("Metadata read from the file", icon=":material/description:"):
    if target.source_metadata:
        st.json(target.source_metadata, expanded=False)
    else:
        st.caption(
            "This format carried no metadata. That is fine — the export works "
            "regardless; a profile is the way to add it."
        )
