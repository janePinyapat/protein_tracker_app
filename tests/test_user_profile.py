import database
from user_profile import get_priority_tags, save_profile_and_targets


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
    protein_targets, fiber_target = save_profile_and_targets(
        "Omnivore", ["Strength training / muscle recovery"], 70.0, "kg"
    )

    assert protein_targets == {"rest": 98, "training": 126}
    assert fiber_target == 25

    goals = database.get_protein_goals()
    rest_goal = goals[goals["day_type"] == "Rest day"].iloc[0]
    training_goal = goals[goals["day_type"] == "Training day"].iloc[0]

    assert rest_goal["daily_target_grams"] == 98
    assert training_goal["daily_target_grams"] == 126
    assert rest_goal["fiber_target_grams"] == 25


def test_save_profile_and_targets_skips_goal_calculation_without_weight(
    temp_database,
):
    protein_targets, fiber_target = save_profile_and_targets(
        "Omnivore", ["General health tracking"], None, "kg"
    )

    assert protein_targets is None
    assert database.get_protein_goals().empty


def test_save_profile_and_targets_does_not_erase_existing_goals_when_weight_omitted(
    temp_database,
):
    save_profile_and_targets("Omnivore", ["General health tracking"], 70.0, "kg")
    save_profile_and_targets("Omnivore", ["General health tracking"], None, "kg")

    goals = database.get_protein_goals()
    rest_goal = goals[goals["day_type"] == "Rest day"].iloc[0]
    assert rest_goal["daily_target_grams"] == 70
