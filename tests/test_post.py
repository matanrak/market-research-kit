import json
from marketkit.collectors.base import Post, popularity_bonus


def test_post_from_dict():
    data = {
        "id": "123",
        "platform": "x",
        "author": "jane",
        "text": "Claude Code is slow over SSH",
        "url": "https://x.com/jane/status/123",
        "timestamp": "2026-03-01T10:00:00Z",
        "metrics": {"likes": 10, "retweets": 2},
    }
    post = Post(**data)
    assert post.id == "123"
    assert post.platform == "x"
    assert post.author == "jane"
    assert post.metrics["likes"] == 10
    # Defaults
    assert post.raw == {}


def test_post_to_dict():
    post = Post(
        id="456",
        platform="x",
        author="bob",
        text='He said "hello"',
        url="https://x.com/bob/status/456",
        timestamp="2026-03-01T12:00:00Z",
        metrics={"likes": 5},
        score=3,
    )
    d = post.to_dict()
    assert d["id"] == "456"
    assert d["author"] == "bob"
    assert d["text"] == 'He said "hello"'
    assert d["metrics"]["likes"] == 5
    assert d["score"] == 3
    # raw should not be in the dict output
    assert "raw" not in d


def test_post_to_dict_roundtrip():
    """Serializing to dict and back should preserve all fields."""
    post = Post(
        id="789",
        platform="x",
        author="alice",
        text="Switching from Cursor\nNew line here\tand a tab",
        url="https://x.com/alice/status/789",
        timestamp="2026-03-01T14:00:00Z",
        metrics={"likes": 20, "impressions": 8500},
    )
    d = post.to_dict()
    # Must be JSON-serializable
    json_str = json.dumps(d)
    loaded = json.loads(json_str)
    restored = Post(**loaded)
    assert restored.id == post.id
    assert restored.text == post.text
    assert restored.metrics == post.metrics


def test_post_to_dict_empty_metrics():
    post = Post(
        id="000",
        platform="x",
        author="test",
        text="no metrics",
        url="https://x.com/test/status/000",
        timestamp="2026-03-01T00:00:00Z",
    )
    d = post.to_dict()
    assert d["metrics"] == {}


def test_post_to_dict_special_chars():
    """Text with quotes, backslashes, unicode should roundtrip cleanly."""
    post = Post(
        id="999",
        platform="x",
        author="test",
        text='triple quotes \'\'\' and "doubles" and back\\slash and emoji 🎉',
        url="https://x.com/test/status/999",
        timestamp="2026-03-01T00:00:00Z",
        metrics={"likes": 1},
    )
    d = post.to_dict()
    json_str = json.dumps(d)
    loaded = json.loads(json_str)
    assert loaded["text"] == post.text


def test_post_score_default():
    """Score defaults to 0."""
    post = Post(
        id="1", platform="x", author="a", text="t",
        url="https://x.com/a/status/1", timestamp="2026-03-01T00:00:00Z",
    )
    assert post.score == 0
    assert post.to_dict()["score"] == 0


def test_post_score_in_roundtrip():
    """Score survives JSON serialization roundtrip."""
    post = Post(
        id="1", platform="x", author="a", text="t",
        url="https://x.com/a/status/1", timestamp="2026-03-01T00:00:00Z",
        score=4,
    )
    d = post.to_dict()
    json_str = json.dumps(d)
    loaded = json.loads(json_str)
    restored = Post(**loaded)
    assert restored.score == 4


class TestPopularityBonus:
    def test_twitter_low(self):
        assert popularity_bonus("x", {"likes": 5}) == 0

    def test_twitter_moderate(self):
        assert popularity_bonus("x", {"likes": 10}) == 1
        assert popularity_bonus("x", {"likes": 50}) == 1

    def test_twitter_high(self):
        assert popularity_bonus("x", {"likes": 100}) == 2
        assert popularity_bonus("x", {"likes": 9999}) == 2

    def test_twitter_alias(self):
        assert popularity_bonus("twitter", {"likes": 50}) == 1

    def test_reddit_low(self):
        assert popularity_bonus("reddit", {"score": 3}) == 0

    def test_reddit_moderate(self):
        assert popularity_bonus("reddit", {"score": 42}) == 1

    def test_reddit_high(self):
        assert popularity_bonus("reddit", {"score": 200}) == 2

    def test_reddit_scrape_alias(self):
        assert popularity_bonus("reddit-scrape", {"score": 50}) == 1

    def test_unknown_platform(self):
        assert popularity_bonus("mastodon", {"likes": 999}) == 0

    def test_missing_metric(self):
        assert popularity_bonus("x", {}) == 0
        assert popularity_bonus("reddit", {}) == 0
