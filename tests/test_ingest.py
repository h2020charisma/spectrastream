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


def test_the_temp_filename_never_reaches_the_metadata(target_spectrum):
    """Uploads are parsed from a temporary file, so ramanchada2 records a name
    like "tmpluguj6qq.spc" as the original. That is worse than absent: it looks
    authoritative and would travel into the published NeXus record."""
    for key, value in target_spectrum.source_metadata.items():
        assert "tmp" not in str(value).lower(), f"{key} leaked a temp name"
        assert str(key).strip().lower() != "original file"

    # The real name is kept, just not in the vendor metadata bag.
    assert target_spectrum.filename.endswith(".spc")
    assert "tmp" not in target_spectrum.filename


def test_real_vendor_metadata_still_comes_through(neon_spectrum):
    """Stripping path-derived keys must not throw out the actual header."""
    assert len(neon_spectrum.source_metadata) > 10
    assert "laser_wavelength" in neon_spectrum.source_metadata
