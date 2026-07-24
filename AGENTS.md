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

Three layers, and the boundary between them is load-bearing:

- `src/spectrastream/` is the framework-independent core and **must not import streamlit**. It holds ingestion, instrument profiles, NeXus export, CWA §8 export, and the pluggable calibration API. Keeping it clean is what makes it testable and what will let the UI be replaced later.
- `src/ui/` is Streamlit-only: one typed `AppState`, Altair charts, the browser-storage bridge, and the recipe-driven form renderer.
- `src/streamlit_app.py` declares navigation via `st.navigation`; `src/app_pages/*.py` are page bodies kept as direct scripts, with logic in the modules above.

Raman algorithms come from [`ramanchada2`](https://github.com/h2020charisma/ramanchada2); NeXus output from [`pyambit`](https://github.com/ideaconsult/pyambit). This repository orchestrates them.

### Instruments have optical paths

`InstrumentProfile` is the box (make, model, serial); `OpticalPath` is one configuration of it (wavelength, grating, slit, pinhole, collection optics) and an instrument holds several. Wavelength and calibrations live on the **path**, not the instrument — a correction derived at 532 nm says nothing about a 785 nm path. `ProfileLibrary.from_json` migrates the older flat schema by lifting everything path-shaped into a single `OP1`.

### Calibration is data, not code

A `RecipeSpec` (YAML in `src/spectrastream/calibration/recipes/`) declares which reference spectra a protocol needs and which steps run over them. Engines implement a deliberately narrow interface — spectra in, corrected spectrum out, plus a JSON `to_dict` — so nothing about *how* a correction was derived reaches the app or the exported file. Add a protocol by adding a file; `$SPECTRASTREAM_RECIPES` adds directories.

## Gotchas

- Calling the public `CalibrationModel.derive_model_curve` / `derive_model_zero` raises `DeprecationWarning`, and pytest runs with `filterwarnings = ["error"]`. The engine calls the private `_derive_*` on purpose.
- `LazerZeroingComponent.model_units` is `"nm"` but its `process()` returns cm-1 — `model_units` describes the stored model, not the output axis. Use `Rc2Fitted.output_units`.
- Silicon must be cropped to a window around the band before peak fitting (`window_cm1`). Without it, noise yields dozens of candidates and each costs a Pearson4 fit; the run effectively hangs.
- `export_cwa_x` labels both CSV columns `_cm1` while sampling the model directly, so a calibration that outputs nm would publish mislabelled data. `x_calibration_model()` withholds the download instead.
- `pyambit.configure_papp` iterates `meta.keys()` unconditionally despite defaulting the argument to `None`; always pass a dict.
- The browser-storage component registers into the *runtime's* registry at import time, but the module is cached in `sys.modules` — a second runtime in one process (every AppTest after the first) finds nothing registered, so `_mount` re-registers on demand.
- Never write to browser storage before the bridge has answered: "no reply yet" is not "no profiles", and confusing them destroys the user's data.
- `.streamlit/config.toml` must remain at the repository root so root-level local runs and the image use the same navigation and theme settings.
- The image runs as UID/GID 10001 with root-owned application files and expects only `/tmp` to be writable.
- Same-repository PRs publish `pr-N` and `pr-N-sha-<commit>` images; fork and Dependabot PRs are build-only.
- Successful `main` builds publish `latest`, `stable`, and `sha-<commit>`. External automation may deploy `latest` automatically.
- Production images include SBOM/provenance and a keyless signature. Do not add reusable caches to the production image job.
