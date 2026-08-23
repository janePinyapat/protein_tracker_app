import database
from user_profile import (
    calculation_inputs_changed,
    get_priority_tags,
    save_profile_and_targets,
)


def test_get_priority_tags_promotes_diet_tags():
    priority = get_priority_tags("Vegan", None)
    assert priority == ["Plant-based"]


def test_get_priority_tags_promotes_purpose_tags():
    priority = get_priority_tags(None, ["PCOS management"])
    assert priority == ["Low glycemic", "High fiber", "Added sugar", "Refined carbs"]


def test_get_priority_tags_combines_diet_and_purpose_without_duplicates():
    priority = get_priority_tags("Vegetarian", ["PCOS management"])

    assert priority[:2] == ["Plant-based", "Dairy"]
    assert "Low glycemic" in priority
    # Plant-based only appears once even though it could theoretically be
    # relevant to more than one rule.
    assert priority.count("Plant-based") == 1


def test_get_priority_tags_handles_multiple_purposes():
    priority = get_priority_tags(
        None, ["PCOS management", "Strength training / muscle recovery"]
    )

    assert "Low glycemic" in priority
    assert "High protein" in priority


def test_get_priority_tags_returns_empty_for_unknown_profile():
    assert get_priority_tags("Omnivore", ["General health tracking"]) == []


def test_get_priority_tags_handles_none_diet_and_purposes():
    assert get_priority_tags(None, None) == []


def test_get_priority_tags_ignores_unrecognized_purpose_strings():
    assert get_priority_tags(None, ["Not a real purpose"]) == []


def test_save_profile_and_targets_saves_profile(temp_database):
    save_profile_and_targets("Vegan", ["General health tracking"], 70.0, "kg")

    profile = database.get_user_profile()
    assert profile["diet_type"] == "Vegan"
    assert profile["weight_value"] == 70.0


def test_save_profile_and_targets_calculates_and_saves_protein_goals(temp_database):
    protein_targets, fiber_target, water_target_ml, recalculated = (
        save_profile_and_targets(
            "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
        )
    )

    assert protein_targets == {"rest": 98, "training": 126}
    assert fiber_target == 25
    assert water_target_ml == 2100  # 70 kg x 30 mL/kg, above the floor
    assert recalculated is True

    goals = database.get_protein_goals()
    rest_goal = goals[goals["day_type"] == "Rest day"].iloc[0]
    training_goal = goals[goals["day_type"] == "Training day"].iloc[0]

    assert rest_goal["daily_target_grams"] == 98
    assert training_goal["daily_target_grams"] == 126
    assert rest_goal["fiber_target_grams"] == 25

    wellness_goals = database.get_wellness_goals()
    assert wellness_goals["water_target_ml"] == 2100


def test_save_profile_and_targets_calculates_water_target_above_the_floor(
    temp_database,
):
    _, _, water_target_ml, _ = save_profile_and_targets(
        "Omnivore", ["General health tracking"], 90.0, "kg"
    )

    assert water_target_ml == 2700  # 90 kg x 30 mL/kg, above the floor
    assert database.get_wellness_goals()["water_target_ml"] == 2700


def test_save_profile_and_targets_preserves_existing_sleep_target(temp_database):
    save_profile_and_targets("Omnivore", ["General health tracking"], 70.0, "kg")
    database.save_wellness_goals(water_target_ml=1500.0, sleep_target_hours=7.5)

    save_profile_and_targets("Omnivore", ["General health tracking"], 75.0, "kg")

    wellness_goals = database.get_wellness_goals()
    assert wellness_goals["water_target_ml"] == 2250  # recalculated for 75 kg
    assert wellness_goals["sleep_target_hours"] == 7.5  # untouched


def test_save_profile_and_targets_skips_goal_calculation_without_weight(
    temp_database,
):
    protein_targets, fiber_target, water_target_ml, recalculated = (
        save_profile_and_targets(
            "Omnivore", ["General health tracking"], None, "kg"
        )
    )

    assert protein_targets is None
    assert water_target_ml is None
    assert recalculated is True  # attempted — first save, always "changed"
    assert database.get_protein_goals().empty
    assert database.get_wellness_goals() is None


def test_save_profile_and_targets_does_not_erase_existing_goals_when_weight_omitted(
    temp_database,
):
    save_profile_and_targets("Omnivore", ["General health tracking"], 70.0, "kg")
    save_profile_and_targets("Omnivore", ["General health tracking"], None, "kg")

    goals = database.get_protein_goals()
    rest_goal = goals[goals["day_type"] == "Rest day"].iloc[0]
    assert rest_goal["daily_target_grams"] == 70


def test_save_profile_and_targets_saves_height(temp_database):
    save_profile_and_targets(
        "Omnivore", ["General health tracking"], 70.0, "kg", 175.0, "cm"
    )

    profile = database.get_user_profile()
    assert profile["height_value"] == 175.0
    assert profile["height_unit"] == "cm"


