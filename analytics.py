from datetime import date, timedelta

import pandas as pd


# Macro columns tracked per entry. Calories are kept separate because they are
# a total rather than a macro.
MACRO_COLUMNS = ["protein_grams", "carbs_grams", "fat_grams", "fiber_grams"]

MACRO_LABELS = {
    "protein_grams": "Protein",
    "carbs_grams": "Carbs",
    "fat_grams": "Fat",
    "fiber_grams": "Fiber",
}

# Atwater factors, used only to show how a day's calories split across macros.
CALORIES_PER_GRAM = {"protein_grams": 4, "carbs_grams": 4, "fat_grams": 9}


def column_sum(food_entries, column_name):
    """Sum one column, treating a missing column or missing values as zero.

    Entries saved by the protein-only version have no macro values, so the
    macro columns are frequently partly empty.
    """
    if food_entries.empty or column_name not in food_entries.columns:
        return 0.0

    total = pd.to_numeric(food_entries[column_name], errors="coerce").sum()
    return float(total)


def calculate_total_protein(food_entries):
    """Calculate total protein grams across the given entries."""
    return column_sum(food_entries, "protein_grams")


def calculate_macro_totals(food_entries):
    """Total each macro plus calories across the given entries."""
    totals = {column: column_sum(food_entries, column) for column in MACRO_COLUMNS}
    totals["calories"] = column_sum(food_entries, "calories")
    return totals


def calculate_macro_calorie_split(food_entries):
    """Split calories across protein, carbs, and fat for a composition chart.

    Fiber is left out because it is already counted inside total carbohydrate.
    """
    rows = []
    for column, calories_per_gram in CALORIES_PER_GRAM.items():
        grams = column_sum(food_entries, column)
        rows.append(
            {
                "macro": MACRO_LABELS[column],
                "grams": grams,
                "calories": grams * calories_per_gram,
            }
        )

    split = pd.DataFrame(rows)
    if split["calories"].sum() <= 0:
        return split.iloc[0:0]

    split["percent"] = split["calories"] / split["calories"].sum() * 100
    return split


def calculate_protein_by_source(food_entries):
    """Group protein grams by protein source for chart display."""
    if food_entries.empty:
        return food_entries

    return (
        food_entries.groupby("protein_source")["protein_grams"]
        .sum()
        .reset_index()
        .sort_values("protein_grams", ascending=False)
    )


def calculate_protein_by_meal(food_entries):
    """Group protein grams by meal type for chart display."""
    if food_entries.empty:
        return food_entries

    return (
        food_entries.groupby("meal_type")["protein_grams"]
        .sum()
        .reset_index()
        .sort_values("protein_grams", ascending=False)
    )


def calculate_macros_by_meal(food_entries):
    """Group every macro by meal type, in long form for a grouped bar chart."""
    if food_entries.empty:
        return pd.DataFrame(columns=["meal_type", "macro", "grams"])

    available = [
        column for column in MACRO_COLUMNS if column in food_entries.columns
    ]
    grouped = (
        food_entries.groupby("meal_type")[available]
        .sum()
        .reset_index()
        .melt(id_vars="meal_type", var_name="macro", value_name="grams")
    )
    grouped["macro"] = grouped["macro"].map(MACRO_LABELS)
    return grouped


def calculate_daily_protein_trend(food_entries):
    """Group protein grams by day for a trend chart."""
    if food_entries.empty:
        return food_entries

    return (
        food_entries.groupby("log_date")["protein_grams"]
        .sum()
        .reset_index()
        .sort_values("log_date")
    )


def calculate_daily_macro_trend(food_entries):
    """Group every macro by day, one row per logged date."""
    if food_entries.empty:
        return pd.DataFrame(columns=["log_date"] + MACRO_COLUMNS)

    available = [
        column for column in MACRO_COLUMNS if column in food_entries.columns
    ]
    return (
        food_entries.groupby("log_date")[available]
        .sum()
        .reset_index()
        .sort_values("log_date")
    )


def calculate_goal_progress(total_protein_grams, daily_target_grams):
    """Compare protein consumed so far against the daily target."""
    if daily_target_grams <= 0:
        return {
            "total_protein_grams": total_protein_grams,
            "daily_target_grams": daily_target_grams,
            "remaining_grams": 0.0,
            "progress_percent": 0.0,
        }

    remaining_grams = daily_target_grams - total_protein_grams
    progress_percent = (total_protein_grams / daily_target_grams) * 100

    return {
        "total_protein_grams": total_protein_grams,
        "daily_target_grams": daily_target_grams,
        "remaining_grams": remaining_grams,
        "progress_percent": progress_percent,
    }


