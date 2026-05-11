import time

import streamlit as st
from utils.storage import (
    get_feed_topics,
    get_categories,
    add_xp,
    create_lobby,
    join_lobby,
    start_lobby,
    finish_lobby_player,
    cancel_lobby,
    get_lobby,
)
from utils.constants import CATEGORY_COLORS, ACHIEVEMENT_NAMES

st.set_page_config(
    page_title="StudySwipe - Multiplayer",
    page_icon=":material/group:",
    layout="wide",
)

user_session = st.session_state.get("user_session", "default")
categories = get_categories()
all_cats = ["All"] + categories

with st.sidebar:
    st.subheader("Lobby settings")
    mp_cat = st.selectbox("Category", all_cats, key="mp_category")
    mp_num_q = st.slider("Questions", 3, 20, 5, key="mp_num_q")
    mp_difficulty = st.selectbox(
        "Difficulty",
        ["All", "Easy", "Medium", "Hard"],
        key="mp_difficulty",
    )

lobby_state = st.session_state.get("lobby_state", "none")

if lobby_state == "waiting":
    lobby_code = st.session_state.get("lobby_code", "")
    lobby = get_lobby(lobby_code)

    if not lobby or lobby["status"] == "cancelled":
        st.warning("This lobby has been cancelled by the host.")
        st.session_state.lobby_state = "none"
        st.session_state.lobby_code = None
        st.rerun()

    is_host = st.session_state.get("is_host", False)

    st.subheader(":material/group: Lobby")
    st.code(lobby_code)
    st.caption("Share this code with other players")

    st.markdown("### Players")
    for i, p in enumerate(lobby["players"]):
        you = " (you)" if p["session"] == user_session else ""
        host_tag = " :crown:" if i == 0 else ""
        st.markdown(f"{'🟢' if not p['finished'] else '✅'} **{p['name']}**{host_tag}{you}")

    btn_col1, btn_col2 = st.columns(2)
    if is_host:
        with btn_col1:
            if len(lobby["players"]) < 2:
                st.info("Waiting for at least 1 more player...")
            else:
                if st.button(":material/play_arrow: Start game!", key="start_lobby_btn", type="primary", use_container_width=True):
                    from utils.challenge import get_challenge_questions
                    topics = get_feed_topics(user_session, category=None, sort_by="trending", limit=100)
                    seed_data = lobby["seed_data"]
                    n = lobby["num_questions"]
                    quiz_items = get_challenge_questions(seed_data, topics, n)
                    start_lobby(lobby_code, quiz_items=quiz_items)
                    st.session_state.quiz_active = True
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_score = 0
                    st.session_state.quiz_answered = []
                    st.session_state.quiz_items = quiz_items
                    st.session_state.lobby_state = "playing"
                    st.rerun()
        with btn_col2:
            if st.button(":material/cancel: Cancel lobby", key="cancel_lobby_btn", type="secondary", use_container_width=True):
                cancel_lobby(lobby_code)
                st.session_state.lobby_state = "none"
                st.session_state.lobby_code = None
                st.session_state.is_host = False
                st.rerun()
    else:
        with btn_col1:
            if st.button(":material/logout: Leave lobby", key="leave_lobby_btn", use_container_width=True):
                st.session_state.lobby_state = "none"
                st.session_state.lobby_code = None
                st.rerun()

    placeholder = st.empty()
    with placeholder:
        st.caption("Refreshing lobby...")

    time.sleep(3)

    lobby = get_lobby(lobby_code)
    if not lobby:
        st.rerun()
    elif lobby["status"] == "cancelled":
        st.session_state.lobby_state = "none"
        st.session_state.lobby_code = None
        st.rerun()
    elif lobby["status"] == "active":
        quiz_items = lobby.get("quiz_items", [])
        if not quiz_items:
            st.error("No quiz questions available — the host may still be starting.")
            st.rerun()

        st.session_state.quiz_active = True
        st.session_state.quiz_index = 0
        st.session_state.quiz_score = 0
        st.session_state.quiz_answered = []
        st.session_state.quiz_items = quiz_items
        st.session_state.lobby_state = "playing"
        st.rerun()
    else:
        st.rerun()

