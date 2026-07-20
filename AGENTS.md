# Repository Guide

## Commands

- This is a non-package Streamlit application (`tool.uv.package = false`) supporting Python 3.10-3.12; use the root Python 3.12 pin.
- Install with `uv sync --locked`. Do not run upgrade-oriented uv commands unless dependency changes are intended.
- Run locally from the repository root with `uv run streamlit run src/streamlit_app.py`.
- Run tests with `uv run pytest`; coverage with `uv run pytest --cov`; one test with `uv run pytest tests/basic_test.py::test_app`.
- The four current tests are render smoke tests only. Pytest treats warnings as errors, and CI runs Python 3.10-3.12; add interaction or utility regressions for behavior changes.
- Run hooks on staged files with `uv run pre-commit run`, explicit files with `uv run pre-commit run --files <paths>`, or the complete tree with `uv run pre-commit run --all-files`; hooks can rewrite files.
- Ruff handles Python linting, import sorting, and formatting. The complete tree passes every hook, and CI enforces the all-files baseline.
- Build the deployment image with `docker build -t spectrastream:local .`; it serves `/stream` on port 8501.

## Application Shape

- `src/streamlit_app.py` is the entrypoint and initializes shared session-state caches.
- `src/pages/load_instrument_settings.py` stores instrument metadata required by later pages.
- `src/pages/load_or_create_calibration.py` is the large, top-level X/Y calibration workflow.
- `src/pages/apply_calibration.py` preprocesses target spectra and applies saved calibrations.
- `src/modules/models.py` defines UI state; `src/modules/util.py` owns upload, session, plotting, and calibration helpers.
- Raman algorithms come from [`ramanchada2`](https://github.com/h2020charisma/ramanchada2); this repository mainly orchestrates them through Streamlit state.

## Gotchas

- Streamlit pages execute at import time and assume the main page initialized session state. Tests that open a page directly must seed the cache as `tests/basic_test.py` does.
- The expected UI order is main page, instrument settings, create/load calibration, then apply calibration.
- `src/experiments/tests01.py` is not a pytest test.
- Uploaded calibration files are passed to `pickle.load`; treat them as trusted-only and do not weaken this warning in user or contributor docs.
- `.streamlit/config.toml` must remain at the repository root so root-level local runs and the image use the same navigation setting.
- The image runs as UID/GID 10001 with root-owned application files and expects only `/tmp` to be writable.
- Same-repository PRs publish `pr-N` and `pr-N-sha-<commit>` images; fork and Dependabot PRs are build-only.
- Successful `main` builds publish `latest`, `stable`, and `sha-<commit>`. External automation may deploy `latest` automatically.
- Production images include SBOM/provenance and a keyless signature. Do not add reusable caches to the production image job.
