from food_tags import STARTER_TAGS, build_tag_options


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
