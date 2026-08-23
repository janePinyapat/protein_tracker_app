import streamlit as st

from database import save_user_profile
from user_profile import DIET_TYPES, PURPOSES


st.title("Welcome")
st.write(
    "Before you start logging, tell us a bit about yourself. This only "
    "changes which labels are suggested first when you tag a food — every "
    "label stays available to everyone, and none of this is used to rate "
    "your food or give medical advice."
)

with st.form("onboarding_form"):
    diet_type = st.radio("Which best describes your diet?", DIET_TYPES)

    purposes = st.multiselect(
        "What are you using this tracker for? (pick any that apply)",
        options=PURPOSES,
    )

    submitted = st.form_submit_button("Get started")

    if submitted:
        if not purposes:
            st.error("Pick at least one purpose to continue.")
        else:
            save_user_profile(diet_type, purposes)
            st.success("Saved! Taking you to your dashboard...")
            st.rerun()

st.caption("You can change these anytime from the Profile page in the sidebar.")
