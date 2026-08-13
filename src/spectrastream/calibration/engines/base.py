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
    #: Axis units per slot id. Nothing in a data file states them, so the user
    #: declares them per upload -- and the engine must honour that rather than
    #: assuming the recipe's default. A neon spectrum in nm and a silicon one
    #: in cm-1 is a perfectly ordinary combination.
    input_units: Mapping[str, str] = field(default_factory=dict)

    def units_for(self, slot_id: str, default: str = "cm-1") -> str:
        return self.input_units.get(slot_id) or default


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
    #: A matplotlib figure produced by the engine's own library, shown as-is.
    #: Re-plotting it here would risk showing something subtly different from
    #: the model that was actually fitted.
    figure: Any | None = None


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
    """Raised when a recipe cannot be fitted from the given inputs.

    ``detail`` carries the underlying traceback for an expander in the UI. The
    message itself should say which step failed and what the user can change --
    a bare library exception leaves someone staring at a screen with no idea
    which of their uploads caused it.
    """

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message)
        self.detail = detail


#: Recognisable library failures, and what the user can actually do about them.
#: Matching on message text is brittle, but the alternative is showing a raw
#: scipy error to a spectroscopist, which helps nobody.
_HINTS: tuple[tuple[str, str], ...] = (
    (
        "must not exceed func output vector length",
        "peak finding grouped peaks so tightly that a group covers fewer data "
        "points than the model has parameters — typically two candidates a few "
        "points apart. Raise **minimum width** under Peak finding: it discards "
        "the narrow candidates that form these groups. Raising the prominence "
        "or trying another peak-finding strategy also helps. Widening the peak "
        "window does not, and neither does turning off peak fitting — the "
        "group is built and measured either way.",
    ),
    (
        "No peaks found",
        "no peaks were found in this spectrum. Check the crop range and the "
        "axis units, and that the file really is the material this step "
        "expects.",
    ),
    (
        "x-axes of the spectra should be equal",
        "the acquisitions are on different x axes and cannot be combined. "
        "They must come from the same instrument settings.",
    ),
    (
        "Unsupported conversion",
        "the axis units do not match what this step expects. Check the units "
        "selected for the uploaded spectrum.",
    ),
)


def explain(error: Exception) -> str | None:
    """A usable suggestion for a known failure, or None."""
    text = str(error)
    for needle, hint in _HINTS:
        if needle.lower() in text.lower():
            return hint
    return None


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
