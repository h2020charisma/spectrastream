"""Deciding whether a re-upload actually changed anything.

Filename alone cannot distinguish a regenerated file from an untouched one --
only content can. Every loaded spectrum already carries the SHA-256 of the
bytes it came from, so that is what a re-upload is compared against.
"""

import hashlib
from types import SimpleNamespace

from spectrastream.upload import files_changed


def _loaded(*payloads: bytes):
    return [SimpleNamespace(sha256=hashlib.sha256(p).hexdigest()) for p in payloads]


def test_same_filename_different_bytes_is_a_change():
    """The actual bug: comparing by filename let a regenerated file with the
    same name keep the previous bytes and spectrum."""
    loaded = _loaded(b"old data")
    assert files_changed([b"new data"], loaded)


def test_same_bytes_is_not_a_change():
    payload = b"identical bytes"
    loaded = _loaded(payload)
    assert not files_changed([payload], loaded)


def test_same_bytes_under_a_new_name_is_not_a_change():
    """files_changed only ever sees bytes, never a filename -- this is
    exactly the case the old filename comparison could not express."""
    payload = b"unchanged content"
    loaded = _loaded(payload)
    assert not files_changed([payload], loaded)


def test_a_different_number_of_files_is_a_change():
    loaded = _loaded(b"one")
    assert files_changed([b"one", b"two"], loaded)
