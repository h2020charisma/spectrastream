"""Engine and recipe registry.

Recipes are loaded from ``recipes/*.yaml`` next to this module, plus every
directory listed in ``$SPECTRASTREAM_RECIPES`` (os.pathsep-separated). Adding a
calibration protocol is therefore a YAML file, not a code change -- which is the
point: engines differ in what reference spectra they need, and the app should
not have to know.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import yaml

from spectrastream.calibration.engines.base import CalibrationEngine
from spectrastream.calibration.spec import RecipeSpec

BUILTIN_RECIPE_DIR = Path(__file__).parent / "recipes"
RECIPE_PATH_ENV = "SPECTRASTREAM_RECIPES"


class RecipeError(ValueError):
    """A recipe file is malformed or refers to an unknown engine."""


def recipe_dirs() -> list[Path]:
    dirs = [BUILTIN_RECIPE_DIR]
    extra = os.environ.get(RECIPE_PATH_ENV, "")
    dirs.extend(Path(p) for p in extra.split(os.pathsep) if p.strip())
    return [d for d in dirs if d.is_dir()]


def load_recipe_file(path: Path) -> RecipeSpec:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        raise RecipeError(f"{path.name}: not valid YAML: {err}") from err
    if not isinstance(raw, dict):
        raise RecipeError(f"{path.name}: expected a mapping at the top level")
    try:
        return RecipeSpec.model_validate(raw)
    except Exception as err:
        raise RecipeError(f"{path.name}: {err}") from err


def load_recipes(dirs: Iterable[Path] | None = None) -> dict[str, RecipeSpec]:
    """Load every recipe, later directories overriding earlier ids."""
    recipes: dict[str, RecipeSpec] = {}
    for directory in dirs if dirs is not None else recipe_dirs():
        for path in sorted(Path(directory).glob("*.yaml")):
            recipe = load_recipe_file(path)
            recipes[recipe.id] = recipe
    return recipes


@lru_cache(maxsize=1)
def _registry() -> tuple[dict[str, CalibrationEngine], dict[str, RecipeSpec]]:
    from spectrastream.calibration.engines.rc2 import Rc2Engine

    recipes = load_recipes()
    engines: dict[str, CalibrationEngine] = {}

    def register(engine: CalibrationEngine) -> None:
        engines[engine.id] = engine

    register(Rc2Engine(r for r in recipes.values() if r.engine == Rc2Engine.id))

    unknown = {r.id: r.engine for r in recipes.values() if r.engine not in engines}
    if unknown:
        raise RecipeError(
            "recipe(s) refer to unregistered engines: "
            + ", ".join(f"{rid} -> {eng!r}" for rid, eng in sorted(unknown.items()))
        )
    return engines, recipes


def reset_cache() -> None:
    """Drop the cached registry -- used by tests that set $SPECTRASTREAM_RECIPES."""
    _registry.cache_clear()


def get_engine(engine_id: str) -> CalibrationEngine:
    engines, _ = _registry()
    try:
        return engines[engine_id]
    except KeyError as err:
        raise KeyError(
            f"Unknown calibration engine {engine_id!r} (have: {sorted(engines)})"
        ) from err


def get_recipe(recipe_id: str) -> RecipeSpec:
    _, recipes = _registry()
    try:
        return recipes[recipe_id]
    except KeyError as err:
        raise KeyError(
            f"Unknown calibration recipe {recipe_id!r} (have: {sorted(recipes)})"
        ) from err


def all_recipes() -> list[RecipeSpec]:
    _, recipes = _registry()
    return sorted(recipes.values(), key=lambda r: (r.engine, r.label))


def recipes_for_wavelength(laser_wl_nm: float | None) -> list[RecipeSpec]:
    return [r for r in all_recipes() if r.supports_wavelength(laser_wl_nm)]


def engine_for_recipe(recipe: RecipeSpec) -> CalibrationEngine:
    return get_engine(recipe.engine)
