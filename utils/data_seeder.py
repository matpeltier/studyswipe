import json
import os
import random
import logging

from utils.database import (
    get_connection,
    insert_topic,
    insert_metrics,
    insert_fact,
    insert_quiz,
    get_topic_count,
)
from utils.models import Topic, TopicMetrics, FactCard, QuizItem

logger = logging.getLogger(__name__)

SEED_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "seed_topics.json")


def seed_database(force: bool = False):
    conn = get_connection()
    try:
        count = get_topic_count(conn)
        if count > 0 and not force:
            logger.info("Database already has %d topics, skipping seed.", count)
            return

        if not os.path.exists(SEED_FILE):
            logger.error("Seed file not found: %s", SEED_FILE)
            return

        with open(SEED_FILE, "r", encoding="utf-8") as f:
            topics_data = json.load(f)

        for item in topics_data:
            topic = Topic(
                topic_id=item["topic_id"],
                title=item["title"],
                summary=item["summary"],
                category=item["category"],
                url=item.get("url", ""),
                why_matters=item.get("why_matters", ""),
            )
            insert_topic(conn, topic)

            base_pv = random.randint(5000, 500000)
            pv_7d = int(base_pv * random.uniform(0.15, 0.35))
            metrics = TopicMetrics(
                topic_id=item["topic_id"],
                pageviews_7d=pv_7d,
                pageviews_30d=base_pv,
                trend_score=round(random.uniform(0.1, 10.0), 2),
                difficulty_score=item.get(
                    "difficulty_score", round(random.uniform(1.0, 5.0), 1)
                ),
            )
            insert_metrics(conn, metrics)

            for fact_data in item.get("facts", []):
                fact = FactCard(
                    fact_id=fact_data["fact_id"],
                    topic_id=item["topic_id"],
                    fact_text=fact_data["fact_text"],
                    source_section=fact_data.get("source_section", ""),
                )
                insert_fact(conn, fact)

            for quiz_data in item.get("quiz", []):
                quiz = QuizItem(
                    quiz_id=quiz_data["quiz_id"],
                    topic_id=item["topic_id"],
                    question=quiz_data["question"],
                    option_a=quiz_data.get("option_a", ""),
                    option_b=quiz_data.get("option_b", ""),
                    option_c=quiz_data.get("option_c", ""),
                    option_d=quiz_data.get("option_d", ""),
                    correct_option=quiz_data.get("correct_option", "a"),
                )
                insert_quiz(conn, quiz)

        conn.commit()
        logger.info("Seeded %d topics successfully.", len(topics_data))
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_database(force=True)
