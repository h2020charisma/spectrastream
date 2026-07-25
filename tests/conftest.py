from pathlib import Path

import pytest

from spectrastream.ingest import load_spectrum

EXPERIMENTS = Path(__file__).parents[1] / "src" / "experiments"

NEON_532 = EXPERIMENTS / "NeonSNQ043_iR532_Probe_5msx2.txt"
PST_532 = EXPERIMENTS / "PST_WITEcAlpha532nm_20x_PFO_PH_10mW_10x30s_005_Spec.Data 1.spc"
#: Real silicon from the CHARISMA round robin, so the laser-zeroing path is
#: exercised against a measurement rather than a model of one.
SILICON_532 = EXPERIMENTS / "S0B_1_OP1_silicon_532.csv"


def _load(path: Path):
    if not path.exists():  # pragma: no cover - guards a missing fixture
        pytest.skip(f"fixture not available: {path.name}")
    return load_spectrum(path.read_bytes(), path.name)


@pytest.fixture(scope="session")
def neon_path():
    if not NEON_532.exists():  # pragma: no cover
        pytest.skip(f"fixture not available: {NEON_532.name}")
    return NEON_532


@pytest.fixture(scope="session")
def neon_spectrum():
    return _load(NEON_532)


@pytest.fixture(scope="session")
def target_spectrum():
    return _load(PST_532)


@pytest.fixture(scope="session")
def fitted_ne_si(neon_spectrum, silicon_spectrum):
    """A real Neon+Silicon calibration, derived once via the rc2 engine.

    Shared by the verification and resolution tests so the (slow) fit runs a
    single time. Built through the engine, not the factory, so it is exactly
    what the app produces and saves.
    """
    from spectrastream.calibration import (
        CalibrationContext,
        engine_for_recipe,
        get_recipe,
    )

    recipe = get_recipe("rc2.ne_si")
    engine = engine_for_recipe(recipe)
    ctx = CalibrationContext(
        laser_wl_nm=532, input_units={"neon": "cm-1", "si": "cm-1"}
    )
    return engine.fit(
        recipe,
        {"neon": neon_spectrum.spectrum, "si": silicon_spectrum},
        ctx,
    )


@pytest.fixture(scope="session")
def silicon_spectrum():
    """A real silicon wafer measurement, 532 nm, from the CHARISMA round robin.

    Deliberately not synthetic. A Gaussian plus flat noise puts its noise floor
    just under the prominence threshold, so peak finding treats every wiggle as
    a candidate and each one costs a Pearson4 fit -- which says a great deal
    about the fixture and nothing about the code. Real silicon has a band three
    orders of magnitude above its noise, and its band sits at 520.84 rather
    than the certified 520.45: that offset is the instrument error the
    calibration exists to remove.
    """
    return _load(SILICON_532).spectrum
