# SpectraStream

SpectraStream is a [Streamlit](https://streamlit.io/) application that turns a Raman spectrum in almost any vendor format into a **NeXus** file, optionally with a calibrated wavenumber axis. It builds on the [`ramanchada2`](https://github.com/h2020charisma/ramanchada2) processing library and [`pyambit`](https://github.com/ideaconsult/pyambit) for NeXus output.

The project is currently alpha software; results are indicative.

## Workflow

1. **Convert** — upload a spectrum and download NeXus. Beyond the file you need only its x axis units and the laser wavelength; everything else is optional.
2. **Instruments** *(optional)* — record an instrument and its optical paths, so their metadata enriches every export and calibrations have somewhere to live.
3. **Calibrate** *(optional)* — derive a calibration from reference spectra and attach it to an optical path for reuse.

Metadata fields follow the CHARISMA/VAMAS Raman reporting template, so a spectrum described here carries the same facts as one described for a round-robin. Where a file's own header states something — many formats record the laser wavelength and integration time — those fields are prefilled and left editable.

### Instruments and optical paths

An **instrument** is the box: make, model, serial. An **optical path** (OP) is one configuration of it — excitation wavelength, grating, objective, slit — and one instrument commonly has several. This mirrors the VAMAS template, where each Front sheet row is an OP and each measurement names the OP it used.

Calibrations belong to an optical path, never to the instrument. Change the grating and the correction changes; change the wavelength and even the reference lines are different, so a 532 nm calibration applied to a 785 nm path is not merely inaccurate but meaningless.

### Calibration protocols

Calibration is pluggable. A *recipe* declares which reference spectra a protocol needs and which steps run over them, as YAML rather than code — see [`src/spectrastream/calibration/recipes/`](src/spectrastream/calibration/recipes/). The UI is generated from the recipe, so supporting a protocol that needs entirely different reference materials means adding a file, not changing a page. Point `$SPECTRASTREAM_RECIPES` at a directory to add your own.

Shipped protocols use the open ramanchada2 engine:

| Recipe | Needs | Produces |
| --- | --- | --- |
| `rc2.ne_si` | Neon lamp (silicon and SRM optional) | Wavenumber axis, laser zero, relative intensity |
| `rc2.si_only` | Silicon wafer | Laser zero only |
| `rc2.y_srm` | Standard reference material | Relative intensity only |

Steps whose optional inputs are missing are skipped rather than failing the run: without a silicon spectrum you still get the neon curve.

### Where your data lives

Instrument profiles are stored **in your browser**, not on the server, and calibrations are stored as JSON inside them. Clearing site data removes them; export from the Instruments page to keep a copy or move to another machine. Uploaded spectra are never persisted.

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

> **Note** — `ramanchada2` and `pyambit` are pinned to unreleased branches that
> carry the portable JSON calibration format and the NeXus writer. For local
> development they resolve to sibling checkouts; see the comment above
> `[tool.uv.sources]` in `pyproject.toml` for the git URLs to use in CI and
> container builds, which cannot reach paths outside the build context.

## Run With Docker

```sh
docker build -t spectrastream:local .
docker run --rm -p 8501:8501 spectrastream:local
```

Open <http://localhost:8501/stream>. The image includes a health check at `/stream/_stcore/health` and runs as an unprivileged user.

Published images are available from `ghcr.io/h2020charisma/spectrastream`. The `latest` tag tracks successful builds from `main`; commit-addressed `sha-<commit>` tags support rollback. Use the image digest when deployment requires an immutable reference.

## Security

Calibrations are serialized as JSON, so importing a profile cannot execute code. Profile exports are plain `.json` and can be inspected before import.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, pull-request images, and container guidance.

## License

SpectraStream is available under the [MIT License](LICENSE).

## Acknowledgements

🇪🇺 This project received funding from the European Union's Horizon 2020 research and innovation programme under [grant agreement No. 952921](https://cordis.europa.eu/project/id/952921).
