"""The Verify page renders for an empty session and for a fresh draft fit.

A page that raises on first paint is exactly the kind of regression a render
smoke test catches; the heavier verify/resolution maths is covered by the
unit tests, so here we only drive the page and assert it does not blow up.
"""

from streamlit.testing.v1 import AppTest

PAGE = "src/app_pages/verify.py"


def test_verify_page_with_nothing_to_check():
    at = AppTest.from_file(PAGE)
    at.run(timeout=60)
    assert not at.exception
    assert any("Nothing to verify" in i.value for i in at.info)


def test_verify_page_with_a_draft_fit(fitted_ne_si):
    at = AppTest.from_file(PAGE)
    at.run(timeout=60)  # first run creates the shared AppState, then stops
    at.session_state["spectrastream"].draft.fitted = fitted_ne_si
    at.run(timeout=120)
    assert not at.exception
    # got past the "nothing to verify" stop into the real page
    assert any(
        "What this calibration does" in s.value for s in at.subheader
    )
    assert not any("Nothing to verify" in i.value for i in at.info)
