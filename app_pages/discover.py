import streamlit as st
from utils.storage import get_topic_count
from utils.wikipedia_fetcher import fetch_trending_articles, search_and_add
from utils.constants import CATEGORY_COLORS

st.subheader("Discover from Wikipedia")

current_count = get_topic_count()
st.caption(f"Your database has **{current_count}** topics. Use the tools below to fetch more from Wikipedia.")

st.markdown("---")

st.subheader("Search Wikipedia")
search_query = st.text_input(
    "Search for a topic",
    key="wiki_search_query",
    placeholder="e.g. Black holes, Roman Empire...",
)

if st.button(":material/search: Search and add topics", key="wiki_search_btn", type="primary", use_container_width=True):
    if search_query.strip():
        with st.spinner(f"Searching Wikipedia for '{search_query}'..."):
            added = search_and_add(search_query, max_results=5)
        if added:
            st.success(f"Added **{len(added)}** new topics from Wikipedia!", icon=":material/check_circle:")
            for tid in added:
                from utils.storage import get_topic_by_id
                topic = get_topic_by_id(tid)
                if topic:
                    cat_color = CATEGORY_COLORS.get(topic["category"], "gray")
                    st.markdown(f"- :{cat_color}-badge[{topic['category']}] **{topic['title']}**")
        else:
            st.warning("No new articles found. Try different keywords.", icon=":material/warning:")
    else:
        st.warning("Enter a search query first.", icon=":material/warning:")

st.markdown("---")

st.subheader("Fetch random articles")
num_fetch = st.slider("How many articles to fetch", 3, 20, 5, key="wiki_fetch_count")

if st.button(":material/casino: Fetch random from Wikipedia", key="wiki_fetch_btn", use_container_width=True):
    with st.spinner(f"Fetching {num_fetch} random articles from Wikipedia..."):
        added = fetch_trending_articles(count=num_fetch)
    if added:
        st.success(f"Added **{len(added)}** new topics!", icon=":material/check_circle:")
        for tid in added:
            from utils.storage import get_topic_by_id
            topic = get_topic_by_id(tid)
            if topic:
                cat_color = CATEGORY_COLORS.get(topic["category"], "gray")
                st.markdown(f"- :{cat_color}-badge[{topic['category']}] **{topic['title']}**")
    else:
        st.warning("Could not fetch articles. Try again later.", icon=":material/warning:")
