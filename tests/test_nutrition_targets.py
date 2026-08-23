from nutrition_targets import (
    WOMEN_FLUID_AI_FLOOR_ML,
    calculate_bmi,
    calculate_fiber_target,
    calculate_protein_targets,
    calculate_water_target_ml,
    convert_to_cm,
    convert_to_kg,
    get_bmi_category,
)


def test_convert_to_kg_passes_through_kg():
    assert convert_to_kg(70.0, "kg") == 70.0


def test_convert_to_kg_converts_pounds():
    # 154 lb is approximately 69.85 kg
    assert round(convert_to_kg(154.0, "lb"), 2) == 69.85


def test_convert_to_kg_handles_none():
    assert convert_to_kg(None, "kg") is None


def test_convert_to_kg_handles_zero_or_negative():
    assert convert_to_kg(0, "kg") is None
    assert convert_to_kg(-5, "kg") is None


def test_calculate_protein_targets_returns_none_without_weight():
    assert calculate_protein_targets(None, ["General health tracking"]) is None
    assert calculate_protein_targets(0, ["General health tracking"]) is None


def test_calculate_protein_targets_uses_general_health_rate():
    # 70 kg x 1.0 g/kg (general health) for both rest and training
    targets = calculate_protein_targets(70.0, ["General health tracking"])
    assert targets == {"rest": 70, "training": 70}


def test_calculate_protein_targets_uses_strength_training_rate():
    # 70 kg x 1.4 g/kg rest, x 1.8 g/kg training
    targets = calculate_protein_targets(70.0, ["Strength training / muscle recovery"])
    assert targets == {"rest": 98, "training": 126}


def test_calculate_protein_targets_uses_pcos_rate():
    # 70 kg x 1.2 g/kg both days
    targets = calculate_protein_targets(70.0, ["PCOS management"])
    assert targets == {"rest": 84, "training": 84}


def test_calculate_protein_targets_falls_back_to_rda_for_unrecognized_purpose():
    # 70 kg x 0.8 g/kg (RDA baseline) both days
    targets = calculate_protein_targets(70.0, ["Something not in the list"])
    assert targets == {"rest": 56, "training": 56}


def test_calculate_protein_targets_takes_the_higher_rate_across_purposes():
    """PCOS + strength training should get the strength-training rate, not
    an average that could undershoot muscle-building needs."""
    targets = calculate_protein_targets(
        70.0, ["PCOS management", "Strength training / muscle recovery"]
    )
    assert targets == {"rest": 98, "training": 126}


def test_calculate_protein_targets_handles_empty_purposes():
    # No purposes at all falls back to the RDA baseline.
    targets = calculate_protein_targets(70.0, [])
    assert targets == {"rest": 56, "training": 56}


def test_calculate_fiber_target_default_is_25():
    assert calculate_fiber_target(["General health tracking"]) == 25
    assert calculate_fiber_target([]) == 25


def test_calculate_fiber_target_pcos_is_30():
    assert calculate_fiber_target(["PCOS management"]) == 30


def test_calculate_fiber_target_takes_the_higher_value_across_purposes():
    fiber = calculate_fiber_target(
        ["General health tracking", "PCOS management"]
    )
    assert fiber == 30


def test_convert_to_cm_passes_through_cm():
    assert convert_to_cm(175.0, "cm") == 175.0


def test_convert_to_cm_converts_inches():
    # 70 in is exactly 177.8 cm
    assert round(convert_to_cm(70.0, "in"), 1) == 177.8


def test_convert_to_cm_handles_none_and_non_positive():
    assert convert_to_cm(None, "cm") is None
    assert convert_to_cm(0, "cm") is None
    assert convert_to_cm(-1, "cm") is None


def test_calculate_bmi_matches_known_value():
    # 70 kg at 175 cm is a BMI of 22.9 (WHO formula: kg / m^2)
    assert calculate_bmi(70.0, 175.0) == 22.9


def test_calculate_bmi_returns_none_without_both_measurements():
    assert calculate_bmi(None, 175.0) is None
    assert calculate_bmi(70.0, None) is None
    assert calculate_bmi(70.0, 0) is None


def test_get_bmi_category_underweight():
    assert get_bmi_category(17.0) == "Underweight"


def test_get_bmi_category_normal_weight_including_boundary():
    assert get_bmi_category(18.5) == "Normal weight"
    assert get_bmi_category(24.9) == "Normal weight"


def test_get_bmi_category_overweight_including_boundary():
    assert get_bmi_category(25.0) == "Overweight"
    assert get_bmi_category(29.9) == "Overweight"


def test_get_bmi_category_obese_including_boundary():
    assert get_bmi_category(30.0) == "Obese"
    assert get_bmi_category(40.0) == "Obese"


def test_get_bmi_category_handles_none():
    assert get_bmi_category(None) is None


def test_calculate_water_target_ml_scales_with_weight():
    # 80 kg x 30 mL/kg = 2400 ml, above the women's AI floor
    assert calculate_water_target_ml(80.0) == 2400


def test_calculate_water_target_ml_floors_at_womens_ai_for_light_weight():
    # 50 kg x 30 mL/kg = 1500 ml, below the floor, so the floor wins
    assert calculate_water_target_ml(50.0) == WOMEN_FLUID_AI_FLOOR_ML


def test_calculate_water_target_ml_returns_none_without_weight():
    assert calculate_water_target_ml(None) is None
    assert calculate_water_target_ml(0) is None
    assert calculate_water_target_ml(-5) is None
