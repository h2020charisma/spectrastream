"""Turn an uploaded file into a ramanchada2 Spectrum.

ramanchada2 reads from paths, not file objects, so an upload has to touch disk
briefly. The original implementation wrote into a ``NamedTemporaryFile`` and
parsed inside the ``with`` block, which fails on Windows (the file is still
open). Here the handle is closed before parsing and removed in a ``finally``.
"""

import hashlib
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ramanchada2 as rc2
from ramanchada2.spectrum import Spectrum


class IngestError(ValueError):
    """The uploaded file could not be parsed as a spectrum."""


@dataclass
class LoadedSpectrum:
    """A parsed spectrum plus the provenance of the file it came from."""

    spectrum: Spectrum
    filename: str
    sha256: str
    filetype: str
    units: str = "cm-1"
    source_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_points(self) -> int:
        return len(self.spectrum.x)

    @property
    def x_range(self) -> tuple[float, float]:
        x = self.spectrum.x
        return float(min(x)), float(max(x))


def _spectrum_metadata(spe: Spectrum) -> dict[str, Any]:
    """Metadata the vendor format carried, if any. Never fatal."""
    meta: dict[str, Any] = {}
    try:
        keys = spe.meta.get_all_keys()
    except (AttributeError, TypeError):
        return meta
    for key in keys:
        if key.startswith("@"):
            continue
        try:
            meta[str(key)] = spe.meta[key]
        except (KeyError, TypeError):
            continue
    return meta


def load_spectrum(
    data: bytes,
    filename: str,
    units: str = "cm-1",
    filetype: str | None = None,
) -> LoadedSpectrum:
    """Parse ``data`` using whichever ramanchada2 reader matches its extension."""
    if not data:
        raise IngestError(f"{filename}: file is empty")

    extension = (filetype or Path(filename).suffix.lstrip(".")).lower()
    if not extension:
        raise IngestError(
            f"{filename}: no file extension, so the format cannot be determined"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as handle:
        handle.write(data)
        tmp_name = handle.name
    try:
        try:
            spe = rc2.spectrum.from_local_file(tmp_name, filetype=extension)
        except Exception as err:  # noqa: BLE001 - reader errors vary by format
            raise IngestError(
                f"{filename}: could not read as {extension}: {err}"
            ) from err
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

    if len(spe.x) == 0:
        raise IngestError(f"{filename}: parsed successfully but contains no points")

    return LoadedSpectrum(
        spectrum=spe,
        filename=filename,
        sha256=hashlib.sha256(data).hexdigest(),
        filetype=extension,
        units=units,
        source_metadata=_spectrum_metadata(spe),
    )
