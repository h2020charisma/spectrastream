# SpectraStream

SpectraStream is a Streamlit application for creating and applying Raman spectra calibrations in a browser. It coordinates instrument settings, reference spectra, and calibration models using the [`ramanchada2`](https://github.com/h2020charisma/ramanchada2) processing library.

The project is currently alpha software.

## Workflow

1. Enter and save instrument settings, including the laser wavelength.
2. Upload reference spectra or a previously saved calibration.
3. Build X and Y calibrations through the guided processing workflow.
4. Upload target spectra, apply the calibration, and download calibrated data.

Application state is held in the Streamlit session. Start from the main page and save instrument settings before opening the calibration pages.

## Run Locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), clone the repository, and install the locked environment:

```sh
git clone git@github.com:h2020charisma/spectrastream.git
cd spectrastream
uv sync --locked
```

Start Streamlit from the repository root:

```sh
uv run streamlit run src/streamlit_app.py
```

Open <http://localhost:8501>.

Supported Python versions are 3.10 through 3.12; Python 3.12 is the project default.

## Run With Docker

```sh
docker build -t spectrastream:local .
docker run --rm -p 8501:8501 spectrastream:local
```

Open <http://localhost:8501/stream>. The image includes a health check at `/stream/_stcore/health` and runs as an unprivileged user.

Published images are available from `ghcr.io/h2020charisma/spectrastream`. The `latest` tag tracks successful builds from `main`; commit-addressed `sha-<commit>` tags support rollback. Use the image digest when deployment requires an immutable reference.

## Security

Calibration files are currently serialized with Python pickle. Only upload calibration files from trusted sources: opening a malicious pickle can execute arbitrary code on the application server.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, pull-request images, and container guidance.

## License

SpectraStream is available under the [MIT License](LICENSE).

## Acknowledgements

This project received funding from the European Union's Horizon 2020 research and innovation programme under [grant agreement No. 952921](https://cordis.europa.eu/project/id/952921).
