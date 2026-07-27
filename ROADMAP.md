# Roadmap

*Living document. Reflects current thinking, not a commitment — dates and scope will move.*

## Near term: alpha release

Goal: extend the working `x-calib-nopeak-find` demo so an attendee can upload a spectrum in (almost) any format and get back a **NeXus file**, carrying a calibrated wavenumber axis when possible.

- **Floor — always delivered:** any supported format → NeXus. FAIR value even with no calibration; the demo never fails to return something useful.
- **Bonus:** optional x-(and y-)calibration improves the axis before the NeXus is written, using the existing open [ramanchada2](https://github.com/h2020charisma/ramanchada2) calibration stack (Neon/Si x-cal, NIST/LED SRM y-cal).
- **FAIR capture:** consent + license (default CC-BY) + attribution at upload; contributed spectra + instrument metadata flow into `spectra.adma.ai` as open records — each upload also seeds a growing instrument/spectra corpus.
- **Output is a NeXus file carrying a calibrated axis — not the calibration method.** The calibration engine behind the axis is an implementation detail and stays swappable.

Milestones:

- **Milestone 0** — ~~Upgrade to the current ramanchada2 API; get the existing app green end-to-end (format load → x-cal → y-cal → apply → download).~~ **Done** — `ramanchada2` is pinned to `>=1.3.1,<2.0.0`.
  - **TODO:** upgrade to ramanchada2 1.4.0 (releasing 2026-07-27).
- **Milestone 1** — ~~NeXus export beside the existing CSV download; any format → NeXus with instrument metadata, calibration optional (the FAIR floor).~~ **Done** — the **Convert** page writes any ramanchada2-supported format to NeXus, with or without instrument metadata, with or without calibration.
- **Milestone 2** — ~~Calibrated NeXus: embed the calibrated spectrum + axis using the existing classic calibration.~~ **Done** — recipe-driven calibration engines (`rc2.ne_si`, `rc2.si_only`, `rc2.y_srm`) wrap the open ramanchada2 stack; instrument/optical-path profiles carry calibrations for reuse; the **Calibrate** page derives and applies them, and the calibrated axis plus its provenance (recipe, engine, steps) rides in the NeXus metadata. A **Verify** page, not originally scoped, adds an in-app check against CWA 18133 reference values and resolution curves.
- **Milestone 3** — FAIR capture + organised storage: consent/license/attribution flow; persist uploads (original + NeXus + manifest) outside the source tree; push records to `spectra.adma.ai`. **Not started** — uploaded spectra are still never persisted (in-memory for the session only); this is the next milestone.
- **Milestone 4** — ~~Harden~~ the container image — **done**: CI builds and signs images to `ghcr.io` on every merge to `main`, plus PR preview builds. Deploying to `spectra.adma.ai/stream/` and adding an async upload path to de-risk unreliable network conditions during live demos are still open.
- **Milestone 5** — Buffer: polish + dry-run on real spectra before release.

## Beyond the alpha

- **Move off Streamlit.** The current app is a real, working demo, but a rewrite (likely FastAPI + React) around a framework-independent `ingest → optional calibrate → write_nexus` core is the preferred direction once the alpha ships. This also makes the UI swappable independent of the calibration engine underneath.
- **Pluggable calibration engines.** Live today: the calibration step already runs behind a narrow interface (recipe in, calibrated axis out) implemented in `spectrastream/calibration/`, so alternative x-calibration implementations can be evaluated and swapped in without touching ingestion, NeXus export, or FAIR capture.
- **Growing the FAIR corpus.** As the upload/consent flow matures, the accumulating `spectra.adma.ai` corpus becomes useful beyond the demo itself (e.g. as data for future calibration research), but that is downstream of getting ingestion + storage right first.

## Out of scope for now

- No reworking of the existing x/y calibration internals under the alpha timeline — only the delivery format changes.
