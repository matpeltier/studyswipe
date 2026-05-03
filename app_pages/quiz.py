import random as _random

import streamlit as st
from utils.database import (
    get_connection,
    get_feed_topics,
    get_categories,
    record_quiz_answer,
    get_quiz_stats,
)
from utils.constants import CATEGORY_COLORS

conn = get_connection()
user_session = st.session_state.get("user_session", "default")
categories = get_categories(conn)
all_cats = ["All"] + categories

stats = get_quiz_stats(conn, user_session)

with st.sidebar:
    st.subheader("Quiz settings")
    quiz_cat = st.selectbox("Category", all_cats, key="quiz_category")
    num_questions = st.slider("Questions", 3, 20, 5, key="quiz_num_q")
    difficulty_filter = st.selectbox(
        "Difficulty",
        ["All", "Easy", "Medium", "Hard"],
        key="quiz_difficulty",
    )

st.subheader("Your quiz stats")
stat_col1, stat_col2, stat_col3 = st.columns(3)
with stat_col1:
    st.metric("Questions answered", stats["total_answers"])
with stat_col2:
    st.metric("Correct answers", stats["correct_answers"])
with stat_col3:
    st.metric("Accuracy", f"{stats['accuracy']}%")

if st.button(
    ":material/play_arrow: Start new quiz",
    key="start_quiz",
    type="primary",
    use_container_width=True,
):
    st.session_state.quiz_active = True
    st.session_state.quiz_index = 0
    st.session_state.quiz_score = 0
    st.session_state.quiz_answered = []

    cat_filter = quiz_cat if quiz_cat != "All" else None
    sort_map = {
        "Easy": "difficulty_easy",
        "Medium": "trending",
        "Hard": "difficulty_hard",
    }
    sort_by = sort_map.get(difficulty_filter, "random")
    cards = get_feed_topics(
        conn, user_session, category=cat_filter, sort_by=sort_by, limit=50
    )

    quiz_items = []
    card_index = 0
    while len(quiz_items) < num_questions and card_index < len(cards):
        card = cards[card_index]
        for qi in card.quiz_items:
            quiz_items.append(
                {
                    "topic_id": card.topic.topic_id,
                    "topic_title": card.topic.title,
                    "category": card.topic.category,
                    "quiz_id": qi.quiz_id,
                    "question": qi.question,
                    "options": [
                        o
                        for o in [
                            qi.option_a,
                            qi.option_b,
                            qi.option_c,
                            qi.option_d,
                        ]
                        if o
                    ],
                    "correct_option": qi.correct_option,
                }
            )
            if len(quiz_items) >= num_questions:
                break
        card_index = card_index + 1

    _random.shuffle(quiz_items)
    st.session_state.quiz_items = quiz_items[:num_questions]
    st.rerun()

if not st.session_state.get("quiz_active", False):
    conn.close()
else:
    quiz_items = st.session_state.get("quiz_items", [])
    quiz_idx = st.session_state.get("quiz_index", 0)

    if quiz_idx >= len(quiz_items):
        st.success("Quiz complete!", icon=":material/trophy:")
        score = st.session_state.get("quiz_score", 0)
        total = len(quiz_items)
        pct = round(score / total * 100) if total > 0 else 0

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric("Final score", f"{score}/{total}")
        with res_col2:
            st.metric("Accuracy", f"{pct}%")

        if pct >= 80:
            st.balloons()
            st.markdown(":material/star: **Excellent!** You really know your topics!")
        elif pct >= 60:
            st.markdown(":material/thumb_up: **Good job!** Keep reviewing to improve.")
        else:
            st.markdown(
                ":material/menu_book: **Keep learning!** Review saved topics and try again."
            )

        answered = st.session_state.get("quiz_answered", [])
        if answered:
            st.markdown("### Review")
            for ans in answered:
                icon = (
                    ":material/check_circle:" if ans["correct"] else ":material/cancel:"
                )
                color = "green" if ans["correct"] else "red"
                st.markdown(
                    f":{color}[{icon}] **{ans['topic_title']}** — {ans['question']}"
                )

        if st.button(":material/refresh: New quiz", key="new_quiz_btn"):
            st.session_state.quiz_active = False
            st.rerun()
    else:
        item = quiz_items[quiz_idx]
        progress = (quiz_idx + 1) / len(quiz_items)
        st.progress(progress, text=f"Question {quiz_idx + 1} of {len(quiz_items)}")

        with st.container(border=True):
            cat_color = CATEGORY_COLORS.get(item["category"], "gray")
            st.markdown(f":{cat_color}-badge[{item['category']}]")
            st.markdown(f"**{item['topic_title']}**")
            st.markdown(f"### {item['question']}")

        options = item["options"]
        correct_key = item["correct_option"]
        correct_idx = ord(correct_key) - ord("a")
        correct_text = (
            options[correct_idx] if correct_idx < len(options) else options[0]
        )

        answer_key = f"quiz_answer_{quiz_idx}"
        selected = st.radio("Your answer:", options, index=None, key=answer_key)

        if st.button("Submit answer", key=f"submit_{quiz_idx}", type="primary"):
            if selected:
                is_correct = selected == correct_text
                record_quiz_answer(
                    conn,
                    user_session,
                    item["topic_id"],
                    item["quiz_id"],
                    selected,
                    is_correct,
                )
                st.session_state.quiz_answered.append(
                    {
                        "topic_title": item["topic_title"],
                        "question": item["question"],
                        "correct": is_correct,
                    }
                )
                if is_correct:
                    st.session_state.quiz_score = (
                        st.session_state.get("quiz_score", 0) + 1
                    )
                st.session_state.quiz_index = quiz_idx + 1

                if is_correct:
                    st.toast("Correct!", icon=":material/check_circle:")
                else:
                    st.toast(
                        f"Wrong! Answer: {correct_text}", icon=":material/cancel:"
                    )
                st.rerun()
            else:
                st.warning("Select an answer first.", icon=":material/warning:")

    conn.close()
