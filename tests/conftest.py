from pathlib import Path

import pytest

from spectrastream.ingest import load_spectrum

EXPERIMENTS = Path(__file__).parents[1] / "src" / "experiments"

#: The repository ships a 532 nm neon spectrum but no silicon wafer spectrum,
#: so the "silicon missing" path is the one exercised end to end here.
NEON_532 = EXPERIMENTS / "NeonSNQ043_iR532_Probe_5msx2.txt"
PST_532 = EXPERIMENTS / "PST_WITEcAlpha532nm_20x_PFO_PH_10mW_10x30s_005_Spec.Data 1.spc"


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
