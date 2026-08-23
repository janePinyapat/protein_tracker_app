"""Vocabulary and behavior driven by the user's profile.

The profile (diet type, purpose, and optional weight/height) is captured
once during onboarding and can be edited any time from the Profile page. It
does two things:

1. Reorders which tag suggestions appear first when logging food — this
   never hides a tag or restricts what can be logged; every starter tag
   stays available to everyone regardless of profile.
2. When weight or purpose changes, calculates suggested Rest day / Training
   day protein and fiber targets (see ``nutrition_targets.py`` for the
   guidelines and sources used) and saves them. These are starting points
   the user can fine-tune any time on the Meal Recommendations page — not a
   personalized medical recommendation. Re-saving the profile without
   changing weight or purpose leaves existing targets alone, so it never
   silently overwrites a manual edit made on the Meal Recommendations page.
   Height (with weight) is used only to show BMI as general context; it
   doesn't affect the protein/fiber numbers or count as a "changed" input.
"""

from database import get_user_profile, save_protein_goal, save_user_profile
from nutrition_targets import (
    calculate_fiber_target,
    calculate_protein_targets,
    convert_to_kg,
)


DIET_TYPES = [
    "Omnivore",
    "Vegetarian",
    "Vegan",
    "Pescatarian",
    "Other / prefer not to say",
]

PURPOSES = [
    "PCOS management",
    "Strength training / muscle recovery",
    "General health tracking",
    "Other",
]

# Starter tags (see food_tags.STARTER_TAGS) promoted to the top of the tag
# picker for a given diet type or purpose. This is a suggested order only.
DIET_TAG_PRIORITY = {
    "Vegan": ["Plant-based"],
    "Vegetarian": ["Plant-based", "Dairy"],
    "Pescatarian": ["Plant-based"],
}

PURPOSE_TAG_PRIORITY = {
    "PCOS management": ["Low glycemic", "High fiber", "Added sugar", "Refined carbs"],
    "Strength training / muscle recovery": [
        "High protein",
        "Pre-workout",
        "Post-workout",
        "Home cooked",
    ],
}


def get_priority_tags(diet_type, purposes):
    """Tags to suggest first, in order, for this profile.

    Duplicates across diet type and purpose are kept only once, in the order
    first encountered.
    """
    priority = []

    for tag in DIET_TAG_PRIORITY.get(diet_type, []):
        if tag not in priority:
            priority.append(tag)

    for purpose in purposes or []:
        for tag in PURPOSE_TAG_PRIORITY.get(purpose, []):
            if tag not in priority:
                priority.append(tag)

    return priority


def calculation_inputs_changed(previous_profile, purposes, weight_value, weight_unit):
    """Whether purpose or weight differ from the last saved profile.

    Diet type and height are deliberately excluded — neither feeds the
    protein/fiber calculation, so changing only those must not trigger a
    recalculation. No previous profile (first-run onboarding) always counts
    as changed, since there's nothing yet to preserve.
    """
    if previous_profile is None:
        return True

    if set(previous_profile.get("purposes") or []) != set(purposes or []):
        return True

    if previous_profile.get("weight_value") != weight_value:
        return True

    if previous_profile.get("weight_unit") != weight_unit:
        return True

    return False


def save_profile_and_targets(
    diet_type,
    purposes,
    weight_value=None,
    weight_unit=None,
    height_value=None,
    height_unit=None,
):
    """Save the profile, recalculating Rest day / Training day targets only
    when weight or purpose actually changed from what's currently saved.

    This is deliberate: re-submitting the Profile form — even just to tweak
    diet type, or by habit — must not silently overwrite protein/fiber
    targets the user customized by hand on the Meal Recommendations page.
    Height is saved (for the BMI shown on the Profile page) but never
    affects the calculation either way — protein and fiber needs are dosed
    from bodyweight directly in the guidelines this app cites, and BMI isn't
    a recognized input for that calculation.

    Returns ``(protein_targets, fiber_target, recalculated)``.
    ``protein_targets``/``fiber_target`` are None whenever nothing was
    recalculated — either because the inputs didn't change, or because
    there's still no usable weight. ``recalculated`` tells the caller
    whether this save attempted a recalculation at all (even one that
    produced no usable weight), so the two None cases can be told apart.
    """
    previous_profile = get_user_profile()
    inputs_changed = calculation_inputs_changed(
        previous_profile, purposes, weight_value, weight_unit
    )

    save_user_profile(
        diet_type, purposes, weight_value, weight_unit, height_value, height_unit
    )

    if not inputs_changed:
        return None, None, False

    weight_kg = convert_to_kg(weight_value, weight_unit)
    protein_targets = calculate_protein_targets(weight_kg, purposes)
    fiber_target = calculate_fiber_target(purposes)

    if protein_targets:
        save_protein_goal("Rest day", protein_targets["rest"], fiber_target)
        save_protein_goal("Training day", protein_targets["training"], fiber_target)

    return protein_targets, fiber_target, True
