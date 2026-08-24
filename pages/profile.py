import pandas as pd
import streamlit as st

from database import get_protein_goals, get_user_profile, get_wellness_goals
from nutrition_targets import (
    BMI_SOURCE_NOTE,
    SOURCES_NOTE,
    WATER_SOURCE_NOTE,
    calculate_bmi,
    convert_to_cm,
    convert_to_kg,
    get_bmi_category,
)
from user_profile import DIET_TYPES, PURPOSES, save_profile_and_targets
from wellness import format_hours, format_ml


st.title("Profile")
st.caption(
    "Built for women's nutrition, hydration, sleep, and recovery — "
    "protein, fiber, and water targets use guidelines published for women "
    "wherever the source differentiates by sex."
)
st.write(
    "Your diet type and purpose affect which labels are suggested first "
    "when you log food — nothing is hidden. If you add your weight, the "
    "app also suggests Rest day / Training day protein and fiber targets, "
    "and a daily water target, calculated from published guidelines (not a "
    "personalized medical recommendation). Adding your height too shows "
    "your BMI as general context. Saving here updates your daily targets; "
    "you can still fine-tune protein/fiber on the Meal Recommendations page "
    "and water on the Log Water page."
)

profile = get_user_profile()
default_diet_type = profile["diet_type"] if profile else DIET_TYPES[0]
default_purposes = profile["purposes"] if profile else []
default_weight_value = profile["weight_value"] if profile else None
default_weight_unit = profile["weight_unit"] if profile else "kg"
default_height_value = profile["height_value"] if profile else None
default_height_unit = profile["height_unit"] if profile else "cm"

with st.form("profile_form"):
    diet_type = st.radio(
        "Which best describes your diet?",
        DIET_TYPES,
        index=DIET_TYPES.index(default_diet_type)
        if default_diet_type in DIET_TYPES
        else 0,
    )

    purposes = st.multiselect(
        "What are you using this tracker for?",
        options=PURPOSES,
        default=[purpose for purpose in default_purposes if purpose in PURPOSES],
    )

    weight_column, weight_unit_column = st.columns([2, 1])

    with weight_column:
        weight_value = st.number_input(
            "Your weight (optional)",
            min_value=0.0,
            step=0.5,
            value=float(default_weight_value) if default_weight_value else 0.0,
            help=(
                "Used to calculate suggested protein and fiber targets, and "
                "(with height) your BMI. Leave at 0 to skip."
            ),
        )

    with weight_unit_column:
        weight_unit = st.selectbox(
            "Weight unit",
            ["kg", "lb"],
            index=["kg", "lb"].index(default_weight_unit)
            if default_weight_unit in ["kg", "lb"]
            else 0,
        )

    height_column, height_unit_column = st.columns([2, 1])

    with height_column:
        height_value = st.number_input(
            "Your height (optional)",
            min_value=0.0,
            step=1.0,
            value=float(default_height_value) if default_height_value else 0.0,
            help="Used only to calculate BMI, alongside your weight. Leave at 0 to skip.",
        )

    with height_unit_column:
        height_unit = st.selectbox(
            "Height unit",
            ["cm", "in"],
            index=["cm", "in"].index(default_height_unit)
            if default_height_unit in ["cm", "in"]
            else 0,
        )

    submitted = st.form_submit_button("Save profile")

    if submitted:
        if not purposes:
            st.error("Pick at least one purpose.")
        else:
            protein_targets, fiber_target, water_target_ml, recalculated = (
                save_profile_and_targets(
                    diet_type,
                    purposes,
                    weight_value if weight_value > 0 else None,
                    weight_unit,
                    height_value if height_value > 0 else None,
                    height_unit,
                )
            )

            if protein_targets:
                st.success(
                    f"Profile saved. Weight or purpose changed, so targets "
                    f"were recalculated — Rest day: {protein_targets['rest']} "
                    f"g protein, Training day: {protein_targets['training']} "
                    f"g protein, {fiber_target} g fiber (both days), "
                    f"{int(water_target_ml)} ml water."
                )
            elif recalculated:
                st.success(
                    "Profile saved. Add your weight above to also get "
                    "suggested protein, fiber, and water targets."
                )
            else:
                st.success(
                    "Profile saved. Weight and purpose are unchanged, so "
                    "your daily targets were left as-is — edit protein/fiber "
                    "on the Meal Recommendations page, or water/sleep on the "
                    "Log Water / Log Sleep pages."
                )

            st.rerun()

st.subheader("Your numbers")

