from user_profile import get_priority_tags


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
