"""Base collector interface and universal Post dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Post:
    """Universal post format — works for tweets, reddit posts, etc."""

    id: str
    platform: str
    author: str
    text: str
    url: str
    timestamp: str
    metrics: dict = field(default_factory=dict)
    score: int = 0
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict. Excludes raw API response."""
        return {
            "id": self.id,
            "platform": self.platform,
            "author": self.author,
            "text": self.text,
            "url": self.url,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
            "score": self.score,
        }


def popularity_bonus(platform: str, metrics: dict) -> int:
    """Return 0/1/2 based on engagement thresholds.

    Twitter uses 'likes', Reddit uses 'score' (upvotes).
    """
    if platform in ("x", "twitter"):
        value = metrics.get("likes", 0)
    elif platform in ("reddit", "reddit-scrape"):
        value = metrics.get("score", 0)
    else:
        return 0

    if value >= 100:
        return 2
    if value >= 10:
        return 1
    return 0


class Collector(ABC):
    """Abstract interface. Each data source implements this."""

    platform: str = ""

    @abstractmethod
    def search(self, query: str, **opts) -> list[Post]:
        """Search for posts matching query. Returns list of Post."""
        ...

    @abstractmethod
    def profile(self, username: str) -> dict:
        """Fetch user profile info. Returns platform-specific dict."""
        ...
