"""Instruments, their optical paths, and the calibrations derived for them.

The shape here follows how a Raman lab actually works, and it is two levels
deep for a reason. An *instrument* is the box: make, model, serial. An *optical
path* (OP) is one configuration of it -- excitation wavelength, grating,
objective, slit -- and a single instrument commonly has several. A calibration
belongs to an optical path, never to the instrument: change the grating and the
correction changes; change the wavelength and even the reference lines are
different, so a 532 nm calibration applied to a 785 nm path is not merely
inaccurate, it is meaningless.

This mirrors the CHARISMA/VAMAS reporting template, where each Front sheet row
is one OP identified by "Identifier (ID)", and each Files sheet row names the
OP it was measured on.

Only names are required. The NeXus floor must work for someone who knows little
about their rig, so nothing here is mandatory beyond enough to tell one path
from another. Calibrations are stored as the engine's own JSON, never as a
pickle -- profiles are meant to leave this machine.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol, runtime_checkable

from pydantic import BaseModel, Field

SCHEMA_VERSION = 2


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class SourceFile(BaseModel):
    """Provenance of one reference spectrum a calibration was derived from."""

    slot: str
    filename: str
    sha256: str


class CalibrationRecord(BaseModel):
    """One derived calibration, stored inside an optical path."""

    id: str = Field(default_factory=_new_id)
    label: str
    recipe_id: str
    engine_id: str
    created: datetime = Field(default_factory=_now)
    laser_wl_nm: float | None = None
    sources: list[SourceFile] = Field(default_factory=list)
    model: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    notes: str = ""

    @property
    def applied_step_labels(self) -> list[str]:
        return [s.get("label", "") for s in self.steps if s.get("status") == "applied"]

    @property
    def skipped_step_labels(self) -> list[str]:
        return [s.get("label", "") for s in self.steps if s.get("status") != "applied"]


class OpticalPath(BaseModel):
    """One configuration of an instrument, and its calibrations.

    Fields follow the VAMAS template Front sheet -- each row there is an OP.
    """

    id: str = Field(default_factory=_new_id)
    #: VAMAS "Identifier (ID)", e.g. "OP1". What a measurement cites.
    op_id: str = "OP1"
    #: VAMAS "Wavelength, nm". Belongs to the path, not the instrument: a rig
    #: with 532 and 785 lines has two optical paths, not one.
    laser_wl_nm: float | None = None
    #: VAMAS "Grating, l/mm".
    grating: str | None = None
    #: VAMAS "Slit Size, um".
    slit: str | None = None
    #: VAMAS "Pin hole size".
    pin_hole_size: str | None = None
    #: VAMAS "Collection optics".
    collection_optics: str | None = None
    #: VAMAS "Collection Fibre Diameter, mm".
    collection_fibre_diameter_mm: str | None = None
    #: VAMAS "Max laser power, mW".
    max_laser_power_mw: float | None = None
    #: VAMAS "Spectral range / scanning mode".
    spectral_range: str | None = None
    #: VAMAS "Notes".
    notes: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)
    calibrations: list[CalibrationRecord] = Field(default_factory=list)
    active_calibration_id: str | None = None
    created: datetime = Field(default_factory=_now)
    updated: datetime = Field(default_factory=_now)

    @property
    def active_calibration(self) -> CalibrationRecord | None:
        if self.active_calibration_id is None:
            return None
        return self.calibration(self.active_calibration_id)

    def calibration(self, calibration_id: str) -> CalibrationRecord | None:
        for record in self.calibrations:
            if record.id == calibration_id:
                return record
        return None

    def add_calibration(
        self, record: CalibrationRecord, make_active: bool = True
    ) -> None:
        self.calibrations = [c for c in self.calibrations if c.id != record.id]
        self.calibrations.append(record)
        if make_active:
            self.active_calibration_id = record.id
        self.updated = _now()

    def remove_calibration(self, calibration_id: str) -> None:
        self.calibrations = [c for c in self.calibrations if c.id != calibration_id]
        if self.active_calibration_id == calibration_id:
            self.active_calibration_id = (
                self.calibrations[-1].id if self.calibrations else None
            )
        self.updated = _now()

    def metadata(self) -> dict[str, str]:
        """Flat, non-empty optical-path metadata for the NeXus writer.

        Keys are spelled the way pyambit's ``configure_papp`` recognises them
        (``grating``, ``pin hole size``) so they land on real NeXus paths
        instead of the generic ``/parameters/*`` bucket. Empty fields are
        dropped rather than written as blanks -- an absent value is more honest
        than an empty string.
        """
        named = {
            "op_id": self.op_id,
            "grating": self.grating,
            "slit": self.slit,
            "pin hole size": self.pin_hole_size,
            "collection_optics": self.collection_optics,
            "collection_fibre_diameter_mm": self.collection_fibre_diameter_mm,
            "max_laser_power_mw": self.max_laser_power_mw,
            "spectral_range": self.spectral_range,
            "optical_path_notes": self.notes,
        }
        meta = {k: str(v) for k, v in named.items() if v not in (None, "")}
        meta.update({k: str(v) for k, v in self.extra.items() if v not in (None, "")})
        return meta

    def describe(self) -> str:
        bits = []
        if self.laser_wl_nm:
            bits.append(f"{self.laser_wl_nm:g} nm")
        if self.grating:
            bits.append(f"{self.grating} l/mm")
        if self.slit:
            bits.append(f"slit {self.slit}")
        if self.calibrations:
            bits.append(f"{len(self.calibrations)} calibration(s)")
        return " · ".join(bits) if bits else "no details recorded"


class InstrumentProfile(BaseModel):
    """A Raman instrument and its optical paths."""

    id: str = Field(default_factory=_new_id)
    name: str
    #: VAMAS "Make" / "Model".
    vendor: str | None = None
    model: str | None = None
    serial: str | None = None
    device_type: str | None = None
    #: Anything the forms do not cover; lands under NeXus /parameters/*.
    extra: dict[str, str] = Field(default_factory=dict)
    optical_paths: list[OpticalPath] = Field(default_factory=list)
    created: datetime = Field(default_factory=_now)
    updated: datetime = Field(default_factory=_now)

    def optical_path(self, path_id: str | None) -> OpticalPath | None:
        if path_id is None:
            return None
        for path in self.optical_paths:
            if path.id == path_id:
                return path
        return None

    def add_optical_path(self, path: OpticalPath) -> None:
        self.optical_paths = [p for p in self.optical_paths if p.id != path.id]
        self.optical_paths.append(path)
        self.updated = _now()

    def remove_optical_path(self, path_id: str) -> None:
        self.optical_paths = [p for p in self.optical_paths if p.id != path_id]
        self.updated = _now()

    def next_op_id(self) -> str:
        """A default identifier that does not collide with an existing one."""
        taken = {p.op_id for p in self.optical_paths}
        index = len(self.optical_paths) + 1
        while f"OP{index}" in taken:
            index += 1
        return f"OP{index}"

    def instrument_metadata(self) -> dict[str, str]:
        """Instrument-level metadata only; the optical path adds its own."""
        named = {
            "serial_number": self.serial,
            "device_type": self.device_type,
        }
        meta = {k: str(v) for k, v in named.items() if v not in (None, "")}
        meta.update({k: str(v) for k, v in self.extra.items() if v not in (None, "")})
        return meta

    def describe(self) -> str:
        """One-line summary for profile cards."""
        bits = [b for b in (self.vendor, self.model) if b]
        wavelengths = sorted(
            {p.laser_wl_nm for p in self.optical_paths if p.laser_wl_nm}
        )
        if wavelengths:
            bits.append(", ".join(f"{wl:g} nm" for wl in wavelengths))
        if self.optical_paths:
            bits.append(f"{len(self.optical_paths)} optical path(s)")
        return " · ".join(bits) if bits else "no details recorded"


class ProfileLibrary(BaseModel):
    """The whole set of profiles -- what gets serialised to local storage."""

    schema_version: int = SCHEMA_VERSION
    profiles: list[InstrumentProfile] = Field(default_factory=list)

    def get(self, profile_id: str) -> InstrumentProfile | None:
        for profile in self.profiles:
            if profile.id == profile_id:
                return profile
        return None

    def upsert(self, profile: InstrumentProfile) -> None:
        profile.updated = _now()
        for index, existing in enumerate(self.profiles):
            if existing.id == profile.id:
                self.profiles[index] = profile
                return
        self.profiles.append(profile)

    def remove(self, profile_id: str) -> None:
        self.profiles = [p for p in self.profiles if p.id != profile_id]

    def find_optical_path(
        self, path_id: str | None
    ) -> tuple[InstrumentProfile, OpticalPath] | tuple[None, None]:
        if path_id is not None:
            for profile in self.profiles:
                path = profile.optical_path(path_id)
                if path is not None:
                    return profile, path
        return None, None

    def to_json(self, indent: int | None = None) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, text: str) -> "ProfileLibrary":
        data = json.loads(text)
        version = data.get("schema_version", SCHEMA_VERSION)
        if version > SCHEMA_VERSION:
            raise ValueError(
                f"profile library was written by a newer version "
                f"(schema {version} > {SCHEMA_VERSION})"
            )
        if version < 2:
            data = _migrate_v1(data)
        return cls.model_validate(data)


def _migrate_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Lift schema 1 profiles into an optical path.

    Version 1 hung the wavelength, optics and calibrations directly off the
    instrument, which cannot express a rig with both a 532 and a 785 line.
    Everything path-shaped moves into a single OP so nothing is lost.
    """
    migrated = dict(data)
    profiles = []
    for old in data.get("profiles", []):
        path = {
            "op_id": "OP1",
            "laser_wl_nm": old.get("laser_wl_nm"),
            "grating": old.get("grating"),
            "slit": old.get("slit"),
            "pin_hole_size": old.get("pin_hole_size"),
            "collection_optics": old.get("numerical_aperture"),
            "collection_fibre_diameter_mm": old.get("collection_fibre_diameter_mm"),
            "max_laser_power_mw": old.get("max_laser_power_mw"),
            "spectral_range": old.get("spectral_range"),
            "notes": old.get("notes"),
            "calibrations": old.get("calibrations", []),
            "active_calibration_id": old.get("active_calibration_id"),
        }
        profile = {
            "id": old.get("id", _new_id()),
            "name": old.get("name", "Unnamed instrument"),
            "vendor": old.get("vendor"),
            "model": old.get("model"),
            "serial": old.get("serial"),
            "device_type": old.get("device_type"),
            "extra": old.get("extra", {}),
            "optical_paths": [path],
        }
        # Omit absent timestamps rather than passing None, so the model's
        # defaults apply instead of failing validation.
        for key in ("created", "updated"):
            if old.get(key):
                profile[key] = old[key]
        profiles.append(profile)
    migrated["profiles"] = profiles
    migrated["schema_version"] = SCHEMA_VERSION
    return migrated


@runtime_checkable
class ProfileStore(Protocol):
    """Where profiles live. Browser-local today, server-synced later."""

    def load(self) -> ProfileLibrary: ...

    def save(self, library: ProfileLibrary) -> None: ...

    @property
    def is_persistent(self) -> bool:
        """False when profiles will not survive a page reload."""
        ...


def export_bytes(library: ProfileLibrary) -> bytes:
    return library.to_json(indent=2).encode("utf-8")


def import_bytes(data: bytes) -> ProfileLibrary:
    return ProfileLibrary.from_json(data.decode("utf-8"))


def merge(
    into: ProfileLibrary, incoming: Iterable[InstrumentProfile]
) -> tuple[int, int]:
    """Merge imported profiles, returning (added, replaced) counts."""
    added = replaced = 0
    for profile in incoming:
        if into.get(profile.id) is None:
            added += 1
        else:
            replaced += 1
        into.upsert(profile)
    return added, replaced
