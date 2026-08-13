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


#: Keys ramanchada2 fills in from the path it was handed. Since uploads are
#: parsed from a temporary file, these hold a meaningless name like
#: "tmpluguj6qq.spc" -- worse than absent, because they look authoritative and
#: would travel into the published NeXus record. The real upload name is
#: recorded separately as LoadedSpectrum.filename.
_PATH_DERIVED_KEYS = {"original file", "filename", "file", "temporary file"}


def _spectrum_metadata(spe: Spectrum, tmp_name: str) -> dict[str, Any]:
    """Metadata the vendor format carried, if any. Never fatal."""
    meta: dict[str, Any] = {}
    try:
        keys = spe.meta.get_all_keys()
    except (AttributeError, TypeError):
        return meta

    tmp_stem = os.path.basename(tmp_name)
    for key in keys:
        if key.startswith("@") or str(key).strip().lower() in _PATH_DERIVED_KEYS:
            continue
        try:
            value = spe.meta[key]
        except (KeyError, TypeError):
            continue
        # Catch any other key that happens to hold the temp path.
        if isinstance(value, str) and tmp_stem in value:
            continue
        meta[str(key)] = value
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
        source_metadata=_spectrum_metadata(spe, tmp_name),
    )
