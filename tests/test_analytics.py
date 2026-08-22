import pandas as pd

from analytics import (
    calculate_daily_protein_trend,
    calculate_goal_progress,
    calculate_protein_by_meal,
    calculate_protein_by_source,
    calculate_total_protein,
    get_top_protein_source,
)


def make_food_entries():
    return pd.DataFrame(
        [
            {
                "description": "Chicken breast",
                "protein_grams": 35.0,
                "meal_type": "Lunch",
                "protein_source": "Meat/Poultry",
                "log_date": "2026-08-20",
            },
            {
                "description": "Greek yogurt",
                "protein_grams": 18.0,
                "meal_type": "Breakfast",
                "protein_source": "Dairy",
                "log_date": "2026-08-20",
            },
            {
                "description": "Protein shake",
                "protein_grams": 25.0,
                "meal_type": "Post-workout",
                "protein_source": "Protein powder",
                "log_date": "2026-08-21",
            },
        ]
    )


def test_calculate_total_protein_sums_grams():
    food_entries = make_food_entries()
    assert calculate_total_protein(food_entries) == 78.0


def test_calculate_total_protein_handles_empty():
    empty_entries = pd.DataFrame(columns=["protein_grams"])
    assert calculate_total_protein(empty_entries) == 0.0


def test_calculate_protein_by_source_groups_correctly():
    food_entries = make_food_entries()
    summary = calculate_protein_by_source(food_entries)

    dairy_row = summary[summary["protein_source"] == "Dairy"].iloc[0]
    assert dairy_row["protein_grams"] == 18.0


def test_calculate_protein_by_meal_groups_correctly():
    food_entries = make_food_entries()
    summary = calculate_protein_by_meal(food_entries)

    lunch_row = summary[summary["meal_type"] == "Lunch"].iloc[0]
    assert lunch_row["protein_grams"] == 35.0


def test_calculate_daily_protein_trend_groups_by_date():
    food_entries = make_food_entries()
    trend = calculate_daily_protein_trend(food_entries)

    day_one = trend[trend["log_date"] == "2026-08-20"].iloc[0]
    assert day_one["protein_grams"] == 53.0


def test_calculate_goal_progress_reports_remaining():
    progress = calculate_goal_progress(total_protein_grams=60.0, daily_target_grams=100.0)

    assert progress["remaining_grams"] == 40.0
    assert progress["progress_percent"] == 60.0


def test_calculate_goal_progress_handles_zero_target():
    progress = calculate_goal_progress(total_protein_grams=60.0, daily_target_grams=0.0)

    assert progress["progress_percent"] == 0.0


def test_get_top_protein_source_returns_highest():
    food_entries = make_food_entries()
    summary = calculate_protein_by_source(food_entries)

    assert get_top_protein_source(summary) == "Meat/Poultry"


def test_get_top_protein_source_handles_empty():
    empty_summary = pd.DataFrame(columns=["protein_source", "protein_grams"])
    assert get_top_protein_source(empty_summary) is None
