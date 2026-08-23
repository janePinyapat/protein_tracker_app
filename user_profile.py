"""Vocabulary and behavior driven by the user's profile.

The profile (diet type, purpose, and optional weight/height) is captured
once during onboarding and can be edited any time from the Profile page. It
does two things:

1. Reorders which tag suggestions appear first when logging food — this
   never hides a tag or restricts what can be logged; every starter tag
   stays available to everyone regardless of profile.
2. When a weight is given, calculates suggested Rest day / Training day
   protein and fiber targets (see ``nutrition_targets.py`` for the
   guidelines and sources used) and saves them. These are starting points
   the user can fine-tune any time on the Set Daily Targets page — not a
   personalized medical recommendation. Height (with weight) is used only to
   show BMI as general context; it doesn't affect the protein/fiber numbers.
"""

from database import save_protein_goal, save_user_profile
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


def save_profile_and_targets(
    diet_type,
    purposes,
    weight_value=None,
    weight_unit=None,
    height_value=None,
    height_unit=None,
):
    """Save the profile, and recalculate Rest day / Training day targets from it.

    Height is saved (for the BMI shown on the Profile page) but doesn't feed
    into the protein/fiber calculation — protein and fiber needs are dosed
    from bodyweight directly in the guidelines this app cites, and BMI isn't
    a recognized input for that calculation.

    Returns ``(protein_targets, fiber_target)``. ``protein_targets`` is None
    when no usable weight was given, in which case any previously saved
    protein/fiber targets are left untouched — this only ever recalculates
    when it has a weight to calculate from.
    """
    save_user_profile(
        diet_type, purposes, weight_value, weight_unit, height_value, height_unit
    )

    weight_kg = convert_to_kg(weight_value, weight_unit)
    protein_targets = calculate_protein_targets(weight_kg, purposes)
    fiber_target = calculate_fiber_target(purposes)

    if protein_targets:
        save_protein_goal("Rest day", protein_targets["rest"], fiber_target)
        save_protein_goal("Training day", protein_targets["training"], fiber_target)

    return protein_targets, fiber_target
