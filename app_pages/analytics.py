import pandas as pd
import plotly.express as px
import streamlit as st
from utils.storage import get_analytics, get_categories, get_user_progress
from utils.constants import CATEGORY_COLORS, ACHIEVEMENT_NAMES

user_session = st.session_state.get("user_session", "default")
analytics = get_analytics(user_session)

st.subheader("Your learning dashboard")

progress = get_user_progress(user_session)

pcol1, pcol2, pcol3 = st.columns(3)
with pcol1:
    st.metric("Level", progress["level"])
    xp_in_level = progress["xp"] % 100
    st.progress(xp_in_level / 100, text=f"{xp_in_level}/100 XP to next level")
with pcol2:
    st.metric("Total XP", progress["xp"])
with pcol3:
    st.metric("Day streak", f"{progress['streak_days']}")

if progress["achievements"]:
    st.subheader("Achievements")
    ach_cols = st.columns(min(len(progress["achievements"]), 3))
    for i, ach in enumerate(progress["achievements"]):
        name, desc = ACHIEVEMENT_NAMES.get(ach, (ach, ""))
        with ach_cols[i % 3]:
            st.markdown(f":trophy: **{name}** — {desc}")

st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Topics viewed", analytics["viewed_count"])
with col2:
    st.metric("Topics saved", analytics["saved_count"])
with col3:
    st.metric("Quiz accuracy", f"{analytics['accuracy']}%")

category_stats = analytics.get("category_stats", {})
if category_stats:
    st.subheader("Topics quizzed by category")
    cat_items = list(category_stats.items())
    cat_df = pd.DataFrame(cat_items, columns=["Category", "Topics quizzed"])
    fig = px.bar(
        cat_df, x="Category", y="Topics quizzed",
        color="Topics quizzed", color_continuous_scale="indigo",
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

category_accuracy = analytics.get("category_accuracy", {})
if category_accuracy:
    st.subheader("Accuracy by category")
    acc_items = list(category_accuracy.items())
    acc_df = pd.DataFrame(acc_items, columns=["Category", "Accuracy (%)"])
    fig2 = px.bar(
        acc_df, x="Category", y="Accuracy (%)",
        color="Accuracy (%)", color_continuous_scale="RdYlGn",
    )
    fig2.update_layout(showlegend=False, yaxis_range=[0, 100])
    st.plotly_chart(fig2, use_container_width=True)

most_saved = analytics.get("most_saved", [])
if most_saved:
    st.subheader("Most saved topics")
    for i, item in enumerate(most_saved[:10]):
        cat_color = CATEGORY_COLORS.get(item["category"], "gray")
        st.markdown(
            f"{i + 1}. :{cat_color}-badge[{item['category']}] **{item['title']}** ({item['save_count']} saves)"
        )

st.subheader("Database overview")
categories = get_categories()
overview_cols = st.columns(len(categories)) if categories else []
for i, cat in enumerate(categories):
    with overview_cols[i]:
        count = category_stats.get(cat, 0)
        cat_color = CATEGORY_COLORS.get(cat, "gray")
        st.metric(f":{cat_color}-badge[{cat}]", f"{count} quizzed")
