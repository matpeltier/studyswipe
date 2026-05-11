import random as _random

import streamlit as st
from utils.storage import (
    get_feed_topics,
    get_categories,
    record_quiz_answer,
    get_quiz_stats,
    add_xp,
)
from utils.constants import CATEGORY_COLORS, ACHIEVEMENT_NAMES
from utils.spaced_repetition import get_due_cards, record_review, get_card_state

user_session = st.session_state.get("user_session", "default")
categories = get_categories()
all_cats = ["All"] + categories

stats = get_quiz_stats(user_session)

with st.sidebar:
    st.subheader("Quiz settings")
    quiz_cat = st.selectbox("Category", all_cats, key="quiz_category")
    num_questions = st.slider("Questions", 3, 20, 5, key="quiz_num_q")
    difficulty_filter = st.selectbox(
        "Difficulty",
        ["All", "Easy", "Medium", "Hard"],
        key="quiz_difficulty",
    )
    sr_mode = st.toggle("Spaced repetition", value=False, key="sr_mode")

    if sr_mode:
        due = get_due_cards(limit=20)
        if due:
            st.caption(f":material/schedule: **{len(due)}** cards due for review")
        else:
            st.caption(":material/check_circle: No cards due — keep reviewing!")

if not st.session_state.get("quiz_active", False):
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
        st.session_state.sr_mode_active = sr_mode

        cat_filter = quiz_cat if quiz_cat != "All" else None
        sort_map = {
            "Easy": "difficulty_easy",
            "Medium": "trending",
            "Hard": "difficulty_hard",
        }
        sort_by = sort_map.get(difficulty_filter, "random")
        topics = get_feed_topics(
            user_session, category=cat_filter, sort_by=sort_by, limit=50
        )

        def _build_quiz_item(qi, topic):
            option_keys = ("option_a", "option_b", "option_c", "option_d")
            options = []
            correct_idx = 0
            for oi, opt_key in enumerate(option_keys):
                opt_val = qi.get(opt_key, "")
                if opt_val:
                    options.append(opt_val)
                    if opt_key == qi["correct_option"]:
                        correct_idx = oi
            return {
                "topic_id": topic["topic_id"],
                "topic_title": topic["title"],
                "category": topic["category"],
                "quiz_id": qi["quiz_id"],
                "question": qi["question"],
                "options": options,
                "correct_idx": correct_idx,
            }

        if sr_mode:
            due_quiz_ids = get_due_cards(user_session, limit=num_questions)
            sr_items = []
            for quiz_id in due_quiz_ids:
                for topic in topics:
                    for qi in topic.get("quizzes", []):
                        if qi["quiz_id"] == quiz_id:
                            sr_items.append(_build_quiz_item(qi, topic))
                            break
                    if len(sr_items) >= num_questions:
                        break
                if len(sr_items) >= num_questions:
                    break
            remaining = num_questions - len(sr_items)
            if remaining > 0:
                for topic in topics:
                    for qi in topic.get("quizzes", []):
                        if qi["quiz_id"] not in due_quiz_ids:
                            sr_items.append(_build_quiz_item(qi, topic))
                            if len(sr_items) >= num_questions:
                                break
                    if len(sr_items) >= num_questions:
                        break
            quiz_items = sr_items[:num_questions]
        else:
            quiz_items = []
            topic_index = 0
            while len(quiz_items) < num_questions and topic_index < len(topics):
                topic = topics[topic_index]
                for qi in topic.get("quizzes", []):
                    quiz_items.append(_build_quiz_item(qi, topic))
                    if len(quiz_items) >= num_questions:
                        break
                topic_index = topic_index + 1
            _random.shuffle(quiz_items)
            quiz_items = quiz_items[:num_questions]

        st.session_state.quiz_items = quiz_items
        st.rerun()

