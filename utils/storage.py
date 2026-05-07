import json
import os
import tempfile

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "studyswipe_data.json")
LOCK_FILE = DATA_FILE + ".lock"


def _ensure_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def _lock():
    import fcntl
    _ensure_dir()
    _lock._fd = open(LOCK_FILE, "w")
    fcntl.flock(_lock._fd, fcntl.LOCK_EX)


def _unlock():
    import fcntl
    if hasattr(_lock, "_fd") and _lock._fd:
        fcntl.flock(_lock._fd, fcntl.LOCK_UN)
        _lock._fd.close()
        _lock._fd = None


def load_data():
    _ensure_dir()
    defaults = {
        "topics": [],
        "saved": {},
        "quiz_history": [],
        "viewed": {},
        "user_progress": {},
        "spaced_repetition": {},
        "challenge_results": {},
        "lobbies": {},
    }
    if os.path.exists(DATA_FILE):
        _lock()
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            for key, value in defaults.items():
                if key not in data:
                    data[key] = value
            return data
        except (json.JSONDecodeError, ValueError):
            return defaults
        finally:
            _unlock()
    return defaults


def save_data(data):
    _ensure_dir()
    _lock()
    try:
        fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, DATA_FILE)
    finally:
        _unlock()


def get_topic_count():
    data = load_data()
    return len(data["topics"])


def get_categories():
    data = load_data()
    categories = []
    for topic in data["topics"]:
        if topic["category"] not in categories:
            categories.append(topic["category"])
    categories.sort()
    return categories


def add_topic(topic_dict):
    data = load_data()
    for existing in data["topics"]:
        if existing["topic_id"] == topic_dict["topic_id"]:
            return
    data["topics"].append(topic_dict)
    save_data(data)


def add_fact(topic_id, fact_id, fact_text):
    data = load_data()
    for topic in data["topics"]:
        if topic["topic_id"] == topic_id:
            if "facts" not in topic:
                topic["facts"] = []
            for existing in topic["facts"]:
                if existing["fact_id"] == fact_id:
                    return
            topic["facts"].append({"fact_id": fact_id, "fact_text": fact_text})
            save_data(data)
            return


def add_quiz(topic_id, quiz_dict):
    data = load_data()
    for topic in data["topics"]:
        if topic["topic_id"] == topic_id:
            if "quizzes" not in topic:
                topic["quizzes"] = []
            for existing in topic["quizzes"]:
                if existing["quiz_id"] == quiz_dict["quiz_id"]:
                    return
            topic["quizzes"].append(quiz_dict)
            save_data(data)
            return


def get_topic_by_id(topic_id):
    data = load_data()
    for topic in data["topics"]:
        if topic["topic_id"] == topic_id:
            return topic
    return None


def get_feed_topics(user_session, category=None, sort_by="trending", limit=50):
    data = load_data()
    topics = []
    for topic in data["topics"]:
        topics.append(topic)

    if category and category != "All":
        filtered = []
        for topic in topics:
            if topic["category"] == category:
                filtered.append(topic)
        topics = filtered

    if sort_by == "trending":
        topics.sort(key=lambda t: t.get("trend_score", 0), reverse=True)
    elif sort_by == "popular":
        topics.sort(key=lambda t: t.get("pageviews_30d", 0), reverse=True)
    elif sort_by == "random":
        import random
        random.shuffle(topics)
    elif sort_by == "difficulty_easy":
        topics.sort(key=lambda t: t.get("difficulty_score", 2.0))
    elif sort_by == "difficulty_hard":
        topics.sort(key=lambda t: t.get("difficulty_score", 2.0), reverse=True)
    elif sort_by == "alpha":
        topics.sort(key=lambda t: t["title"])

    return topics[:limit]


def save_topic(user_session, topic_id, collection_name):
    data = load_data()
    if user_session not in data["saved"]:
        data["saved"][user_session] = []

    for entry in data["saved"][user_session]:
        if entry["topic_id"] == topic_id and entry["collection_name"] == collection_name:
            return

    from datetime import datetime, timezone
    data["saved"][user_session].append({
        "topic_id": topic_id,
        "collection_name": collection_name,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    })
    save_data(data)


def unsave_topic(user_session, topic_id, collection_name=None):
    data = load_data()
    if user_session not in data["saved"]:
        return

    if collection_name:
        data["saved"][user_session] = [
            e for e in data["saved"][user_session]
            if not (e["topic_id"] == topic_id and e["collection_name"] == collection_name)
        ]
    else:
        data["saved"][user_session] = [
            e for e in data["saved"][user_session]
            if e["topic_id"] != topic_id
        ]
    save_data(data)


