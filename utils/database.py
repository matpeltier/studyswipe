import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from utils.models import (
    Topic,
    TopicMetrics,
    FactCard,
    QuizItem,
    SavedTopic,
    QuizHistoryEntry,
    TopicCard,
)

import tempfile
import os

_DB_DIR = os.path.join(tempfile.gettempdir(), "studyswipe")
os.makedirs(_DB_DIR, exist_ok=True)
DB_PATH = os.path.join(_DB_DIR, "studyswipe.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS topics (
            topic_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            category TEXT NOT NULL,
            wikidata_id TEXT,
            image_url TEXT,
            url TEXT,
            why_matters TEXT
        );

        CREATE TABLE IF NOT EXISTS topic_metrics (
            topic_id TEXT PRIMARY KEY REFERENCES topics(topic_id),
            pageviews_7d INTEGER DEFAULT 0,
            pageviews_30d INTEGER DEFAULT 0,
            trend_score REAL DEFAULT 0.0,
            difficulty_score REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS fact_cards (
            fact_id TEXT PRIMARY KEY,
            topic_id TEXT NOT NULL REFERENCES topics(topic_id),
            fact_text TEXT NOT NULL,
            source_section TEXT
        );

        CREATE TABLE IF NOT EXISTS quiz_items (
            quiz_id TEXT PRIMARY KEY,
            topic_id TEXT NOT NULL REFERENCES topics(topic_id),
            question TEXT NOT NULL,
            option_a TEXT DEFAULT '',
            option_b TEXT DEFAULT '',
            option_c TEXT DEFAULT '',
            option_d TEXT DEFAULT '',
            correct_option TEXT DEFAULT 'a'
        );

        CREATE TABLE IF NOT EXISTS saved_topics (
            user_session TEXT NOT NULL,
            topic_id TEXT NOT NULL REFERENCES topics(topic_id),
            collection_name TEXT NOT NULL DEFAULT 'General',
            saved_at TEXT NOT NULL,
            PRIMARY KEY (user_session, topic_id, collection_name)
        );

        CREATE TABLE IF NOT EXISTS quiz_history (
            history_id TEXT PRIMARY KEY,
            user_session TEXT NOT NULL,
            topic_id TEXT NOT NULL REFERENCES topics(topic_id),
            quiz_id TEXT NOT NULL REFERENCES quiz_items(quiz_id),
            selected_option TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            answered_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS viewed_topics (
            user_session TEXT NOT NULL,
            topic_id TEXT NOT NULL REFERENCES topics(topic_id),
            viewed_at TEXT NOT NULL,
            PRIMARY KEY (user_session, topic_id)
        );

        CREATE INDEX IF NOT EXISTS idx_topics_category ON topics(category);
        CREATE INDEX IF NOT EXISTS idx_fact_cards_topic ON fact_cards(topic_id);
        CREATE INDEX IF NOT EXISTS idx_quiz_items_topic ON quiz_items(topic_id);
        CREATE INDEX IF NOT EXISTS idx_saved_topics_session ON saved_topics(user_session);
        CREATE INDEX IF NOT EXISTS idx_quiz_history_session ON quiz_history(user_session);
        CREATE INDEX IF NOT EXISTS idx_viewed_topics_session ON viewed_topics(user_session);
    """)
    conn.commit()
    conn.close()


def insert_topic(conn: sqlite3.Connection, topic: Topic):
    conn.execute(
        """INSERT OR IGNORE INTO topics (topic_id, title, summary, category, wikidata_id, image_url, url, why_matters)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            topic.topic_id,
            topic.title,
            topic.summary,
            topic.category,
            topic.wikidata_id,
            topic.image_url,
            topic.url,
            topic.why_matters,
        ),
    )


def insert_metrics(conn: sqlite3.Connection, metrics: TopicMetrics):
    conn.execute(
        """INSERT OR IGNORE INTO topic_metrics (topic_id, pageviews_7d, pageviews_30d, trend_score, difficulty_score)
           VALUES (?, ?, ?, ?, ?)""",
        (
            metrics.topic_id,
            metrics.pageviews_7d,
            metrics.pageviews_30d,
            metrics.trend_score,
            metrics.difficulty_score,
        ),
    )


def insert_fact(conn: sqlite3.Connection, fact: FactCard):
    conn.execute(
        """INSERT OR IGNORE INTO fact_cards (fact_id, topic_id, fact_text, source_section)
           VALUES (?, ?, ?, ?)""",
        (fact.fact_id, fact.topic_id, fact.fact_text, fact.source_section),
    )


