import streamlit as st
from utils.database import get_connection, get_topic_count
from utils.wikipedia_fetcher import (
    fetch_trending_articles,
    search_and_add,
    refresh_pageviews_for_existing,
)

st.subheader("Discover from Wikipedia")

conn = get_connection()
current_count = get_topic_count(conn)
conn.close()

st.caption(
    f"Your database has **{current_count}** topics. Use the tools below to fetch more from Wikipedia."
)

st.markdown("---")

st.subheader("Search Wikipedia")
search_query = st.text_input(
    "Search for a topic",
    key="wiki_search_query",
    placeholder="e.g. Black holes, Roman Empire, Python programming...",
)

if st.button(
    ":material/search: Search and add topics",
    key="wiki_search_btn",
    type="primary",
    use_container_width=True,
):
    if search_query.strip():
        with st.spinner(f"Searching Wikipedia for '{search_query}'..."):
            added = search_and_add(search_query, max_results=5)
        if added:
            st.success(
                f"Added **{len(added)}** new topics from Wikipedia!",
                icon=":material/check_circle:",
            )
            for tid in added:
                conn = get_connection()
                row = conn.execute(
                    "SELECT title, category FROM topics WHERE topic_id = ?", (tid,)
                ).fetchone()
                conn.close()
                if row:
                    cat_color = {
                        "Science": "green",
                        "History": "blue",
                        "Politics": "orange",
                        "Culture": "violet",
                        "Technology": "red",
                    }.get(row["category"], "gray")
                    st.markdown(
                        f"- :{cat_color}-badge[{row['category']}] **{row['title']}**"
                    )
        else:
            st.warning(
                "No new articles found. Try different keywords.",
                icon=":material/warning:",
            )
    else:
        st.warning("Enter a search query first.", icon=":material/warning:")

st.markdown("---")

st.subheader("Fetch random articles")
num_fetch = st.slider("How many articles to fetch", 3, 20, 5, key="wiki_fetch_count")

if st.button(
    ":material/casino: Fetch random from Wikipedia",
    key="wiki_fetch_btn",
    use_container_width=True,
):
    with st.spinner(f"Fetching {num_fetch} random articles from Wikipedia..."):
        added = fetch_trending_articles(count=num_fetch)
    if added:
        st.success(
            f"Added **{len(added)}** new topics!", icon=":material/check_circle:"
        )
        for tid in added:
            conn = get_connection()
            row = conn.execute(
                "SELECT title, category FROM topics WHERE topic_id = ?", (tid,)
            ).fetchone()
            conn.close()
            if row:
                cat_color = {
                    "Science": "green",
                    "History": "blue",
                    "Politics": "orange",
                    "Culture": "violet",
                    "Technology": "red",
                }.get(row["category"], "gray")
                st.markdown(
                    f"- :{cat_color}-badge[{row['category']}] **{row['title']}**"
                )
    else:
        st.warning(
            "Could not fetch articles. Try again later.", icon=":material/warning:"
        )

st.markdown("---")

st.subheader("Refresh pageview data")
st.caption(
    "Update trending/popularity metrics for existing topics using live Wikipedia pageview data."
)

if st.button(
    ":material/trending_up: Refresh all pageviews",
    key="wiki_refresh_btn",
    use_container_width=True,
):
    with st.spinner("Fetching live pageview data from Wikimedia Analytics API..."):
        updated = refresh_pageviews_for_existing()
    st.success(
        f"Updated pageview metrics for **{updated}** topics!",
        icon=":material/check_circle:",
    )
