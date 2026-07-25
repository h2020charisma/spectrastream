"""Local-storage soft caps on instruments and optical paths.

The caps nudge toward server sync; they must never cost anyone data, so they
gate only *new* additions — editing or replacing an existing entry is always
allowed even at the limit.
"""

from spectrastream.profiles import (
    MAX_INSTRUMENTS,
    MAX_OPTICAL_PATHS,
    InstrumentProfile,
    OpticalPath,
    ProfileLibrary,
)


def test_instrument_capacity_gates_new_only():
    lib = ProfileLibrary()
    assert not lib.at_instrument_capacity()
    for i in range(MAX_INSTRUMENTS):
        lib.upsert(InstrumentProfile(name=f"rig {i}"))
    assert lib.at_instrument_capacity()

    # editing an existing instrument still saves, even at the cap
    existing = lib.profiles[0]
    existing.name = "renamed"
    lib.upsert(existing)
    assert len(lib.profiles) == MAX_INSTRUMENTS
    assert lib.profiles[0].name == "renamed"


def test_optical_path_capacity_gates_new_only():
    profile = InstrumentProfile(name="rig")
    assert not profile.at_path_capacity()
    for i in range(MAX_OPTICAL_PATHS):
        profile.add_optical_path(OpticalPath(op_id=f"OP{i}"))
    assert profile.at_path_capacity()

    # replacing an existing path does not push past the cap
    first = profile.optical_paths[0]
    profile.add_optical_path(first)
    assert len(profile.optical_paths) == MAX_OPTICAL_PATHS
