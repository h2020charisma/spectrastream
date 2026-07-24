"""Declarative description of a calibration protocol.

A *recipe* says which reference spectra a calibration needs and which steps run
over them, in order. It is data (YAML), not code, so supporting a new protocol
is a new file rather than a new page: the UI renders one uploader per
:class:`SpectrumSlot` and one status line per :class:`StepSpec`.

This matters because engines disagree about their inputs. The ramanchada2 path
wants Neon and Silicon; CWA 18133 fits peaks on a calibrant and splines them;
the optimal-transport engine works from anchor materials (PST/CAL/APAP) and
never sees a Neon lamp. Only the recipe knows.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SpectrumUnits = Literal["cm-1", "nm", "pixel"]

#: What a step contributes to the final calibration. The UI groups steps by
#: this, and engines use it to decide ordering (intensity always applies last,
#: on an already x-corrected axis).
StepProduct = Literal["x_axis", "x_zero", "y_response"]


class SpectrumSlot(BaseModel):
    """One reference spectrum the recipe may consume."""

    id: str
    label: str
    material: str | None = None
    required: bool = True
    units: SpectrumUnits = "cm-1"
    help: str | None = None

    model_config = {"extra": "forbid"}


class StepSpec(BaseModel):
    """One action in the recipe, consuming zero or more slots."""

    id: str
    label: str
    action: str
    inputs: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    optional: bool = False
    produces: StepProduct

    model_config = {"extra": "forbid"}


class RecipeSpec(BaseModel):
    """A named, versioned calibration protocol for one engine."""

    id: str
    label: str
    engine: str
    version: int = 1
    description: str = ""
    laser_wavelengths: list[int] | None = None
    slots: list[SpectrumSlot] = Field(default_factory=list)
    steps: list[StepSpec] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @field_validator("slots")
    @classmethod
    def _unique_slot_ids(cls, slots: list[SpectrumSlot]) -> list[SpectrumSlot]:
        seen = {slot.id for slot in slots}
        if len(seen) != len(slots):
            raise ValueError("duplicate slot id in recipe")
        return slots

    @field_validator("steps")
    @classmethod
    def _unique_step_ids(cls, steps: list[StepSpec]) -> list[StepSpec]:
        seen = {step.id for step in steps}
        if len(seen) != len(steps):
            raise ValueError("duplicate step id in recipe")
        return steps

    @model_validator(mode="after")
    def _steps_reference_known_slots(self) -> "RecipeSpec":
        known = {slot.id for slot in self.slots}
        for step in self.steps:
            unknown = set(step.inputs) - known
            if unknown:
                raise ValueError(
                    f"step {step.id!r} consumes undeclared slot(s) {sorted(unknown)!r}"
                )
        return self

    @model_validator(mode="after")
    def _required_slots_are_reachable(self) -> "RecipeSpec":
        """A required slot nobody consumes would ask the user for a dead file."""
        consumed = {slot_id for step in self.steps for slot_id in step.inputs}
        orphans = [s.id for s in self.slots if s.required and s.id not in consumed]
        if orphans:
            raise ValueError(f"required slot(s) {orphans!r} are not used by any step")
        return self

    def slot(self, slot_id: str) -> SpectrumSlot:
        for slot in self.slots:
            if slot.id == slot_id:
                return slot
        raise KeyError(slot_id)

    def supports_wavelength(self, laser_wl_nm: float | None) -> bool:
        """Recipes with no ``laser_wavelengths`` list accept anything."""
        if self.laser_wavelengths is None:
            return True
        if laser_wl_nm is None:
            return False
        return int(round(laser_wl_nm)) in self.laser_wavelengths

    def missing_required_slots(self, available: set[str]) -> list[str]:
        return [s.id for s in self.slots if s.required and s.id not in available]

    def runnable_steps(self, available: set[str]) -> list[StepSpec]:
        """Steps whose inputs are all present.

        A step is skipped -- not failed -- when an *optional* input is absent.
        This is the "no Silicon spectrum" case: the Neon curve is still worth
        deriving on its own, so laser zeroing drops out quietly instead of
        taking the whole calibration down with it.
        """
        runnable = []
        for step in self.steps:
            if all(slot_id in available for slot_id in step.inputs):
                runnable.append(step)
        return runnable
