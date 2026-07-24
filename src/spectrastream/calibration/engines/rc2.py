"""The open ramanchada2 calibration engine.

Wraps :class:`ramanchada2.protocols.calibration.CalibrationModel` behind the
generic engine interface. Each recipe step maps to one action; actions append a
component to a shared ``CalibrationModel``, which already knows how to apply its
components in order and hand units between them.

The private ``_derive_model_curve`` / ``_derive_model_zero`` are called on
purpose: the public wrappers raise ``DeprecationWarning``, and this project runs
pytest with ``filterwarnings = ["error"]``.
"""

import traceback
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
import ramanchada2.misc.constants as rc2const
from ramanchada2.misc.utils.ramanshift_to_wavelength import shift_cm_1_to_abs_nm
from ramanchada2.protocols.calibration.calibration_model import CalibrationModel
from ramanchada2.protocols.calibration.xcalibration import (
    LazerZeroingComponent,
    XCalibrationComponent,
)
from ramanchada2.protocols.calibration.ycalibration import (
    CertificatesDict,
    YCalibrationCertificate,
    YCalibrationComponent,
)
from ramanchada2.spectrum import Spectrum

from spectrastream.calibration.spec import RecipeSpec, StepSpec

from .base import (
    CalibrationContext,
    CalibrationError,
    Diagnostic,
    StepOutcome,
    explain,
    merged_params,
)

ENGINE_ID = "rc2"

#: Silicon's certified first-order band.
SI_REF_CM1 = 520.45

#: Peak-finding defaults. These are the VAMAS pipeline's, tuned over months of
#: real round-robin data -- wlen in particular, because a narrower window makes
#: narrower candidate groups and a group with fewer points than the model has
#: parameters cannot be fitted at all.
DEFAULT_FIND_KW = {"wlen": 200, "width": 1}


def _clip_window(spe: Spectrum, low: float, high: float, pad: float = 10.0):
    """Trim to a window, padded, and leave the spectrum alone if it misses."""
    lo = max(low - pad, float(min(spe.x)))
    hi = min(high + pad, float(max(spe.x)))
    if lo >= hi:
        return spe
    return spe.trim_axes(method="x-axis", boundaries=(lo, hi))


def _output_units(component) -> str | None:
    """Units of the axis a component's ``process`` produces.

    Not the same as ``model_units``, which describes the *stored model*.
    LazerZeroingComponent keeps a wavelength (so ``model_units == "nm"``) but
    its ``process`` returns Raman shift; trusting ``model_units`` here would
    convert an already-correct cm-1 axis a second time.
    """
    if isinstance(component, (LazerZeroingComponent, YCalibrationComponent)):
        return "cm-1"
    return getattr(component, "model_units", None)


class Rc2Fitted:
    """A derived ramanchada2 calibration."""

    def __init__(
        self,
        calmodel: CalibrationModel,
        recipe_id: str,
        outcomes: list[StepOutcome] | None = None,
        diagnostics: list[Diagnostic] | None = None,
    ):
        self.calmodel = calmodel
        self.recipe_id = recipe_id
        self.engine_id = ENGINE_ID
        self._outcomes = outcomes or []
        self._diagnostics = diagnostics or []

    @property
    def laser_wl_nm(self) -> float | None:
        return self.calmodel.laser_wl

    @property
    def output_units(self) -> str | None:
        """Units of the axis this calibration produces."""
        if not self.calmodel.components:
            return None
        return _output_units(self.calmodel.components[-1])

    def apply(self, spe: Spectrum, spe_units: str = "cm-1") -> Spectrum:
        if not self.calmodel.components:
            return spe
        out = self.calmodel.apply_calibration_x(spe, spe_units=spe_units)

        # The neon curve emits nm; converting back to Raman shift is laser
        # zeroing's job. With no silicon spectrum that step is skipped and the
        # axis would come back in nm, which is not what the caller asked for.
        # Convert using the *nominal* laser wavelength: the curve still
        # corrects the shape of the axis, it just carries no measured zero.
        final_units = self.output_units
        if final_units and final_units != spe_units:
            out = self.calmodel.components[-1].convert_units(
                out, final_units, spe_units, laser_wl=self.calmodel.laser_wl
            )
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine_id,
            "recipe": self.recipe_id,
            "model": self.calmodel.to_dict(),
            "outcomes": [
                {
                    "step_id": o.step_id,
                    "label": o.label,
                    "status": o.status,
                    "detail": o.detail,
                }
                for o in self._outcomes
            ],
        }

    def diagnostics(self) -> list[Diagnostic]:
        return list(self._diagnostics)

    def outcomes(self) -> list[StepOutcome]:
        return list(self._outcomes)

    @property
    def applied_steps(self) -> list[str]:
        return [o.step_id for o in self._outcomes if o.status == "applied"]