def get_saved_topics(user_session, collection_name=None):
    data = load_data()
    if user_session not in data["saved"]:
        return []

    entries = data["saved"][user_session]
    if collection_name and collection_name != "All Collections":
        entries = [e for e in entries if e["collection_name"] == collection_name]

    topics = []
    for entry in entries:
        topic = get_topic_by_id(entry["topic_id"])
        if topic:
            topics.append(topic)
    return topics


def get_collections(user_session):
    data = load_data()
    if user_session not in data["saved"]:
        return []
    collections = []
    for entry in data["saved"][user_session]:
        if entry["collection_name"] not in collections:
            collections.append(entry["collection_name"])
    collections.sort()
    return collections


def record_quiz_answer(user_session, topic_id, quiz_id, selected_option, is_correct):
    data = load_data()
    from datetime import datetime, timezone
    data["quiz_history"].append({
        "user_session": user_session,
        "topic_id": topic_id,
        "quiz_id": quiz_id,
        "selected_option": selected_option,
        "is_correct": is_correct,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    })
    save_data(data)


def record_view(user_session, topic_id):
    data = load_data()
    if user_session not in data["viewed"]:
        data["viewed"][user_session] = []
    if topic_id not in data["viewed"][user_session]:
        data["viewed"][user_session].append(topic_id)
        save_data(data)


def get_quiz_history(user_session):
    data = load_data()
    history = []
    for entry in data["quiz_history"]:
        if entry["user_session"] == user_session:
            history.append(entry)
    return history


def get_quiz_stats(user_session):
    data = load_data()
    total = 0
    correct = 0
    topics_quizzed = set()
    quiz_ids = set()
    for entry in data["quiz_history"]:
        if entry["user_session"] == user_session:
            total = total + 1
            if entry["is_correct"]:
                correct = correct + 1
            topics_quizzed.add(entry["topic_id"])
            quiz_ids.add(entry["quiz_id"])

    if total == 0:
        return {
            "total_answers": 0,
            "correct_answers": 0,
            "accuracy": 0.0,
            "topics_quizzed": 0,
            "unique_questions": 0,
        }
    return {
        "total_answers": total,
        "correct_answers": correct,
        "accuracy": round(correct / total * 100, 1),
        "topics_quizzed": len(topics_quizzed),
        "unique_questions": len(quiz_ids),
    }


def get_analytics(user_session):
    data = load_data()
    stats = get_quiz_stats(user_session)

    viewed_count = 0
    if user_session in data["viewed"]:
        viewed_count = len(data["viewed"][user_session])

    saved_count = 0
    if user_session in data["saved"]:
        saved_ids = set()
        for entry in data["saved"][user_session]:
            saved_ids.add(entry["topic_id"])
        saved_count = len(saved_ids)

    category_stats = {}
    category_accuracy = {}
    for entry in data["quiz_history"]:
        if entry["user_session"] == user_session:
            topic = get_topic_by_id(entry["topic_id"])
            if topic:
                cat = topic["category"]
                if cat not in category_stats:
                    category_stats[cat] = 0
                    category_accuracy[cat] = {"total": 0, "correct": 0}
                category_stats[cat] = category_stats[cat] + 1
                category_accuracy[cat]["total"] = category_accuracy[cat]["total"] + 1
                if entry["is_correct"]:
                    category_accuracy[cat]["correct"] = category_accuracy[cat]["correct"] + 1

    cat_acc = {}
    for cat, counts in category_accuracy.items():
        total = counts["total"]
        correct = counts["correct"]
        cat_acc[cat] = round(correct / total * 100, 1) if total > 0 else 0.0

    most_saved = {}
    if user_session in data["saved"]:
        for entry in data["saved"][user_session]:
            topic = get_topic_by_id(entry["topic_id"])
            if topic:
                title = topic["title"]
                if title not in most_saved:
                    most_saved[title] = {"title": title, "category": topic["category"], "save_count": 0}
                most_saved[title]["save_count"] = most_saved[title]["save_count"] + 1
    most_saved_list = sorted(most_saved.values(), key=lambda x: x["save_count"], reverse=True)[:10]

    return {
        "total_answers": stats["total_answers"],
        "correct_answers": stats["correct_answers"],
        "accuracy": stats["accuracy"],
        "topics_quizzed": stats["topics_quizzed"],
        "unique_questions": stats["unique_questions"],
        "viewed_count": viewed_count,
        "saved_count": saved_count,
        "category_stats": category_stats,
        "most_saved": most_saved_list,
        "category_accuracy": cat_acc,
    }


def is_topic_saved(user_session, topic_id):
    data = load_data()
    if user_session not in data["saved"]:
        return False
    for entry in data["saved"][user_session]:
        if entry["topic_id"] == topic_id:
            return True
    return False


def is_topic_viewed(user_session, topic_id):
    data = load_data()
    if user_session not in data["viewed"]:
        return False
    return topic_id in data["viewed"][user_session]


