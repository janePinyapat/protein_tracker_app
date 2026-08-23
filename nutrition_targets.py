"""Suggested protein, fiber, and water daily targets from published guidelines.

These are population-level starting points, not a personalized clinical
prescription. They're calculated from body weight and the purpose(s) chosen
on the Profile page, then saved as the Rest day / Training day (and water)
targets — the user can always fine-tune them afterward.

This app is built for women's nutrition, hydration, and recovery tracking.
Where the source guidelines differentiate by sex — fiber and water Adequate
Intakes — the figures published for adult women are used. The protein RDA
and the ISSN exercise range below are not sex-specific in the source
material and are used here as published, applying to everyone.

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
- BMI: calculated as weight (kg) / height (m)^2, and categorized using the
  World Health Organization's standard adult BMI classification (Underweight
  < 18.5, Normal weight 18.5-24.9, Overweight 25-29.9, Obese >= 30). This
  classification is the same for all adults — the WHO does not publish a
  separate scale for women, so none is applied here. BMI is a
  population-level screening measure — it does not account for muscle mass,
  bone density, or fat distribution, so it can be misleading for very
  muscular or very lean individuals. It's shown for general context only.
  There is no validated clinical formula that derives daily water needs
  from BMI, so the water target below is calculated from body weight
  instead, the same way protein and fiber already are.
- Water: 30 mL per kg of body weight per day is a commonly used clinical
  estimate for adult daily fluid needs, within the 25-35 mL/kg/day range
  used in dietetic and clinical practice (e.g. NICE guidance on maintenance
  fluid therapy in adults). The suggestion is floored at approximately
  1.6 L/day — roughly the beverage portion (about 80%) of the European Food
  Safety Authority's Adequate Intake for total water in adult women, 2.0
  L/day total ("Scientific Opinion on Dietary Reference Values for water",
  EFSA NDA Panel, EFSA Journal, 2010). A higher Adequate Intake of 2.7 L/day
  total (about 2.2 L from beverages) is published by the U.S./Canadian
  National Academies ("Dietary Reference Intakes for Water, Potassium,
  Sodium, Chloride, and Sulfate", Institute of Medicine, 2005); the lower,
  still-sourced EFSA figure is used as the floor here so the estimate stays
  responsive to body weight across typical body weights, rather than
  flattening out at a higher one, while still never dropping below that
  published population baseline for women at a very low body weight.

None of this is medical advice. Anyone with a health condition, or who wants
targets tailored to their individual situation, should talk to a registered
dietitian or their doctor.
"""

KG_PER_POUND = 0.45359237
CM_PER_INCH = 2.54

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

BMI_SOURCE_NOTE = (
    "BMI uses the World Health Organization's standard adult classification "
    "(weight in kg divided by height in m, squared) — the same scale for "
    "everyone, since the WHO doesn't publish a separate one for women. It's "
    "a general population screening measure, not a diagnosis — it doesn't "
    "account for muscle mass, bone density, or where the body carries "
    "weight, so it can read misleadingly high for muscular or very active "
    "people. Shown for general context only."
)

WATER_ML_PER_KG_DAY = 30
WOMEN_FLUID_AI_FLOOR_ML = 1600

WATER_SOURCE_NOTE = (
    "Suggested starting point, not medical advice: 30 mL per kg of body "
    "weight per day, a commonly used clinical estimate for adult fluid "
    "needs (within the 25-35 mL/kg/day range used in dietetic practice, "
    "e.g. NICE guidance on maintenance fluid therapy), floored at "
    "approximately 1.6 L/day — roughly the beverage portion (about 80%) of "
    "the European Food Safety Authority's Adequate Intake for total water "
    "in adult women (2.0 L/day total; EFSA NDA Panel, 2010). A higher "
    "Adequate Intake of 2.7 L/day total (about 2.2 L from beverages) is "
    "published by the U.S./Canadian National Academies (Institute of "
    "Medicine, 2005); this app uses the lower, still-sourced EFSA figure as "
    "the floor so the weight-based estimate stays responsive across typical "
    "body weights instead of flattening out. There is no validated clinical "
    "formula linking water needs to BMI, so this is calculated from body "
    "weight instead, the same way protein and fiber are. Talk to a "
    "registered dietitian or your doctor for targets tailored to you, "
    "especially with a heart, kidney, or other condition that affects "
    "fluid needs."
)

BMI_CATEGORIES = [
    (18.5, "Underweight"),
    (25.0, "Normal weight"),
    (30.0, "Overweight"),
]
BMI_CATEGORY_ABOVE_ALL_THRESHOLDS = "Obese"


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


def convert_to_cm(height_value, height_unit):
    """Convert a height in cm or inches to centimeters."""
    if height_value is None or height_value <= 0:
        return None

    if height_unit == "in":
        return height_value * CM_PER_INCH

    return height_value


def calculate_bmi(weight_kg, height_cm):
    """Body Mass Index: weight (kg) / height (m) squared, rounded to 1 decimal."""
    if weight_kg is None or weight_kg <= 0 or height_cm is None or height_cm <= 0:
        return None

    height_m = height_cm / 100
    return round(weight_kg / (height_m**2), 1)


def calculate_water_target_ml(weight_kg):
    """Suggested daily water target, in ml, from body weight.

    30 mL/kg/day, floored at the beverage portion of the NASEM Adequate
    Intake for adult women (~2200 ml) so the suggestion never drops below
    the published population baseline at a lower body weight.
    """
    if weight_kg is None or weight_kg <= 0:
        return None

    return max(round(weight_kg * WATER_ML_PER_KG_DAY), WOMEN_FLUID_AI_FLOOR_ML)


def get_bmi_category(bmi):
    """WHO standard adult BMI category label for a calculated BMI value."""
    if bmi is None:
        return None

    for threshold, label in BMI_CATEGORIES:
        if bmi < threshold:
            return label

    return BMI_CATEGORY_ABOVE_ALL_THRESHOLDS
