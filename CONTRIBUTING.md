# Contributing

SpectraStream uses a pull-request workflow against `main`. Keep changes focused, add tests for changed behavior, and avoid mixing broad formatting or dependency updates with functional work.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker or a compatible OCI builder when changing the container

The project supports Python 3.10 through 3.12 and uses Python 3.12 by default. uv can install the pinned interpreter automatically.

## Setup

```sh
git clone git@github.com:h2020charisma/spectrastream.git
cd spectrastream
uv sync --locked
uv run pre-commit install
```

Run commands through `uv run`; activating `.venv` is unnecessary.

## Run The Application

From the repository root:

```sh
uv run streamlit run src/streamlit_app.py
```

Open <http://localhost:8501>. In a fresh session, visit the pages in this order:

1. Load the main page so shared session state is initialized.
2. Save instrument settings, including the laser wavelength.
3. Create or load a calibration.
4. Apply the calibration to target spectra.

## Checks

Run the test suite:

```sh
uv run pytest
```

Run coverage or a focused test:

```sh
uv run pytest --cov
uv run pytest tests/basic_test.py::test_app
```

Run pre-commit against staged files, named files, or the complete tree:

```sh
uv run pre-commit run
uv run pre-commit run --files path/to/changed.py
uv run pre-commit run --all-files
```

Ruff applies safe lint and import fixes, then formats Python files. Review and stage hook changes before rerunning the hooks.

The complete source tree passes every hook. CI runs pre-commit with `--all-files` and runs the complete test suite.

Pytest treats warnings as errors. The current tests are Streamlit render smoke tests, so changes to widgets, session state, uploads, calibration processing, or downloads need interaction or utility-level regression tests rather than another render-only assertion.

## Dependencies

Use uv so `pyproject.toml` and `uv.lock` remain synchronized:

```sh
uv add package-name
uv add --dev development-tool
```

Do not edit `uv.lock` manually. Keep dependency-only changes separate from application changes, and explain material direct or transitive version changes in the pull request. Run tests on Python 3.10, 3.11, and 3.12 when changing runtime dependencies.

```sh
uv run --isolated -p 3.10 pytest
uv run --isolated -p 3.11 pytest
uv run --isolated -p 3.12 pytest
```

## Container

Build and run the image locally:

```sh
docker build -t spectrastream:local .
docker run --rm -p 8501:8501 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev \
  --cap-drop ALL \
  --security-opt no-new-privileges=true \
  spectrastream:local
```

Open <http://localhost:8501/stream>. The image health endpoint is `/stream/_stcore/health`.

The runtime process is UID/GID 10001, application files are root-owned, and uploaded spectra require writable `/tmp`. Preserve these properties when changing the Dockerfile.

## Images And Deployment

CI builds every pull request. Same-repository pull requests publish these GHCR tags for testing:

```text
pr-<number>
pr-<number>-sha-<commit>
```

Fork and Dependabot pull requests are build-only because their tokens cannot safely publish packages.

Successful `main` builds publish `latest`, `stable`, and `sha-<commit>`. Production images include an SBOM, provenance attestations, and a keyless signature. External deployment automation may track `latest`, so merging to `main` can update running deployments automatically.

## Data And Security

- Do not commit user spectra, generated calibrations, or other data without explicit approval and documented provenance.
- Calibration uploads use Python pickle deserialization. Only load files from trusted sources; malicious pickle data can execute arbitrary code.
- Keep temporary upload processing under `/tmp` so the production image can retain a read-only root filesystem.
- Do not pass credentials through Docker build arguments or add write permissions to untrusted pull-request jobs.

## Pull Requests

Before requesting review:

- Rebase or otherwise update the branch against current `main`.
- Run the relevant tests and pre-commit hooks.
- Build the image when changing dependencies, Streamlit configuration, or container behavior.
- Update relevant documentation when behavior, setup, security, or deployment changes.
- Describe user-visible behavior, dependency changes, security implications, and remaining limitations.
- Keep generated caches, virtual environments, local coverage files, and temporary calibration artifacts out of commits.
