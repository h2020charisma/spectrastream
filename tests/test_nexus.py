"""The NeXus floor.

The contract is that a file always comes out, however little the contributor
knows about their instrument. These tests hold that line: no profile, no
calibration, no metadata still produces a valid NXraman record that reads back.
"""

import os
import tempfile
from contextlib import contextmanager

import nexusformat.nexus.tree as nx
import numpy as np
import pytest

from spectrastream.nexus import (
    AXIS_NAME,
    SIGNAL_NAME,
    build_metadata,
    nexus_filename,
    spectrum_to_nexus,
)
from spectrastream.profiles import CalibrationRecord, InstrumentProfile


@contextmanager
def _read_back(data: bytes):
    """Reopen exported bytes as NeXus.

    A context manager because nxload is lazy: array data is fetched on access,
    so the backing file has to outlive the assertions.
    """
    handle, path = tempfile.mkstemp(suffix=".nxs")
    os.close(handle)
    try:
        with open(path, "wb") as fh:
            fh.write(data)
        root = nx.nxload(path)
        yield root, root.tree
    finally:
        os.remove(path)


def _spectrum_group(root):
    """The NXdata holding the exported spectrum."""
    entry = root[list(root)[0]]
    group = entry[entry.attrs["default"]]
    return group[list(group)[0]]


def test_floor_writes_valid_nexus_with_no_metadata_at_all(target_spectrum):
    """The whole point: someone uploads a file and gets FAIR data back, with
    no profile, no calibration and nothing filled in."""
    data = spectrum_to_nexus(target_spectrum.spectrum)
    assert data[:8] == b"\x89HDF\r\n\x1a\n"

    with _read_back(data) as (_, tree):
        assert "NXraman" in tree
        assert SIGNAL_NAME in tree
        assert AXIS_NAME in tree


def test_floor_preserves_the_data(target_spectrum):
    data = spectrum_to_nexus(target_spectrum.spectrum)
    with _read_back(data) as (root, _):
        nxdata = _spectrum_group(root)
        # Fields are named semantically, not "signal"/"y" -- that is what
        # setting @signal/@axes buys, and h5web users see these names.
        assert nxdata.attrs["signal"] == SIGNAL_NAME
        assert nxdata.attrs["axes"] == AXIS_NAME
        np.testing.assert_allclose(
            np.asarray(nxdata[SIGNAL_NAME]), np.asarray(target_spectrum.spectrum.y)
        )
        np.testing.assert_allclose(
            np.asarray(nxdata[AXIS_NAME]), np.asarray(target_spectrum.spectrum.x)
        )


def test_local_temp_path_does_not_leak_into_the_record(target_spectrum):
    """nexusformat stamps the save path into @file_name; a contributor's
    directory layout is not something to publish."""
    data = spectrum_to_nexus(
        target_spectrum.spectrum, original_filename="PST_sample.spc"
    )
    with _read_back(data) as (root, _):
        assert root.attrs["file_name"] == "PST_sample.nxs"
        assert tempfile.gettempdir() not in str(root.attrs["file_name"])


def test_profile_metadata_reaches_the_file(target_spectrum):
    profile = InstrumentProfile(
        name="Lab 2 WITec",
        vendor="WITec",
        model="Alpha 300R",
        serial="SN-12345",
        laser_wl_nm=532,
        grating="600 g/mm",
    )
    data = spectrum_to_nexus(target_spectrum.spectrum, profile=profile)
    with _read_back(data) as (_, tree):
        assert "WITec" in tree
        assert "Alpha 300R" in tree
        assert "SN-12345" in tree


def test_partial_profile_is_accepted(target_spectrum):
    """Only `name` is required -- a half-filled profile must not break export."""
    profile = InstrumentProfile(name="Borrowed instrument")
    data = spectrum_to_nexus(target_spectrum.spectrum, profile=profile)
    assert len(data) > 0


def test_metadata_is_never_none():
    """configure_papp iterates meta.keys() unconditionally, so None would raise
    on exactly the minimal path this floor serves."""
    meta = build_metadata()
    assert isinstance(meta, dict)
    assert meta["@signal"] == SIGNAL_NAME
    assert meta["calibration_applied"] == "false"


def test_empty_metadata_values_are_dropped_not_blanked():
    meta = build_metadata(
        profile=InstrumentProfile(name="x", vendor="", grating=None),
        source_metadata={"junk": "   ", "real": "value"},
    )
    assert "junk" not in meta
    assert "grating" not in meta
    assert meta["real"] == "value"


def test_calibration_provenance_is_recorded_without_the_method():
    record = CalibrationRecord(
        label="Neon 2026-07",
        recipe_id="rc2.ne_si",
        engine_id="rc2",
        laser_wl_nm=532,
        model={"format": "ramanchada2-calmodel", "secret": "internals"},
        steps=[{"step_id": "x_curve", "label": "Curve", "status": "applied"}],
    )
    meta = build_metadata(calibration=record)
    assert meta["calibration_applied"] == "true"
    assert meta["calibration_recipe"] == "rc2.ne_si"
    assert meta["calibration_engine"] == "rc2"
    assert meta["calibration_steps"] == "Curve"
    # The model itself is provenance the file has no business carrying.
    assert not any("secret" in str(v) for v in meta.values())


def test_profile_metadata_wins_over_stale_vendor_headers():
    meta = build_metadata(
        profile=InstrumentProfile(name="p", grating="600 g/mm"),
        source_metadata={"grating": "300 g/mm"},
    )
    assert meta["grating"] == "600 g/mm"


def test_calibrated_axis_is_what_gets_written(neon_spectrum):
    """The file carries the corrected axis, which is the deliverable."""
    from spectrastream.calibration import (
        CalibrationContext,
        engine_for_recipe,
        get_recipe,
    )

    recipe = get_recipe("rc2.ne_si")
    engine = engine_for_recipe(recipe)
    fit = engine.fit(
        recipe,
        {"neon": neon_spectrum.spectrum},
        CalibrationContext(laser_wl_nm=532),
    )
    calibrated = fit.apply(neon_spectrum.spectrum)

    data = spectrum_to_nexus(calibrated)
    with _read_back(data) as (root, _):
        nxdata = _spectrum_group(root)
        written = np.asarray(nxdata[AXIS_NAME])

    np.testing.assert_allclose(written, np.asarray(calibrated.x))
    assert not np.allclose(written, np.asarray(neon_spectrum.spectrum.x))


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("spectrum.spc", "spectrum.nxs"),
        ("/some/dir/thing.txt", "thing.nxs"),
        ("Data 1.spc", "Data 1.nxs"),
        (None, "spectrum.nxs"),
        ("", "spectrum.nxs"),
    ],
)
def test_output_filename_derivation(given, expected):
    assert nexus_filename(given) == expected