def insert_quiz(conn: sqlite3.Connection, quiz: QuizItem):
    conn.execute(
        """INSERT OR IGNORE INTO quiz_items (quiz_id, topic_id, question, option_a, option_b, option_c, option_d, correct_option)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            quiz.quiz_id,
            quiz.topic_id,
            quiz.question,
            quiz.option_a,
            quiz.option_b,
            quiz.option_c,
            quiz.option_d,
            quiz.correct_option,
        ),
    )


def get_topic_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) as c FROM topics").fetchone()
    return row["c"]


def get_categories(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT category FROM topics ORDER BY category"
    ).fetchall()
    return [r["category"] for r in rows]


def get_topic_card(
    conn: sqlite3.Connection, topic_id: str, user_session: str
) -> Optional[TopicCard]:
    row = conn.execute(
        "SELECT * FROM topics WHERE topic_id = ?", (topic_id,)
    ).fetchone()
    if not row:
        return None
    topic = Topic(**dict(row))

    mrow = conn.execute(
        "SELECT * FROM topic_metrics WHERE topic_id = ?", (topic_id,)
    ).fetchone()
    metrics = TopicMetrics(**dict(mrow)) if mrow else None

    frows = conn.execute(
        "SELECT * FROM fact_cards WHERE topic_id = ?", (topic_id,)
    ).fetchall()
    facts = [FactCard(**dict(r)) for r in frows]

    qrows = conn.execute(
        "SELECT * FROM quiz_items WHERE topic_id = ?", (topic_id,)
    ).fetchall()
    quizzes = [QuizItem(**dict(r)) for r in qrows]

    saved = (
        conn.execute(
            "SELECT 1 FROM saved_topics WHERE topic_id = ? AND user_session = ?",
            (topic_id, user_session),
        ).fetchone()
        is not None
    )

    viewed = (
        conn.execute(
            "SELECT 1 FROM viewed_topics WHERE topic_id = ? AND user_session = ?",
            (topic_id, user_session),
        ).fetchone()
        is not None
    )

    return TopicCard(
        topic=topic,
        metrics=metrics,
        facts=facts,
        quiz_items=quizzes,
        is_saved=saved,
        is_viewed=viewed,
    )


def get_feed_topics(
    conn: sqlite3.Connection,
    user_session: str,
    category: Optional[str] = None,
    sort_by: str = "trending",
    limit: int = 50,
    exclude_ids: Optional[list[str]] = None,
) -> list[TopicCard]:
    excluded = exclude_ids or []
    query = """
        SELECT t.topic_id FROM topics t
        LEFT JOIN topic_metrics m ON t.topic_id = m.topic_id
        WHERE 1=1
    """
    params: list = []

    if category and category != "All":
        query += " AND t.category = ?"
        params.append(category)

    if excluded:
        placeholders = ",".join("?" for _ in excluded)
        query += f" AND t.topic_id NOT IN ({placeholders})"
        params.extend(excluded)

    if sort_by == "trending":
        query += " ORDER BY COALESCE(m.trend_score, 0) DESC, COALESCE(m.pageviews_7d, 0) DESC"
    elif sort_by == "popular":
        query += " ORDER BY COALESCE(m.pageviews_30d, 0) DESC"
    elif sort_by == "random":
        query += " ORDER BY RANDOM()"
    elif sort_by == "difficulty_easy":
        query += " ORDER BY COALESCE(m.difficulty_score, 2.0) ASC"
    elif sort_by == "difficulty_hard":
        query += " ORDER BY COALESCE(m.difficulty_score, 2.0) DESC"
    else:
        query += " ORDER BY t.title ASC"

    query += " LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    cards = []
    for r in rows:
        card = get_topic_card(conn, r["topic_id"], user_session)
        if card:
            cards.append(card)
    return cards


def save_topic(
    conn: sqlite3.Connection, user_session: str, topic_id: str, collection_name: str
):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR IGNORE INTO saved_topics (user_session, topic_id, collection_name, saved_at)
           VALUES (?, ?, ?, ?)""",
        (user_session, topic_id, collection_name, now),
    )
    conn.commit()


def unsave_topic(
    conn: sqlite3.Connection,
    user_session: str,
    topic_id: str,
    collection_name: Optional[str] = None,
):
    if collection_name:
        conn.execute(
            "DELETE FROM saved_topics WHERE user_session = ? AND topic_id = ? AND collection_name = ?",
            (user_session, topic_id, collection_name),
        )
    else:
        conn.execute(
            "DELETE FROM saved_topics WHERE user_session = ? AND topic_id = ?",
            (user_session, topic_id),
        )
    conn.commit()


def get_saved_topics(
    conn: sqlite3.Connection, user_session: str, collection_name: Optional[str] = None
) -> list[TopicCard]:
    query = """
        SELECT DISTINCT t.topic_id FROM topics t
        INNER JOIN saved_topics s ON t.topic_id = s.topic_id
        WHERE s.user_session = ?
    """
    params: list = [user_session]

    if collection_name and collection_name != "All Collections":
        query += " AND s.collection_name = ?"
        params.append(collection_name)

    query += " ORDER BY s.saved_at DESC"
    rows = conn.execute(query, params).fetchall()
    return [get_topic_card(conn, r["topic_id"], user_session) for r in rows if r]