def _as_float_dict(ref: Any) -> dict[float, float]:
    return {float(k): float(v) for k, v in dict(ref).items()}


def _neon_reference(
    params: Mapping[str, Any], laser_wl: float | None
) -> dict[float, float]:
    """Reference Neon lines, from the recipe if given, else ramanchada2's table."""
    ref = params.get("ref")
    if ref:
        return _as_float_dict(ref)
    if laser_wl is None:
        raise CalibrationError(
            "Neon calibration needs a laser wavelength: set one on the "
            "instrument profile, or put an explicit line list in the recipe."
        )
    try:
        return rc2const.NEON_WL[int(laser_wl)]
    except KeyError as err:
        available = sorted(rc2const.NEON_WL)
        raise CalibrationError(
            f"No built-in Neon reference for {laser_wl:g} nm "
            f"(available: {available}). Supply one in the recipe."
        ) from err


def _curve_diagnostic(step: StepSpec, component: XCalibrationComponent) -> Diagnostic:
    """Sample the fitted curve so the UI can draw uncalibrated vs calibrated."""
    peaks = getattr(component, "peaks", None)
    table = None
    if peaks is not None and len(peaks):
        try:
            table = pd.DataFrame(peaks)
        except (ValueError, TypeError):
            table = None
    return Diagnostic(
        step_id=step.id,
        label=step.label,
        kind="table",
        text=f"matched {0 if table is None else len(table)} peaks",
        table=table,
    )


def _action_x_curve(
    calmodel: CalibrationModel,
    step: StepSpec,
    inputs: Mapping[str, Spectrum],
    ctx: CalibrationContext,
    params: Mapping[str, Any],
) -> tuple[StepOutcome, list[Diagnostic]]:
    spe = inputs[step.inputs[0]]
    ref = _neon_reference(params, calmodel.laser_wl)
    find_kw = dict(params.get("find_kw") or DEFAULT_FIND_KW)
    prominence_coeff = float(params.get("prominence_coeff", 3))
    calmodel.prominence_coeff = prominence_coeff
    find_kw["prominence"] = spe.y_noise_MAD() * prominence_coeff

    component = calmodel._derive_model_curve(
        spe=spe,
        ref=ref,
        spe_units=ctx.units_for(step.inputs[0], params.get("spe_units", "cm-1")),
        ref_units=params.get("ref_units", "nm"),
        find_kw=find_kw,
        fit_peaks_kw=dict(params.get("fit_peaks_kw") or {}),
        should_fit=bool(params.get("should_fit", False)),
        name=step.label,
        match_method=params.get("match_method", "qargmin2d"),
        interpolator_method=params.get("interpolator_method", "poly"),
        extrapolate=bool(params.get("extrapolate", True)),
    )
    outcome = StepOutcome(step.id, step.label, "applied", f"{len(ref)} reference lines")
    return outcome, [_curve_diagnostic(step, component)]