elif lobby_state == "done":
    lobby_code = st.session_state.get("lobby_code", "")
    lobby = get_lobby(lobby_code)

    if lobby:
        st.subheader(":material/emoji_events: Final Leaderboard")
        sorted_players = sorted(lobby["players"], key=lambda p: (p["score"] or 0), reverse=True)
        for i, p in enumerate(sorted_players):
            is_me = p["session"] == user_session
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i + 1}"
            score_str = f"{p['score']}/{p['total']}" if p["score"] is not None else "DNF"
            pct_str = f" ({round(p['score']/p['total']*100)}%)" if p["score"] is not None else ""
            you_tag = " (you)" if is_me else ""
            host_tag = " :crown:" if i == 0 and p["score"] is not None else ""
            style = "**" if is_me else ""
            st.markdown(f"{style}{medal} {p['name']}: {score_str}{pct_str}{host_tag}{you_tag}{style}")

        if st.button(":material/refresh: New lobby", key="exit_lobby_btn"):
            st.session_state.lobby_state = "none"
            st.session_state.lobby_code = None
            st.rerun()

elif st.session_state.get("quiz_active", False):
    quiz_items = st.session_state.get("quiz_items", [])
    quiz_idx = st.session_state.get("quiz_index", 0)

    if quiz_idx >= len(quiz_items):
        score = st.session_state.get("quiz_score", 0)
        total = len(quiz_items)
        pct = round(score / total * 100) if total > 0 else 0

        lobby_code = st.session_state.get("lobby_code", "")
        finish_lobby_player(lobby_code, user_session, score, total)
        st.session_state.lobby_state = "done"

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
            st.markdown(":material/star: **Excellent!** +15 XP bonus")
        elif pct >= 60:
            st.markdown(":material/thumb_up: **Good job!**")
        else:
            st.markdown(":material/menu_book: **Keep learning!**")

        st.markdown("---")
        st.markdown("### :material/hourglass_empty: Waiting for other players...")
        placeholder = st.empty()
        with placeholder:
            st.spinner("Checking for other players...")

        time.sleep(3)

        lobby = get_lobby(lobby_code)
        if lobby and lobby["status"] == "finished":
            st.session_state.lobby_state = "done"
            st.rerun()
        else:
            st.rerun()
    else:
        item = quiz_items[quiz_idx]
        progress = (quiz_idx + 1) / len(quiz_items)
        st.progress(progress, text=f"Question {quiz_idx + 1} of {len(quiz_items)}")

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

        answer_key = f"mp_answer_{quiz_idx}"
        selected = st.radio("Your answer:", options, index=None, key=answer_key)

        if st.button("Submit answer", key=f"mp_submit_{quiz_idx}", type="primary"):
            if selected:
                is_correct = selected == correct_text
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

                st.rerun()
            else:
                st.warning("Select an answer first.", icon=":material/warning:")

else:
    st.subheader(":material/group: Multiplayer")
    st.caption("Challenge your friends to a quiz battle!")

    mp_col1, mp_col2 = st.columns(2)

    with mp_col1:
        with st.container(border=True):
            st.markdown(":material/add_circle: **Create Lobby**")
            st.caption("Start a game and invite others")
            player_name = st.text_input("Your name", value="Player 1", key="host_name")
            if st.button("Create lobby", key="create_lobby_btn", type="primary", use_container_width=True):
                from utils.challenge import generate_challenge_code
                code, seed_data = generate_challenge_code(
                    mp_cat, mp_num_q, mp_difficulty
                )
                create_lobby(code, user_session, player_name, seed_data, mp_num_q)
                st.session_state.lobby_code = code
                st.session_state.lobby_state = "waiting"
                st.session_state.is_host = True
                st.rerun()

    with mp_col2:
        with st.container(border=True):
            st.markdown(":material/login: **Join Lobby**")
            st.caption("Enter a code to join a game")
            join_code = st.text_input("Lobby code", key="join_code_input")
            join_name = st.text_input("Your name", value="Player 2", key="join_name")
            if st.button("Join lobby", key="join_lobby_btn", use_container_width=True):
                lobby = join_lobby(join_code, user_session, join_name)
                if lobby:
                    st.session_state.lobby_code = join_code
                    st.session_state.lobby_state = "waiting"
                    st.session_state.is_host = False
                    st.rerun()
                else:
                    st.error("Lobby not found or already started")
