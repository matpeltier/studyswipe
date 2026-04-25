from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Topic:
    topic_id: str
    title: str
    summary: str
    category: str
    wikidata_id: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    why_matters: Optional[str] = None


@dataclass
class TopicMetrics:
    topic_id: str
    pageviews_7d: int = 0
    pageviews_30d: int = 0
    trend_score: float = 0.0
    difficulty_score: float = 0.0


@dataclass
class FactCard:
    fact_id: str
    topic_id: str
    fact_text: str
    source_section: Optional[str] = None


@dataclass
class QuizItem:
    quiz_id: str
    topic_id: str
    question: str
    option_a: str = ""
    option_b: str = ""
    option_c: str = ""
    option_d: str = ""
    correct_option: str = "a"


@dataclass
class SavedTopic:
    user_session: str
    topic_id: str
    collection_name: str
    saved_at: str = ""


@dataclass
class QuizHistoryEntry:
    history_id: str
    user_session: str
    topic_id: str
    quiz_id: str
    selected_option: str
    is_correct: bool
    answered_at: str = ""


@dataclass
class TopicCard:
    topic: Topic
    metrics: Optional[TopicMetrics] = None
    facts: list = field(default_factory=list)
    quiz_items: list = field(default_factory=list)
    is_saved: bool = False
    is_viewed: bool = False

    @property
    def popularity_label(self) -> str:
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

    @property
    def difficulty_label(self) -> str:
        if not self.metrics:
            return "Medium"
        ds = self.metrics.difficulty_score
        if ds <= 2.0:
            return "Easy"
        elif ds <= 3.5:
            return "Medium"
        return "Hard"
