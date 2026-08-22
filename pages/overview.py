from datetime import date

import plotly.express as px
import streamlit as st

from analytics import (
    calculate_daily_protein_trend,
    calculate_goal_progress,
    calculate_protein_by_meal,
    calculate_protein_by_source,
    calculate_total_protein,
    format_grams,
)
from database import (
    create_food_log_table,
    create_protein_goals_table,
    get_all_food_entries,
    get_protein_goals,
)


DAY_TYPES = ["Rest day", "Training day"]


def create_source_chart(protein_by_source):
    """Create a donut chart of protein grams by source."""
    chart = px.pie(
        protein_by_source,
        names="protein_source",
        values="protein_grams",
        title="Protein by Source",
        hole=0.45,
    )
    chart.update_traces(
        textinfo="label+percent",
        hovertemplate="%{label}<br>%{value:.0f} g<br>%{percent}<extra></extra>",
    )
    return chart


def create_meal_chart(protein_by_meal):
    """Create a bar chart of protein grams by meal."""
    chart = px.bar(
        protein_by_meal,
        x="meal_type",
        y="protein_grams",
        title="Protein by Meal",
    )
    chart.update_traces(hovertemplate="%{x}<br>%{y:.0f} g<extra></extra>")
    chart.update_layout(xaxis_title=None, yaxis_title="Protein (g)")
    return chart


def create_trend_chart(daily_trend, daily_target_grams):
    """Create a line chart of daily protein intake against the goal."""
    chart = px.line(
        daily_trend,
        x="log_date",
        y="protein_grams",
        title="Daily Protein Trend",
        markers=True,
    )
    chart.add_hline(
        y=daily_target_grams,
        line_dash="dash",
        line_color="#2e8b57",
        annotation_text="Goal",
    )
    chart.update_layout(xaxis_title=None, yaxis_title="Protein (g)")
    return chart


create_food_log_table()
create_protein_goals_table()

st.title("Overview")
st.write("Track daily protein intake against your recovery goal.")

food_entries = get_all_food_entries()
goals = get_protein_goals()

filter_column_one, filter_column_two = st.columns(2)

with filter_column_one:
    selected_date = st.date_input("Date", value=date.today())

with filter_column_two:
    selected_day_type = st.selectbox("Day type", DAY_TYPES)

daily_target_grams = 0.0
if not goals.empty:
    matching_goal = goals[goals["day_type"] == selected_day_type]
    if not matching_goal.empty:
        daily_target_grams = float(matching_goal.iloc[0]["daily_target_grams"])

todays_entries = food_entries[
    food_entries["log_date"] == selected_date.isoformat()
]
total_protein = calculate_total_protein(todays_entries)
progress = calculate_goal_progress(total_protein, daily_target_grams)

metric_column_one, metric_column_two, metric_column_three = st.columns(3)

with metric_column_one:
    st.metric("Protein so far", format_grams(progress["total_protein_grams"]))

with metric_column_two:
    st.metric("Daily target", format_grams(progress["daily_target_grams"]))

with metric_column_three:
    st.metric("Remaining", format_grams(max(progress["remaining_grams"], 0.0)))

if daily_target_grams <= 0:
    st.info("Set a protein goal on the Set Protein Goal page to see progress.")
else:
    st.progress(min(progress["progress_percent"] / 100, 1.0))

st.subheader("Overview charts")

chart_column_one, chart_column_two = st.columns(2)

protein_by_source = calculate_protein_by_source(todays_entries)
protein_by_meal = calculate_protein_by_meal(todays_entries)

with chart_column_one:
    if protein_by_source.empty:
        st.info("No food logged for this date yet.")
    else:
        st.plotly_chart(
            create_source_chart(protein_by_source), use_container_width=True
        )

with chart_column_two:
    if protein_by_meal.empty:
        st.info("No food logged for this date yet.")
    else:
        st.plotly_chart(
            create_meal_chart(protein_by_meal), use_container_width=True
        )

st.subheader("Trend")

daily_trend = calculate_daily_protein_trend(food_entries)

if daily_trend.empty:
    st.info("Log food on the Log Food page to build a trend.")
else:
    st.plotly_chart(
        create_trend_chart(daily_trend, daily_target_grams),
        use_container_width=True,
    )
