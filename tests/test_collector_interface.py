import pytest
from marketkit.collectors.base import Collector, Post


class FakeCollector(Collector):
    platform = "fake"

    def search(self, query, **opts):
        return [
            Post(
                id="1",
                platform="fake",
                author="test",
                text=f"result for: {query}",
                url="https://fake.com/1",
                timestamp="2026-03-01T00:00:00Z",
            )
        ]

    def profile(self, username):
        return {"username": username, "followers": 100}


def test_collector_search():
    c = FakeCollector()
    results = c.search("test query")
    assert len(results) == 1
    assert results[0].platform == "fake"
    assert "test query" in results[0].text


def test_collector_profile():
    c = FakeCollector()
    info = c.profile("testuser")
    assert info["username"] == "testuser"


def test_collector_platform():
    c = FakeCollector()
    assert c.platform == "fake"


def test_abstract_collector_cannot_instantiate():
    with pytest.raises(TypeError):
        Collector()


def test_partial_search_only_cannot_instantiate():
    """A collector implementing only search (not profile) cannot be instantiated."""
    class SearchOnly(Collector):
        platform = "partial"
        def search(self, query, **opts):
            return []
    with pytest.raises(TypeError):
        SearchOnly()


def test_partial_profile_only_cannot_instantiate():
    """A collector implementing only profile (not search) cannot be instantiated."""
    class ProfileOnly(Collector):
        platform = "partial"
        def profile(self, username):
            return {}
    with pytest.raises(TypeError):
        ProfileOnly()
