import logging
import time

from utils.database import get_connection, get_topic_count
from utils.wikipedia_fetcher import fetch_and_add_article

logger = logging.getLogger(__name__)

SEED_TITLES = (
    "Albert Einstein",
    "Quantum mechanics",
    "Theory of relativity",
    "DNA",
    "Black hole",
    "Periodic table",
    "Evolution",
    "Climate change",
    "Artificial intelligence",
    "Solar System",
    "Atomic theory",
    "Photosynthesis",
    "Neuroscience",
    "Vaccine",
    "CRISPR",
    "General relativity",
    "Superconductivity",
    "Machine learning",
    "Robotics",
    "Internet",
    "Blockchain",
    "Virtual reality",
    "Space exploration",
    "Satellite",
    "3D printing",
    "Nanotechnology",
    "Cybersecurity",
    "Quantum computing",
    "Algorithm",
    "Drones",
    "World War II",
    "Roman Empire",
    "French Revolution",
    "Ancient Egypt",
    "Renaissance",
    "Byzantine Empire",
    "Viking Age",
    "Industrial Revolution",
    "Cold War",
    "Silk Road",
    "Democracy",
    "United Nations",
    "European Union",
    "Constitution",
    "Human rights",
    "Impressionism",
    "Jazz",
    "Ancient Greece",
    "Philosophy",
    "Opera",
)

MAX_RETRIES = 3


def seed_database(force=False, progress_cb=None):
    conn = get_connection()
    try:
        count = get_topic_count(conn)
        if count > 0 and not force:
            logger.info("Database already has %d topics, skipping seed.", count)
            return count

        titles_to_fetch = []
        existing_rows = conn.execute("SELECT title FROM topics").fetchall()
        existing = set()
        for r in existing_rows:
            existing.add(r["title"])
        for title in SEED_TITLES:
            if title not in existing:
                titles_to_fetch.append(title)

        if not titles_to_fetch:
            logger.info("All seed topics already in database.")
            return get_topic_count(conn)

        logger.info("Seeding %d topics from Wikipedia...", len(titles_to_fetch))
        added = 0
        for i, title in enumerate(titles_to_fetch):
            if progress_cb:
                progress_cb(i, len(titles_to_fetch), title)

            retries = 0
            tid = None
            while tid is None and retries < MAX_RETRIES:
                tid = fetch_and_add_article(title)
                if tid is None:
                    retries = retries + 1
                    if retries < MAX_RETRIES:
                        time.sleep(1)

            if tid:
                added = added + 1
                logger.info("  [%d/%d] Added: %s", i + 1, len(titles_to_fetch), title)
            else:
                logger.warning(
                    "  [%d/%d] Skipped: %s", i + 1, len(titles_to_fetch), title
                )

            time.sleep(0.3)

        final_count = get_topic_count(conn)
        logger.info(
            "Seeding complete: %d/%d topics added, %d total in DB.",
            added,
            len(titles_to_fetch),
            final_count,
        )
        return final_count
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_database(force=True)
