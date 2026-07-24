"""Write a spectrum to NeXus.

This is the floor: any spectrum ramanchada2 can read becomes a valid NXraman
file, with or without instrument metadata, with or without a calibration. A
contributor who knows nothing about their rig still gets a FAIR record; every
extra field they do supply makes it richer.

The file carries the *calibrated axis*, never the calibration method -- which
engine produced it is recorded as provenance, its internals are not.
"""

import os
import tempfile
import uuid
from typing import Any, Mapping

import nexusformat.nexus.tree as nx
import numpy as np
import pyambit.datamodel as mx
from pyambit.nexus_spectra import spe2ambit
from ramanchada2.spectrum import Spectrum

from spectrastream import __version__
from spectrastream.profiles import (
    CalibrationRecord,
    InstrumentProfile,
    OpticalPath,
)

#: uuid prefix for records minted by this app.
UUID_PREFIX = "SSTR"

DEFAULT_SAMPLE = "unknown"
DEFAULT_PROVIDER = "anonymous"
DEFAULT_INVESTIGATION = "SpectraStream"

#: Without these, pyambit falls back to naming the axis "y".
SIGNAL_NAME = "Raman intensity"
AXIS_NAME = "Raman shift"


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def missing_minimum(
    optical_path: OpticalPath | None = None,
    laser_wl_nm: float | None = None,
) -> list[str]:
    """What still has to be supplied before a record is worth writing.

    The axis units and the laser wavelength are not optional extras. Units
    decide whether the numbers are Raman shifts or wavelengths, and without the
    excitation wavelength one cannot convert between them or compare the record
    with anything else. Everything beyond these two genuinely is optional.

    The wavelength comes from the *optical path*, not the instrument: a rig with
    both a 532 and a 785 line has two paths and two different answers.
    """
    if laser_wl_nm is None and optical_path is not None:
        laser_wl_nm = optical_path.laser_wl_nm
    missing = []
    if not laser_wl_nm:
        missing.append("laser wavelength")
    return missing