def test_save_profile_and_targets_height_does_not_affect_protein_calculation(
    tmp_path, monkeypatch
):
    """Height is for BMI display only. Compared across two independent first
    saves (not sequential calls) so the new change-detection behavior below
    can't mask the result — a height-only change on a second call wouldn't
    recalculate at all, which is covered separately."""
    db_one = tmp_path / "one.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(db_one))
    database.initialize_database()
    without_height, fiber_one, water_one, _ = save_profile_and_targets(
        "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
    )

    db_two = tmp_path / "two.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(db_two))
    database.initialize_database()
    with_height, fiber_two, water_two, _ = save_profile_and_targets(
        "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg", 150.0, "cm"
    )

    assert without_height == with_height
    assert fiber_one == fiber_two
    assert water_one == water_two


def test_calculation_inputs_changed_true_when_no_previous_profile():
    assert calculation_inputs_changed(None, ["Other"], 70.0, "kg") is True


def test_calculation_inputs_changed_false_when_nothing_differs():
    previous = {"purposes": ["Other"], "weight_value": 70.0, "weight_unit": "kg"}
    assert calculation_inputs_changed(previous, ["Other"], 70.0, "kg") is False


def test_calculation_inputs_changed_true_when_weight_differs():
    previous = {"purposes": ["Other"], "weight_value": 70.0, "weight_unit": "kg"}
    assert calculation_inputs_changed(previous, ["Other"], 71.0, "kg") is True


def test_calculation_inputs_changed_true_when_weight_unit_differs():
    previous = {"purposes": ["Other"], "weight_value": 70.0, "weight_unit": "kg"}
    assert calculation_inputs_changed(previous, ["Other"], 70.0, "lb") is True


def test_calculation_inputs_changed_true_when_purposes_differ():
    previous = {"purposes": ["Other"], "weight_value": 70.0, "weight_unit": "kg"}
    assert (
        calculation_inputs_changed(previous, ["PCOS management"], 70.0, "kg") is True
    )


def test_calculation_inputs_changed_ignores_purpose_order():
    previous = {
        "purposes": ["PCOS management", "Other"],
        "weight_value": 70.0,
        "weight_unit": "kg",
    }
    assert (
        calculation_inputs_changed(
            previous, ["Other", "PCOS management"], 70.0, "kg"
        )
        is False
    )


def test_save_profile_and_targets_does_not_recalculate_when_nothing_changed(
    temp_database,
):
    save_profile_and_targets(
        "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
    )

    # Simulate the user hand-editing targets on the Set Daily Targets page.
    database.save_protein_goal("Rest day", 150.0, 40.0)
    database.save_protein_goal("Training day", 200.0, 40.0)

    protein_targets, fiber_target, water_target_ml, recalculated = (
        save_profile_and_targets(
            "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
        )
    )

    assert protein_targets is None
    assert fiber_target is None
    assert water_target_ml is None
    assert recalculated is False

    goals = database.get_protein_goals()
    rest_goal = goals[goals["day_type"] == "Rest day"].iloc[0]
    assert rest_goal["daily_target_grams"] == 150.0
    assert rest_goal["fiber_target_grams"] == 40.0


def test_save_profile_and_targets_does_not_recalculate_for_diet_type_only_change(
    temp_database,
):
    """Diet type never feeds the calculation, so changing only it must not
    trigger a recalculation either."""
    save_profile_and_targets(
        "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
    )
    database.save_protein_goal("Rest day", 150.0, 40.0)

    _, _, _, recalculated = save_profile_and_targets(
        "Vegan", ["Strength training / muscle recovery"], 70.0, "kg"
    )

    assert recalculated is False
    goals = database.get_protein_goals()
    assert goals[goals["day_type"] == "Rest day"].iloc[0]["daily_target_grams"] == 150.0


def test_save_profile_and_targets_does_not_recalculate_for_height_only_change(
    temp_database,
):
    save_profile_and_targets(
        "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
    )
    database.save_protein_goal("Rest day", 150.0, 40.0)

    _, _, _, recalculated = save_profile_and_targets(
        "Omnivore",
        ["Strength training / muscle recovery"],
        70.0,
        "kg",
        180.0,
        "cm",
    )

    assert recalculated is False
    goals = database.get_protein_goals()
    assert goals[goals["day_type"] == "Rest day"].iloc[0]["daily_target_grams"] == 150.0


def test_save_profile_and_targets_recalculates_when_weight_changes(temp_database):
    save_profile_and_targets(
        "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
    )
    database.save_protein_goal("Rest day", 150.0, 40.0)

    protein_targets, fiber_target, water_target_ml, recalculated = (
        save_profile_and_targets(
            "Omnivore", ["Strength training / muscle recovery"], 75.0, "kg"
        )
    )

    assert recalculated is True
    assert protein_targets == {"rest": 105, "training": 135}
    assert water_target_ml == 2250
    goals = database.get_protein_goals()
    assert goals[goals["day_type"] == "Rest day"].iloc[0]["daily_target_grams"] == 105


def test_save_profile_and_targets_recalculates_when_purposes_change(temp_database):
    save_profile_and_targets("Omnivore", ["General health tracking"], 70.0, "kg")
    database.save_protein_goal("Rest day", 150.0, 40.0)

    protein_targets, fiber_target, water_target_ml, recalculated = (
        save_profile_and_targets(
            "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
        )
    )

    assert recalculated is True
    assert protein_targets == {"rest": 98, "training": 126}
    assert water_target_ml == 2100
    goals = database.get_protein_goals()
    assert goals[goals["day_type"] == "Rest day"].iloc[0]["daily_target_grams"] == 98
