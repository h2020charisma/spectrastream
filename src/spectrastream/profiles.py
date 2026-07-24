"""Instrument profiles: what an instrument is, and how to correct it.

A profile is the unit a user recognises -- "my 532 nm WITec in lab 2" -- and it
carries both the instrument metadata that goes into NeXus and the calibrations
derived for it. Only ``name`` is required: the NeXus floor must work for someone
who knows nothing about their rig, and demanding a serial number before letting
them convert a file would defeat the point.

Calibrations are stored as the engine's own JSON (``FittedCalibration.to_dict``),
never as a pickle -- profiles are meant to leave this machine.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol, runtime_checkable

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class SourceFile(BaseModel):
    """Provenance of one reference spectrum a calibration was derived from."""

    slot: str
    filename: str
    sha256: str


class CalibrationRecord(BaseModel):
    """One derived calibration, stored inside a profile."""

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


class InstrumentProfile(BaseModel):
    """An instrument, its optional metadata, and its calibrations."""

    id: str = Field(default_factory=_new_id)
    name: str
    laser_wl_nm: float | None = None
    vendor: str | None = None
    model: str | None = None
    serial: str | None = None
    device_type: str | None = None
    numerical_aperture: str | None = None
    grating: str | None = None
    slit: str | None = None
    #: Anything the forms do not cover; lands under NeXus /parameters/*.
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

    def instrument_metadata(self) -> dict[str, str]:
        """Flat, non-empty metadata for the NeXus writer.

        Empty fields are dropped rather than written as blanks -- an absent
        value is more honest than an empty string, and keeps minimal records
        genuinely minimal.
        """
        named = {
            "device_type": self.device_type,
            "numerical_aperture": self.numerical_aperture,
            "grating": self.grating,
            "slit": self.slit,
            "serial_number": self.serial,
        }
        meta = {k: str(v) for k, v in named.items() if v not in (None, "")}
        meta.update({k: str(v) for k, v in self.extra.items() if v not in (None, "")})
        return meta

    def describe(self) -> str:
        """One-line summary for profile cards."""
        bits = [b for b in (self.vendor, self.model) if b]
        if self.laser_wl_nm:
            bits.append(f"{self.laser_wl_nm:g} nm")
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
        return cls.model_validate(data)


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
