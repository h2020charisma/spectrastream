"""Deciding whether a re-upload actually changed anything.

Comparing by filename lets a regenerated file with the same name keep the
previous bytes and spectrum, since nothing about the name changed. Every
``LoadedSpectrum`` already carries the SHA-256 of the bytes it was parsed
from, so content, not filename, is what should decide it.
"""

import hashlib
from collections.abc import Sequence

from spectrastream.ingest import LoadedSpectrum


def files_changed(payloads: Sequence[bytes], loaded: Sequence[LoadedSpectrum]) -> bool:
    """True when ``payloads`` differ in content from what ``loaded`` came from."""
    if len(payloads) != len(loaded):
        return True
    return [hashlib.sha256(p).hexdigest() for p in payloads] != [
        item.sha256 for item in loaded
    ]
