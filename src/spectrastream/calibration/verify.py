"""Verify a calibration against a reference material (CWA 18133 verification).

The question this answers is *how good is the calibration* — not how it was
derived. A reference material with certified line positions (polystyrene,
calcite, silicon) is measured, its peaks are fitted before and after the
calibration is applied, and the per-peak distance to the certified positions is
compared. If the calibration is doing its job, those distances shrink.

The peak matching is ramanchada2's own ``match_peaks4analysis`` — this module
only assembles its inputs (the reference line tables come straight from
``ramanchada2.misc.constants``) and summarises its output. It is engine-agnostic:
it uses nothing but ``FittedCalibration.apply``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import ramanchada2.misc.constants as rc2const
from ramanchada2.protocols.calibration.xcalibration import match_peaks4analysis
from ramanchada2.spectrum import Spectrum

from .engines.base import CalibrationError, FittedCalibration

#: Certified line positions (cm-1) keyed by material, taken from ramanchada2's
#: constants so there is a single source of truth. Silicon is the one first-order
#: band; polystyrene and calcite are the CWA/ASTM tables.
REFERENCE_MATERIALS: dict[str, dict[float, float]] = {
    "Si": {520.45: 1.0},
    "PST": dict(rc2const.PST_RS_dict),
    "CAL": dict(rc2const.calcite_cwa_dict),
}

MATERIAL_LABELS = {
    "Si": "Silicon — 520.45 cm⁻¹",
    "PST": "Polystyrene — ASTM E1840",
    "CAL": "Calcite — CWA Table 7",
}

#: Beyond this, a "matched" pair is a matching artifact (a found peak paired with
#: an unrelated reference line), present before *and* after calibration; it is
#: excluded from the summary so a few artifacts cannot mask or fake a change.
ARTIFACT_TOLERANCE_CM1 = 20.0

AS_MEASURED = "As measured"
CALIBRATED = "Calibrated"


def _profile_for(material: str) -> str:
    # Silicon's band is asymmetric; the CHARISMA pipeline fits it with Pearson4.
    return "Pearson4" if material == "Si" else "Gaussian"


def _reference_span(ref: dict[float, float]) -> tuple[float, float]:
    lines = sorted(ref)
    return lines[0], lines[-1]


def _prepare(spe: Spectrum, material: str, ref: dict[float, float]) -> Spectrum:
    """Trim to the material's band and remove pedestal + baseline.

    Mirrors the CHARISMA verification pre-processing: silicon is cropped tight
    around 520.45, other materials to their certified span (with a margin), then
    the pedestal is zeroed and a SNIP baseline removed so peak fitting sees the
    bands and not the background.
    """
    if material == "Si":
        low, high = 520.45 - 100, 520.45 + 100
    else:
        lo, hi = _reference_span(ref)
        low, high = lo - 100, hi + 100
    xmin, xmax = float(min(spe.x)), float(max(spe.x))
    low, high = max(low, xmin), min(high, xmax)
    if low < high:
        spe = spe.trim_axes(method="x-axis", boundaries=(low, high))
    y = np.asarray(spe.y) - float(np.min(spe.y))
    spe = spe.__class__(x=np.asarray(spe.x, dtype=float), y=y)
    return spe.subtract_baseline_rc1_snip(niter=40)


@dataclass
class VerifyResult:
    """Per-peak agreement with the certified positions, before and after."""

    material: str
    #: The certified positions (cm-1 → relative intensity) checked against, so
    #: the UI can mark them on the plot and export them.
    reference: dict[float, float]
    matched: pd.DataFrame  # spe / reference / distances / before_after
    summary: pd.DataFrame  # mean/median |distance| and count per stage
    as_measured: tuple[np.ndarray, np.ndarray]
    calibrated: tuple[np.ndarray, np.ndarray]
    mean_before: float | None
    mean_after: float | None
    n_matched: int

    @property
    def improved(self) -> bool | None:
        if self.mean_before is None or self.mean_after is None:
            return None
        return self.mean_after <= self.mean_before


def verify_against_reference(
    fitted: FittedCalibration,
    spe: Spectrum,
    *,
    material: str,
    spe_units: str = "cm-1",
    match_method: str = "qargmin2d",
    profile: str | None = None,
    ref: dict[float, float] | None = None,
    find_kw: dict | None = None,
    fit_peaks_kw: dict | None = None,
    preprocess: bool = True,
) -> VerifyResult:
    """Fit a reference material's peaks before/after calibration and compare them
    to the certified positions.

    ``material`` selects a built-in reference table (``"Si"``/``"PST"``/``"CAL"``)
    unless an explicit ``ref`` (position → relative intensity) is supplied.
    """
    if ref is None:
        try:
            ref = REFERENCE_MATERIALS[material]
        except KeyError as err:
            raise CalibrationError(
                f"No built-in reference lines for {material!r} "
                f"(have: {sorted(REFERENCE_MATERIALS)}). Supply an explicit line list."
            ) from err
    profile = profile or _profile_for(material)

    # When the caller has already cropped and baselined (the Verify page does,
    # via its own controls), preprocessing again would double the baseline.
    prepared = _prepare(spe, material, ref) if preprocess else spe
    calibrated = fitted.apply(prepared, spe_units=spe_units)

    matched = match_peaks4analysis(
        [prepared, calibrated],
        ref=ref,
        # the certified table is cm-1 and the calibrated axis is cm-1; the
        # as-measured spectrum is compared on the same footing
        spe_units="cm-1",
        find_kw=find_kw or {},
        fit_peaks_kw=fit_peaks_kw or {},
        profile=profile,
        should_fit=True,
        match_method=match_method,
        stages=[AS_MEASURED, CALIBRATED],
    )
    if matched is None or matched.empty:
        raise CalibrationError(
            "No peaks could be matched to the reference. Check the material, the "
            "axis units, and that the band is present in the crop."
        )

    mp = matched.copy()
    mp["absd"] = mp["distances"].abs()
    ok = mp[mp["absd"] <= ARTIFACT_TOLERANCE_CM1]
    summary = (
        ok.groupby("before_after")["absd"]
        .agg(mean="mean", median="median", n="count")
        .reindex([AS_MEASURED, CALIBRATED])
    )

    def _mean(stage: str) -> float | None:
        if stage in summary.index and np.isfinite(summary.loc[stage, "mean"]):
            return float(summary.loc[stage, "mean"])
        return None

    return VerifyResult(
        material=material,
        reference=dict(ref),
        matched=matched,
        summary=summary.reset_index().rename(columns={"before_after": "stage"}),
        as_measured=(np.asarray(prepared.x), np.asarray(prepared.y)),
        calibrated=(np.asarray(calibrated.x), np.asarray(calibrated.y)),
        mean_before=_mean(AS_MEASURED),
        mean_after=_mean(CALIBRATED),
        n_matched=int(len(ok)),
    )


__all__ = [
    "REFERENCE_MATERIALS",
    "MATERIAL_LABELS",
    "VerifyResult",
    "verify_against_reference",
]
