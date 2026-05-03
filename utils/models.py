class Topic:
    def __init__(self, topic_id, title, summary, category, wikidata_id=None, image_url=None, url=None, why_matters=None):
        self.topic_id = topic_id
        self.title = title
        self.summary = summary
        self.category = category
        self.wikidata_id = wikidata_id
        self.image_url = image_url
        self.url = url
        self.why_matters = why_matters


class TopicMetrics:
    def __init__(self, topic_id, pageviews_7d=0, pageviews_30d=0, trend_score=0.0, difficulty_score=0.0):
        self.topic_id = topic_id
        self.pageviews_7d = pageviews_7d
        self.pageviews_30d = pageviews_30d
        self.trend_score = trend_score
        self.difficulty_score = difficulty_score


class FactCard:
    def __init__(self, fact_id, topic_id, fact_text, source_section=None):
        self.fact_id = fact_id
        self.topic_id = topic_id
        self.fact_text = fact_text
        self.source_section = source_section


class QuizItem:
    def __init__(self, quiz_id, topic_id, question, option_a="", option_b="", option_c="", option_d="", correct_option="a"):
        self.quiz_id = quiz_id
        self.topic_id = topic_id
        self.question = question
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c
        self.option_d = option_d
        self.correct_option = correct_option


class SavedTopic:
    def __init__(self, user_session, topic_id, collection_name, saved_at=""):
        self.user_session = user_session
        self.topic_id = topic_id
        self.collection_name = collection_name
        self.saved_at = saved_at


class QuizHistoryEntry:
    def __init__(self, history_id, user_session, topic_id, quiz_id, selected_option, is_correct, answered_at=""):
        self.history_id = history_id
        self.user_session = user_session
        self.topic_id = topic_id
        self.quiz_id = quiz_id
        self.selected_option = selected_option
        self.is_correct = is_correct
        self.answered_at = answered_at


class TopicCard:
    def __init__(self, topic, metrics=None, facts=None, quiz_items=None, is_saved=False, is_viewed=False):
        self.topic = topic
        self.metrics = metrics
        self.facts = facts if facts else []
        self.quiz_items = quiz_items if quiz_items else []
        self.is_saved = is_saved
        self.is_viewed = is_viewed

    def get_popularity_label(self):
        if not self.metrics:
            return "Unknown"
        pv = self.metrics.pageviews_7d
        if pv >= 100000:
            return "Trending"
        elif pv >= 10000:
            return "Popular"
        elif pv >= 1000:
            return "Moderate"
        return "Niche"

    def get_difficulty_label(self):
        if not self.metrics:
            return "Medium"
        ds = self.metrics.difficulty_score
        if ds <= 2.0:
            return "Easy"
        elif ds <= 3.5:
            return "Medium"
        return "Hard"

    def has_quiz(self):
        return len(self.quiz_items) > 0
