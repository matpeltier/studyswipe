import json
import random
import base64


def generate_challenge_code(category, num_questions, difficulty):
    seed_data = {
        "c": (category or "all")[:10],
        "n": num_questions,
        "d": difficulty[:3],
        "s": random.randint(10000, 999999),
    }
    json_str = json.dumps(seed_data, separators=(",", ":"))
    code = base64.urlsafe_b64encode(json_str.encode()).decode().rstrip("=")
    return code, seed_data


def decode_challenge_code(code):
    padding = 4 - len(code) % 4
    if padding != 4:
        code += "=" * padding
    json_str = base64.urlsafe_b64decode(code).decode()
    return json.loads(json_str)


def get_challenge_questions(seed_data, topics, num_questions):
    rng = random.Random(seed_data["s"])

    cat = seed_data.get("c", "all").lower()
    filtered = topics
    if cat != "all":
        filtered = [t for t in topics if t["category"].lower()[:10] == cat]

    rng.shuffle(filtered)

    def _build_quiz_item(qi, topic):
        option_keys = ("option_a", "option_b", "option_c", "option_d")
        options = []
        correct_idx = 0
        for oi, opt_key in enumerate(option_keys):
            opt_val = qi.get(opt_key, "")
            if opt_val:
                options.append(opt_val)
                if opt_key == qi["correct_option"]:
                    correct_idx = oi
        return {
            "topic_id": topic["topic_id"],
            "topic_title": topic["title"],
            "category": topic["category"],
            "quiz_id": qi["quiz_id"],
            "question": qi["question"],
            "options": options,
            "correct_idx": correct_idx,
        }

    quiz_items = []
    for topic in filtered:
        for qi in topic.get("quizzes", []):
            quiz_items.append(_build_quiz_item(qi, topic))
            if len(quiz_items) >= num_questions:
                break
        if len(quiz_items) >= num_questions:
            break

    return quiz_items[:num_questions]
