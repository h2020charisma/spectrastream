"""The calibration engine boundary.

Deliberately narrow: an engine takes reference spectra plus a recipe and hands
back something that can correct a spectrum's axis. Callers never learn *how*
the correction was derived, which is what lets a closed engine sit behind this
interface without leaking its method into the app, the UI, or the NeXus output.
"""

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Protocol, runtime_checkable

import pandas as pd
from ramanchada2.spectrum import Spectrum

from spectrastream.calibration.spec import RecipeSpec


@dataclass(frozen=True)
class CalibrationContext:
    """Everything an engine may need that is not a spectrum."""

    laser_wl_nm: float | None = None
    instrument: Mapping[str, Any] = field(default_factory=dict)
    spectral_range_cm1: tuple[float, float] | None = None


@dataclass
class Diagnostic:
    """One piece of evidence about a fitted step, for the UI to render.

    ``kind`` picks the renderer; ``curve`` and ``table`` are optional payloads.
    Engines report what they have -- nothing here is mandatory.
    """

    step_id: str
    label: str
    kind: Literal["curve", "table", "scalar", "note"] = "note"
    text: str | None = None
    value: float | None = None
    curve: tuple[list[float], list[float]] | None = None
    table: pd.DataFrame | None = None


@dataclass
class StepOutcome:
    """Whether a recipe step ran, and why not if it did not."""

    step_id: str
    label: str
    status: Literal["applied", "skipped", "failed"]
    detail: str = ""


@runtime_checkable
class FittedCalibration(Protocol):
    """A derived calibration: spectrum in, corrected spectrum out."""

    recipe_id: str
    engine_id: str

    def apply(self, spe: Spectrum, spe_units: str = "cm-1") -> Spectrum: ...

    def to_dict(self) -> dict[str, Any]:
        """JSON-clean form, stored inside an instrument profile."""
        ...

    def diagnostics(self) -> list[Diagnostic]: ...

    def outcomes(self) -> list[StepOutcome]: ...


@runtime_checkable
class CalibrationEngine(Protocol):
    id: str
    label: str

    def recipes(self) -> Iterable[RecipeSpec]: ...

    def fit(
        self,
        recipe: RecipeSpec,
        inputs: Mapping[str, Spectrum],
        context: CalibrationContext,
        params: Mapping[str, Any] | None = None,
    ) -> FittedCalibration: ...

    def load(self, data: Mapping[str, Any]) -> FittedCalibration:
        """Rebuild a calibration from :meth:`FittedCalibration.to_dict` output."""
        ...


class CalibrationError(RuntimeError):
    """Raised when a recipe cannot be fitted from the given inputs."""


def merged_params(
    step_params: Mapping[str, Any] | None,
    overrides: Mapping[str, Any] | None,
    step_id: str,
) -> dict[str, Any]:
    """Recipe defaults overlaid with user overrides.

    Overrides are keyed either globally (``{"should_fit": True}``) or per step
    (``{"x_curve": {"should_fit": True}}``); the per-step form wins.
    """
    params = dict(step_params or {})
    if not overrides:
        return params
    # A Mapping value is a per-step scope; anything else is a global override.
    params.update(
        {k: v for k, v in overrides.items() if not isinstance(v, Mapping)},
    )
    scoped = overrides.get(step_id)
    if isinstance(scoped, Mapping):
        params.update(scoped)
    return params
