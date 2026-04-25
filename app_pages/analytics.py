import pandas as pd
import streamlit as st
from utils.database import get_connection, get_analytics, get_categories


conn = get_connection()
user_session = st.session_state.get("user_session", "default")
analytics = get_analytics(conn, user_session)

st.subheader("Your learning dashboard")

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
    cat_df = pd.DataFrame(
        list(category_stats.items()), columns=["Category", "Topics quizzed"]
    )
    st.bar_chart(cat_df, x="Category", y="Topics quizzed")

category_accuracy = analytics.get("category_accuracy", {})
if category_accuracy:
    st.subheader("Accuracy by category")
    acc_df = pd.DataFrame(
        list(category_accuracy.items()), columns=["Category", "Accuracy (%)"]
    )
    st.bar_chart(acc_df, x="Category", y="Accuracy (%)")

most_saved = analytics.get("most_saved", [])
if most_saved:
    st.subheader("Most saved topics")
    for i, item in enumerate(most_saved[:10]):
        cat_color = {
            "Science": "green",
            "History": "blue",
            "Politics": "orange",
            "Culture": "violet",
            "Technology": "red",
        }.get(item["category"], "gray")
        st.markdown(
            f"{i + 1}. :{cat_color}-badge[{item['category']}] **{item['title']}** ({item['save_count']} saves)"
        )

st.subheader("Database overview")
categories = get_categories(conn)
overview_cols = st.columns(len(categories)) if categories else []
for i, cat in enumerate(categories):
    with overview_cols[i]:
        count = category_stats.get(cat, 0)
        cat_color = {
            "Science": "green",
            "History": "blue",
            "Politics": "orange",
            "Culture": "violet",
            "Technology": "red",
        }.get(cat, "gray")
        st.metric(f":{cat_color}-badge[{cat}]", f"{count} quizzed")

conn.close()
