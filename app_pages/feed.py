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
    add_xp,
    get_user_progress,
)
from utils.constants import CATEGORY_COLORS, ACHIEVEMENT_NAMES
from utils.spaced_repetition import record_review, get_due_cards, get_card_state

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

    st.markdown("---")
    anki_mode = st.toggle("Anki mode", value=True, key="anki_mode")

    if anki_mode:
        due = get_due_cards(limit=100)
        st.caption(f":material/schedule: **{len(due)}** cards due for review")

    st.caption(f"Session: `{user_session[:8]}...`")

category_filter = selected_cat if selected_cat != "All" else None
topics = get_feed_topics(user_session, category=category_filter, sort_by=sort_by, limit=100)

if not topics:
    st.info("No topics found matching your filters.")
else:
    progress_data = get_user_progress(user_session)
    xp_in_level = progress_data["xp"] % 100
    xp_col1, xp_col2, xp_col3 = st.columns(3)
    with xp_col1:
        st.progress(xp_in_level / 100, text=f"Lvl {progress_data['level']} — {xp_in_level}/100 XP")
    with xp_col2:
        st.markdown(f":fire: **{progress_data['streak_days']}** day streak")
    with xp_col3:
        st.markdown(f":star: **{progress_data['xp']}** total XP")

    if anki_mode:
        # --- ANKI MODE ---
        st.session_state.setdefault("anki_seen_today", [])

        # Only rebuild queue when needed (not mid-card)
        needs_rebuild = "anki_queue" not in st.session_state or st.session_state.get("anki_current_card") is None
        if needs_rebuild:
            seen_today = st.session_state.anki_seen_today
            due_quiz_ids = get_due_cards(limit=100)

            queue = []
            due_topics = []
            for topic in topics:
                for qi in topic.get("quizzes", []):
                    if qi["quiz_id"] in due_quiz_ids and topic["topic_id"] not in seen_today:
                        due_topics.append(topic)
                        break
            queue.extend(due_topics)

            new_topics = []
            for topic in topics:
                if topic["topic_id"] not in seen_today and topic not in queue:
                    has_sr = False
                    for qi in topic.get("quizzes", []):
                        if get_card_state(qi["quiz_id"]):
                            has_sr = True
                            break
                    if not has_sr:
                        new_topics.append(topic)
            _random.shuffle(new_topics)
            queue.extend(new_topics)
            st.session_state.anki_queue = queue

        queue = st.session_state.anki_queue

        revealed = st.session_state.get("anki_revealed", False)
        remaining = len(queue)
        viewed_today = len(st.session_state.anki_seen_today)
        st.progress(
            min(viewed_today / max(remaining + viewed_today, 1), 1.0),
            text=f"{viewed_today} reviewed · {remaining} remaining",
        )

        if remaining == 0 and not revealed:
            st.success("All caught up! No more cards to review.", icon=":material/check_circle:")
            st.markdown("Come back later when cards are due.")
            if st.button("Reset session", key="anki_reset"):
                st.session_state.anki_seen_today = []
                if "anki_queue" in st.session_state:
                    del st.session_state.anki_queue
                st.rerun()
        else:
            card = queue[0] if queue else st.session_state.get("anki_current_card")
            if not card:
                st.info("No more cards.")
            else:
                st.session_state.anki_current_card = card
                quizzes = card.get("quizzes", [])

                # Card front (always visible)
                if not revealed:
                    sr_state = None
                    for qi in card.get("quizzes", []):
                        sr_state = get_card_state(qi["quiz_id"])
                        if sr_state:
                            break
                    if sr_state and sr_state.get("repetitions", 0) > 0:
                        st.caption(f"Review #{sr_state['repetitions']} (every {sr_state['interval']} days)")
                    else:
                        st.caption("New card")

                if revealed:
                    # Full card content
                    with st.container(border=True):
                        cat_color = CATEGORY_COLORS.get(card["category"], "gray")
                        st.markdown(f":{cat_color}-badge[{card['category']}]")
                        st.markdown(f"## {card['title']}")
                        st.markdown(card["summary"])

                        if card.get("why_matters"):
                            st.info(f"**Why this matters:** {card['why_matters']}")

                        facts = card.get("facts", [])
                        if facts:
                            for fact in facts:
                                st.markdown(f"- {fact['fact_text']}")
                else:
                    cat_color = CATEGORY_COLORS.get(card["category"], "gray")
                    st.markdown(f":{cat_color}-badge[{card['category']}]")
                    st.markdown(f"## {card['title']}")

                    st.markdown(
                        '<style>'
                        '[data-testid="stBaseButton-secondaryAnki"] button, '
                        '[data-testid="stBaseButton-primaryAnki"] button {'
                        '  height: 180px; font-size: 1.3rem; '
                        '  border: 2px dashed #6366f1; border-radius: 12px; '
                        '  background: transparent; color: #6366f1;'
                        '}'
                        '</style>',
                        unsafe_allow_html=True,
                    )
                    if st.button("Tap to flip", key="anki_reveal", type="secondary", use_container_width=True):
                        st.session_state.anki_revealed = True
                        st.rerun()

                # Quiz (always visible)
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

                    quiz_key = f"anki_quiz_{card['topic_id']}"
                    selected = st.radio(
                        "Choose your answer:",
                        options=options,
                        index=None,
                        key=quiz_key,
                        label_visibility="collapsed",
                    )

                    if selected:
                        is_correct = selected == options[correct_idx]
                        if is_correct:
                            st.success("Correct!", icon=":material/check_circle:")
                        else:
                            st.error(
                                f"Incorrect. The answer was: **{options[correct_idx]}**",
                                icon=":material/cancel:",
                            )

                # Action buttons
                st.markdown("---")

                if revealed:
                    # Rating buttons
                    st.markdown("**How well did you know this?**")
                    rating_col1, rating_col2, rating_col3, rating_col4 = st.columns(4)

                    ratings = [
                        (0, "Again", "primary"),
                        (2, "Hard", "secondary"),
                        (3, "Good", "secondary"),
                        (5, "Easy", "secondary"),
                    ]

                    for i, (quality, label, btn_type) in enumerate(ratings):
                        with [rating_col1, rating_col2, rating_col3, rating_col4][i]:
                            if st.button(label, key=f"anki_{label}", type=btn_type, use_container_width=True):
                                for qi in card.get("quizzes", []):
                                    record_review(qi["quiz_id"], quality)
                                record_view(user_session, card["topic_id"])
                                result = add_xp(user_session, 5, "viewed_card")
                                for ach in result.get("new_achievements", []):
                                    name, desc = ACHIEVEMENT_NAMES.get(ach, (ach, ""))
                                    st.toast(f"Achievement: {name} — {desc}", icon=":material/trophy:")

                                st.session_state.anki_seen_today.append(card["topic_id"])
                                st.session_state.anki_revealed = False
                                st.session_state.anki_current_card = None
                                del st.session_state.anki_queue
                                st.rerun()
                else:
                    saved = is_topic_saved(user_session, card["topic_id"])
                    if saved:
                        if st.button("Unsave", key=f"anki_unsave_{card['topic_id']}", use_container_width=True):
                            unsave_topic(user_session, card["topic_id"])
                            st.rerun()
                    else:
                        if st.button("Save", key=f"anki_save_{card['topic_id']}", use_container_width=True):
                            col_name = st.session_state.get("feed_collection", "General")
                            save_topic(user_session, card["topic_id"], col_name)
                            st.toast("Saved!", icon=":material/bookmark_added:")
                            st.rerun()

    else:
        # --- CLASSIC MODE ---
        st.session_state.setdefault("feed_index", 0)
        st.session_state.setdefault("feed_viewed", [])

        idx = st.session_state.feed_index % len(topics)
        card = topics[idx]

        viewed_count = len(set(st.session_state.feed_viewed))
        st.progress(viewed_count / len(topics), text=f"Viewed {viewed_count} of {len(topics)} cards")

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
            diff_colors = {"Easy": "green", "Medium": "orange", "Hard": "red"}
            diff_color = diff_colors.get(difficulty, "gray")
            st.markdown(f":{cat_color}-badge[{card['category']}]  :{diff_color}-badge[{difficulty}]")
            st.markdown(f"## {card['title']}")

            meta_line = f"{popularity} · {pv:,} views/wk"
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
                        add_xp(user_session, 10, "correct_answer")
                        st.success("Correct! +10 XP", icon=":material/check_circle:")
                    else:
                        add_xp(user_session, 2, "wrong_answer")
                        st.error(
                            f"Incorrect. The answer was: **{options[correct_idx]}** (+2 XP)",
                            icon=":material/cancel:",
                        )
                else:
                    st.warning("Select an answer first.", icon=":material/warning:")

        btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)
        with btn_col1:
            if st.button(":material/skip_previous: Prev", key="feed_prev", use_container_width=True):
                if card["topic_id"] not in st.session_state.feed_viewed:
                    st.session_state.feed_viewed.append(card["topic_id"])
                    result = add_xp(user_session, 5, "viewed_card")
                    for ach in result.get("new_achievements", []):
                        name, desc = ACHIEVEMENT_NAMES.get(ach, (ach, ""))
                        st.toast(f"Achievement: {name} — {desc}", icon=":material/trophy:")
                record_view(user_session, card["topic_id"])
                st.session_state.feed_index = max(0, idx - 1)
                st.rerun()
        with btn_col2:
            if st.button(":material/bookmark_remove: Skip", key="feed_skip", use_container_width=True):
                if card["topic_id"] not in st.session_state.feed_viewed:
                    st.session_state.feed_viewed.append(card["topic_id"])
                    result = add_xp(user_session, 5, "viewed_card")
                    for ach in result.get("new_achievements", []):
                        name, desc = ACHIEVEMENT_NAMES.get(ach, (ach, ""))
                        st.toast(f"Achievement: {name} — {desc}", icon=":material/trophy:")
                record_view(user_session, card["topic_id"])
                st.session_state.feed_index = (idx + 1) % len(topics)
                st.toast("Skipped! +5 XP", icon=":material/fast_forward:")
                st.rerun()
        with btn_col3:
            if st.button(":material/shuffle: Random", key="feed_random", use_container_width=True):
                if card["topic_id"] not in st.session_state.feed_viewed:
                    st.session_state.feed_viewed.append(card["topic_id"])
                    result = add_xp(user_session, 5, "viewed_card")
                    for ach in result.get("new_achievements", []):
                        name, desc = ACHIEVEMENT_NAMES.get(ach, (ach, ""))
                        st.toast(f"Achievement: {name} — {desc}", icon=":material/trophy:")
                record_view(user_session, card["topic_id"])
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
