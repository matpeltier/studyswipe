import uuid
import streamlit as st
from utils.database import init_db, get_connection, get_topic_count
from utils.data_seeder import seed_database

st.set_page_config(
    page_title="StudySwipe",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

if "user_session" not in st.session_state:
    st.session_state.user_session = str(uuid.uuid4())

conn = get_connection()
topic_count = get_topic_count(conn)
conn.close()

if topic_count == 0:
    progress_text = st.empty()
    progress_bar = st.progress(0, text="Loading topics from Wikipedia...")

    def on_progress(current, total, title):
        pct = int((current + 1) / total * 100)
        progress_bar.progress(
            pct,
            text=f"Loading {current + 1}/{total}: {title}",
        )

    seed_database(progress_cb=on_progress)
    progress_bar.empty()
    progress_text.empty()

pages = [
    st.Page("app_pages/feed.py", title="Feed", icon=":material/swipe:"),
    st.Page("app_pages/discover.py", title="Discover", icon=":material/explore:"),
    st.Page("app_pages/saved.py", title="Saved", icon=":material/bookmark:"),
    st.Page("app_pages/quiz.py", title="Quiz", icon=":material/quiz:"),
    st.Page("app_pages/analytics.py", title="Analytics", icon=":material/analytics:"),
]

page = st.navigation(pages, position="top")

conn = get_connection()
topic_count = get_topic_count(conn)
conn.close()

with st.sidebar:
    st.markdown("## :material/school: StudySwipe")
    st.caption("Swipe, save, and quiz yourself on anything.")
    st.markdown("---")
    st.caption(f":material/database: **{topic_count}** topics loaded")

page.run()
