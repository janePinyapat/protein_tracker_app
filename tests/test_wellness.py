from datetime import date

import pandas as pd

from wellness import (
    QUICK_ADD_AMOUNTS_ML,
    calculate_daily_water_trend,
    calculate_water_total,
    convert_to_ml,
    format_hours,
    format_ml,
    summarize_week_sleep,
    summarize_week_water,
)


def make_water_entries():
    return pd.DataFrame(
        [
            {"id": 1, "amount_ml": 250.0, "log_date": "2026-08-17"},
            {"id": 2, "amount_ml": 500.0, "log_date": "2026-08-17"},
            {"id": 3, "amount_ml": 300.0, "log_date": "2026-08-19"},
        ]
    )


def make_sleep_entries():
    return pd.DataFrame(
        [
            {"id": 1, "log_date": "2026-08-17", "hours_slept": 7.5, "notes": None},
            {"id": 2, "log_date": "2026-08-19", "hours_slept": 6.0, "notes": "Woke up early"},
        ]
    )


def test_convert_to_ml_passes_through_ml():
    assert convert_to_ml(250.0, "ml") == 250.0


def test_convert_to_ml_converts_fl_oz():
    # 8 fl oz is about 236.6 ml
    assert round(convert_to_ml(8.0, "fl oz"), 1) == 236.6


def test_convert_to_ml_handles_none_and_non_positive():
    assert convert_to_ml(None, "ml") is None
    assert convert_to_ml(0, "ml") is None
    assert convert_to_ml(-5, "ml") is None


def test_quick_add_amounts_are_positive_and_sorted():
    assert QUICK_ADD_AMOUNTS_ML == sorted(QUICK_ADD_AMOUNTS_ML)
    assert all(amount > 0 for amount in QUICK_ADD_AMOUNTS_ML)


def test_calculate_water_total_sums_amounts():
    assert calculate_water_total(make_water_entries()) == 1050.0


def test_calculate_water_total_handles_empty():
    empty_entries = pd.DataFrame(columns=["amount_ml"])
    assert calculate_water_total(empty_entries) == 0.0


def test_calculate_daily_water_trend_groups_by_date():
    trend = calculate_daily_water_trend(make_water_entries())

    day_one = trend[trend["log_date"] == "2026-08-17"].iloc[0]
    assert day_one["amount_ml"] == 750.0


def test_calculate_daily_water_trend_handles_empty():
    empty_entries = pd.DataFrame(columns=["log_date", "amount_ml"])
    assert calculate_daily_water_trend(empty_entries).empty


def test_summarize_week_water_averages_over_logged_days_only():
    summary = summarize_week_water(
        make_water_entries(), date(2026, 8, 17), date(2026, 8, 23), daily_target_ml=1000.0
    )

    assert summary["days_logged"] == 2
    assert summary["total_ml"] == 1050.0
    assert summary["average_ml"] == 525.0


def test_summarize_week_water_counts_days_meeting_goal():
    summary = summarize_week_water(
        make_water_entries(), date(2026, 8, 17), date(2026, 8, 23), daily_target_ml=500.0
    )

    assert summary["days_meeting_goal"] == 1  # only the 750ml day meets 500ml


def test_summarize_week_water_handles_no_entries():
    empty_entries = pd.DataFrame(columns=["id", "amount_ml", "log_date"])
    summary = summarize_week_water(
        empty_entries, date(2026, 8, 17), date(2026, 8, 23), daily_target_ml=1000.0
    )

    assert summary["days_logged"] == 0
    assert summary["average_ml"] == 0.0
    assert summary["days_meeting_goal"] == 0


def test_summarize_week_sleep_averages_over_logged_nights_only():
    summary = summarize_week_sleep(
        make_sleep_entries(), date(2026, 8, 17), date(2026, 8, 23), target_hours=8.0
    )

    assert summary["nights_logged"] == 2
    assert summary["total_hours"] == 13.5
    assert summary["average_hours"] == 6.75


def test_summarize_week_sleep_counts_nights_meeting_goal():
    summary = summarize_week_sleep(
        make_sleep_entries(), date(2026, 8, 17), date(2026, 8, 23), target_hours=7.0
    )

    assert summary["nights_meeting_goal"] == 1  # only the 7.5h night meets 7h


def test_summarize_week_sleep_handles_no_entries():
    empty_entries = pd.DataFrame(columns=["id", "log_date", "hours_slept", "notes"])
    summary = summarize_week_sleep(
        empty_entries, date(2026, 8, 17), date(2026, 8, 23), target_hours=8.0
    )

    assert summary["nights_logged"] == 0
    assert summary["average_hours"] == 0.0
    assert summary["nights_meeting_goal"] == 0


def test_format_ml():
    assert format_ml(1250.4) == "1250 ml"


def test_format_hours():
    assert format_hours(7.25) == "7.2 h"