def _action_laser_zero(
    calmodel: CalibrationModel,
    step: StepSpec,
    inputs: Mapping[str, Spectrum],
    ctx: CalibrationContext,
    params: Mapping[str, Any],
) -> tuple[StepOutcome, list[Diagnostic]]:
    spe = inputs[step.inputs[0]]
    ref = _as_float_dict(params.get("ref") or {SI_REF_CM1: 1})
    ref_cm1 = next(iter(ref))
    spe_units = ctx.units_for(step.inputs[0], params.get("spe_units", "cm-1"))

    # This mirrors the VAMAS pipeline's spectraframe_calibrate, which is the
    # sequence known to work on real round-robin data. Each step below exists
    # because leaving it out breaks on ordinary spectra.
    window = float(params.get("window_cm1", 100.0))

    # 1. Narrow to the band while still on a Raman-shift axis, where the window
    #    is expressible. Everything outside it is a source of spurious peaks.
    if window and spe_units == "cm-1":
        low, high = ref_cm1 - window, ref_cm1 + window
        if min(spe.x) < high and max(spe.x) > low:
            spe = spe.trim_axes(
                method="x-axis",
                boundaries=(max(low, float(min(spe.x))), min(high, float(max(spe.x)))),
            )

    # 2. Push it through the steps derived so far: zeroing measures the band on
    #    whatever axis those produced.
    if calmodel.components:
        spe = calmodel.apply_calibration_x(spe, spe_units=spe_units)
        spe_units = _output_units(calmodel.components[-1])

        # 3. Extrapolating the neon curve beyond its matched range yields NaNs.
        #    Peak fitting over them is what produces "func input vector length
        #    N must not exceed func output vector length M": the fit sees far
        #    fewer usable points than it has parameters.
        spe = spe.dropna()

        # 4. Re-narrow on the *converted* axis. The cm-1 window above no longer
        #    applies once the axis is in nm, and without this the fit is back to
        #    chasing noise across the full range.
        if window:
            laser = calmodel.laser_wl
            if laser and spe_units == "nm":
                lo_nm = shift_cm_1_to_abs_nm(ref_cm1 - window, laser)
                hi_nm = shift_cm_1_to_abs_nm(ref_cm1 + window, laser)
                spe = _clip_window(spe, *sorted([lo_nm, hi_nm]))

    if len(spe.x) < 5:
        raise CalibrationError(
            "After cropping to the band and discarding points the calibration "
            "curve could not reach, too little of the silicon spectrum is left "
            "to fit. Widen the crop, or check that the neon calibration covers "
            "the silicon band."
        )

    find_kw = dict(params.get("find_kw") or DEFAULT_FIND_KW)
    find_kw["prominence"] = spe.y_noise_MAD() * calmodel.prominence_coeff

    component = calmodel._derive_model_zero(
        spe=spe,
        ref=ref,
        spe_units=spe_units,
        ref_units=params.get("ref_units", "cm-1"),
        find_kw=find_kw,
        fit_peaks_kw=dict(params.get("fit_peaks_kw") or {}),
        should_fit=bool(params.get("should_fit", True)),
        name=step.label,
        profile=params.get("si_profile", "Pearson4"),
    )
    zero_nm = float(component.model)
    laser_nm = 1e7 / (1e7 / zero_nm + ref_cm1)
    detail = f"band at {zero_nm:.4f} nm, laser {laser_nm:.4f} nm"
    return (
        StepOutcome(step.id, step.label, "applied", detail),
        [
            Diagnostic(
                step_id=step.id,
                label=step.label,
                kind="scalar",
                value=laser_nm,
                text=f"calibrated laser wavelength {laser_nm:.4f} nm",
            )
        ],
    )


def _resolve_certificate(
    params: Mapping[str, Any], laser_wl: float | None
) -> YCalibrationCertificate:
    cert = params.get("certificate")
    if isinstance(cert, YCalibrationCertificate):
        return cert
    if isinstance(cert, Mapping):
        return YCalibrationCertificate.model_validate(dict(cert))
    if laser_wl is None:
        raise CalibrationError(
            "Intensity calibration needs a laser wavelength to pick a certificate."
        )
    certificates = CertificatesDict()
    available = certificates.get_certificates(wavelength=int(laser_wl))
    if not available:
        raise CalibrationError(
            f"No intensity-calibration certificate for {laser_wl:g} nm."
        )
    key = cert if isinstance(cert, str) else None
    if key is None:
        key = next(iter(available))
    if key not in available:
        raise CalibrationError(
            f"Certificate {key!r} not available for {laser_wl:g} nm "
            f"(have: {sorted(available)})."
        )
    return certificates.get(wavelength=int(laser_wl), key=key)


def _action_y_intensity(
    calmodel: CalibrationModel,
    step: StepSpec,
    inputs: Mapping[str, Spectrum],
    ctx: CalibrationContext,
    params: Mapping[str, Any],
) -> tuple[StepOutcome, list[Diagnostic]]:
    spe = inputs[step.inputs[0]]
    certificate = _resolve_certificate(params, calmodel.laser_wl)

    # The certificate's response is a function of *calibrated* Raman shift, so
    # the measured reference has to go through the x-steps derived above first.
    if calmodel.components:
        spe = calmodel.apply_calibration_x(
            spe,
            spe_units=ctx.units_for(step.inputs[0], params.get("spe_units", "cm-1")),
        )

    component = YCalibrationComponent(
        calmodel.laser_wl,
        reference_spe_xcalibrated=spe,
        certificate=certificate,
    )
    component.name = step.label
    calmodel.components.append(component)

    lo, hi = certificate.raman_shift or (float(min(spe.x)), float(max(spe.x)))
    grid = np.linspace(float(lo), float(hi), 200)
    return (
        StepOutcome(step.id, step.label, "applied", f"certificate {certificate.id}"),
        [
            Diagnostic(
                step_id=step.id,
                label=step.label,
                kind="curve",
                text=f"certificate {certificate.id}",
                curve=(grid.tolist(), np.asarray(certificate.Y(grid)).tolist()),
            )
        ],
    )


