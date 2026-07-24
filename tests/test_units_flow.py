"""Declared axis units must reach the engine, not just the axis label.

A neon lamp recorded in nm alongside a silicon wafer in cm-1 is an ordinary
combination. Before CalibrationContext carried per-slot units, every action fell
back to the recipe's default of cm-1, so choosing "nm" changed the chart label
and nothing else -- the engine went on treating wavelengths as Raman shifts.
"""

import pytest

from spectrastream.calibration import (
    CalibrationContext,
    engine_for_recipe,
    get_recipe,
)


def test_context_defaults_to_the_recipes_units_when_none_declared():
    ctx = CalibrationContext()
    assert ctx.units_for("neon") == "cm-1"
    assert ctx.units_for("neon", "nm") == "nm"


def test_context_prefers_what_the_user_declared():
    ctx = CalibrationContext(input_units={"neon": "nm", "si": "cm-1"})
    assert ctx.units_for("neon", "cm-1") == "nm"
    assert ctx.units_for("si", "cm-1") == "cm-1"
    # A slot with nothing declared still falls back.
    assert ctx.units_for("srm", "cm-1") == "cm-1"


def test_blank_declaration_does_not_override_the_default():
    ctx = CalibrationContext(input_units={"neon": ""})
    assert ctx.units_for("neon", "cm-1") == "cm-1"


@pytest.mark.parametrize("declared", ["cm-1", "nm", "pixel"])
def test_the_declared_units_are_what_the_engine_is_told(
    monkeypatch, neon_spectrum, declared
):
    """Assert the wiring, not the numerics.

    What matters is that the units the user chose are the units handed to the
    fit. Comparing fitted models instead would make this test hostage to
    whether a synthetic spectrum happens to converge.
    """
    from ramanchada2.protocols.calibration.calibration_model import CalibrationModel

    seen: dict[str, str] = {}
    original = CalibrationModel._derive_model_curve

    def capture(self, *args, **kwargs):
        seen["spe_units"] = kwargs.get("spe_units")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CalibrationModel, "_derive_model_curve", capture)

    recipe = get_recipe("rc2.ne_si")
    engine_for_recipe(recipe).fit(
        recipe,
        {"neon": neon_spectrum.spectrum},
        CalibrationContext(laser_wl_nm=532, input_units={"neon": declared}),
    )
    assert seen["spe_units"] == declared


def test_undeclared_slots_still_use_the_recipe_default(monkeypatch, neon_spectrum):
    from ramanchada2.protocols.calibration.calibration_model import CalibrationModel

    seen: dict[str, str] = {}
    original = CalibrationModel._derive_model_curve

    def capture(self, *args, **kwargs):
        seen["spe_units"] = kwargs.get("spe_units")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(CalibrationModel, "_derive_model_curve", capture)

    recipe = get_recipe("rc2.ne_si")
    engine_for_recipe(recipe).fit(
        recipe, {"neon": neon_spectrum.spectrum}, CalibrationContext(laser_wl_nm=532)
    )
    assert seen["spe_units"] == "cm-1"


def test_silicon_recipes_offer_a_crop(neon_spectrum):
    """Cropping silicon to its band is the single most useful adjustment, and
    the one the engine's internal window hides from view."""
    for recipe_id in ("rc2.ne_si", "rc2.si_only"):
        recipe = get_recipe(recipe_id)
        si = recipe.slot("si")
        ops = [p.op for p in si.preprocess]
        assert "trim" in ops, f"{recipe_id} offers no crop on silicon"
        crop = next(p for p in si.preprocess if p.op == "trim")
        assert crop.enabled, "the silicon crop should be on by default"
        assert crop.params["min"] < 520.45 < crop.params["max"]


@pytest.mark.parametrize("recipe_id", ["rc2.ne_si", "rc2.si_only", "rc2.y_srm"])
def test_every_slot_declares_its_units(recipe_id):
    for slot in get_recipe(recipe_id).slots:
        assert slot.units in ("cm-1", "nm", "pixel")
