"""Water and sleep logging calculations: unit conversion and weekly summaries.

Mirrors ``nutrition_targets.py``'s role for the water/sleep logging pages —
pure calculation and conversion, no database or Streamlit imports.
Persistence lives in ``database.py``; the page-level UI lives in
``pages/log_water.py`` and ``pages/log_sleep.py``.
"""

import pandas as pd

from analytics import filter_entries_by_date_range


ML_PER_FL_OZ = 29.5735

# One-click amounts shown as quick-add buttons on the Log Water page.
QUICK_ADD_AMOUNTS_ML = [250, 500]


def convert_to_ml(amount, unit):
    """Convert a water amount in ml or fl oz to milliliters."""
    if amount is None or amount <= 0:
        return None

    if unit == "fl oz":
        return amount * ML_PER_FL_OZ

    return amount


def calculate_water_total(water_entries):
    """Sum amount_ml across the given water entries."""
    if water_entries.empty or "amount_ml" not in water_entries.columns:
        return 0.0

    total = pd.to_numeric(water_entries["amount_ml"], errors="coerce").sum()
    return float(total)


def calculate_daily_water_trend(water_entries):
    """Group water amount by day, one row per logged date."""
    if water_entries.empty:
        return pd.DataFrame(columns=["log_date", "amount_ml"])

    return (
        water_entries.groupby("log_date")["amount_ml"]
        .sum()
        .reset_index()
        .sort_values("log_date")
    )


def summarize_week_water(water_entries, week_start, week_end, daily_target_ml=0.0):
    """Summarise one week of water logging for the weekly dashboard.

    ``days_logged`` counts distinct dates with at least one entry; the
    average is taken over those days, not all seven, matching
    ``analytics.summarize_week``'s approach for food.
    """
    week_entries = filter_entries_by_date_range(water_entries, week_start, week_end)
    total_ml = calculate_water_total(week_entries)

    daily_totals = calculate_daily_water_trend(week_entries)
    days_logged = len(daily_totals)

    average_ml = total_ml / days_logged if days_logged else 0.0

    days_meeting_goal = 0
    if daily_target_ml and daily_target_ml > 0 and days_logged:
        days_meeting_goal = int((daily_totals["amount_ml"] >= daily_target_ml).sum())

    return {
        "week_start": week_start,
        "week_end": week_end,
        "total_ml": total_ml,
        "average_ml": average_ml,
        "daily_totals": daily_totals,
        "days_logged": days_logged,
        "days_meeting_goal": days_meeting_goal,
    }


def summarize_week_sleep(sleep_entries, week_start, week_end, target_hours=0.0):
    """Summarise one week of sleep logging for the weekly dashboard.

    Sleep is already one row per date, so "nights logged" is just the
    filtered row count — no grouping needed.
    """
    week_entries = filter_entries_by_date_range(sleep_entries, week_start, week_end)
    nights_logged = len(week_entries)

    hours = (
        pd.to_numeric(week_entries["hours_slept"], errors="coerce")
        if nights_logged
        else pd.Series(dtype=float)
    )
    total_hours = float(hours.sum()) if nights_logged else 0.0
    average_hours = total_hours / nights_logged if nights_logged else 0.0

    nights_meeting_goal = 0
    if target_hours and target_hours > 0 and nights_logged:
        nights_meeting_goal = int((hours >= target_hours).sum())

    return {
        "week_start": week_start,
        "week_end": week_end,
        "total_hours": total_hours,
        "average_hours": average_hours,
        "nights_logged": nights_logged,
        "nights_meeting_goal": nights_meeting_goal,
    }


def format_ml(amount):
    """Format a number as a milliliter amount for display."""
    return f"{amount:.0f} ml"


def format_hours(amount):
    """Format a number as an hours amount for display."""
    return f"{amount:.1f} h"