st.markdown(
    """
    <style>
    .ptr-stat-card { padding: 0.15rem 0 0.5rem 0; }
    .ptr-stat-label {
        font-size: 0.7rem;
        opacity: 0.65;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 0.15rem;
    }
    .ptr-stat-value {
        font-size: 1.05rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.4rem;
        flex-wrap: wrap;
        line-height: 1.3;
    }
    .ptr-stat-caption {
        font-size: 0.7rem;
        opacity: 0.65;
        margin-top: 0.1rem;
    }
    .ptr-badge {
        display: inline-block;
        background: #D6336C;
        color: #FFFFFF;
        font-size: 0.65rem;
        font-weight: 600;
        padding: 0.1rem 0.5rem;
        border-radius: 999px;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_stat_card(
    column, label, value, badge=None, caption=None, link_page=None, link_label=None
):
    """Render one small stat card — label, value, optional badge, caption, and link."""
    badge_html = f'<span class="ptr-badge">{badge}</span>' if badge else ""
    caption_html = f'<div class="ptr-stat-caption">{caption}</div>' if caption else ""
    with column:
        st.markdown(
            f"""
            <div class="ptr-stat-card">
                <div class="ptr-stat-label">{label}</div>
                <div class="ptr-stat-value">{value}{badge_html}</div>
                {caption_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if link_page:
            st.page_link(link_page, label=link_label)


profile = get_user_profile()
goals = get_protein_goals()

weight_kg = convert_to_kg(
    profile["weight_value"] if profile else None,
    profile["weight_unit"] if profile else None,
)
height_cm = convert_to_cm(
    profile["height_value"] if profile else None,
    profile["height_unit"] if profile else None,
)
bmi = calculate_bmi(weight_kg, height_cm)
bmi_category = get_bmi_category(bmi)

rest_protein = None
training_protein = None
fiber_value = None

if not goals.empty:
    rest_row = goals[goals["day_type"] == "Rest day"]
    training_row = goals[goals["day_type"] == "Training day"]
    if not rest_row.empty:
        rest_protein = rest_row.iloc[0]["daily_target_grams"]
    if not training_row.empty:
        training_protein = training_row.iloc[0]["daily_target_grams"]
    fiber_value = goals.iloc[0]["fiber_target_grams"]

wellness_goals = get_wellness_goals()
water_target_ml = wellness_goals["water_target_ml"] if wellness_goals else None
sleep_target_hours = wellness_goals["sleep_target_hours"] if wellness_goals else None

body_columns = st.columns(3)

render_stat_card(
    body_columns[0],
    "Weight",
    f"{profile['weight_value']:.0f} {profile['weight_unit']}"
    if profile and profile["weight_value"]
    else "Not set",
)

render_stat_card(
    body_columns[1],
    "Height",
    f"{profile['height_value']:.0f} {profile['height_unit']}"
    if profile and profile["height_value"]
    else "Not set",
)

render_stat_card(
    body_columns[2],
    "BMI",
    bmi if bmi else "—",
    badge=bmi_category if bmi else None,
    caption=None if bmi else "Add weight & height",
)

if bmi:
    st.caption(BMI_SOURCE_NOTE)

st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)

target_columns = st.columns(4)

if pd.notna(rest_protein) and pd.notna(training_protein):
    protein_value = (
        f"{int(rest_protein)} g"
        if rest_protein == training_protein
        else f"{int(rest_protein)}–{int(training_protein)} g"
    )
    protein_caption = "Rest day – Training day"
else:
    protein_value = "Not set"
    protein_caption = None

render_stat_card(
    target_columns[0], "Protein target", protein_value, caption=protein_caption
)

render_stat_card(
    target_columns[1],
    "Fiber target",
    f"{int(fiber_value)} g" if pd.notna(fiber_value) else "Not set",
)

render_stat_card(
    target_columns[2],
    "Water target",
    format_ml(water_target_ml) if water_target_ml else "Not set",
    link_page="pages/log_water.py",
    link_label="Log Water",
)

render_stat_card(
    target_columns[3],
    "Sleep target",
    format_hours(sleep_target_hours) if sleep_target_hours else "Not set",
    link_page="pages/log_sleep.py",
    link_label="Log Sleep",
)

if not goals.empty:
    st.dataframe(
        goals[["day_type", "daily_target_grams", "fiber_target_grams"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "day_type": "Day type",
            "daily_target_grams": st.column_config.NumberColumn(
                "Protein target (g)", format="%.0f"
            ),
            "fiber_target_grams": st.column_config.NumberColumn(
                "Fiber target (g)", format="%.0f"
            ),
        },
    )
else:
    st.info("Add your weight above to get suggested protein and fiber targets.")

st.caption(SOURCES_NOTE)
st.caption(WATER_SOURCE_NOTE)
