"""Per-measurement metadata, aligned with the VAMAS reporting template.

The instrument profile describes the rig; this describes the one measurement
being converted. Fields mirror the *Files sheet* of the CHARISMA/VAMAS Raman
reporting template so that a spectrum described here and the same spectrum
described in a round-robin template carry the same facts.

Everything is optional except the axis units, because units are not metadata
about the data -- they are what makes the numbers mean anything.
"""

from datetime import date, time
from typing import Any, Literal

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
    #: VAMAS "OP ID": which operating procedure / instrument configuration.
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
