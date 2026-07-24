"""Per-measurement metadata, aligned with the VAMAS reporting template.

The instrument profile describes the rig; this describes the one measurement
being converted. Fields mirror the *Files sheet* of the CHARISMA/VAMAS Raman
reporting template so that a spectrum described here and the same spectrum
described in a round-robin template carry the same facts.

Everything is optional except the axis units, because units are not metadata
about the data -- they are what makes the numbers mean anything.
"""

from datetime import date, datetime, time
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field

#: What the x axis of the uploaded file actually holds.
AxisUnits = Literal["cm-1", "nm", "pixel"]

UNIT_LABELS: dict[str, str] = {
    "cm-1": "Raman shift (cm⁻¹)",
    "nm": "Absolute wavelength (nm)",
    "pixel": "Detector pixel index",
}

BACKGROUND_CHOICES = [
    "Background_Not_Subtracted",
    "Background_Subtracted",
    "Background_Only",
]


class Acquisition(BaseModel):
    """How one spectrum was measured."""

    #: VAMAS "Sample".
    sample: str | None = None
    #: Units of the x axis as uploaded. Not optional -- see module docstring.
    units: AxisUnits = "cm-1"
    #: VAMAS "OP ID": which *optical path* was used. One instrument commonly
    #: has several -- different grating, objective or slit -- and they
    #: calibrate differently, so the measurement records which one it was.
    op_id: str | None = None
    #: VAMAS "Measurement #".
    measurement: int | None = None
    #: VAMAS "Laser power, %".
    laser_power_percent: float | None = None
    #: VAMAS "Power meter, mW".
    power_meter_mw: float | None = None
    #: VAMAS "Integration t, ms".
    integration_time_ms: float | None = None
    #: VAMAS "Temp, C".
    temperature_c: float | None = None
    #: VAMAS "Date yyyy/mm/dd" and "Time hh:mm".
    measured_on: date | None = None
    measured_at: time | None = None
    #: VAMAS "Background".
    background: str | None = None
    #: VAMAS "Overexposed".
    overexposed: bool | None = None
    provider: str | None = None
    investigation: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)

    def as_metadata(self) -> dict[str, Any]:
        """Flat metadata for the NeXus writer, blanks dropped.

        ``integration time`` is spelled the way pyambit's ``configure_papp``
        expects so it reaches ``instrument/detector/count_time`` rather than
        the generic parameters bucket.
        """
        named: dict[str, Any] = {
            "sample": self.sample,
            "op_id": self.op_id,
            "measurement": self.measurement,
            "laser_power_percent": self.laser_power_percent,
            "power_meter_mw": self.power_meter_mw,
            "integration time": self.integration_time_ms,
            "temperature_c": self.temperature_c,
            "background": self.background,
            "x_axis_units": self.units,
        }
        if self.overexposed is not None:
            named["overexposed"] = "YES" if self.overexposed else "NO"
        if self.measured_on is not None:
            named["measurement_date"] = self.measured_on.isoformat()
        if self.measured_at is not None:
            named["measurement_time"] = self.measured_at.isoformat(timespec="minutes")

        meta = {k: v for k, v in named.items() if v not in (None, "")}
        meta.update({k: v for k, v in self.extra.items() if v not in (None, "")})
        return meta


#: Header keys seen in the wild, mapped to the field they describe. Vendors are
#: inconsistent and some are misspelled at source ("intigration") -- matching
#: what files actually contain beats matching what they should contain.
_GUESSES: dict[str, tuple[str, ...]] = {
    "laser_wl_nm": (
        "laser_wavelength",
        "laser wavelength",
        "excitation_wavelength",
        "excitation wavelength",
        "laser",
        "excitation",
    ),
    "integration_time_ms": (
        "intigration times(ms)",
        "integration times(ms)",
        "integration time",
        "integration_time",
        "integ_time",
        "acquisition_time",
        "exposure_time",
    ),
    "temperature_c": ("temperature", "temp", "temperature_c", "detector_temperature"),
    "laser_power_percent": ("laser_powerlevel", "laser power level", "laser_power"),
    "power_meter_mw": ("power_mw", "laser power, mw", "power meter, mw"),
    "sample": ("sample", "sample_name", "title"),
}


def _lookup(source: Mapping[str, Any], names: tuple[str, ...]) -> Any | None:
    lowered = {str(k).strip().lower(): v for k, v in source.items()}
    for name in names:
        if name in lowered:
            value = lowered[name]
            if value not in (None, "") and not (
                isinstance(value, str) and not value.strip()
            ):
                return value
    return None


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def guess_from_metadata(
    source_metadata: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], float | None]:
    """Read what the file already told us.

    Returns ``(acquisition_fields, laser_wl_nm)``. These are *suggestions*: the
    caller shows them in editable fields rather than committing them, because a
    header can be stale or plain wrong and the contributor is the one who knows.
    """
    source = dict(source_metadata or {})
    fields: dict[str, Any] = {}
    if not source:
        return fields, None

    laser_wl = _as_float(_lookup(source, _GUESSES["laser_wl_nm"]))

    for field_name in (
        "integration_time_ms",
        "temperature_c",
        "laser_power_percent",
        "power_meter_mw",
    ):
        value = _as_float(_lookup(source, _GUESSES[field_name]))
        if value is not None:
            fields[field_name] = value

    sample = _lookup(source, _GUESSES["sample"])
    if isinstance(sample, str) and sample.strip():
        fields["sample"] = sample.strip()

    measured = _lookup(source, ("date", "datetime", "acquisition_date"))
    if isinstance(measured, datetime):
        fields["measured_on"] = measured.date()
        fields["measured_at"] = measured.time().replace(second=0, microsecond=0)
    elif isinstance(measured, date):
        fields["measured_on"] = measured

    return fields, laser_wl