else:
    quiz_items = st.session_state.get("quiz_items", [])
    quiz_idx = st.session_state.get("quiz_index", 0)
    is_sr = st.session_state.get("sr_mode_active", False)

    if quiz_idx >= len(quiz_items):
        score = st.session_state.get("quiz_score", 0)
        total = len(quiz_items)
        pct = round(score / total * 100) if total > 0 else 0

        st.success("Quiz complete!", icon=":material/trophy:")
        add_xp(user_session, 20, "quiz_completed")

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric("Final score", f"{score}/{total}")
        with res_col2:
            st.metric("Accuracy", f"{pct}%")

        if pct >= 80:
            st.balloons()
            add_xp(user_session, 15, "high_score")
            st.markdown(":material/star: **Excellent!** You really know your topics! +15 XP bonus")
        elif pct >= 60:
            st.markdown(":material/thumb_up: **Good job!** Keep reviewing to improve.")
        else:
            st.markdown(":material/menu_book: **Keep learning!** Review saved topics and try again.")

        answered = st.session_state.get("quiz_answered", [])
        if answered:
            st.markdown("### Review")
            for ans in answered:
                icon = ":material/check_circle:" if ans["correct"] else ":material/cancel:"
                color = "green" if ans["correct"] else "red"
                st.markdown(f":{color}[{icon}] **{ans['topic_title']}** — {ans['question']}")

        if st.button(":material/refresh: New quiz", key="new_quiz_btn"):
            st.session_state.quiz_active = False
            st.rerun()
    else:
        item = quiz_items[quiz_idx]
        progress = (quiz_idx + 1) / len(quiz_items)
        st.progress(progress, text=f"Question {quiz_idx + 1} of {len(quiz_items)}")

        sr_state = get_card_state(item["quiz_id"]) if is_sr else None
        if sr_state and sr_state.get("repetitions", 0) > 0:
            interval = sr_state.get("interval", 0)
            reps = sr_state.get("repetitions", 0)
            st.caption(f":material/history: Review #{reps} (was due every {interval} days)")

        with st.container(border=True):
            st.markdown(
                f'<div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); '
                f'padding: 16px; border-radius: 8px; margin-bottom: 12px;">'
                f'<span style="color: white; font-size: 1.1rem;">'
                f'Question {quiz_idx + 1} of {len(quiz_items)}</span></div>',
                unsafe_allow_html=True,
            )
            cat_color = CATEGORY_COLORS.get(item["category"], "gray")
            st.markdown(f":{cat_color}-badge[{item['category']}]")
            st.markdown(f"**{item['topic_title']}**")
            st.markdown(f"### {item['question']}")

        options = item["options"]
        correct_idx = item["correct_idx"]
        correct_text = options[correct_idx]

        answer_key = f"quiz_answer_{quiz_idx}"
        selected = st.radio("Your answer:", options, index=None, key=answer_key)

        if is_sr:
            quality_labels = ["Again", "Hard", "Difficult", "Good", "Easy", "Perfect"]
            quality_colors = ["red", "orange", "orange", "green", "green", "blue"]
            quality_options = [
                f":{c}[{l}]" for l, c in zip(quality_labels, quality_colors)
            ]
            quality = st.radio(
                "How well did you know this?",
                quality_options,
                index=3,
                key=f"quality_{quiz_idx}",
                horizontal=True,
                label_visibility="collapsed",
            )

        if st.button("Submit answer", key=f"submit_{quiz_idx}", type="primary"):
            if selected:
                is_correct = selected == correct_text
                record_quiz_answer(
                    user_session,
                    item["topic_id"],
                    item["quiz_id"],
                    selected,
                    is_correct,
                )
                st.session_state.quiz_answered.append({
                    "topic_title": item["topic_title"],
                    "question": item["question"],
                    "correct": is_correct,
                })
                if is_correct:
                    st.session_state.quiz_score = st.session_state.get("quiz_score", 0) + 1
                    result = add_xp(user_session, 10, "correct_answer")
                else:
                    result = add_xp(user_session, 2, "wrong_answer")
                for ach in result.get("new_achievements", []):
                    name, desc = ACHIEVEMENT_NAMES.get(ach, (ach, ""))
                    st.toast(f"Achievement: {name} — {desc}", icon=":material/trophy:")
                st.session_state.quiz_index = quiz_idx + 1

                if is_correct:
                    st.toast("Correct! +10 XP", icon=":material/check_circle:")
                else:
                    st.toast(f"Wrong! Answer: {correct_text} (+2 XP)", icon=":material/cancel:")

                if is_sr:
                    q_val = quality_labels.index(
                        quality.replace(":red[", "").replace(":orange[", "")
                        .replace(":green[", "").replace(":blue[", "").rstrip("]")
                    )
                    record_review(item["quiz_id"], q_val)

                st.rerun()
            else:
                st.warning("Select an answer first.", icon=":material/warning:")
