"""Profiles are the user-facing unit and they travel: to browser storage, to an
export file, and back. The invariants worth holding are that a nearly-empty
profile is legal, and that a round trip through JSON loses nothing."""

import pytest

from spectrastream.profiles import (
    CalibrationRecord,
    InstrumentProfile,
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


def test_name_is_the_only_required_field():
    profile = InstrumentProfile(name="Borrowed rig")
    assert profile.laser_wl_nm is None
    assert profile.id
    assert profile.describe() == "no details recorded"


def test_describe_summarises_what_is_known():
    profile = InstrumentProfile(name="x", vendor="WITec", laser_wl_nm=532)
    assert profile.describe() == "WITec · 532 nm"


def test_adding_a_calibration_makes_it_active():
    profile = InstrumentProfile(name="x")
    record = _record()
    profile.add_calibration(record)
    assert profile.active_calibration_id == record.id
    assert profile.active_calibration is record


def test_adding_a_calibration_can_leave_the_active_one_alone():
    profile = InstrumentProfile(name="x")
    first = _record("first")
    profile.add_calibration(first)
    profile.add_calibration(_record("second"), make_active=False)
    assert profile.active_calibration_id == first.id
    assert len(profile.calibrations) == 2


def test_removing_the_active_calibration_falls_back():
    profile = InstrumentProfile(name="x")
    first, second = _record("first"), _record("second")
    profile.add_calibration(first, make_active=False)
    profile.add_calibration(second)
    profile.remove_calibration(second.id)
    assert profile.active_calibration_id == first.id


def test_removing_the_last_calibration_clears_the_active_pointer():
    profile = InstrumentProfile(name="x")
    record = _record()
    profile.add_calibration(record)
    profile.remove_calibration(record.id)
    assert profile.active_calibration_id is None
    assert profile.active_calibration is None


def test_instrument_metadata_drops_blanks():
    profile = InstrumentProfile(
        name="x", serial="SN1", grating="", slit=None, extra={"lab": "2", "junk": ""}
    )
    meta = profile.instrument_metadata()
    assert meta == {"serial_number": "SN1", "lab": "2"}


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
    profile = InstrumentProfile(name="Lab 2", vendor="WITec", laser_wl_nm=532)
    profile.add_calibration(_record())
    library.upsert(profile)

    restored = import_bytes(export_bytes(library))
    assert len(restored.profiles) == 1
    back = restored.profiles[0]
    assert back.name == "Lab 2"
    assert back.id == profile.id
    assert back.active_calibration_id == profile.active_calibration_id
    assert back.calibrations[0].model == profile.calibrations[0].model


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
    payload = '{"schema_version": 99, "profiles": []}'
    with pytest.raises(ValueError, match="newer version"):
        ProfileLibrary.from_json(payload)
