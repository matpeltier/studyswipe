import uuid
import streamlit as st
from utils.storage import get_topic_count
from utils.data_seeder import seed_database

st.set_page_config(
    page_title="StudySwipe",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Navigation tabs — much bigger */
    .stNavigationTabs [data-baseweb="tab"],
    [data-testid="stTabs"] [data-baseweb="tab"],
    [data-baseweb="tab"] {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        padding: 16px 36px !important;
        min-height: 56px !important;
    }
    .stNavigationTabs [data-baseweb="tab-list"],
    [data-testid="stTabs"] [data-baseweb="tab-list"],
    [data-baseweb="tab-list"] {
        gap: 4px !important;
        height: auto !important;
    }
    .stNavigationTabs [data-baseweb="tab-border"],
    [data-testid="stTabs"] [data-baseweb="tab-border"],
    [data-baseweb="tab-border"] {
        height: 5px !important;
    }
    header [data-testid="stTabs"],
    .stApp > header > div {
        padding: 8px 16px !important;
        min-height: 64px !important;
    }

    /* Sidebar logo */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

if "user_session" not in st.session_state:
    st.session_state.user_session = str(uuid.uuid4())

topic_count = get_topic_count()

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

st.markdown("""
<div style="display: flex; align-items: center; gap: 14px; padding: 8px 0 12px 0;">
    <span style="font-size: 2.8rem; line-height: 1;">&#127891;</span>
    <div>
        <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #6366f1; letter-spacing: -0.02em;">StudySwipe</h1>
        <p style="margin: 0; font-size: 0.9rem; color: #94a3b8;">Swipe, save, and quiz yourself on anything.</p>
    </div>
</div>
""", unsafe_allow_html=True)

topic_count = get_topic_count()

with st.sidebar:
    st.markdown("# :material/school: StudySwipe")
    st.caption("Swipe, save, and quiz yourself on anything.")
    st.markdown("---")
    st.caption(f":material/database: **{topic_count}** topics loaded")

page.run()
