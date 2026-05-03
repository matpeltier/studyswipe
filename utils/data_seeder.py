import time

from utils.storage import get_topic_count
from utils.wikipedia_fetcher import fetch_and_add_article

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
    count = get_topic_count()
    if count > 0 and not force:
        print(f"Database already has {count} topics, skipping seed.")
        return count

    titles_to_fetch = []
    from utils.storage import load_data
    data = load_data()
    existing = set()
    for topic in data["topics"]:
        existing.add(topic["title"])
    for title in SEED_TITLES:
        if title not in existing:
            titles_to_fetch.append(title)

    if not titles_to_fetch:
        print("All seed topics already in database.")
        return get_topic_count()

    print(f"Seeding {len(titles_to_fetch)} topics from Wikipedia...")
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
            print(f"  [{i + 1}/{len(titles_to_fetch)}] Added: {title}")
        else:
            print(f"  [{i + 1}/{len(titles_to_fetch)}] Skipped: {title}")

        time.sleep(0.3)

    final_count = get_topic_count()
    print(f"Seeding complete: {added}/{len(titles_to_fetch)} topics added, {final_count} total.")
    return final_count


if __name__ == "__main__":
    seed_database(force=True)
