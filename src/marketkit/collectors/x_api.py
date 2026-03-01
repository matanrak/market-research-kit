"""X API v2 collector for marketkit.

Ported from x-research-skill (TypeScript) to Python.
Uses Bearer token auth, pay-per-use ($0.005/tweet read).
"""

from __future__ import annotations

import os
import ssl
import time
from pathlib import Path

import httpx
import truststore

from .base import Collector, Post, popularity_bonus

BASE_URL = "https://api.x.com/2"
RATE_DELAY = 0.35  # 350ms between requests


class RateLimitError(RuntimeError):
    """Raised when the X API rate limit is hit."""

    def __init__(self, wait_seconds: int):
        self.wait_seconds = wait_seconds
        super().__init__(f"Rate limited. Resets in {wait_seconds}s")


class XApiCollector(Collector):
    """Wraps X API v2 recent search. Bearer token auth."""

    platform = "x"

    def __init__(self):
        self._token = self._resolve_token()
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {self._token}"},
            verify=ssl_context,
            timeout=30.0,
        )

    def _resolve_token(self) -> str:
        """Find bearer token from env or ~/.config/env/global.env."""
        token = os.environ.get("X_BEARER_TOKEN", "").strip()
        if token:
            return token

        env_file = Path.home() / ".config" / "env" / "global.env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Strip optional 'export ' prefix
                if line.startswith("export "):
                    line = line[7:]
                if line.startswith("X_BEARER_TOKEN="):
                    val = line.split("=", 1)[1].strip().strip("\"'")
                    if val:
                        return val

        raise ValueError(
            "X_BEARER_TOKEN not found. Set it as an env var or in "
            "~/.config/env/global.env"
        )

    def _api_get(self, url: str, *, params: dict) -> dict:
        """Make authenticated GET request with rate limit handling."""
        resp = self._client.get(url, params=params)

        if resp.status_code == 429:
            reset = resp.headers.get("x-rate-limit-reset")
            wait = int(reset) - int(time.time()) if reset else 60
            raise RateLimitError(max(wait, 1))

        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def parse_response(raw: dict) -> list[Post]:
        """Parse X API response into Post objects."""
        data = raw.get("data")
        if not data:
            return []

        users = {}
        for u in raw.get("includes", {}).get("users", []):
            users[u["id"]] = u

        posts = []
        for t in data:
            u = users.get(t.get("author_id", ""), {})
            m = t.get("public_metrics", {})
            username = u.get("username", "?")

            metrics = {
                "likes": m.get("like_count", 0),
                "retweets": m.get("retweet_count", 0),
                "replies": m.get("reply_count", 0),
                "quotes": m.get("quote_count", 0),
                "impressions": m.get("impression_count", 0),
                "bookmarks": m.get("bookmark_count", 0),
            }
            posts.append(
                Post(
                    id=t["id"],
                    platform="x",
                    author=username,
                    text=t.get("text", ""),
                    url=f"https://x.com/{username}/status/{t['id']}",
                    timestamp=t.get("created_at", ""),
                    metrics=metrics,
                    score=popularity_bonus("x", metrics),
                    raw=t,
                )
            )
        return posts

    def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        pages: int = 1,
        sort_order: str = "relevancy",
    ) -> list[Post]:
        """Search recent tweets (last 7 days)."""
        max_results = max(10, min(max_results, 100))
        all_posts: list[Post] = []
        next_token = None

        for page in range(pages):
            params = {
                "query": query,
                "max_results": max_results,
                "tweet.fields": "created_at,public_metrics,author_id,conversation_id,entities",
                "expansions": "author_id",
                "user.fields": "username,name,public_metrics",
                "sort_order": sort_order,
            }
            if next_token:
                params["pagination_token"] = next_token

            raw = self._api_get(f"{BASE_URL}/tweets/search/recent", params=params)
            all_posts.extend(self.parse_response(raw))

            next_token = raw.get("meta", {}).get("next_token")
            if not next_token:
                break
            if page < pages - 1:
                time.sleep(RATE_DELAY)

        return all_posts

    def profile(self, username: str) -> dict:
        """Fetch user profile info."""
        params = {
            "user.fields": "public_metrics,description,created_at",
        }
        raw = self._api_get(
            f"{BASE_URL}/users/by/username/{username}",
            params=params,
        )
        return raw.get("data", {})
