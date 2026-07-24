"""Pluggable calibration: declarative recipes over swappable engines.

"No calibration" is represented by the absence of a recipe, not by a null
engine -- the NeXus floor does not need a calibration object to produce a
valid file.
"""

from .engines.base import (
    CalibrationContext,
    CalibrationEngine,
    CalibrationError,
    Diagnostic,
    FittedCalibration,
    StepOutcome,
)
from .registry import (
    RecipeError,
    all_recipes,
    engine_for_recipe,
    get_engine,
    get_recipe,
    recipes_for_wavelength,
    reset_cache,
)
from .spec import RecipeSpec, SpectrumSlot, StepSpec

__all__ = [
    "CalibrationContext",
    "CalibrationEngine",
    "CalibrationError",
    "Diagnostic",
    "FittedCalibration",
    "RecipeError",
    "RecipeSpec",
    "SpectrumSlot",
    "StepOutcome",
    "StepSpec",
    "all_recipes",
    "engine_for_recipe",
    "get_engine",
    "get_recipe",
    "recipes_for_wavelength",
    "reset_cache",
]
