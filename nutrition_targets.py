"""Suggested protein and fiber daily targets from published nutrition guidelines.

These are population-level starting points, not a personalized clinical
prescription. They're calculated from body weight and the purpose(s) chosen
on the Profile page, then saved as the Rest day / Training day targets — the
user can always fine-tune them afterward on the Set Daily Targets page.

Sources used:

- Protein, general adults: 0.8 g/kg/day is the Recommended Dietary Allowance
  (RDA) from the U.S./Canadian Dietary Reference Intakes (National Academy of
  Medicine, "Dietary Reference Intakes for Energy, Carbohydrate, Fiber, Fat,
  Fatty Acids, Cholesterol, Protein, and Amino Acids", 2005). Many general
  preventive-health sources suggest a somewhat higher intake, up to roughly
  1.0-1.2 g/kg, to support muscle maintenance.
- Protein, exercise/strength training: 1.4-2.0 g/kg/day is the range given by
  the International Society of Sports Nutrition Position Stand on protein
  and exercise (Jager et al., Journal of the ISSN, 2017) for building and
  maintaining muscle mass in exercising adults.
- Protein, PCOS: there is no single universal gram-per-kilogram figure in the
  major PCOS guidelines (e.g., the 2023 International Evidence-Based
  Guideline for the Assessment and Management of PCOS recommends following
  healthy-eating patterns rather than a specific protein target). A moderate
  protein intake is commonly discussed in PCOS nutrition education for
  satiety and blood-sugar management; this app uses 1.2 g/kg as a reasonable
  moderate starting point, not a clinical prescription.
- Fiber: 25 g/day is the Adequate Intake (AI) for adult women from the same
  National Academy of Medicine Dietary Reference Intakes report. Higher
  fiber intake (commonly 30 g/day or more) is frequently discussed in PCOS
  nutrition education for blood-sugar regulation, so that purpose uses 30 g.

None of this is medical advice. Anyone with a health condition, or who wants
targets tailored to their individual situation, should talk to a registered
dietitian or their doctor.
"""

KG_PER_POUND = 0.45359237

DEFAULT_PROTEIN_G_PER_KG = {"rest": 0.8, "training": 0.8}

# grams of protein per kg of bodyweight per day, by purpose, for a rest day
# and a training/active day.
PURPOSE_PROTEIN_G_PER_KG = {
    "Strength training / muscle recovery": {"rest": 1.4, "training": 1.8},
    "PCOS management": {"rest": 1.2, "training": 1.2},
    "General health tracking": {"rest": 1.0, "training": 1.0},
    "Other": {"rest": 0.8, "training": 0.8},
}

DEFAULT_FIBER_G_PER_DAY = 25

# grams of fiber per day, by purpose.
PURPOSE_FIBER_G_PER_DAY = {
    "PCOS management": 30,
    "Strength training / muscle recovery": 25,
    "General health tracking": 25,
    "Other": 25,
}

SOURCES_NOTE = (
    "Suggested starting points, not medical advice: protein from the "
    "National Academy of Medicine's Dietary Reference Intakes (0.8 g/kg "
    "general RDA) and the International Society of Sports Nutrition's "
    "position stand on protein and exercise (1.4-2.0 g/kg for training "
    "adults); fiber from the Dietary Reference Intakes' Adequate Intake for "
    "adult women (25 g/day), with 30 g/day reflecting fiber levels commonly "
    "discussed in PCOS nutrition education. Talk to a registered dietitian "
    "or your doctor for targets tailored to you."
)


def convert_to_kg(weight_value, weight_unit):
    """Convert a weight in kg or lb to kilograms."""
    if weight_value is None or weight_value <= 0:
        return None

    if weight_unit == "lb":
        return weight_value * KG_PER_POUND

    return weight_value


def calculate_protein_targets(weight_kg, purposes):
    """Suggested Rest day / Training day protein targets, in grams.

    When more than one purpose is selected, the higher per-kilogram figure
    for each day type is used, so a combination like PCOS management plus
    strength training gets the strength-training protein level rather than
    an average that could undershoot muscle-building needs.
    """
    if weight_kg is None or weight_kg <= 0:
        return None

    rest_rate = DEFAULT_PROTEIN_G_PER_KG["rest"]
    training_rate = DEFAULT_PROTEIN_G_PER_KG["training"]

    for purpose in purposes or []:
        rates = PURPOSE_PROTEIN_G_PER_KG.get(purpose)
        if rates:
            rest_rate = max(rest_rate, rates["rest"])
            training_rate = max(training_rate, rates["training"])

    return {
        "rest": round(weight_kg * rest_rate),
        "training": round(weight_kg * training_rate),
    }


def calculate_fiber_target(purposes):
    """Suggested daily fiber target, in grams, as the highest matching purpose."""
    fiber_target = DEFAULT_FIBER_G_PER_DAY

    for purpose in purposes or []:
        fiber_target = max(fiber_target, PURPOSE_FIBER_G_PER_DAY.get(purpose, fiber_target))

    return fiber_target
