from food_tags import STARTER_TAGS, build_tag_options, suggest_tags_from_entry


def test_build_tag_options_defaults_to_alphabetical():
    options = build_tag_options()
    assert options == sorted(STARTER_TAGS, key=str.casefold)


def test_build_tag_options_appends_saved_tags_not_in_starter_list():
    options = build_tag_options(saved_tags=["Zzz custom tag"])
    assert "Zzz custom tag" in options
    assert options[-1] == "Zzz custom tag"  # not in any priority list, sorts last


def test_build_tag_options_deduplicates_saved_tags_already_in_starter_list():
    options = build_tag_options(saved_tags=["Dairy"])
    assert options.count("Dairy") == 1


def test_build_tag_options_promotes_priority_tags_first():
    options = build_tag_options(priority_tags=["Plant-based"])
    assert options[0] == "Plant-based"


def test_build_tag_options_promotes_multiple_priority_tags_in_order():
    options = build_tag_options(
        priority_tags=["Low glycemic", "High fiber", "Added sugar", "Refined carbs"]
    )
    assert options[:4] == ["Low glycemic", "High fiber", "Added sugar", "Refined carbs"]


def test_build_tag_options_keeps_remaining_tags_alphabetical_after_priority():
    options = build_tag_options(priority_tags=["Plant-based"])
    remaining = options[1:]
    assert remaining == sorted(remaining, key=str.casefold)


def test_build_tag_options_ignores_priority_tags_not_in_the_list():
    options = build_tag_options(priority_tags=["Not a real tag"])
    assert options == sorted(STARTER_TAGS, key=str.casefold)


def test_build_tag_options_priority_tag_can_be_a_saved_custom_tag():
    options = build_tag_options(
        saved_tags=["My custom tag"], priority_tags=["My custom tag"]
    )
    assert options[0] == "My custom tag"


# --- suggest_tags_from_entry --------------------------------------------------


def test_suggest_tags_matches_description_keyword():
    assert suggest_tags_from_entry("Greek yogurt with berries") == ["Dairy"]


def test_suggest_tags_matches_are_case_insensitive():
    assert suggest_tags_from_entry("GREEK YOGURT") == ["Dairy"]


def test_suggest_tags_matches_multiple_description_keywords():
    tags = suggest_tags_from_entry("Chocolate cake with cheese frosting")
    assert "Added sugar" in tags
    assert "Dairy" in tags


def test_suggest_tags_maps_protein_source_directly():
    tags = suggest_tags_from_entry("Stir-fry", protein_source="Plant-based/Tofu")
    assert "Plant-based" in tags


def test_suggest_tags_maps_legumes_to_plant_based():
    tags = suggest_tags_from_entry("Bean bowl", protein_source="Legumes/Beans")
    assert "Plant-based" in tags


def test_suggest_tags_maps_protein_powder_to_processed():
    tags = suggest_tags_from_entry("Shake", protein_source="Protein powder")
    assert "Processed" in tags


def test_suggest_tags_maps_post_workout_meal_type():
    tags = suggest_tags_from_entry("Recovery shake", meal_type="Post-workout")
    assert "Post-workout" in tags


def test_suggest_tags_does_not_add_post_workout_for_other_meal_types():
    tags = suggest_tags_from_entry("Oatmeal", meal_type="Breakfast")
    assert "Post-workout" not in tags


def test_suggest_tags_adds_high_protein_at_threshold():
    assert "High protein" in suggest_tags_from_entry("Chicken", protein_grams=20.0)


def test_suggest_tags_omits_high_protein_below_threshold():
    assert "High protein" not in suggest_tags_from_entry("Chicken", protein_grams=19.9)


def test_suggest_tags_adds_high_fiber_at_threshold():
    assert "High fiber" in suggest_tags_from_entry("Beans", fiber_grams=5.0)


def test_suggest_tags_omits_high_fiber_below_threshold():
    assert "High fiber" not in suggest_tags_from_entry("Beans", fiber_grams=4.9)


def test_suggest_tags_combines_multiple_signal_sources():
    tags = suggest_tags_from_entry(
        "Tofu stir-fry",
        protein_grams=25.0,
        fiber_grams=6.0,
        meal_type="Post-workout",
        protein_source="Plant-based/Tofu",
    )
    assert set(tags) == {"Plant-based", "Post-workout", "High protein", "High fiber"}


def test_suggest_tags_deduplicates_across_sources():
    # Description keyword and protein source both point to "Plant-based" —
    # it should only appear once.
    tags = suggest_tags_from_entry("Tofu bowl", protein_source="Plant-based/Tofu")
    assert tags.count("Plant-based") == 1


def test_suggest_tags_returns_empty_list_when_nothing_matches():
    assert suggest_tags_from_entry("Mystery meal") == []


def test_suggest_tags_handles_all_defaults():
    assert suggest_tags_from_entry() == []


def test_suggest_tags_handles_none_description():
    assert suggest_tags_from_entry(None) == []
