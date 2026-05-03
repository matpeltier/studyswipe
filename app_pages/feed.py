import random as _random

import streamlit as st
from utils.storage import (
    get_feed_topics,
    get_categories,
    save_topic,
    unsave_topic,
    record_view,
    record_quiz_answer,
    is_topic_saved,
    is_topic_viewed,
)
from utils.constants import CATEGORY_COLORS

user_session = st.session_state.get("user_session", "default")
categories = get_categories()
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
    st.caption(f"Session: `{user_session[:8]}...`")

st.session_state.setdefault("feed_index", 0)

category_filter = selected_cat if selected_cat != "All" else None
topics = get_feed_topics(user_session, category=category_filter, sort_by=sort_by, limit=100)

if not topics:
    st.info("No topics found matching your filters.")
else:
    idx = st.session_state.feed_index % len(topics)
    card = topics[idx]

    st.progress((idx + 1) / len(topics), text=f"Card {idx + 1} of {len(topics)}")

    popularity = "Unknown"
    pv = card.get("pageviews_7d", 0)
    if pv >= 100000:
        popularity = "Trending"
    elif pv >= 10000:
        popularity = "Popular"
    elif pv >= 1000:
        popularity = "Moderate"
    else:
        popularity = "Niche"

    difficulty = "Medium"
    ds = card.get("difficulty_score", 2.0)
    if ds <= 2.0:
        difficulty = "Easy"
    elif ds > 3.5:
        difficulty = "Hard"

    quizzes = card.get("quizzes", [])

    with st.container(border=True):
        cat_color = CATEGORY_COLORS.get(card["category"], "gray")
        st.markdown(f":{cat_color}-badge[{card['category']}]")
        st.markdown(f"## {card['title']}")

        meta_line = f"{popularity} · {difficulty} · {pv} views/wk"
        st.caption(meta_line)

        st.markdown(card["summary"])

        if card.get("why_matters"):
            st.info(f"**Why this matters:** {card['why_matters']}")

        facts = card.get("facts", [])
        if facts:
            with st.expander(f"View {len(facts)} key facts"):
                for fact in facts:
                    st.markdown(f"- {fact['fact_text']}")

    if len(quizzes) > 0:
        quiz = quizzes[0]
        st.markdown("---")
        st.markdown(f"**:material/quiz: Quick check:** {quiz['question']}")
        option_keys = ("option_a", "option_b", "option_c", "option_d")
        options = []
        correct_idx = 0
        for oi, opt_key in enumerate(option_keys):
            opt_val = quiz.get(opt_key, "")
            if opt_val:
                options.append(opt_val)
                if opt_key == quiz["correct_option"]:
                    correct_idx = oi

        quiz_key = f"feed_quiz_{card['topic_id']}_{idx}"
        selected = st.radio(
            "Choose your answer:",
            options=options,
            index=None,
            key=quiz_key,
            label_visibility="collapsed",
        )

        check_key = f"feed_check_{card['topic_id']}_{idx}"
        if st.button("Check answer", key=check_key, type="primary"):
            if selected:
                is_correct = selected == options[correct_idx]
                record_quiz_answer(
                    user_session,
                    card["topic_id"],
                    quiz["quiz_id"],
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

    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)
    with btn_col1:
        if st.button(":material/skip_previous: Prev", key="feed_prev", use_container_width=True):
            st.session_state.feed_index = max(0, idx - 1)
            st.rerun()
    with btn_col2:
        if st.button(":material/bookmark_remove: Skip", key="feed_skip", use_container_width=True):
            record_view(user_session, card["topic_id"])
            st.session_state.feed_index = (idx + 1) % len(topics)
            st.toast("Skipped!", icon=":material/fast_forward:")
            st.rerun()
    with btn_col3:
        if st.button(":material/shuffle: Random", key="feed_random", use_container_width=True):
            st.session_state.feed_index = _random.randint(0, len(topics) - 1)
            st.rerun()
    with btn_col4:
        saved = is_topic_saved(user_session, card["topic_id"])
        if saved:
            if st.button(":material/bookmark_remove: Unsave", key=f"unsave_{card['topic_id']}", use_container_width=True):
                unsave_topic(user_session, card["topic_id"])
                st.rerun()
        else:
            if st.button(":material/bookmark_add: Save", key=f"save_{card['topic_id']}", use_container_width=True, type="primary"):
                col_name = st.session_state.get("feed_collection", "General")
                save_topic(user_session, card["topic_id"], col_name)
                st.toast("Saved!", icon=":material/bookmark_added:")
    with btn_col5:
        if card.get("url"):
            st.link_button(":material/open_in_new: Wikipedia", card["url"], use_container_width=True)
