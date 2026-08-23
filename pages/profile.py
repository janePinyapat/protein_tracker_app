import streamlit as st

from database import get_user_profile, save_user_profile
from user_profile import DIET_TYPES, PURPOSES


st.title("Profile")
st.write(
    "Your diet type and purpose only affect which labels are suggested "
    "first when you log food — nothing is hidden, and the app still never "
    "rates your food or gives medical advice."
)

profile = get_user_profile()
default_diet_type = profile["diet_type"] if profile else DIET_TYPES[0]
default_purposes = profile["purposes"] if profile else []

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

    submitted = st.form_submit_button("Save profile")

    if submitted:
        if not purposes:
            st.error("Pick at least one purpose.")
        else:
            save_user_profile(diet_type, purposes)
            st.success("Profile updated.")
            st.rerun()
