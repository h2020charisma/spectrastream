"""CWA 18133:2024 §8 portable calibration files.

The standard asks for a calibration to be publishable as a curve of points plus
metadata, so it can be read without the software that produced it. ramanchada2
implements the exporters; this module only adapts them to in-memory bytes,
since the app never writes to the server's disk.

Offering these matters beyond tidiness: it is the interoperable artefact a
spectroscopist can hand to a colleague on a different stack.
"""

import os
import tempfile
from typing import Any, Mapping

from ramanchada2.protocols.calibration.serialization import export_cwa_x
from ramanchada2.protocols.calibration.xcalibration import XCalibrationComponent


class CwaExportError(RuntimeError):
    """The fitted calibration cannot be expressed as a CWA §8 file."""


def has_x_calibration(calmodel: Any) -> bool:
    """CWA §8 describes an x-calibration; an intensity-only model has none."""
    return any(
        isinstance(c, XCalibrationComponent)
        for c in getattr(calmodel, "components", [])
    )


def x_calibration_model(fitted: Any) -> Any | None:
    """The underlying model of ``fitted``, if it can be exported as CWA §8.

    Two conditions, and both are refusals rather than best-effort exports:

    * There has to be a wavenumber-axis component at all -- an intensity-only
      calibration is not what §8 describes.
    * The calibration has to *output* Raman shift. A neon curve on its own maps
      cm-1 to nm, and ``export_cwa_x`` samples the model while labelling both
      CSV columns ``_cm1``. Exporting that would publish wavelengths under a
      wavenumber header, which is worse than offering no file.

    Reaching for a ramanchada2 CalibrationModel is engine-specific by nature --
    the standard describes that shape of calibration. Asking rather than
    assuming keeps the generic interface intact: an engine with no such model
    simply does not offer this download.
    """
    calmodel = getattr(fitted, "calmodel", None)
    if calmodel is None or not has_x_calibration(calmodel):
        return None
    if getattr(fitted, "output_units", None) != "cm-1":
        return None
    return calmodel


def export_x_files(
    calmodel: Any,
    spectral_range: tuple[float, float],
    npoints: int = 200,
    metadata: Mapping[str, Any] | None = None,
) -> tuple[str, str]:
    """Return ``(csv_text, json_text)`` for an x-calibration model."""
    if not has_x_calibration(calmodel):
        raise CwaExportError(
            "This calibration has no wavenumber-axis component, so there is no "
            "CWA 18133 §8 curve to export."
        )

    directory = tempfile.mkdtemp(prefix="spectrastream-cwa-")
    base = os.path.join(directory, "calibration")
    try:
        csv_path, json_path = export_cwa_x(
            calmodel,
            base,
            spectral_range=spectral_range,
            npoints=npoints,
            metadata=dict(metadata or {}),
        )
        with open(csv_path, encoding="utf-8") as fh:
            csv_text = fh.read()
        with open(json_path, encoding="utf-8") as fh:
            json_text = fh.read()
        return csv_text, json_text
    finally:
        for name in os.listdir(directory):
            os.remove(os.path.join(directory, name))
        os.rmdir(directory)
