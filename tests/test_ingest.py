import pytest

from spectrastream.ingest import IngestError, load_spectrum


def test_loads_a_text_spectrum(neon_spectrum):
    assert neon_spectrum.n_points > 100
    lo, hi = neon_spectrum.x_range
    assert lo < hi
    assert len(neon_spectrum.sha256) == 64


def test_loads_a_binary_vendor_format(target_spectrum):
    """Any ramanchada2-supported format is the whole point of the floor."""
    assert target_spectrum.filetype == "spc"
    assert target_spectrum.n_points > 100


def test_checksum_is_of_the_original_bytes(neon_path):
    import hashlib

    data = neon_path.read_bytes()
    loaded = load_spectrum(data, neon_path.name)
    assert loaded.sha256 == hashlib.sha256(data).hexdigest()


def test_empty_file_is_rejected():
    with pytest.raises(IngestError, match="empty"):
        load_spectrum(b"", "thing.txt")


def test_missing_extension_is_rejected():
    with pytest.raises(IngestError, match="no file extension"):
        load_spectrum(b"1 2\n3 4\n", "noextension")


def test_unparseable_content_is_reported_with_the_filename():
    with pytest.raises(IngestError, match="notaspectrum.spc"):
        load_spectrum(b"definitely not a spectrum", "notaspectrum.spc")
