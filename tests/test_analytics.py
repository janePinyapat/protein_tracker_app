from datetime import date

import pandas as pd

from analytics import (
    build_full_week_frame,
    calculate_daily_macro_trend,
    calculate_daily_protein_trend,
    calculate_goal_progress,
    calculate_macro_calorie_split,
    calculate_macro_totals,
    calculate_macros_by_meal,
    calculate_protein_by_meal,
    calculate_protein_by_source,
    calculate_remaining_targets,
    calculate_tag_totals,
    calculate_total_protein,
    explode_tags,
    filter_entries_by_date_range,
    get_top_protein_source,
    get_week_bounds,
    summarize_week,
)


def make_food_entries():
    return pd.DataFrame(
        [
            {
                "description": "Chicken breast",
                "protein_grams": 35.0,
                "carbs_grams": 0.0,
                "fat_grams": 12.0,
                "fiber_grams": 0.0,
                "calories": 280.0,
                "meal_type": "Lunch",
                "protein_source": "Meat/Poultry",
                "log_date": "2026-08-20",
                "tags": "Home cooked, Low glycemic",
            },
            {
                "description": "Greek yogurt",
                "protein_grams": 18.0,
                "carbs_grams": 9.0,
                "fat_grams": 4.0,
                "fiber_grams": 0.0,
                "calories": 150.0,
                "meal_type": "Breakfast",
                "protein_source": "Dairy",
                "log_date": "2026-08-20",
                "tags": "Dairy, Low glycemic",
            },
            {
                "description": "Lentil soup",
                "protein_grams": 25.0,
                "carbs_grams": 30.0,
                "fat_grams": 4.0,
                "fiber_grams": 11.0,
                "calories": 220.0,
                "meal_type": "Post-workout",
                "protein_source": "Protein powder",
                "log_date": "2026-08-21",
                "tags": "High fiber",
            },
        ]
    )


def test_calculate_total_protein_sums_grams():
    food_entries = make_food_entries()
    assert calculate_total_protein(food_entries) == 78.0


def test_calculate_total_protein_handles_empty():
    empty_entries = pd.DataFrame(columns=["protein_grams"])
    assert calculate_total_protein(empty_entries) == 0.0


def test_calculate_macro_totals_sums_every_macro():
    totals = calculate_macro_totals(make_food_entries())

    assert totals["protein_grams"] == 78.0
    assert totals["carbs_grams"] == 39.0
    assert totals["fat_grams"] == 20.0
    assert totals["fiber_grams"] == 11.0
    assert totals["calories"] == 650.0


def test_calculate_macro_totals_ignores_missing_macro_values():
    """Entries saved before macros existed have empty macro columns."""
    legacy_entries = pd.DataFrame(
        [
            {"protein_grams": 20.0, "carbs_grams": None, "fat_grams": None},
            {"protein_grams": 10.0, "carbs_grams": 5.0, "fat_grams": None},
        ]
    )
    totals = calculate_macro_totals(legacy_entries)

    assert totals["protein_grams"] == 30.0
    assert totals["carbs_grams"] == 5.0
    assert totals["fiber_grams"] == 0.0


def test_calculate_macro_calorie_split_uses_atwater_factors():
    split = calculate_macro_calorie_split(make_food_entries())

    fat_row = split[split["macro"] == "Fat"].iloc[0]
    assert fat_row["calories"] == 180.0

    protein_row = split[split["macro"] == "Protein"].iloc[0]
    assert protein_row["calories"] == 312.0


def test_calculate_macro_calorie_split_handles_no_macros():
    empty_entries = pd.DataFrame(columns=["protein_grams", "carbs_grams", "fat_grams"])
    assert calculate_macro_calorie_split(empty_entries).empty


def test_calculate_protein_by_source_groups_correctly():
    summary = calculate_protein_by_source(make_food_entries())

    dairy_row = summary[summary["protein_source"] == "Dairy"].iloc[0]
    assert dairy_row["protein_grams"] == 18.0


def test_calculate_protein_by_meal_groups_correctly():
    summary = calculate_protein_by_meal(make_food_entries())

    lunch_row = summary[summary["meal_type"] == "Lunch"].iloc[0]
    assert lunch_row["protein_grams"] == 35.0


def test_calculate_macros_by_meal_returns_long_form():
    summary = calculate_macros_by_meal(make_food_entries())

    lunch_fat = summary[
        (summary["meal_type"] == "Lunch") & (summary["macro"] == "Fat")
    ].iloc[0]
    assert lunch_fat["grams"] == 12.0


def test_calculate_daily_protein_trend_groups_by_date():
    trend = calculate_daily_protein_trend(make_food_entries())

    day_one = trend[trend["log_date"] == "2026-08-20"].iloc[0]
    assert day_one["protein_grams"] == 53.0


def test_calculate_daily_macro_trend_groups_every_macro():
    trend = calculate_daily_macro_trend(make_food_entries())

    day_one = trend[trend["log_date"] == "2026-08-20"].iloc[0]
    assert day_one["carbs_grams"] == 9.0
    assert day_one["fat_grams"] == 16.0


def test_calculate_goal_progress_reports_remaining():
    progress = calculate_goal_progress(total_protein_grams=60.0, daily_target_grams=100.0)

    assert progress["remaining_grams"] == 40.0
    assert progress["progress_percent"] == 60.0


