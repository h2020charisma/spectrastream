from streamlit.testing.v1 import AppTest

at = AppTest.from_file("src/spectrastream/app.py", default_timeout=10)
at.run()
assert not at.exception


def test_title():
    assert at.title is not None
