import uuid
import random

from utils.ai_quiz_generator import generate_quizzes_with_ai
from utils.storage import add_topic, add_fact, add_quiz, get_topic_by_id
from utils.wikipedia_api import (
    get_summary,
    get_extract,
    get_page_views,
    search_articles,
    get_random_articles,
)

CATEGORY_KEYWORDS = {
    "Science": ("physics", "chemistry", "biology", "dna", "evolution", "climate", "quantum"),
    "History": ("war", "empire", "revolution", "ancient", "medieval", "roman", "civilization"),
    "Politics": ("democracy", "election", "government", "law", "rights", "constitution", "united nations"),
    "Culture": ("art", "music", "painting", "literature", "theatre", "opera", "jazz", "cinema"),
    "Technology": ("computer", "software", "internet", "algorithm", "robot", "programming", "blockchain"),
}


def _guess_category(title, summary):
    text = (title + " " + summary).lower()
    best_cat = "Technology"
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text:
                score = score + 1
        if score > best_score:
            best_cat = cat
            best_score = score
    return best_cat


def _split_sentences(text):
    sentences = []
    current = ""
    for char in text:
        current = current + char
        if char in ".!?":
            sentences.append(current.strip())
            current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences


def _extract_facts(extract):
    paragraphs = [p.strip() for p in extract.split("\n\n") if p.strip()]
    facts = []
    for para in paragraphs[:4]:
        sentences = _split_sentences(para)
        for sent in sentences:
            if len(sent) > 30 and len(sent) < 300 and not sent.startswith("="):
                facts.append(sent)
                if len(facts) >= 5:
                    return facts
    return facts


def _find_numbers(text):
    words = text.split()
    numbers = []
    for word in words:
        cleaned = word.replace(",", "").replace(".", "")
        if cleaned.isdigit() and len(cleaned) > 0:
            numbers.append(word)
    return numbers


def _find_years(text):
    words = text.split()
    years = []
    for word in words:
        cleaned = word.replace(",", "").replace(".", "")
        if len(cleaned) == 4 and cleaned.isdigit():
            y = int(cleaned)
            if y >= 1000 and y <= 2029:
                years.append(cleaned)
    return years


def _create_number_quiz(sentence, idx):
    numbers = _find_numbers(sentence)
    if numbers:
        original = numbers[0]
        try:
            val = float(original.replace(",", ""))
            wrong_a = str(int(val * 2)) if val > 1 else str(val + 1)
            wrong_b = str(int(val / 2)) if val > 2 else str(val + 2)
            wrong_c = str(int(val + val * 0.5))
            question = sentence.replace(original, "____")
            return {
                "quiz_id": f"wiki-q-{idx}",
                "question": question,
                "option_a": original,
                "option_b": wrong_a,
                "option_c": wrong_b,
                "option_d": wrong_c,
                "correct_option": "a",
            }
        except (ValueError, ZeroDivisionError):
            pass

    year_match = _find_years(sentence)
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
        return {
            "quiz_id": f"wiki-q-{idx}",
            "question": question,
            "option_a": original,
            "option_b": wrongs[0],
            "option_c": wrongs[1],
            "option_d": wrongs[2],
            "correct_option": "a",
        }

    return None


def _generate_number_quizzes(facts, prefix):
    quizzes = []
    for i, fact in enumerate(facts):
        quiz = _create_number_quiz(fact, i)
        if quiz:
            quiz["quiz_id"] = f"wiki-{prefix}-q{i}"
            quizzes.append(quiz)
    return quizzes


def _modify_fact(fact):
    number_words = {
        "first": "second",
        "last": "first",
        "largest": "smallest",
        "smallest": "largest",
        "oldest": "youngest",
        "highest": "lowest",
        "longest": "shortest",
        "most": "least",
        "over": "under",
    }
    for word, replacement in number_words.items():
        if word in fact.lower():
            if word == fact.lower().split()[0]:
                return fact.lower().replace(word, replacement).capitalize()
            else:
                return fact.replace(word, replacement)
    return None


def _generate_true_false_quiz(fact, topic_title, index):
    if random.random() < 0.5:
        return {
            "quiz_id": f"tf-{topic_title[:3].lower()}-{index}-t",
            "question": f"True or False: {fact}",
            "option_a": "True",
            "option_b": "False",
            "option_c": "Not sure",
            "option_d": "",
            "correct_option": "a",
        }
    else:
        modified = _modify_fact(fact)
        if modified:
            return {
                "quiz_id": f"tf-{topic_title[:3].lower()}-{index}-f",
                "question": f"True or False: {modified}",
                "option_a": "True",
                "option_b": "False",
                "option_c": "Not sure",
                "option_d": "",
                "correct_option": "b",
            }
    return None


def _generate_quizzes(facts, prefix, topic_title):
    quizzes = _generate_number_quizzes(facts, prefix)
    if len(quizzes) == 0:
        for i, fact in enumerate(facts):
            quiz = _generate_true_false_quiz(fact, topic_title, i)
            if quiz:
                quiz["quiz_id"] = f"wiki-{prefix}-tf{i}"
                quizzes.append(quiz)
    return quizzes


def fetch_and_add_article(title):
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

    pv_7d = 0
    pv_30d = 0
    trend = 0.0
    if pageviews:
        pv_7d = pageviews["pageviews_7d"]
        pv_30d = pageviews["pageviews_30d"]
        trend = round(pv_7d / max(pv_30d, 1) * 10, 2)

    topic_dict = {
        "topic_id": topic_id,
        "title": summary_data["title"],
        "summary": summary,
        "category": category,
        "image_url": summary_data.get("thumbnail"),
        "url": summary_data.get("url", ""),
        "why_matters": f"Discovered via Wikipedia. {summary[:100]}...",
        "pageviews_7d": pv_7d,
        "pageviews_30d": pv_30d,
        "trend_score": trend,
        "difficulty_score": round(len(summary.split()) / 20, 1),
        "facts": [],
        "quizzes": [],
    }

    add_topic(topic_dict)

    facts_text = _extract_facts(extract_text) if extract_text else []
    if not facts_text:
        sentences = _split_sentences(summary)
        facts_text = [s.strip() for s in sentences if len(s.strip()) > 30][:4]

    for i in range(min(len(facts_text), 5)):
        add_fact(topic_id, f"{topic_id}-f{i}", facts_text[i])

    ai_raw = generate_quizzes_with_ai(topic_dict["title"], summary, facts_text, count=3)
    if ai_raw:
        for i, qd in enumerate(ai_raw):
            quiz_dict = {
                "quiz_id": f"ai-{topic_id}-q{i}",
                "topic_id": topic_id,
                "question": qd["question"],
                "option_a": qd["option_a"],
                "option_b": qd["option_b"],
                "option_c": qd["option_c"],
                "option_d": qd["option_d"],
                "correct_option": qd["correct_option"],
            }
            add_quiz(topic_id, quiz_dict)
    else:
        quizzes = _generate_quizzes(facts_text, topic_id, topic_dict["title"])
        for q in quizzes:
            q["topic_id"] = topic_id
            add_quiz(topic_id, q)

    return topic_id


def fetch_trending_articles(count=10):
    added = []
    titles = get_random_articles(count * 3)
    for title in titles:
        if len(added) >= count:
            break
        tid = fetch_and_add_article(title)
        if tid:
            added.append(tid)
    return added


def search_and_add(query, max_results=5):
    results = search_articles(query, limit=max_results * 2)
    added = []
    for r in results:
        if len(added) >= max_results:
            break
        tid = fetch_and_add_article(r["title"])
        if tid:
            added.append(tid)
    return added
