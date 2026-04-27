import logging
import re
import uuid
from typing import Optional

from utils.ai_quiz_generator import generate_quizzes_with_ai
from utils.database import (
    get_connection,
    insert_topic,
    insert_metrics,
    insert_fact,
    insert_quiz,
    get_topic_count,
)
from utils.models import Topic, TopicMetrics, FactCard, QuizItem
from utils.wikipedia_api import (
    get_summary,
    get_extract,
    get_page_views,
    search_articles,
    get_random_articles,
)

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = {
    "Science": [
        "physics",
        "chemistry",
        "biology",
        "medicine",
        "astronomy",
        "genetics",
        "quantum",
        "atom",
        "molecule",
        "evolution",
        "dna",
        "cell",
        "planet",
        "star",
        "galaxy",
        "climate",
        "ecosystem",
        "species",
        "element",
        "chemical",
        "energy",
        "force",
        "gravity",
        "particle",
    ],
    "History": [
        "war",
        "empire",
        "kingdom",
        "revolution",
        "ancient",
        "medieval",
        "dynasty",
        "battle",
        "treaty",
        "colonial",
        "century",
        "civilization",
        "pharaoh",
        "roman",
        "greece",
        "renaissance",
        "independence",
        "conquest",
        "monarchy",
        "republic",
    ],
    "Politics": [
        "democracy",
        "election",
        "government",
        "parliament",
        "congress",
        "constitution",
        "law",
        "rights",
        "vote",
        "political",
        "president",
        "senate",
        "legislation",
        "policy",
        "diplomacy",
        "treaty",
        "international",
        "united nations",
        "nato",
        "eu ",
    ],
    "Culture": [
        "art",
        "music",
        "painting",
        "sculpture",
        "film",
        "literature",
        "poetry",
        "theatre",
        "theater",
        "dance",
        "architecture",
        "mythology",
        "language",
        "religion",
        "festival",
        "cuisine",
        "fashion",
        "design",
        "opera",
        "jazz",
        "rock",
        "cinema",
    ],
    "Technology": [
        "computer",
        "software",
        "internet",
        "algorithm",
        "artificial intelligence",
        "robot",
        "digital",
        "electronic",
        "programming",
        "data",
        "network",
        "machine learning",
        "blockchain",
        "virtual reality",
        "drone",
        "satellite",
        "rocket",
        "space",
        "engineering",
        "innovation",
    ],
}


def _guess_category(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text)
    if not scores or max(scores.values()) == 0:
        return "Technology"
    return max(scores, key=scores.get)


def _extract_facts_from_sections(extract: str) -> list[str]:
    paragraphs = [p.strip() for p in extract.split("\n\n") if p.strip()]
    facts = []
    for para in paragraphs[:4]:
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 30 and len(sent) < 300 and not sent.startswith("="):
                facts.append(sent)
                if len(facts) >= 5:
                    return facts
    return facts


def _generate_quiz_from_sentence(sentence: str, idx: int) -> Optional[QuizItem]:
    numbers = re.findall(r"\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b", sentence)
    if numbers:
        original = numbers[0]
        try:
            val = float(original.replace(",", ""))
            wrong_a = str(int(val * 2)) if val > 1 else str(val + 1)
            wrong_b = str(int(val / 2)) if val > 2 else str(val + 2)
            wrong_c = str(int(val + val * 0.5))
            question = sentence.replace(original, "____")
            return QuizItem(
                quiz_id=f"wiki-q-{idx}",
                topic_id="",
                question=question,
                option_a=original,
                option_b=wrong_a,
                option_c=wrong_b,
                option_d=wrong_c,
                correct_option="a",
            )
        except (ValueError, ZeroDivisionError):
            pass

    year_match = re.findall(r"\b(1[0-9]{3}|20[0-2][0-9])\b", sentence)
    if year_match:
        original = year_match[0]
        y = int(original)
        offsets = [-10, 10, -50, 50, 5, -5]
        wrongs = []
        for off in offsets:
            w = str(y + off)
            if w != original:
                wrongs.append(w)
            if len(wrongs) >= 3:
                break
        while len(wrongs) < 3:
            wrongs.append(str(y + len(wrongs) + 1))
        question = sentence.replace(original, "____")
        return QuizItem(
            quiz_id=f"wiki-q-{idx}",
            topic_id="",
            question=question,
            option_a=original,
            option_b=wrongs[0],
            option_c=wrongs[1],
            option_d=wrongs[2],
            correct_option="a",
        )

    return None


