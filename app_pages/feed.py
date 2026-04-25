import json
import random as _random

import streamlit as st
from utils.database import (
    get_connection,
    get_feed_topics,
    get_categories,
    save_topic,
    unsave_topic,
    record_view,
    record_quiz_answer,
)
from utils.swipe_component import SWIPE_CARD_HTML, SWIPE_CARD_CSS, SWIPE_CARD_JS

CATEGORY_COLORS = {
    "Science": "green",
    "History": "blue",
    "Politics": "orange",
    "Culture": "violet",
    "Technology": "red",
}

swipe_card = st.components.v2.component(
    "swipe_card",
    html=SWIPE_CARD_HTML,
    css=SWIPE_CARD_CSS,
    js=SWIPE_CARD_JS,
)

conn = get_connection()
user_session = st.session_state.get("user_session", "default")
categories = get_categories(conn)
all_cats = ["All"] + categories

with st.sidebar:
    st.subheader("Filters")
    selected_cat = st.selectbox("Category", all_cats, key="feed_category")
    sort_options = {
        "Trending": "trending",
        "Most popular": "popular",
        "Random discovery": "random",
        "Easy first": "difficulty_easy",
        "Hard first": "difficulty_hard",
        "Alphabetical": "alpha",
    }
    sort_label = st.selectbox("Sort by", list(sort_options.keys()), key="feed_sort")
    sort_by = sort_options[sort_label]

    collection = st.text_input(
        "Save to collection", value="General", key="feed_collection"
    )
    st.caption(f"Logged in as: `{user_session[:8]}...`")

st.session_state.setdefault("feed_index", 0)

category_filter = selected_cat if selected_cat != "All" else None
cards = get_feed_topics(
    conn, user_session, category=category_filter, sort_by=sort_by, limit=100
)

if not cards:
    st.info("No topics found matching your filters.")
    conn.close()
else:
    idx = st.session_state.feed_index % len(cards)
    card = cards[idx]

    st.progress((idx + 1) / len(cards), text=f"Card {idx + 1} of {len(cards)}")

    topic_data = {
        "title": card.topic.title,
        "category": card.topic.category,
        "summary": card.topic.summary,
        "why_matters": card.topic.why_matters or "",
        "popularity": card.popularity_label,
        "difficulty": card.difficulty_label,
        "pageviews": card.metrics.pageviews_7d if card.metrics else 0,
        "facts": [f.fact_text for f in card.facts],
        "quiz_question": card.quiz_items[0].question if card.quiz_items else None,
        "quiz_options": (
            [
                o
                for o in [
                    card.quiz_items[0].option_a,
                    card.quiz_items[0].option_b,
                    card.quiz_items[0].option_c,
                    card.quiz_items[0].option_d,
                ]
                if o
            ]
            if card.quiz_items
            else []
        ),
    }

    needs_reset = st.session_state.pop("swipe_needs_reset", True)

    result = swipe_card(
        data={"topic": topic_data, "reset": needs_reset},
        key=f"swipe_{card.topic.topic_id}_{idx}",
        on_swipe_value_change=lambda: None,
        on_swiped_change=lambda: None,
    )

    swipe_action = result.swiped if result else None

    if swipe_action == "save":
        collection_name = st.session_state.get("feed_collection", "General")
        save_topic(conn, user_session, card.topic.topic_id, collection_name)
        record_view(conn, user_session, card.topic.topic_id)
        st.session_state.feed_index = (idx + 1) % len(cards)
        st.session_state.swipe_needs_reset = True
        st.toast(
            f"Saved '{card.topic.title}' to {collection_name}!",
            icon=":material/bookmark_added:",
        )
        st.rerun()
    elif swipe_action == "skip":
        record_view(conn, user_session, card.topic.topic_id)
        st.session_state.feed_index = (idx + 1) % len(cards)
        st.session_state.swipe_needs_reset = True
        st.toast("Skipped!", icon=":material/fast_forward:")
        st.rerun()

    if card.quiz_items:
        quiz = card.quiz_items[0]
        st.markdown("---")
        st.markdown(f"**:material/quiz: Quick check:** {quiz.question}")
        options = []
        correct_idx = 0
        for oi, opt_key in enumerate(["option_a", "option_b", "option_c", "option_d"]):
            opt_val = getattr(quiz, opt_key)
            if opt_val:
                options.append(opt_val)
                if opt_key == quiz.correct_option:
                    correct_idx = oi

        quiz_key = f"feed_quiz_{card.topic.topic_id}_{idx}"
        selected = st.radio(
            "Choose your answer:",
            options=options,
            index=None,
            key=quiz_key,
            label_visibility="collapsed",
        )

        check_key = f"feed_check_{card.topic.topic_id}_{idx}"
        if st.button("Check answer", key=check_key, type="primary"):
            if selected:
                is_correct = selected == options[correct_idx]
                record_quiz_answer(
                    conn,
                    user_session,
                    card.topic.topic_id,
                    quiz.quiz_id,
                    selected,
                    is_correct,
                )
                if is_correct:
                    st.success("Correct!", icon=":material/check_circle:")
                else:
                    st.error(
                        f"Incorrect. The answer was: **{options[correct_idx]}**",
                        icon=":material/cancel:",
                    )
            else:
                st.warning("Select an answer first.", icon=":material/warning:")

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    with btn_col1:
        if st.button(
            ":material/arrow_back: Prev", key="feed_prev", use_container_width=True
        ):
            st.session_state.feed_index = max(0, idx - 1)
            st.session_state.swipe_needs_reset = True
            st.rerun()
    with btn_col2:
        if st.button(
            ":material/shuffle: Random", key="feed_random", use_container_width=True
        ):
            st.session_state.feed_index = _random.randint(0, len(cards) - 1)
            st.session_state.swipe_needs_reset = True
            st.rerun()
    with btn_col3:
        if card.is_saved:
            if st.button(
                ":material/bookmark_remove: Unsave",
                key=f"unsave_{card.topic.topic_id}",
                use_container_width=True,
            ):
                unsave_topic(conn, user_session, card.topic.topic_id)
                st.rerun()
        else:
            if st.button(
                ":material/bookmark_add: Save",
                key=f"save_{card.topic.topic_id}",
                use_container_width=True,
                type="primary",
            ):
                col_name = st.session_state.get("feed_collection", "General")
                save_topic(conn, user_session, card.topic.topic_id, col_name)
                st.toast("Saved!", icon=":material/bookmark_added:")
    with btn_col4:
        if card.topic.url:
            st.link_button(
                ":material/open_in_new: Wikipedia",
                card.topic.url,
                use_container_width=True,
            )

    conn.close()
