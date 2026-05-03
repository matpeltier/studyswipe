import streamlit as st
from utils.storage import get_saved_topics, get_collections, unsave_topic
from utils.constants import CATEGORY_COLORS

user_session = st.session_state.get("user_session", "default")

collections = get_collections(user_session)
all_collections = ["All Collections"] + collections

with st.sidebar:
    st.subheader("Collections")
    selected_col = st.selectbox(
        "View collection", all_collections, key="saved_collection"
    )

    st.markdown("---")
    st.subheader("New collection")
    new_col_name = st.text_input("Collection name", key="new_collection_name")
    if st.button("Create collection", key="create_col_btn", use_container_width=True):
        if new_col_name.strip():
            st.toast(
                f"Collection '{new_col_name}' will be used when saving topics.",
                icon=":material/folder:",
            )
        else:
            st.warning("Enter a collection name.", icon=":material/warning:")

col_filter = selected_col if selected_col != "All Collections" else None
cards = get_saved_topics(user_session, collection_name=col_filter)

if not cards:
    st.info(
        "No saved topics yet. Browse the feed and save topics to build your study collection!",
        icon=":material/bookmark_add:",
    )
else:
    st.metric("Saved topics", len(cards))

    for i, card in enumerate(cards):
        with st.container(border=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                cat_color = CATEGORY_COLORS.get(card["category"], "gray")
                st.markdown(f":{cat_color}-badge[{card['category']}]")
                st.markdown(f"### {card['title']}")
                summary = card.get("summary", "")
                st.caption(summary[:200] + ("..." if len(summary) > 200 else ""))

                facts = card.get("facts", [])
                if facts:
                    with st.expander(f"View {len(facts)} facts", icon=":material/tips_and_updates:"):
                        for fact in facts:
                            st.markdown(f"- {fact['fact_text']}")

            with col2:
                if card.get("url"):
                    st.link_button(":material/open_in_new:", card["url"], use_container_width=True)

                if st.button(
                    ":material/delete:",
                    key=f"remove_{card['topic_id']}_{i}",
                    use_container_width=True,
                ):
                    unsave_topic(user_session, card["topic_id"])
                    st.toast("Removed from saved.", icon=":material/bookmark_remove:")
                    st.rerun()
