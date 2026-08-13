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
from ramanchada2.protocols.calibration.xcalibration import (
    fit_peaks,
    match_peaks4analysis,
)
from ramanchada2.spectrum import Spectrum

from spectrastream.peaks import to_axis

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


def _prepare(
    spe: Spectrum,
    material: str,
    ref: dict[float, float],
    spe_units: str = "cm-1",
    laser_wl_nm: float | None = None,
) -> Spectrum:
    """Trim to the material's band and remove pedestal + baseline.

    Mirrors the CHARISMA verification pre-processing: silicon is cropped tight
    around 520.45, other materials to their certified span (with a margin), then
    the pedestal is zeroed and a SNIP baseline removed so peak fitting sees the
    bands and not the background.

    The certified span is cm-1, so the spectrum is converted to cm-1 first --
    a trim in the spectrum's own nm or pixel units would crop the wrong region.
    """
    spe = to_axis(spe, spe_units, "cm-1", laser_wl_nm)
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


def _prepared_cm1(
    spe: Spectrum,
    material: str,
    ref: dict[float, float],
    spe_units: str,
    laser_wl_nm: float | None,
    preprocess: bool,
) -> Spectrum:
    """The spectrum verification actually compares, always in cm-1.

    ``preprocess`` only toggles whether trim + baseline run -- the axis is
    converted to cm-1 either way, since certified positions and
    ``match_peaks4analysis`` are always cm-1.
    """
    if spe_units == "pixel":
        raise CalibrationError(
            "Verification needs a Raman-shift or wavelength axis to crop and "
            "match against certified positions; detector pixel positions "
            "have no established conversion to either."
        )
    if spe_units != "cm-1" and laser_wl_nm is None:
        raise CalibrationError(
            "Converting this spectrum to Raman shift for verification needs "
            "the calibration's excitation wavelength, which is not available."
        )
    if preprocess:
        return _prepare(
            spe, material, ref, spe_units=spe_units, laser_wl_nm=laser_wl_nm
        )
    return to_axis(spe, spe_units, "cm-1", laser_wl_nm)


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
    laser_wl_nm = getattr(fitted, "laser_wl_nm", None)
    prepared = _prepared_cm1(spe, material, ref, spe_units, laser_wl_nm, preprocess)
    # `prepared` is cm-1 by construction (see _prepared_cm1) -- not spe_units.
    calibrated = fitted.apply(prepared, spe_units="cm-1")

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


def has_relative_intensities(ref: dict[float, float]) -> bool:
    """True when a reference has *varying* certified intensities to compare.

    Silicon (one band) and calcite (all listed as 1.0) carry no relative
    intensities; polystyrene (ASTM E1840) does.
    """
    return len({round(float(v), 6) for v in ref.values()}) > 1


def _fit_intensities(
    spe: Spectrum,
    ref: dict[float, float],
    profile: str,
    find_kw,
    fit_peaks_kw,
    tolerance: float,
) -> dict[float, float]:
    """``{reference_position: measured amplitude}`` for the reference lines that
    have a fitted peak within ``tolerance``."""
    _, pos_amp = fit_peaks(
        spe,
        dict(find_kw or {}),
        dict(fit_peaks_kw or {}),
        profile=profile,
        should_fit=True,
    )
    if not pos_amp:
        return {}
    positions = np.array(list(pos_amp.keys()), dtype=float)
    amps = np.array(list(pos_amp.values()), dtype=float)
    out: dict[float, float] = {}
    for rpos in ref:
        i = int(np.argmin(np.abs(positions - rpos)))
        if abs(positions[i] - rpos) <= tolerance:
            out[float(rpos)] = float(abs(amps[i]))
    return out


def _normalize_to_100(d: dict[float, float]) -> dict[float, float]:
    top = max(d.values()) if d else 0.0
    return {k: (100.0 * v / top if top else 0.0) for k, v in d.items()}


@dataclass
class IntensityResult:
    """Measured relative peak intensities vs the certified table, before/after."""

    material: str
    table: pd.DataFrame  # position, reference, as_measured, calibrated, dev_*
    mean_before: float | None
    mean_after: float | None
    n_matched: int
    intensity_corrected: bool

    @property
    def improved(self) -> bool | None:
        if self.mean_before is None or self.mean_after is None:
            return None
        return self.mean_after <= self.mean_before


def verify_relative_intensity(
    fitted: FittedCalibration,
    spe: Spectrum,
    *,
    material: str = "PST",
    spe_units: str = "cm-1",
    profile: str = "Gaussian",
    ref: dict[float, float] | None = None,
    find_kw: dict | None = None,
    fit_peaks_kw: dict | None = None,
    preprocess: bool = True,
    tolerance: float = ARTIFACT_TOLERANCE_CM1,
) -> IntensityResult:
    """Compare a material's *relative peak intensities* to its certified table,
    before and after calibration.

    This is the intensity counterpart of :func:`verify_against_reference`: peaks
    are fitted on the as-measured and calibrated spectra, matched to the
    reference lines, and each stage's amplitudes normalised to 100 at the
    strongest line, then compared with the certified relative intensities
    (ASTM E1840 for polystyrene). It is meaningful when a *y*-calibration was
    applied -- an x-only calibration barely moves relative intensities.
    """
    if ref is None:
        ref = REFERENCE_MATERIALS.get(material)
    if not ref:
        raise CalibrationError(
            f"No built-in reference lines for {material!r}. Supply an explicit list."
        )
    if not has_relative_intensities(ref):
        raise CalibrationError(
            "This reference has no relative intensities to compare against."
        )

    laser_wl_nm = getattr(fitted, "laser_wl_nm", None)
    prepared = _prepared_cm1(spe, material, ref, spe_units, laser_wl_nm, preprocess)
    # `prepared` is cm-1 by construction (see _prepared_cm1) -- not spe_units.
    calibrated = fitted.apply(prepared, spe_units="cm-1")

    before = _normalize_to_100(
        _fit_intensities(prepared, ref, profile, find_kw, fit_peaks_kw, tolerance)
    )
    after = _normalize_to_100(
        _fit_intensities(calibrated, ref, profile, find_kw, fit_peaks_kw, tolerance)
    )
    ref_norm = _normalize_to_100({float(k): float(v) for k, v in ref.items()})

    rows = []
    for pos in sorted(ref):
        r = ref_norm[float(pos)]
        b = before.get(float(pos))
        a = after.get(float(pos))
        rows.append(
            {
                "position_cm-1": float(pos),
                "reference": r,
                "as_measured": b,
                "calibrated": a,
                "dev_before": None if b is None else abs(b - r),
                "dev_after": None if a is None else abs(a - r),
            }
        )
    table = pd.DataFrame(rows)

    def _mean(col: str) -> float | None:
        vals = table[col].dropna()
        return float(vals.mean()) if len(vals) else None

    corrections = getattr(fitted, "corrections", lambda: "")()
    return IntensityResult(
        material=material,
        table=table,
        mean_before=_mean("dev_before"),
        mean_after=_mean("dev_after"),
        n_matched=int(table["calibrated"].notna().sum()),
        intensity_corrected="intensity" in (corrections or ""),
    )


__all__ = [
    "REFERENCE_MATERIALS",
    "MATERIAL_LABELS",
    "VerifyResult",
    "IntensityResult",
    "has_relative_intensities",
    "verify_against_reference",
    "verify_relative_intensity",
]
