def calculate_total_protein(food_entries):
    """Calculate total protein grams across the given entries."""
    if food_entries.empty:
        return 0.0
    return float(food_entries["protein_grams"].sum())


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


def format_grams(amount):
    """Format a number as a grams amount for display."""
    return f"{amount:.0f} g"