def _get_user_progress(data, user_session):
    if user_session not in data["user_progress"]:
        data["user_progress"][user_session] = {
            "xp": 0,
            "level": 1,
            "streak_days": 0,
            "last_active_date": "",
            "total_cards_viewed": 0,
            "total_quizzes_taken": 0,
            "achievements": [],
        }
    return data["user_progress"][user_session]


def _check_achievements(progress):
    achievements = []
    checks = [
        ("card_explorer", progress["total_cards_viewed"] >= 10),
        ("knowledge_seeker", progress["total_cards_viewed"] >= 50),
        ("streak_3", progress["streak_days"] >= 3),
        ("streak_7", progress["streak_days"] >= 7),
        ("centurion", progress["xp"] >= 100),
        ("scholar", progress["xp"] >= 500),
    ]
    for ach_id, earned in checks:
        if earned and ach_id not in progress["achievements"]:
            achievements.append(ach_id)
    return achievements


def add_xp(user_session, amount, reason=""):
    data = load_data()
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    progress = _get_user_progress(data, user_session)

    if progress["last_active_date"] and progress["last_active_date"] != today:
        from datetime import timedelta
        last = datetime.strptime(progress["last_active_date"], "%Y-%m-%d")
        now = datetime.strptime(today, "%Y-%m-%d")
        days_diff = (now - last).days
        if days_diff == 1:
            progress["streak_days"] += 1
        elif days_diff > 1:
            progress["streak_days"] = 1

    progress["xp"] += amount
    progress["last_active_date"] = today
    progress["level"] = 1 + progress["xp"] // 100

    new_achievements = _check_achievements(progress)
    for ach in new_achievements:
        if ach not in progress["achievements"]:
            progress["achievements"].append(ach)

    if reason == "viewed_card":
        progress["total_cards_viewed"] += 1
    elif reason in ("correct_answer", "wrong_answer"):
        pass
    elif reason == "quiz_completed":
        progress["total_quizzes_taken"] += 1

    save_data(data)
    return {
        "xp": progress["xp"],
        "level": progress["level"],
        "streak_days": progress["streak_days"],
        "new_achievements": new_achievements,
    }


def get_user_progress(user_session):
    data = load_data()
    return _get_user_progress(data, user_session)


def save_challenge_result(challenge_code, user_session, score, total):
    data = load_data()
    if "challenge_results" not in data:
        data["challenge_results"] = {}
    if challenge_code not in data["challenge_results"]:
        data["challenge_results"][challenge_code] = []
    from datetime import datetime, timezone
    data["challenge_results"][challenge_code].append({
        "user_session": user_session,
        "score": score,
        "total": total,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    save_data(data)


def get_challenge_results(challenge_code):
    data = load_data()
    results = data.get("challenge_results", {}).get(challenge_code, [])
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def create_lobby(lobby_code, host_session, host_name, seed_data, num_questions):
    data = load_data()
    if "lobbies" not in data:
        data["lobbies"] = {}
    from datetime import datetime, timezone
    data["lobbies"][lobby_code] = {
        "status": "waiting",
        "seed_data": seed_data,
        "num_questions": num_questions,
        "players": [{
            "session": host_session,
            "name": host_name,
            "score": None,
            "finished": False,
            "finished_at": None,
        }],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
    }
    save_data(data)


def join_lobby(lobby_code, user_session, user_name):
    data = load_data()
    lobby = data.get("lobbies", {}).get(lobby_code)
    if not lobby or lobby["status"] != "waiting":
        return None
    for p in lobby["players"]:
        if p["session"] == user_session:
            return lobby
    lobby["players"].append({
        "session": user_session,
        "name": user_name,
        "score": None,
        "finished": False,
        "finished_at": None,
    })
    save_data(data)
    return lobby


def start_lobby(lobby_code, quiz_items=None):
    data = load_data()
    lobby = data.get("lobbies", {}).get(lobby_code)
    if not lobby or lobby["status"] != "waiting":
        return False
    from datetime import datetime, timezone
    lobby["status"] = "active"
    lobby["started_at"] = datetime.now(timezone.utc).isoformat()
    if quiz_items is not None:
        lobby["quiz_items"] = quiz_items
    save_data(data)
    return True


def finish_lobby_player(lobby_code, user_session, score, total):
    data = load_data()
    lobby = data.get("lobbies", {}).get(lobby_code)
    if not lobby:
        return
    from datetime import datetime, timezone
    for p in lobby["players"]:
        if p["session"] == user_session:
            p["score"] = score
            p["total"] = total
            p["finished"] = True
            p["finished_at"] = datetime.now(timezone.utc).isoformat()
    all_done = all(p["finished"] for p in lobby["players"])
    if all_done:
        lobby["status"] = "finished"
    save_data(data)


def get_lobby(lobby_code):
    data = load_data()
    return data.get("lobbies", {}).get(lobby_code, None)
