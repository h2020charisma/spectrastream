"""Per-spectrum preprocessing, declared in the recipe.

Reference spectra usually need work before a calibration can be derived from
them: a silicon wafer wants cropping to its band, a neon lamp wants normalising,
an SRM measurement wants its baseline removed. The old app exposed this as a row
of tabs per spectrum; here the *defaults* come from the recipe -- which knows
what its materials need -- and the UI lets you override them.

Every operation is optional and reversible in the sense that the original
spectrum is kept: preprocessing produces a working copy, so a bad choice costs a
click, not a re-upload.
"""

from typing import Any, Callable, Literal, Mapping

from pydantic import BaseModel, Field
from ramanchada2.spectrum import Spectrum

OpName = Literal["trim", "baseline", "normalize", "smooth"]

BASELINE_METHODS = ("snip", "als")
SMOOTH_METHODS = ("savgol", "wiener", "median", "gauss", "boxcar")

#: Normalisation strategies ramanchada2 offers. They are not interchangeable:
#: min-max rescales to [0, 1], area/density normalise the integral, and the
#: L-norms divide by a vector norm. Which one is right depends on what the
#: spectrum is being compared against, so it is the user's call.
NORMALIZE_STRATEGIES = (
    "minmax",
    "unity",
    "min_unity",
    "unity_density",
    "unity_area",
    "L1",
    "L2",
)

NORMALIZE_LABELS = {
    "minmax": "Min-max (0 to 1)",
    "unity": "Unity maximum",
    "min_unity": "Unity, offset to zero",
    "unity_density": "Unity density",
    "unity_area": "Unity area",
    "L1": "L1 norm",
    "L2": "L2 norm",
}


class PreprocessStep(BaseModel):
    """One operation applied to a reference spectrum before fitting."""

    op: OpName
    #: Whether it runs by default. The UI shows a toggle either way.
    enabled: bool = False
    label: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    def display_label(self) -> str:
        if self.label:
            return self.label
        return {
            "trim": "Crop",
            "baseline": "Remove baseline",
            "normalize": "Normalise",
            "smooth": "Smooth",
        }[self.op]


class PreprocessError(ValueError):
    """A preprocessing operation could not be applied."""


def _op_trim(spe: Spectrum, params: Mapping[str, Any]) -> Spectrum:
    low = params.get("min")
    high = params.get("max")
    x_min, x_max = float(min(spe.x)), float(max(spe.x))
    low = x_min if low is None else max(float(low), x_min)
    high = x_max if high is None else min(float(high), x_max)
    if low >= high:
        raise PreprocessError(
            f"crop range {low:g}–{high:g} does not overlap the spectrum "
            f"({x_min:g}–{x_max:g})"
        )
    return spe.trim_axes(method="x-axis", boundaries=(low, high))


def _op_baseline(spe: Spectrum, params: Mapping[str, Any]) -> Spectrum:
    method = str(params.get("method", "snip")).lower()
    if method == "snip":
        return spe.subtract_baseline_rc1_snip(niter=int(params.get("niter", 30)))
    if method == "als":
        return spe.subtract_baseline_rc1_als(
            niter=int(params.get("niter", 30)),
            lam=float(params.get("lam", 1e5)),
            p=float(params.get("p", 0.001)),
        )
    raise PreprocessError(f"unknown baseline method {method!r}")


def _op_normalize(spe: Spectrum, params: Mapping[str, Any]) -> Spectrum:
    strategy = str(params.get("strategy", "minmax"))
    if strategy not in NORMALIZE_STRATEGIES:
        raise PreprocessError(f"unknown normalisation strategy {strategy!r}")
    return spe.normalize(strategy=strategy)


def _op_smooth(spe: Spectrum, params: Mapping[str, Any]) -> Spectrum:
    method = str(params.get("method", "savgol")).lower()
    if method not in SMOOTH_METHODS:
        raise PreprocessError(f"unknown smoothing method {method!r}")
    kwargs: dict[str, Any] = {}
    if method == "savgol":
        kwargs["window_length"] = int(params.get("window_length", 5))
        kwargs["polyorder"] = int(params.get("polyorder", 3))
    return spe.smoothing_RC1(method=method, **kwargs)


OPS: dict[str, Callable[[Spectrum, Mapping[str, Any]], Spectrum]] = {
    "trim": _op_trim,
    "baseline": _op_baseline,
    "normalize": _op_normalize,
    "smooth": _op_smooth,
}


def apply_steps(
    spe: Spectrum, steps: list[PreprocessStep]
) -> tuple[Spectrum, list[str]]:
    """Run the enabled steps in order.

    Returns the processed spectrum and a human-readable list of what ran, so
    the UI and the stored provenance can say what was done to the data rather
    than presenting a silently altered spectrum.
    """
    applied: list[str] = []
    result = spe
    for step in steps:
        if not step.enabled:
            continue
        op = OPS.get(step.op)
        if op is None:
            raise PreprocessError(f"unknown preprocessing operation {step.op!r}")
        try:
            result = op(result, step.params)
        except PreprocessError:
            raise
        except Exception as err:  # noqa: BLE001 - surfaced, not swallowed
            raise PreprocessError(f"{step.display_label()} failed: {err}") from err
        applied.append(step.display_label())
    return result, applied
