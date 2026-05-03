import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

GOOGLE_AI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"


def _get_api_key():
    try:
        import streamlit as st
        key = st.secrets.get("GOOGLE_AI_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GOOGLE_AI_API_KEY")


def generate_quizzes_with_ai(title, summary, facts, count=3):
    api_key = _get_api_key()
    if not api_key:
        logger.warning("No Google AI API key found, skipping AI quiz generation")
        return []

    facts_text = ""
    for i, f in enumerate(facts[:5]):
        if i == 0:
            facts_text = f"- {f}"
        else:
            facts_text = facts_text + f"\n- {f}"

    prompt = f"""Generate {count} multiple-choice quiz questions about "{title}".

Summary: {summary}

Key facts:
{facts_text}

Rules:
- Each question must have exactly 4 options (a, b, c, d)
- Only one correct answer
- Questions should test understanding, not just memorization
- Use information from the summary and facts above
- Wrong answers must be plausible

Return ONLY a JSON array with this exact format, no other text:
[
  {{
    "question": "Question text?",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_option": "a"
  }}
]"""

    try:
        resp = requests.post(
            f"{GOOGLE_AI_URL}?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1500},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data["candidates"][0]["content"]["parts"][0]["text"]

        json_start = content.find("[")
        json_end = content.rfind("]") + 1
        if json_start == -1 or json_end == 0:
            logger.warning("No JSON array found in AI response for %s", title)
            return []

        quizzes = json.loads(content[json_start:json_end])

        valid = []
        required_keys = ("question", "option_a", "option_b", "option_c", "option_d", "correct_option")
        for q in quizzes:
            has_all_keys = True
            for k in required_keys:
                if k not in q:
                    has_all_keys = False
                    break
            if has_all_keys and q["correct_option"] in ("a", "b", "c", "d"):
                valid.append(q)

        logger.info("Generated %d AI quizzes for %s", len(valid), title)
        return valid

    except Exception as e:
        logger.warning("AI quiz generation failed for %s: %s", title, e)
        return []
