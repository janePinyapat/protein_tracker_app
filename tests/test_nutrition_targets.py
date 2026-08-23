from nutrition_targets import (
    calculate_fiber_target,
    calculate_protein_targets,
    convert_to_kg,
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
