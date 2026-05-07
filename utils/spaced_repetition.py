from datetime import datetime, timezone, timedelta
from utils.storage import load_data, save_data


QUALITY_LABELS = {
    0: "Again",
    1: "Hard",
    2: "Difficult",
    3: "Good",
    4: "Easy",
    5: "Perfect",
}


def record_review(quiz_id, quality):
    data = load_data()
    if "spaced_repetition" not in data:
        data["spaced_repetition"] = {}

    if quiz_id not in data["spaced_repetition"]:
        data["spaced_repetition"][quiz_id] = {
            "ease_factor": 2.5,
            "interval": 0,
            "repetitions": 0,
            "next_review": "",
            "last_review": "",
            "last_quality": None,
        }

    card = data["spaced_repetition"][quiz_id]
    card["last_quality"] = quality
    card["last_review"] = datetime.now(timezone.utc).isoformat()

    q = quality
    if q >= 3:
        if card["repetitions"] == 0:
            card["interval"] = 1
        elif card["repetitions"] == 1:
            card["interval"] = 6
        else:
            card["interval"] = round(card["interval"] * card["ease_factor"])
        card["repetitions"] += 1
    else:
        card["repetitions"] = 0
        card["interval"] = 1

    card["ease_factor"] = max(
        1.3,
        card["ease_factor"] + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    )

    next_date = datetime.now(timezone.utc) + timedelta(days=card["interval"])
    card["next_review"] = next_date.isoformat()

    save_data(data)
    return card


def get_due_cards(limit=20):
    data = load_data()
    sr = data.get("spaced_repetition", {})
    now = datetime.now(timezone.utc)

    due = []
    for quiz_id, card_state in sr.items():
        next_review = card_state.get("next_review", "")
        if not next_review:
            continue
        next_dt = datetime.fromisoformat(next_review)
        if next_dt <= now:
            overdue_hours = (now - next_dt).total_seconds() / 3600
            due.append((quiz_id, overdue_hours))

    due.sort(key=lambda x: x[1], reverse=True)
    return [q[0] for q in due[:limit]]


def get_card_state(quiz_id):
    data = load_data()
    sr = data.get("spaced_repetition", {})
    return sr.get(quiz_id, None)
