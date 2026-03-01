import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from marketkit.collectors.x_api import XApiCollector, RateLimitError


MOCK_SEARCH_RESPONSE = {
    "data": [
        {
            "id": "111",
            "text": "Claude Code is slow over SSH",
            "author_id": "u1",
            "created_at": "2026-03-01T10:00:00.000Z",
            "conversation_id": "111",
            "public_metrics": {
                "like_count": 47,
                "retweet_count": 12,
                "reply_count": 3,
                "quote_count": 1,
                "impression_count": 8500,
                "bookmark_count": 5,
            },
            "entities": {
                "urls": [{"expanded_url": "https://example.com"}],
                "mentions": [{"username": "anthropic"}],
                "hashtags": [{"tag": "ClaudeCode"}],
            },
        }
    ],
    "includes": {
        "users": [
            {"id": "u1", "username": "devops_jane", "name": "Jane"}
        ]
    },
    "meta": {"result_count": 1},
}


class TestParseResponse:
    def test_parse_tweets_all_fields(self):
        posts = XApiCollector.parse_response(MOCK_SEARCH_RESPONSE)
        assert len(posts) == 1
        p = posts[0]
        assert p.id == "111"
        assert p.author == "devops_jane"
        assert p.platform == "x"
        assert p.metrics["likes"] == 47
        assert p.metrics["retweets"] == 12
        assert p.metrics["replies"] == 3
        assert p.metrics["quotes"] == 1
        assert p.metrics["impressions"] == 8500
        assert p.metrics["bookmarks"] == 5
        assert "x.com" in p.url
        # 47 likes -> moderate (10-100) -> popularity bonus 1
        assert p.score == 1

    def test_parse_empty_response_missing_data(self):
        posts = XApiCollector.parse_response({"meta": {"result_count": 0}})
        assert posts == []

    def test_parse_empty_response_empty_array(self):
        posts = XApiCollector.parse_response({"data": [], "meta": {"result_count": 0}})
        assert posts == []

    def test_parse_missing_users(self):
        """Author falls back to '?' when includes.users is absent."""
        raw = {"data": [{"id": "1", "text": "hi", "author_id": "u99"}], "meta": {"result_count": 1}}
        posts = XApiCollector.parse_response(raw)
        assert posts[0].author == "?"

    def test_parse_missing_metrics(self):
        """Post with no public_metrics gets zero defaults."""
        raw = {"data": [{"id": "1", "text": "hi"}], "meta": {"result_count": 1}}
        posts = XApiCollector.parse_response(raw)
        assert posts[0].metrics["likes"] == 0
        assert posts[0].score == 0

    def test_parse_high_engagement_score(self):
        """Post with 100+ likes gets popularity bonus 2."""
        raw = {
            "data": [{"id": "1", "text": "viral", "public_metrics": {"like_count": 500}}],
            "meta": {"result_count": 1},
        }
        posts = XApiCollector.parse_response(raw)
        assert posts[0].score == 2


class TestTokenResolution:
    def test_get_token_from_env(self):
        with patch.dict(os.environ, {"X_BEARER_TOKEN": "test-token-123"}):
            collector = XApiCollector()
            assert collector._token == "test-token-123"

    def test_get_token_from_global_env_file(self, tmp_path, monkeypatch):
        """Token found in ~/.config/env/global.env file."""
        config_dir = tmp_path / ".config" / "env"
        config_dir.mkdir(parents=True)
        (config_dir / "global.env").write_text('X_BEARER_TOKEN="file-token-abc"\n')
        monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        collector = XApiCollector()
        assert collector._token == "file-token-abc"

    def test_get_token_with_export_prefix(self, tmp_path, monkeypatch):
        """Token found in env file with 'export' prefix."""
        config_dir = tmp_path / ".config" / "env"
        config_dir.mkdir(parents=True)
        (config_dir / "global.env").write_text('export X_BEARER_TOKEN=exported-token\n')
        monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        collector = XApiCollector()
        assert collector._token == "exported-token"

    def test_get_token_missing_raises(self, tmp_path, monkeypatch):
        """ValueError when token not in env or file."""
        # Clear only X_BEARER_TOKEN, not all env vars
        monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with pytest.raises(ValueError, match="X_BEARER_TOKEN"):
            XApiCollector()


class TestApiGet:
    def test_rate_limit_raises_custom_error(self):
        collector = XApiCollector.__new__(XApiCollector)
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"x-rate-limit-reset": str(int(time.time()) + 30)}
        collector._client = MagicMock()
        collector._client.get.return_value = mock_resp
        with pytest.raises(RateLimitError) as exc_info:
            collector._api_get("https://api.x.com/2/test", params={})
        assert exc_info.value.wait_seconds > 0

    def test_http_error_raises(self):
        collector = XApiCollector.__new__(XApiCollector)
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")
        collector._client = MagicMock()
        collector._client.get.return_value = mock_resp
        with pytest.raises(Exception, match="401"):
            collector._api_get("https://api.x.com/2/test", params={})
