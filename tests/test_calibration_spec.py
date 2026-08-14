"""The recipe schema is the contract the UI renders from, so its invariants
are worth pinning: a malformed recipe should fail at load time, not when a user
is halfway through uploading reference spectra."""

import pytest
import yaml
from pydantic import ValidationError

from spectrastream.calibration.registry import (
    BUILTIN_RECIPE_DIR,
    RecipeError,
    load_recipe_file,
    load_recipes,
)
from spectrastream.calibration.spec import RecipeSpec, base_slot_id, entry_key


def _minimal(**overrides):
    base = {
        "id": "t.demo",
        "label": "Demo",
        "engine": "rc2",
        "slots": [{"id": "a", "label": "A"}],
        "steps": [
            {
                "id": "s1",
                "label": "S1",
                "action": "x_curve",
                "inputs": ["a"],
                "produces": "x_axis",
            }
        ],
    }
    base.update(overrides)
    return base


def test_minimal_recipe_validates():
    recipe = RecipeSpec.model_validate(_minimal())
    assert recipe.slot("a").required is True
    assert recipe.version == 1


def test_step_referring_to_unknown_slot_is_rejected():
    data = _minimal(
        steps=[
            {
                "id": "s1",
                "label": "S1",
                "action": "x_curve",
                "inputs": ["nope"],
                "produces": "x_axis",
            }
        ]
    )
    with pytest.raises(ValidationError, match="undeclared slot"):
        RecipeSpec.model_validate(data)


def test_required_slot_no_step_consumes_is_rejected():
    """Otherwise the UI would demand a file that nothing ever reads."""
    data = _minimal(
        slots=[{"id": "a", "label": "A"}, {"id": "orphan", "label": "Orphan"}]
    )
    with pytest.raises(ValidationError, match="not used by any step"):
        RecipeSpec.model_validate(data)


def test_duplicate_slot_ids_rejected():
    data = _minimal(slots=[{"id": "a", "label": "A"}, {"id": "a", "label": "A2"}])
    with pytest.raises(ValidationError, match="duplicate slot"):
        RecipeSpec.model_validate(data)


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        RecipeSpec.model_validate(_minimal(typoed_field=1))


def test_runnable_steps_skips_absent_optional_input():
    recipe = RecipeSpec.model_validate(
        _minimal(
            slots=[
                {"id": "a", "label": "A"},
                {"id": "b", "label": "B", "required": False},
            ],
            steps=[
                {
                    "id": "s1",
                    "label": "S1",
                    "action": "x_curve",
                    "inputs": ["a"],
                    "produces": "x_axis",
                },
                {
                    "id": "s2",
                    "label": "S2",
                    "action": "laser_zero",
                    "inputs": ["b"],
                    "produces": "x_zero",
                    "optional": True,
                },
            ],
        )
    )
    assert [s.id for s in recipe.runnable_steps({"a"})] == ["s1"]
    assert [s.id for s in recipe.runnable_steps({"a", "b"})] == ["s1", "s2"]
    assert recipe.missing_required_slots({"a"}) == []
    assert recipe.missing_required_slots(set()) == ["a"]


def test_entry_key_round_trips_to_its_base_slot_id():
    assert base_slot_id(entry_key("anchor", 0)) == "anchor"
    assert base_slot_id(entry_key("anchor", 7)) == "anchor"
    # A plain slot id (no entries) is its own base -- callers should not need to
    # special-case a non-repeatable slot before resolving it.
    assert base_slot_id("anchor") == "anchor"


def test_recipe_slot_resolves_a_repeatable_entry_to_its_definition():
    recipe = RecipeSpec.model_validate(
        _minimal(slots=[{"id": "a", "label": "A", "repeatable": True}])
    )
    assert recipe.slot(entry_key("a", 0)) is recipe.slot("a")
    assert recipe.slot(entry_key("a", 3)) is recipe.slot("a")


def test_missing_required_slots_accepts_any_entry_of_a_repeatable_slot():
    """A repeatable slot is satisfied by ANY entry being present -- the caller does not
    have to have filled a specific index."""
    recipe = RecipeSpec.model_validate(
        _minimal(slots=[{"id": "a", "label": "A", "repeatable": True}])
    )
    assert recipe.missing_required_slots({entry_key("a", 0)}) == []
    assert recipe.missing_required_slots({entry_key("a", 2)}) == []
    assert recipe.missing_required_slots(set()) == ["a"]


def test_runnable_steps_treats_any_entry_as_the_slot_being_present():
    recipe = RecipeSpec.model_validate(
        _minimal(slots=[{"id": "a", "label": "A", "repeatable": True}])
    )
    assert [s.id for s in recipe.runnable_steps({entry_key("a", 1)})] == ["s1"]


def test_finds_peaks_in_must_name_a_consumed_slot():
    with pytest.raises(ValidationError, match="finds_peaks_in"):
        RecipeSpec.model_validate(
            _minimal(
                slots=[
                    {"id": "a", "label": "A"},
                    {"id": "b", "label": "B", "required": False},
                ],
                steps=[
                    {
                        "id": "s1",
                        "label": "S1",
                        "action": "x_curve",
                        "inputs": ["a"],
                        "produces": "x_axis",
                        # "b" is not among this step's inputs.
                        "finds_peaks_in": ["b"],
                    }
                ],
            )
        )


def test_wavelength_filter():
    any_wl = RecipeSpec.model_validate(_minimal())
    assert any_wl.supports_wavelength(532) and any_wl.supports_wavelength(None)

    pinned = RecipeSpec.model_validate(_minimal(laser_wavelengths=[532, 785]))
    assert pinned.supports_wavelength(532.0)
    assert not pinned.supports_wavelength(633)
    assert not pinned.supports_wavelength(None)


def test_builtin_recipes_all_load():
    recipes = load_recipes([BUILTIN_RECIPE_DIR])
    assert {"rc2.ne_si", "rc2.si_only", "rc2.y_srm"} <= set(recipes)
    for recipe in recipes.values():
        assert recipe.steps, f"{recipe.id} declares no steps"


def test_malformed_recipe_file_names_itself(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text(yaml.safe_dump({"id": "x"}), encoding="utf-8")
    with pytest.raises(RecipeError, match="broken.yaml"):
        load_recipe_file(path)
