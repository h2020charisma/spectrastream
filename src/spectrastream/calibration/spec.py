"""Declarative description of a calibration protocol.

A *recipe* says which reference spectra a calibration needs and which steps run
over them, in order. It is data, not code, so supporting a new protocol is new
data rather than a new page: the UI renders one uploader per
:class:`SpectrumSlot` and one status line per :class:`StepSpec`.

This matters because engines disagree about their inputs -- the ramanchada2
path wants Neon and Silicon, while another may take any material it holds
reference positions for and never see a Neon lamp. Only the recipe knows.

In-process engines ship their recipes as YAML alongside this module. Remote
ones do not: their recipes are published by the service that implements them
and fetched at registry build time, so an algorithm's material requirements
stay with whoever implements it.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from spectrastream.merge import MergeStrategy
from spectrastream.preprocess import PreprocessStep

SpectrumUnits = Literal["cm-1", "nm", "pixel"]

#: Separates a repeatable slot's id from its entry index ("anchor#0", "anchor#1", ...). A
#: repeatable slot (SpectrumSlot.repeatable) is filled once per *material*, and those
#: entries are never combined with each other -- only the acquisitions within one entry
#: are. The separator is excluded from slot ids themselves (see the validators below), so
#: it unambiguously marks an entry key wherever one appears.
ENTRY_SEP = "#"


def entry_key(slot_id: str, index: int) -> str:
    return f"{slot_id}{ENTRY_SEP}{index}"


def base_slot_id(key: str) -> str:
    """The recipe slot a draft/engine key belongs to ("anchor#1" -> "anchor")."""
    return key.split(ENTRY_SEP, 1)[0]

#: What a step contributes to the final calibration. The UI groups steps by
#: this, and engines use it to decide ordering (intensity always applies last,
#: on an already x-corrected axis).
StepProduct = Literal["x_axis", "x_zero", "y_response"]


class SpectrumSlot(BaseModel):
    """One reference input the recipe may consume.

    A slot can take several acquisitions of the same material: replicates to be
    averaged, or -- for neon especially -- a set of different exposures to be
    HDR-merged, since neon lines span far more dynamic range than one exposure
    can capture.

    That is distinct from ``repeatable``, which takes several *different*
    materials -- see below. One slot, one material, however many acquisitions of
    it; a repeatable slot is instead filled once per material.
    """

    id: str
    label: str
    material: str | None = None
    required: bool = True
    #: Default axis units. The user can correct this per upload: nothing in a
    #: bare data file says whether its x axis is cm-1, nm or pixels.
    units: SpectrumUnits = "cm-1"
    help: str | None = None
    accept_multiple: bool = False
    #: How several acquisitions become one. "auto" HDR-merges when the exposure
    #: times differ and averages when they do not.
    merge: MergeStrategy = "auto"
    #: Preprocessing offered for this material, with recipe-chosen defaults.
    preprocess: list[PreprocessStep] = Field(default_factory=list)
    #: Whether this slot may be filled once per material rather than once. Set
    #: by protocols that take an open-ended set of reference materials instead
    #: of a fixed named list, where how many are supplied is the user's choice.
    #: The UI offers "add another"; engines receive one entry per material.
    repeatable: bool = False
    #: Whether the user names the material for each upload. True when the recipe
    #: does not fix ``material`` -- a protocol accepting any material cannot know
    #: in advance which one a given file holds.
    material_required: bool = False
    #: Whether the user may supply certified peak positions for this slot's
    #: material. Protocols that judge a spectrum against known positions need a
    #: table for it; offering this lets a caller work with a material the
    #: service does not carry, or substitute their own certificate for one it
    #: does.
    accepts_reference_peaks: bool = False

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
    #: Which of this step's inputs it locates peaks in, when that is not all of
    #: them. A step can treat its inputs differently -- deriving a warp from
    #: reference positions alone while still reading a band apex from a
    #: laser-zeroing material -- and only the slots named here get peak-finding
    #: controls. ``None`` means every input, which keeps recipes written before
    #: this field behaving as they did.
    finds_peaks_in: list[str] | None = None

    model_config = {"extra": "forbid"}


class RecipeSpec(BaseModel):
    """A named, versioned calibration protocol for one engine."""

    id: str
    label: str
    engine: str
    version: int = 1
    description: str = ""
    laser_wavelengths: list[int] | None = None
    #: Which server-side algorithm a `remote`-engine recipe targets, set by the service
    #: that published it. Unused by in-process engines. A recipe's slots are that
    #: algorithm's material contract, so the two cannot be chosen independently: a recipe
    #: built around one set of reference materials is meaningless for an algorithm
    #: expecting a different set.
    algorithm_id: str | None = None
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
            if step.finds_peaks_in is not None:
                # Naming a slot the step does not consume would silently offer peak
                # controls on an input this step never reads.
                stray = set(step.finds_peaks_in) - set(step.inputs)
                if stray:
                    raise ValueError(
                        f"step {step.id!r} declares finds_peaks_in {sorted(stray)!r}, "
                        "which it does not consume"
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
        """Look up a slot, or a repeatable slot's entry ("anchor#0" -> "anchor").

        A repeatable slot has one definition but many entries, each holding a
        different material -- entry ids are a UI/engine addressing convention,
        not a distinct slot, so they resolve to the same :class:`SpectrumSlot`.
        """
        base = base_slot_id(slot_id)
        for slot in self.slots:
            if slot.id == base:
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
        present = {base_slot_id(a) for a in available}
        return [s.id for s in self.slots if s.required and s.id not in present]

    def runnable_steps(self, available: set[str]) -> list[StepSpec]:
        """Steps whose inputs are all present.

        A step is skipped -- not failed -- when an *optional* input is absent.
        This is the "no Silicon spectrum" case: the Neon curve is still worth
        deriving on its own, so laser zeroing drops out quietly instead of
        taking the whole calibration down with it. ``available`` may contain
        entry keys for a repeatable slot; any one entry counts as the slot
        being present.
        """
        present = {base_slot_id(a) for a in available}
        runnable = []
        for step in self.steps:
            if all(slot_id in present for slot_id in step.inputs):
                runnable.append(step)
        return runnable