def get_collections(conn: sqlite3.Connection, user_session: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT collection_name FROM saved_topics WHERE user_session = ? ORDER BY collection_name",
        (user_session,),
    ).fetchall()
    return [r["collection_name"] for r in rows]


def record_quiz_answer(
    conn: sqlite3.Connection,
    user_session: str,
    topic_id: str,
    quiz_id: str,
    selected_option: str,
    is_correct: bool,
):
    now = datetime.now(timezone.utc).isoformat()
    history_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO quiz_history (history_id, user_session, topic_id, quiz_id, selected_option, is_correct, answered_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            history_id,
            user_session,
            topic_id,
            quiz_id,
            selected_option,
            int(is_correct),
            now,
        ),
    )
    conn.commit()


def record_view(conn: sqlite3.Connection, user_session: str, topic_id: str):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO viewed_topics (user_session, topic_id, viewed_at)
           VALUES (?, ?, ?)""",
        (user_session, topic_id, now),
    )
    conn.commit()


def get_quiz_history(
    conn: sqlite3.Connection, user_session: str
) -> list[QuizHistoryEntry]:
    rows = conn.execute(
        "SELECT * FROM quiz_history WHERE user_session = ? ORDER BY answered_at DESC",
        (user_session,),
    ).fetchall()
    return [QuizHistoryEntry(**dict(r)) for r in rows]


def get_quiz_stats(conn: sqlite3.Connection, user_session: str) -> dict:
    row = conn.execute(
        """SELECT
            COUNT(*) as total_answers,
            SUM(is_correct) as correct_answers,
            COUNT(DISTINCT topic_id) as topics_quizzed,
            COUNT(DISTINCT quiz_id) as unique_questions
        FROM quiz_history WHERE user_session = ?""",
        (user_session,),
    ).fetchone()
    if not row or row["total_answers"] == 0:
        return {
            "total_answers": 0,
            "correct_answers": 0,
            "accuracy": 0.0,
            "topics_quizzed": 0,
            "unique_questions": 0,
        }
    total = row["total_answers"]
    correct = row["correct_answers"] or 0
    return {
        "total_answers": total,
        "correct_answers": correct,
        "accuracy": round(correct / total * 100, 1),
        "topics_quizzed": row["topics_quizzed"],
        "unique_questions": row["unique_questions"],
    }


def get_analytics(conn: sqlite3.Connection, user_session: str) -> dict:
    stats = get_quiz_stats(conn, user_session)

    viewed = conn.execute(
        "SELECT COUNT(DISTINCT topic_id) as c FROM viewed_topics WHERE user_session = ?",
        (user_session,),
    ).fetchone()["c"]

    saved = conn.execute(
        "SELECT COUNT(DISTINCT topic_id) as c FROM saved_topics WHERE user_session = ?",
        (user_session,),
    ).fetchone()["c"]

    cat_rows = conn.execute(
        """SELECT t.category, COUNT(DISTINCT h.topic_id) as quizzed
        FROM topics t
        LEFT JOIN quiz_history h ON t.topic_id = h.topic_id AND h.user_session = ?
        GROUP BY t.category
        ORDER BY quizzed DESC""",
        (user_session,),
    ).fetchall()
    category_stats = {r["category"]: r["quizzed"] for r in cat_rows}

    top_saved = conn.execute(
        """SELECT t.title, t.category, COUNT(*) as save_count
        FROM saved_topics s
        JOIN topics t ON s.topic_id = t.topic_id
        WHERE s.user_session = ?
        GROUP BY s.topic_id
        ORDER BY save_count DESC
        LIMIT 10""",
        (user_session,),
    ).fetchall()
    most_saved = [dict(r) for r in top_saved]

    accuracy_by_cat = conn.execute(
        """SELECT t.category,
            COUNT(*) as total,
            SUM(h.is_correct) as correct
        FROM quiz_history h
        JOIN topics t ON h.topic_id = t.topic_id
        WHERE h.user_session = ?
        GROUP BY t.category""",
        (user_session,),
    ).fetchall()
    category_accuracy = {}
    for r in accuracy_by_cat:
        total = r["total"]
        correct = r["correct"] or 0
        category_accuracy[r["category"]] = (
            round(correct / total * 100, 1) if total > 0 else 0.0
        )

    return {
        **stats,
        "viewed_count": viewed,
        "saved_count": saved,
        "category_stats": category_stats,
        "most_saved": most_saved,
        "category_accuracy": category_accuracy,
    }