def test_calculate_goal_progress_handles_zero_target():
    progress = calculate_goal_progress(total_protein_grams=60.0, daily_target_grams=0.0)

    assert progress["progress_percent"] == 0.0


def test_get_top_protein_source_returns_highest():
    summary = calculate_protein_by_source(make_food_entries())
    assert get_top_protein_source(summary) == "Meat/Poultry"


def test_get_top_protein_source_handles_empty():
    empty_summary = pd.DataFrame(columns=["protein_source", "protein_grams"])
    assert get_top_protein_source(empty_summary) is None


def test_explode_tags_splits_comma_separated_labels():
    exploded = explode_tags(make_food_entries())

    assert len(exploded) == 5
    assert set(exploded["tag"]) == {
        "Home cooked",
        "Low glycemic",
        "Dairy",
        "High fiber",
    }


def test_explode_tags_drops_entries_without_labels():
    entries = pd.DataFrame(
        [
            {"protein_grams": 10.0, "tags": ""},
            {"protein_grams": 20.0, "tags": "Home cooked"},
        ]
    )
    exploded = explode_tags(entries)

    assert list(exploded["tag"]) == ["Home cooked"]


def test_explode_tags_handles_missing_column():
    entries = pd.DataFrame([{"protein_grams": 10.0}])
    assert explode_tags(entries).empty


def test_calculate_tag_totals_counts_entries_per_label():
    totals = calculate_tag_totals(make_food_entries())

    low_glycemic = totals[totals["tag"] == "Low glycemic"].iloc[0]
    assert low_glycemic["entries"] == 2
    assert low_glycemic["protein_grams"] == 53.0


def test_calculate_tag_totals_sorts_by_entry_count():
    totals = calculate_tag_totals(make_food_entries())
    assert totals.iloc[0]["tag"] == "Low glycemic"


def test_get_week_bounds_returns_monday_to_sunday():
    week_start, week_end = get_week_bounds(date(2026, 8, 20))

    assert week_start == date(2026, 8, 17)
    assert week_end == date(2026, 8, 23)


def test_get_week_bounds_accepts_iso_string():
    week_start, _ = get_week_bounds("2026-08-20")
    assert week_start == date(2026, 8, 17)


def test_get_week_bounds_on_a_monday_returns_that_monday():
    week_start, _ = get_week_bounds(date(2026, 8, 17))
    assert week_start == date(2026, 8, 17)


def test_filter_entries_by_date_range_is_inclusive():
    filtered = filter_entries_by_date_range(
        make_food_entries(), date(2026, 8, 21), date(2026, 8, 21)
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["description"] == "Lentil soup"


def test_summarize_week_averages_over_logged_days_only():
    summary = summarize_week(
        make_food_entries(),
        date(2026, 8, 17),
        date(2026, 8, 23),
        daily_target_grams=50.0,
    )

    assert summary["days_logged"] == 2
    assert summary["totals"]["protein_grams"] == 78.0
    assert summary["averages"]["protein_grams"] == 39.0


def test_summarize_week_counts_days_meeting_goal():
    summary = summarize_week(
        make_food_entries(),
        date(2026, 8, 17),
        date(2026, 8, 23),
        daily_target_grams=50.0,
    )

    assert summary["days_meeting_goal"] == 1


def test_summarize_week_handles_week_with_no_entries():
    summary = summarize_week(
        make_food_entries(),
        date(2026, 9, 7),
        date(2026, 9, 13),
        daily_target_grams=90.0,
    )

    assert summary["days_logged"] == 0
    assert summary["averages"]["protein_grams"] == 0.0
    assert summary["days_meeting_goal"] == 0


def test_build_full_week_frame_pads_missing_days():
    trend = calculate_daily_macro_trend(make_food_entries())
    week_frame = build_full_week_frame(trend, date(2026, 8, 17))

    assert len(week_frame) == 7

    monday = week_frame[week_frame["log_date"] == "2026-08-17"].iloc[0]
    assert monday["protein_grams"] == 0.0

    thursday = week_frame[week_frame["log_date"] == "2026-08-20"].iloc[0]
    assert thursday["protein_grams"] == 53.0


def test_build_full_week_frame_handles_empty_week():
    empty_trend = pd.DataFrame(columns=["log_date", "protein_grams"])
    week_frame = build_full_week_frame(empty_trend, date(2026, 8, 17))

    assert len(week_frame) == 7
    assert week_frame["protein_grams"].sum() == 0.0
    assert list(week_frame["day_name"])[0] == "Mon"


def test_calculate_remaining_targets_subtracts_logged_amounts():
    remaining = calculate_remaining_targets(100.0, 25.0, 60.0, 10.0)
    assert remaining == {"protein_grams": 40.0, "fiber_grams": 15.0}


def test_calculate_remaining_targets_floors_at_zero_when_target_exceeded():
    remaining = calculate_remaining_targets(100.0, 25.0, 150.0, 40.0)
    assert remaining == {"protein_grams": 0.0, "fiber_grams": 0.0}


def test_calculate_remaining_targets_handles_no_logged_food():
    remaining = calculate_remaining_targets(100.0, 25.0, 0.0, 0.0)
    assert remaining == {"protein_grams": 100.0, "fiber_grams": 25.0}


def test_calculate_remaining_targets_handles_none_inputs():
    remaining = calculate_remaining_targets(None, None, None, None)
    assert remaining == {"protein_grams": 0.0, "fiber_grams": 0.0}