def build_metadata(
    profile: InstrumentProfile | None = None,
    optical_path: OpticalPath | None = None,
    source_metadata: Mapping[str, Any] | None = None,
    calibration: CalibrationRecord | None = None,
    original_filename: str | None = None,
    acquisition: Any | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the ``meta`` dict handed to pyambit.

    Always returns a dict, never ``None``: ``configure_papp`` iterates
    ``meta.keys()`` unconditionally despite defaulting the argument to ``None``,
    so passing ``None`` raises ``AttributeError`` on exactly the minimal-metadata
    path this floor exists to serve.
    """
    meta: dict[str, Any] = {"@signal": SIGNAL_NAME, "@axes": [AXIS_NAME]}

    # Whatever the vendor format carried. Lowest precedence: an explicit
    # profile entry should win over a stale header field.
    for key, value in (source_metadata or {}).items():
        cleaned = _clean(value)
        if cleaned is not None:
            meta[str(key)] = cleaned

    if profile is not None:
        meta.update(profile.instrument_metadata())
        if profile.name:
            meta["instrument_profile"] = profile.name

    # The optical path is more specific than the instrument, so it wins.
    if optical_path is not None:
        meta.update(optical_path.metadata())

    # Acquisition detail outranks both: it describes this measurement, not the
    # instrument in general or whatever the file header happened to carry.
    if acquisition is not None:
        meta.update(acquisition.as_metadata())

    if original_filename:
        meta["source_file"] = original_filename
    meta["spectrastream_version"] = __version__

    # Provenance of the axis, not the method behind it.
    if calibration is not None:
        meta["calibration_applied"] = "true"
        meta["calibration_recipe"] = calibration.recipe_id
        meta["calibration_engine"] = calibration.engine_id
        meta["calibration_label"] = calibration.label
        meta["calibration_date"] = calibration.created.isoformat(timespec="seconds")
        applied = calibration.applied_step_labels
        if applied:
            meta["calibration_steps"] = ", ".join(applied)
    else:
        meta["calibration_applied"] = "false"

    for key, value in (extra or {}).items():
        cleaned = _clean(value)
        if cleaned is not None:
            meta[str(key)] = cleaned
    return meta


def spectrum_to_nexus(
    spe: Spectrum,
    profile: InstrumentProfile | None = None,
    optical_path: OpticalPath | None = None,
    calibration: CalibrationRecord | None = None,
    sample: str | None = None,
    original_filename: str | None = None,
    provider: str | None = None,
    investigation: str | None = None,
    units: str | None = None,
    acquisition: Any | None = None,
    laser_wl_nm: float | None = None,
    source_metadata: Mapping[str, Any] | None = None,
    extra_metadata: Mapping[str, Any] | None = None,
    output_filename: str | None = None,
) -> bytes:
    """Serialise ``spe`` as a NXraman file and return its bytes.

    Beyond the spectrum itself, only the axis units and the laser wavelength
    really matter -- see :func:`missing_minimum`. Everything else is optional
    and simply enriches the record. Nothing raises for missing metadata; it is
    the caller's job to decide whether an under-described record is worth
    writing.
    """
    if units is None:
        units = getattr(acquisition, "units", None) or "cm-1"
    if laser_wl_nm is None:
        laser_wl_nm = optical_path.laser_wl_nm if optical_path else None

    sample_name = (
        _clean(sample) or _clean(getattr(acquisition, "sample", None)) or DEFAULT_SAMPLE
    )
    provider_name = (
        _clean(provider)
        or _clean(getattr(acquisition, "provider", None))
        or DEFAULT_PROVIDER
    )
    investigation_name = (
        _clean(investigation)
        or _clean(getattr(acquisition, "investigation", None))
        or DEFAULT_INVESTIGATION
    )

    vendor = _clean(profile.vendor) if profile else None
    model = _clean(profile.model) if profile else None
    laser_wl = laser_wl_nm

    meta = build_metadata(
        profile=profile,
        optical_path=optical_path,
        source_metadata=source_metadata,
        calibration=calibration,
        original_filename=original_filename,
        acquisition=acquisition,
        extra=extra_metadata,
    )

    papp = spe2ambit(
        x=np.asarray(spe.x, dtype=float),
        y=np.asarray(spe.y, dtype=float),
        meta=meta,
        instrument=(vendor or "", model or ""),
        wavelength=str(laser_wl) if laser_wl else None,
        provider=provider_name,
        investigation=investigation_name,
        sample=sample_name,
        sample_provider=provider_name,
        prefix=UUID_PREFIX,
        unit=units,
    )

    substance = mx.SubstanceRecord(
        name=sample_name,
        publicname=sample_name,
        ownerName=provider_name,
    )
    substance.i5uuid = "{}-{}".format(
        UUID_PREFIX, uuid.uuid5(uuid.NAMESPACE_OID, sample_name)
    )
    substance.study = [papp]

    root = nx.NXroot()
    mx.Substances(substance=[substance]).to_nexus(root)
    root.attrs["pyambit"] = "0.0.2"
    # nexusformat stamps the absolute save path here; overwrite it so a local
    # temp directory does not travel with the record.
    root.attrs["file_name"] = output_filename or nexus_filename(original_filename)

    handle, path = tempfile.mkstemp(suffix=".nxs")
    os.close(handle)
    try:
        root.save(path, mode="w")
        with open(path, "rb") as fh:
            return fh.read()
    finally:
        if os.path.exists(path):
            os.remove(path)


def nexus_filename(original_filename: str | None) -> str:
    """A .nxs name derived from the uploaded file's name."""
    if not original_filename:
        return "spectrum.nxs"
    stem = os.path.splitext(os.path.basename(original_filename))[0].strip()
    return f"{stem or 'spectrum'}.nxs"