ACTIONS = {
    "x_curve": _action_x_curve,
    "laser_zero": _action_laser_zero,
    "y_intensity": _action_y_intensity,
}


class Rc2Engine:
    """Neon/Silicon x-calibration and SRM intensity calibration."""

    id = ENGINE_ID
    label = "ramanchada2 (open)"

    def __init__(self, recipes: Iterable[RecipeSpec] = ()):
        self._recipes = list(recipes)

    def recipes(self) -> Iterable[RecipeSpec]:
        return list(self._recipes)

    def fit(
        self,
        recipe: RecipeSpec,
        inputs: Mapping[str, Spectrum],
        context: CalibrationContext,
        params: Mapping[str, Any] | None = None,
    ) -> Rc2Fitted:
        available = {k for k, v in inputs.items() if v is not None}
        missing = recipe.missing_required_slots(available)
        if missing:
            labels = [recipe.slot(s).label for s in missing]
            raise CalibrationError(f"Missing required spectra: {', '.join(labels)}")

        laser_wl = context.laser_wl_nm
        calmodel = CalibrationModel(int(laser_wl) if laser_wl is not None else None)
        # "drop" discards non-monotonic stretches of the fitted curve instead of
        # filling them with NaN. The VAMAS pipeline sets this, and without it
        # every downstream step has to cope with holes in the axis.
        calmodel.nonmonotonic = str((params or {}).get("nonmonotonic", "drop"))

        outcomes: list[StepOutcome] = []
        diagnostics: list[Diagnostic] = []
        for step in recipe.steps:
            absent = [s for s in step.inputs if s not in available]
            if absent:
                # Optional inputs missing is the documented skip case (no Si
                # spectrum still yields a usable Neon curve); a required one
                # missing was already rejected above.
                outcomes.append(
                    StepOutcome(
                        step.id,
                        step.label,
                        "skipped",
                        f"no {', '.join(recipe.slot(s).label for s in absent)}",
                    )
                )
                continue

            action = ACTIONS.get(step.action)
            if action is None:
                raise CalibrationError(
                    f"Engine {self.id!r} has no action {step.action!r} "
                    f"(step {step.id!r})."
                )
            step_params = merged_params(step.params, params, step.id)
            try:
                outcome, step_diags = action(
                    calmodel, step, inputs, context, step_params
                )
            except CalibrationError:
                raise
            except Exception as err:  # noqa: BLE001 - reported, not swallowed
                # Name the step and the spectrum it was working on, and add a
                # suggestion when the underlying failure is one we recognise.
                # A bare library message tells the user nothing about which of
                # their uploads to look at or what to change.
                sources = ", ".join(recipe.slot(s).label for s in step.inputs)
                message = f"Step '{step.label}' failed"
                if sources:
                    message += f" while processing the {sources}"
                hint = explain(err)
                message += f". {hint}" if hint else f": {err}"
                if not step.optional:
                    raise CalibrationError(
                        message, detail=traceback.format_exc()
                    ) from err
                outcomes.append(StepOutcome(step.id, step.label, "failed", message))
                continue
            outcomes.append(outcome)
            diagnostics.extend(step_diags)

        if not calmodel.components:
            raise CalibrationError(
                "No calibration step produced a result -- nothing to apply."
            )
        return Rc2Fitted(calmodel, recipe.id, outcomes, diagnostics)

    def load(self, data: Mapping[str, Any]) -> Rc2Fitted:
        calmodel = CalibrationModel.from_dict(dict(data["model"]))
        outcomes = [
            StepOutcome(
                o.get("step_id", ""),
                o.get("label", ""),
                o.get("status", "applied"),
                o.get("detail", ""),
            )
            for o in data.get("outcomes", [])
        ]
        return Rc2Fitted(calmodel, data.get("recipe", ""), outcomes)


__all__ = [
    "ENGINE_ID",
    "LazerZeroingComponent",
    "Rc2Engine",
    "Rc2Fitted",
    "SI_REF_CM1",
]