def _generate_quizzes(facts: list[str], prefix: str) -> list[QuizItem]:
    quizzes = []
    for i, fact in enumerate(facts):
        quiz = _generate_quiz_from_sentence(fact, i)
        if quiz:
            quiz.quiz_id = f"wiki-{prefix}-q{i}"
            quizzes.append(quiz)
    return quizzes


def fetch_and_add_article(title: str) -> Optional[str]:
    summary_data = get_summary(title)
    if not summary_data or not summary_data.get("extract"):
        return None

    extract_text = get_extract(title, sentences=10) or ""
    pageviews = get_page_views(title)

    topic_id = f"wiki-{uuid.uuid4().hex[:8]}"
    category = _guess_category(title, summary_data["extract"])
    summary = summary_data["extract"]

    if len(summary) < 50:
        return None

    topic = Topic(
        topic_id=topic_id,
        title=summary_data["title"],
        summary=summary,
        category=category,
        image_url=summary_data.get("thumbnail"),
        url=summary_data.get("url", ""),
        why_matters=f"Discovered via Wikipedia. {summary[:100]}...",
    )

    facts_text = _extract_facts_from_sections(extract_text) if extract_text else []
    if not facts_text:
        sentences = re.split(r"(?<=[.!?])\s+", summary)
        facts_text = [s.strip() for s in sentences if len(s.strip()) > 30][:4]

    pv_7d = 0
    pv_30d = 0
    trend = 0.0
    if pageviews:
        pv_7d = pageviews["pageviews_7d"]
        pv_30d = pageviews["pageviews_30d"]
        trend = round(pv_7d / max(pv_30d, 1) * 10, 2)

    metrics = TopicMetrics(
        topic_id=topic_id,
        pageviews_7d=pv_7d,
        pageviews_30d=pv_30d,
        trend_score=trend,
        difficulty_score=round(len(summary.split()) / 20, 1),
    )

    fact_cards = []
    for i, ft in enumerate(facts_text[:5]):
        fact_cards.append(
            FactCard(
                fact_id=f"{topic_id}-f{i}",
                topic_id=topic_id,
                fact_text=ft,
            )
        )

    ai_raw = generate_quizzes_with_ai(topic.title, summary, facts_text, count=3)
    if ai_raw:
        quizzes = []
        for i, qd in enumerate(ai_raw):
            quizzes.append(
                QuizItem(
                    quiz_id=f"ai-{topic_id}-q{i}",
                    topic_id=topic_id,
                    question=qd["question"],
                    option_a=qd["option_a"],
                    option_b=qd["option_b"],
                    option_c=qd["option_c"],
                    option_d=qd["option_d"],
                    correct_option=qd["correct_option"],
                )
            )
    else:
        quizzes = _generate_quizzes(facts_text, topic_id)
        for q in quizzes:
            q.topic_id = topic_id

    conn = get_connection()
    try:
        insert_topic(conn, topic)
        insert_metrics(conn, metrics)
        for fc in fact_cards:
            insert_fact(conn, fc)
        for qz in quizzes:
            insert_quiz(conn, qz)
        conn.commit()
        return topic_id
    except Exception as e:
        logger.error("Failed to insert article %s: %s", title, e)
        conn.rollback()
        return None
    finally:
        conn.close()


def fetch_trending_articles(count: int = 10) -> list[str]:
    added = []
    titles = get_random_articles(count * 3)
    for title in titles:
        if len(added) >= count:
            break
        tid = fetch_and_add_article(title)
        if tid:
            added.append(tid)
    return added


def search_and_add(query: str, max_results: int = 5) -> list[str]:
    results = search_articles(query, limit=max_results * 2)
    added = []
    for r in results:
        if len(added) >= max_results:
            break
        tid = fetch_and_add_article(r["title"])
        if tid:
            added.append(tid)
    return added


def refresh_pageviews_for_existing() -> int:
    conn = get_connection()
    rows = conn.execute("SELECT topic_id, title FROM topics").fetchall()
    conn.close()

    updated = 0
    for row in rows:
        title = row["title"].replace(" ", "_")
        pv = get_page_views(title)
        if pv:
            conn = get_connection()
            conn.execute(
                "UPDATE topic_metrics SET pageviews_7d = ?, pageviews_30d = ?, trend_score = ? WHERE topic_id = ?",
                (
                    pv["pageviews_7d"],
                    pv["pageviews_30d"],
                    round(pv["pageviews_7d"] / max(pv["pageviews_30d"], 1) * 10, 2),
                    row["topic_id"],
                ),
            )
            conn.commit()
            conn.close()
            updated += 1
    return updated
