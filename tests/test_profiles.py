"""Instruments, optical paths, and what belongs where.

The structure is two levels for a physical reason: one instrument commonly has
several optical paths, they differ in wavelength and optics, and a calibration
derived on one says nothing about another. Tests here pin that separation and
the round trip through storage.
"""

import pytest

from spectrastream.profiles import (
    SCHEMA_VERSION,
    CalibrationRecord,
    InstrumentProfile,
    OpticalPath,
    ProfileLibrary,
    export_bytes,
    import_bytes,
    merge,
)


def _record(label="Neon 2026-07", **kwargs):
    return CalibrationRecord(
        label=label,
        recipe_id=kwargs.pop("recipe_id", "rc2.ne_si"),
        engine_id="rc2",
        laser_wl_nm=532,
        model={"format": "ramanchada2-calmodel", "components": []},
        **kwargs,
    )


def _instrument(**paths):
    profile = InstrumentProfile(name="Lab 2", vendor="WITec")
    for op_id, wl in paths.items():
        profile.add_optical_path(OpticalPath(op_id=op_id, laser_wl_nm=wl))
    return profile


def test_name_is_the_only_required_field():
    profile = InstrumentProfile(name="Borrowed rig")
    assert profile.optical_paths == []
    assert profile.describe() == "no details recorded"


def test_one_instrument_can_hold_several_wavelengths():
    """The case the flat model could not express at all."""
    profile = _instrument(OP1=532, OP2=785)
    assert [p.laser_wl_nm for p in profile.optical_paths] == [532, 785]
    assert "532 nm, 785 nm" in profile.describe()
    assert "2 optical path(s)" in profile.describe()


def test_wavelength_belongs_to_the_path_not_the_instrument():
    profile = _instrument(OP1=532, OP2=785)
    assert not hasattr(profile, "laser_wl_nm")
    assert profile.optical_paths[0].laser_wl_nm == 532


def test_calibrations_attach_to_a_path():
    """A 532 nm calibration must not be reachable from the 785 nm path."""
    profile = _instrument(OP1=532, OP2=785)
    green, red = profile.optical_paths
    record = _record()
    green.add_calibration(record)

    assert green.active_calibration is record
    assert red.calibrations == []
    assert red.active_calibration is None


def test_next_op_id_avoids_collisions():
    profile = _instrument(OP1=532, OP2=785)
    assert profile.next_op_id() == "OP3"

    profile.add_optical_path(OpticalPath(op_id="OP3", laser_wl_nm=633))
    assert profile.next_op_id() == "OP4"


def test_adding_a_calibration_makes_it_active():
    path = OpticalPath(op_id="OP1", laser_wl_nm=532)
    record = _record()
    path.add_calibration(record)
    assert path.active_calibration_id == record.id


def test_adding_a_calibration_can_leave_the_active_one_alone():
    path = OpticalPath(op_id="OP1")
    first = _record("first")
    path.add_calibration(first)
    path.add_calibration(_record("second"), make_active=False)
    assert path.active_calibration_id == first.id
    assert len(path.calibrations) == 2


def test_removing_the_active_calibration_falls_back():
    path = OpticalPath(op_id="OP1")
    first, second = _record("first"), _record("second")
    path.add_calibration(first, make_active=False)
    path.add_calibration(second)
    path.remove_calibration(second.id)
    assert path.active_calibration_id == first.id


def test_removing_the_last_calibration_clears_the_active_pointer():
    path = OpticalPath(op_id="OP1")
    record = _record()
    path.add_calibration(record)
    path.remove_calibration(record.id)
    assert path.active_calibration_id is None
    assert path.active_calibration is None


def test_metadata_is_split_between_instrument_and_path():
    profile = InstrumentProfile(name="x", serial="SN1", extra={"lab": "2"})
    path = OpticalPath(op_id="OP1", grating="600", slit="", pin_hole_size="50")

    assert profile.instrument_metadata() == {"serial_number": "SN1", "lab": "2"}
    path_meta = path.metadata()
    assert path_meta["op_id"] == "OP1"
    assert path_meta["grating"] == "600"
    assert path_meta["pin hole size"] == "50"
    assert "slit" not in path_meta  # blanks are dropped, not written empty


def test_finding_a_path_across_the_library():
    library = ProfileLibrary()
    profile = _instrument(OP1=532)
    library.upsert(profile)
    target = profile.optical_paths[0]

    found_profile, found_path = library.find_optical_path(target.id)
    assert found_profile is profile
    assert found_path is target
    assert library.find_optical_path("nope") == (None, None)


def test_step_labels_split_by_status():
    record = _record(
        steps=[
            {"step_id": "x_curve", "label": "Curve", "status": "applied"},
            {"step_id": "laser_zero", "label": "Zeroing", "status": "skipped"},
        ]
    )
    assert record.applied_step_labels == ["Curve"]
    assert record.skipped_step_labels == ["Zeroing"]


def test_library_round_trips_through_json():
    library = ProfileLibrary()
    profile = _instrument(OP1=532, OP2=785)
    profile.optical_paths[0].add_calibration(_record())
    library.upsert(profile)

    restored = import_bytes(export_bytes(library))
    back = restored.profiles[0]
    assert back.name == "Lab 2"
    assert [p.op_id for p in back.optical_paths] == ["OP1", "OP2"]
    assert back.optical_paths[0].calibrations[0].model == {
        "format": "ramanchada2-calmodel",
        "components": [],
    }
    assert back.optical_paths[1].calibrations == []


def test_upsert_replaces_by_id_rather_than_appending():
    library = ProfileLibrary()
    profile = InstrumentProfile(name="one")
    library.upsert(profile)
    profile.name = "renamed"
    library.upsert(profile)
    assert len(library.profiles) == 1
    assert library.profiles[0].name == "renamed"


def test_merge_reports_added_and_replaced():
    library = ProfileLibrary()
    existing = InstrumentProfile(name="existing")
    library.upsert(existing)

    incoming = [InstrumentProfile(name="new"), existing.model_copy()]
    added, replaced = merge(library, incoming)
    assert (added, replaced) == (1, 1)
    assert len(library.profiles) == 2


def test_library_from_a_newer_schema_is_refused_not_mangled():
    payload = f'{{"schema_version": {SCHEMA_VERSION + 90}, "profiles": []}}'
    with pytest.raises(ValueError, match="newer version"):
        ProfileLibrary.from_json(payload)


def test_schema_v1_profiles_are_lifted_into_an_optical_path():
    """Anyone who used the flat model must not silently lose their work."""
    old = """{
      "schema_version": 1,
      "profiles": [{
        "id": "abc123",
        "name": "Old rig",
        "vendor": "WITec",
        "laser_wl_nm": 532,
        "grating": "600",
        "numerical_aperture": "0.9",
        "calibrations": [{
          "id": "cal1", "label": "Neon", "recipe_id": "rc2.ne_si",
          "engine_id": "rc2", "created": "2026-07-01T00:00:00Z",
          "model": {"format": "ramanchada2-calmodel"}
        }],
        "active_calibration_id": "cal1"
      }]
    }"""
    library = ProfileLibrary.from_json(old)

    profile = library.profiles[0]
    assert profile.id == "abc123"
    assert profile.name == "Old rig"
    assert len(profile.optical_paths) == 1

    path = profile.optical_paths[0]
    assert path.op_id == "OP1"
    assert path.laser_wl_nm == 532
    assert path.grating == "600"
    assert path.collection_optics == "0.9"
    assert path.active_calibration_id == "cal1"
    assert path.calibrations[0].label == "Neon"
