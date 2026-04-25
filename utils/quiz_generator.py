import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)


def generate_quiz_from_facts(facts: list[str], topic_title: str) -> list[dict]:
    quizzes = []
    for i, fact in enumerate(facts):
        quiz = _create_true_false(fact, topic_title, i)
        if quiz:
            quizzes.append(quiz)
    return quizzes


def _create_true_false(fact: str, topic_title: str, index: int) -> Optional[dict]:
    if random.random() < 0.5:
        return {
            "quiz_id": f"gen-{topic_title[:3].lower()}-{index}-tf-t",
            "topic_title": topic_title,
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
                "quiz_id": f"gen-{topic_title[:3].lower()}-{index}-tf-f",
                "topic_title": topic_title,
                "question": f"True or False: {modified}",
                "option_a": "True",
                "option_b": "False",
                "option_c": "Not sure",
                "option_d": "",
                "correct_option": "b",
            }
    return None


def _modify_fact(fact: str) -> Optional[str]:
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
            return (
                fact.lower().replace(word, replacement).capitalize()
                if word == fact.lower().split()[0]
                else fact.replace(word, replacement)
            )
    return None