def get_top_protein_source(protein_by_source):
    """Return the protein source contributing the most protein."""
    if protein_by_source.empty:
        return None
    top_row = protein_by_source.iloc[0]
    return top_row["protein_source"]


def explode_tags(food_entries):
    """Return one row per (entry, tag) pair.

    Tags arrive from the database joined into a single comma-separated column,
    so they are split back out before any tag grouping. Entries with no tags
    are dropped.
    """
    empty = pd.DataFrame(columns=["tag"] + MACRO_COLUMNS)

    if food_entries.empty or "tags" not in food_entries.columns:
        return empty

    exploded = food_entries.copy()
    exploded["tag"] = (
        exploded["tags"].fillna("").astype(str).str.split(",")
    )
    exploded = exploded.explode("tag")
    exploded["tag"] = exploded["tag"].str.strip()
    exploded = exploded[exploded["tag"] != ""]

    if exploded.empty:
        return empty

    return exploded


def calculate_tag_totals(food_entries):
    """Count entries and total macros per tag the user applied."""
    exploded = explode_tags(food_entries)

    if exploded.empty:
        return pd.DataFrame(columns=["tag", "entries", "protein_grams", "fiber_grams"])

    available = [column for column in MACRO_COLUMNS if column in exploded.columns]

    totals = exploded.groupby("tag")[available].sum().reset_index()
    totals["entries"] = exploded.groupby("tag").size().reset_index(name="n")["n"]

    return totals.sort_values("entries", ascending=False).reset_index(drop=True)


def get_week_bounds(reference_date):
    """Return the Monday and Sunday bounding the week of the given date."""
    if isinstance(reference_date, str):
        reference_date = date.fromisoformat(reference_date)

    week_start = reference_date - timedelta(days=reference_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def filter_entries_by_date_range(food_entries, start_date, end_date):
    """Keep only entries whose log_date falls inside the inclusive range."""
    if food_entries.empty or "log_date" not in food_entries.columns:
        return food_entries

    start_text = start_date.isoformat()
    end_text = end_date.isoformat()

    log_dates = food_entries["log_date"].astype(str)
    return food_entries[(log_dates >= start_text) & (log_dates <= end_text)]


def summarize_week(food_entries, week_start, week_end, daily_target_grams=0.0):
    """Summarise one week of entries for the weekly dashboard.

    ``days_logged`` counts distinct dates that have at least one entry, and
    averages are taken over those days rather than over all seven, so a
    partly-logged week is not reported as low intake.
    """
    week_entries = filter_entries_by_date_range(food_entries, week_start, week_end)
    totals = calculate_macro_totals(week_entries)

    daily_totals = calculate_daily_macro_trend(week_entries)
    days_logged = len(daily_totals)

    averages = {
        column: (totals[column] / days_logged if days_logged else 0.0)
        for column in MACRO_COLUMNS
    }
    averages["calories"] = totals["calories"] / days_logged if days_logged else 0.0

    days_meeting_goal = 0
    if daily_target_grams > 0 and days_logged:
        days_meeting_goal = int(
            (daily_totals["protein_grams"] >= daily_target_grams).sum()
        )

    return {
        "week_start": week_start,
        "week_end": week_end,
        "entries": week_entries,
        "totals": totals,
        "averages": averages,
        "daily_totals": daily_totals,
        "days_logged": days_logged,
        "days_meeting_goal": days_meeting_goal,
    }


def build_full_week_frame(daily_totals, week_start):
    """Pad a week's daily totals so every day Monday to Sunday has a row."""
    all_days = pd.DataFrame(
        {
            "log_date": [
                (week_start + timedelta(days=offset)).isoformat()
                for offset in range(7)
            ]
        }
    )

    if daily_totals.empty:
        for column in MACRO_COLUMNS:
            all_days[column] = 0.0
    else:
        totals = daily_totals.copy()
        totals["log_date"] = totals["log_date"].astype(str)
        all_days = all_days.merge(totals, on="log_date", how="left").fillna(0.0)

    all_days["day_name"] = pd.to_datetime(all_days["log_date"]).dt.strftime("%a")
    return all_days


def format_grams(amount):
    """Format a number as a grams amount for display."""
    return f"{amount:.0f} g"


def format_calories(amount):
    """Format a number as a calorie amount for display."""
    return f"{amount:.0f} kcal"
